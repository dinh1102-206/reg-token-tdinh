import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
if os.name == "nt":
    os.system("")
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
P = "\033[38;2;121;3;255m"
C = "\033[38;2;3;248;252m"
G = "\033[38;2;68;255;0m"
Y = "\033[38;2;252;248;3m"
D = "\033[38;2;92;94;91m"
W = "\033[97m"
RD = "\033[38;2;255;80;80m"
R = "\033[0m"
DISCORD_API = "https://discord.com/api/v9/experiments"
GENERAL_URL = "https://httpbin.org/ip"
TIMEOUT = 10
MAX_WORKERS = 50
lock = threading.Lock()
results = {"working": [], "blocked": [], "dead": [], "slow": []}
progress = {"done": 0, "total": 0}
def load_proxies(path="input/proxies.txt"):
    if not os.path.exists(path):
        print(f"  {RD}✗ File not found: {path}{R}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return list(dict.fromkeys(proxies))
def mask(proxy):
    if len(proxy) > 35:
        return proxy[:12] + "***" + proxy[-12:]
    return proxy
def test_proxy(proxy):
    
    import primp
    proxy_url = proxy if "://" in proxy else f"http://{proxy}"
    masked = mask(proxy)
    try:
        client = primp.Client(verify=False, proxy=proxy_url)
        start = time.time()
        resp = client.get(GENERAL_URL, timeout=TIMEOUT)
        gen_time = round(time.time() - start, 2)
        if resp.status_code != 200:
            return "dead", masked, 0, 0, "BAD_STATUS"
    except Exception as e:
        err = str(e)[:40]
        if "timeout" in err.lower() or "(28)" in err:
            return "dead", masked, 0, 0, "TIMEOUT"
        return "dead", masked, 0, 0, err[:20]
    try:
        client2 = primp.Client(verify=False, proxy=proxy_url)
        start2 = time.time()
        resp2 = client2.get(DISCORD_API, timeout=TIMEOUT)
        dc_time = round(time.time() - start2, 2)
        if resp2.status_code == 200:
            if dc_time > 5:
                return "slow", masked, gen_time, dc_time, "SLOW"
            return "working", masked, gen_time, dc_time, "OK"
        elif resp2.status_code == 403:
            return "blocked", masked, gen_time, dc_time, "403_BLOCKED"
        else:
            return "blocked", masked, gen_time, dc_time, f"HTTP_{resp2.status_code}"
    except Exception as e:
        err = str(e)[:40]
        if "timeout" in err.lower() or "(28)" in err:
            return "blocked", masked, gen_time, 0, "DC_TIMEOUT"
        return "blocked", masked, gen_time, 0, err[:20]
def check_one(i, proxy, total):
    status, masked, gen_t, dc_t, reason = test_proxy(proxy)
    with lock:
        results[status].append(proxy)
        progress["done"] += 1
        done = progress["done"]
    pct = int(done / total * 100)
    bar_len = 20
    filled = int(bar_len * done / total)
    bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
    if status == "working":
        icon = f"{G}✓{R}"
        detail = f"{G}DC OK{R} {D}({dc_t}s){R}"
    elif status == "slow":
        icon = f"{Y}◐{R}"
        detail = f"{Y}SLOW{R} {D}({dc_t}s){R}"
    elif status == "blocked":
        icon = f"{Y}⚠{R}"
        detail = f"{RD}BLOCKED{R} {D}({reason}){R}"
    else:
        icon = f"{RD}✗{R}"
        detail = f"{RD}DEAD{R} {D}({reason}){R}"
    with lock:
        print(f"  {D}[{bar}]{R} {pct:3d}% {icon} {D}#{i+1:03d}{R} {W}{masked}{R} → {detail}")
    return status
def run_checker():
    proxies = load_proxies()
    if not proxies:
        print(f"  {RD}✗ No proxies found in input/proxies.txt{R}")
        return
    total = len(proxies)
    progress["total"] = total
    progress["done"] = 0
    results["working"].clear()
    results["blocked"].clear()
    results["dead"].clear()
    results["slow"].clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}9DEVS Proxy Checker v4.0{R}                 {P}│{R}")
    print(f"  {P}│{R}  {D}General + Discord Validation{R}             {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}")
    print(f"\n  {D}│{R} Proxies:  {W}{total}{R}")
    print(f"  {D}│{R} Threads:  {W}{MAX_WORKERS}{R}")
    print(f"  {D}│{R} Timeout:  {W}{TIMEOUT}s{R}\n")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futs = {exe.submit(check_one, i, p, total): p for i, p in enumerate(proxies)}
        for f in as_completed(futs):
            try:
                f.result()
            except Exception:
                pass
    elapsed = round(time.time() - start_time, 1)
    w = len(results["working"])
    s = len(results["slow"])
    b = len(results["blocked"])
    d = len(results["dead"])
    print(f"\n  {P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
    print(f"  {G}✓ DC Working  : {w:3d}{R}")
    print(f"  {Y}◐ DC Slow     : {s:3d}{R}  {D}(>5s response){R}")
    print(f"  {RD}⚠ DC Blocked  : {b:3d}{R}  {D}(proxy works, Discord rejects){R}")
    print(f"  {RD}✗ Dead        : {d:3d}{R}")
    print(f"  {D}  Time        : {elapsed}s{R}")
    print(f"  {P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
    good = results["working"] + results["slow"]
    if good:
        with open("input/proxies_dc_working.txt", "w") as f:
            for p in good:
                f.write(p + "\n")
        print(f"\n  {G}✓{R} {W}{len(good)}{R} working proxies → {C}input/proxies_dc_working.txt{R}")
    if results["blocked"]:
        with open("input/proxies_dc_blocked.txt", "w") as f:
            for p in results["blocked"]:
                f.write(p + "\n")
        print(f"  {Y}⚠{R} {W}{b}{R} blocked proxies → {C}input/proxies_dc_blocked.txt{R}")
    if good:
        try:
            choice = input(f"\n  {P}›{R} Replace proxies.txt with working ones? {D}(y/n):{R} ").strip().lower()
            if choice == "y":
                with open("input/proxies.txt", "w") as f:
                    for p in good:
                        f.write(p + "\n")
                print(f"  {G}✓ proxies.txt updated with {len(good)} working proxies{R}")
        except (EOFError, KeyboardInterrupt):
            pass
    elif w == 0 and s == 0:
        print(f"\n  {RD}⚠ CRITICAL: No working proxies found!{R}")
        print(f"  {RD}  Your proxies are either dead or blocked by Discord.{R}")
        print(f"  {RD}  Get fresh residential/mobile proxies before generating.{R}")
    print()
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    run_checker()
    input(f"  {Y}Press Enter to return...{R}")
