import os
import sys
import json
import time
import random
import base64
import threading
import re
import websocket

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from curl_cffi import requests as curl_requests
from main import Solver, ProxyManager, Log, config, _file_log, USER_AGENTS

from engine.bypasses import DetectBypass, OnboardingBypass, BypassRules, RestoreCordBypass

P = "\033[38;2;121;3;255m"
C = "\033[38;2;3;248;252m"
G = "\033[38;2;68;255;0m"
Y = "\033[38;2;252;248;3m"
D = "\033[38;2;92;94;91m"
W = "\033[97m"
RD = "\033[38;2;255;80;80m"
R = "\033[0m"

joiner_lock = threading.Lock()
captcha_lock = threading.Lock()
joiner_stats = {"joined": 0, "failed": 0, "captcha_solved": 0, "invalid": 0}

def build_properties(user_agent: str) -> str:
    version = "127"
    m = re.search(r"Chrome/(\d+)", user_agent)
    if m:
        version = m.group(1)
    props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": user_agent,
        "browser_version": f"{version}.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": 335299,
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()

def build_context(location: str, guild_id, channel_id, type_: str = "0") -> str:
    props = {
        "location": location,
        "location_guild_id": str(guild_id),
        "location_channel_id": str(channel_id),
        "location_channel_type": int(type_) if str(type_).isdigit() else 0,
    }
    return base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()

def build_headers(token: str, user_agent: str, xcaptcha=None, rqtoken=None, rqdata=None, xcontext=None, session_id=None):
    version = "127"
    m = re.search(r"Chrome/(\d+)", user_agent)
    if m:
        version = m.group(1)
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": f'"Not/A)Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": user_agent,
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": build_properties(user_agent),
    }
    if xcaptcha and rqtoken:
        headers["x-captcha-key"] = xcaptcha
        headers["x-captcha-rqtoken"] = rqtoken
        headers["x-captcha-rqdata"] = rqdata or ""
        headers["x-captcha-session-id"] = session_id or ""
    if xcontext:
        headers["x-context-properties"] = xcontext
    return headers

def fetch_session_id(token: str) -> str | None:
    try:
        ws = websocket.WebSocket()
        ws.settimeout(5)
        ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
        hello = json.loads(ws.recv())
        ws.send(json.dumps({
            "op": 2,
            "d": {
                "token": token,
                "capabilities": 16381,
                "properties": {"os": "Windows", "browser": "Chrome", "device": ""},
                "compress": False,
            },
        }))
        ready = json.loads(ws.recv())
        if ready.get("t") == "READY":
            sid = ready["d"].get("session_id")
            ws.close()
            return sid
        ws.close()
    except Exception:
        pass
    return None

def get_xcontext(invite: str, proxy: str | None = None):
    try:
        p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
        client = curl_requests.Session(
            impersonate="chrome120",
            proxies={"http": p_str, "https": p_str} if p_str else None,
        )
        resp = client.get(
            f"https://discord.com/api/v9/invites/{invite}?inputValue={invite}&with_counts=true&with_expiration=true",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return build_context(
                "Join Guild",
                data["guild"]["id"],
                data["channel"]["id"],
                data.get("type", "0"),
            )
    except Exception as e:
        _file_log(f"[JOINER] Context fetch failed: {e}")
    return None

def change_nick(guild_id: str, nick: str, token: str, user_agent: str, proxy: str | None):
    headers = build_headers(token, user_agent)
    p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
    session = curl_requests.Session(impersonate="chrome120", proxies={"http": p_str, "https": p_str} if p_str else None)
    if "{random}" in nick:
        nick = nick.replace("{random}", str(random.randint(1111, 9999)))
    resp = session.patch(
        f"https://discord.com/api/v9/guilds/{guild_id}/members/@me",
        json={"nick": nick},
        headers=headers,
        timeout=10
    )
    if resp.status_code == 200:
        Log._log(f"{G}✓{R}", f"{_censor(token)} → {C}Nickname Set{R}")
    elif resp.status_code == 429:
        Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Nickname ratelimited{R}")

def execute_bypasses(guild_id: str, token: str, user_agent: str, proxy: str):
    import cloudscraper
    cfsession = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "desktop": True})
    detect = DetectBypass(token=token, guildid=guild_id, useragent=user_agent, proxy=proxy, cfsession=cfsession)
    if detect.check_rules():
        BypassRules(token, guild_id, user_agent, proxy).bypass_rules()
    if detect.check_onboarding():
        OnboardingBypass(token, guild_id, user_agent, proxy).bypass_onboarding()
    client_id = detect.check_restorecord()
    if client_id:
        RestoreCordBypass(token, guild_id, client_id, user_agent, proxy, cfsession).bypass()

def join_server(token: str, invite: str, proxy: str | None, user_agent: str, xcontext: str | None, nickname: str | None):
    p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
    session = curl_requests.Session(
        impersonate="chrome120",
        proxies={"http": p_str, "https": p_str} if p_str else None,
    )
    try:
        check_headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        }
        check_resp = session.get("https://discord.com/api/v9/users/@me", headers=check_headers, timeout=10)
        if check_resp.status_code == 401:
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Invalid Token{R}")
            with joiner_lock:
                joiner_stats["invalid"] += 1
            return "invalid"
        elif check_resp.status_code == 403:
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Locked Token{R}")
            with joiner_lock:
                joiner_stats["invalid"] += 1
            return "invalid"
    except Exception as e:
        if "timeout" in str(e).lower() or "read" in str(e).lower():
            Log._log(f"{Y}⚠{R}", f"{_censor(token)} → {Y}Proxy timeout before verify{R}")
            with joiner_lock:
                joiner_stats["failed"] += 1
            return "timeout"

    session_id = fetch_session_id(token)
    if not session_id:
        Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Invalid / Failed to connect{R}")
        with joiner_lock:
            joiner_stats["invalid"] += 1
        return "invalid"

    headers = build_headers(token, user_agent, xcontext=xcontext)
    try:
        resp = session.post(
            f"https://discord.com/api/v9/invites/{invite}",
            json={"session_id": session_id},
            headers=headers,
            timeout=20,
        )
    except Exception as e:
        Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Connection error{R}")
        with joiner_lock:
            joiner_stats["failed"] += 1
        if "timeout" in str(e).lower() or "read" in str(e).lower():
            return "timeout"
        return "failed"
        
    def handle_success(response):
        Log._log(f"{G}✓{R}", f"{_censor(token)} → {G}Joined{R}")
        with joiner_lock:
            joiner_stats["joined"] += 1
        try:
            guild_id = response.json()["guild"]["id"]
            if nickname:
                change_nick(guild_id, nickname, token, user_agent, proxy)
            execute_bypasses(guild_id, token, user_agent, proxy)
        except Exception as e:
            pass

    if resp.status_code == 200:
        handle_success(resp)
        return "joined"

    if "captcha_rqdata" in resp.text:
        Log._log(f"{Y}⏳{R}", f"{_censor(token)} → {Y}Captcha required, solving...{R}")
        try:
            data = resp.json()
            site_key = data["captcha_sitekey"]
            rqdata = data["captcha_rqdata"]
            rqtoken = data["captcha_rqtoken"]
            cap_session = data.get("captcha_session_id", "")
        except Exception:
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Bad captcha response{R}")
            with joiner_lock:
                joiner_stats["failed"] += 1
            return "failed"

        api_key = config.get("9captcha", {}).get("api_key", "")
        start_t = time.time()
        
        with captcha_lock: # lock to prevent multi-captcha rate-limiting
            solver = Solver(
                url="https://discord.com/channels/@me",
                sitekey=site_key,
                rqdata=rqdata,
                user_agent=user_agent,
                proxy=proxy,
                api_key=api_key,
            )
            solution, _ = solver.solve(timeout=90)
            
        if not solution or solution in ("ERROR_RATELIMIT", "ERROR_IP_REJECTED"):
            err = solution or "No solution"
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Captcha failed: {err}{R}")
            with joiner_lock:
                joiner_stats["failed"] += 1
            if not solution: return "timeout"
            return "failed"

        elapsed = time.time() - start_t
        Log._log(f"{C}⚡{R}", f"Captcha solved in {elapsed:.1f}s")
        with joiner_lock:
            joiner_stats["captcha_solved"] += 1

        headers2 = build_headers(
            token, user_agent,
            xcaptcha=solution, rqtoken=rqtoken, rqdata=rqdata,
            xcontext=xcontext, session_id=cap_session,
        )
        try:
            resp2 = session.post(
                f"https://discord.com/api/v9/invites/{invite}",
                json={"session_id": session_id},
                headers=headers2,
                timeout=20,
            )
        except Exception as e:
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Post-captcha connection error{R}")
            with joiner_lock:
                joiner_stats["failed"] += 1
            if "timeout" in str(e).lower() or "read" in str(e).lower():
                return "timeout"
            return "failed"

        if resp2.status_code == 200:
            handle_success(resp2)
            return "joined"
        else:
            try:
                err_body = resp2.json()
                Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Failed: {err_body.get('message', resp2.text)}{R}")
            except Exception:
                Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Failed ({resp2.status_code}) - {resp2.text}{R}")
            with joiner_lock:
                joiner_stats["failed"] += 1
            return "failed"

    if resp.status_code == 401:
        Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Invalid token{R}")
        with joiner_lock:
            joiner_stats["invalid"] += 1
        return "invalid"
    elif resp.status_code == 429:
        Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}Rate limited{R}")
        with joiner_lock:
            joiner_stats["failed"] += 1
        return "failed"
    else:
        try:
            err_body = resp.json()
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}{err_body.get('message', 'Unknown')} ({resp.status_code}){R}")
        except Exception:
            Log._log(f"{RD}✗{R}", f"{_censor(token)} → {RD}HTTP {resp.status_code}{R}")
        with joiner_lock:
            joiner_stats["failed"] += 1
    return "failed"

def _censor(token: str) -> str:
    parts = token.split(".")
    if len(parts) >= 2:
        return f"{parts[0][:8]}...{parts[-1][-4:]}"
    return token[:12] + "..."

def load_tokens(path: str) -> list[str]:
    tokens = []
    if not os.path.exists(path):
        return tokens
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                tokens.append(":".join(parts[2:]))
            else:
                tokens.append(line)
    return tokens

def main():
    if os.name == "nt":
        os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        import keyboard
        def force_exit():
            print(f"\n  {Y}›› Force exiting (Ctrl+X)...{R}")
            import os
            os._exit(0)
        keyboard.add_hotkey('ctrl+x', force_exit)
    except ImportError:
        pass

    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}9DEVS Turbo Joiner{R}                       {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")

    token_path = os.path.join(PROJECT_ROOT, "output", "email_verified.txt")
    tokens = load_tokens(token_path)

    if not tokens:
        print(f"  {RD}✗ No tokens found in output/email_verified.txt{R}")
        print(f"  {D}  Generate tokens first with the 9DEVS Generator.{R}")
        return

    pm_path = os.path.join(PROJECT_ROOT, "input", "proxies.txt")
    total_proxies = 0
    proxy_list = []
    if os.path.exists(pm_path):
        with open(pm_path, "r", encoding="utf-8") as f:
            proxy_list = [l.strip() for l in f if l.strip()]
            total_proxies = len(proxy_list)

    print(f"  {D}│{R} Tokens:    {W}{len(tokens)}{R}")
    print(f"  {D}│{R} Proxies:   {W}{total_proxies}{R}")
    print(f"  {D}│{R} Solver:    {W}{'Extension' if config.get('9captcha', {}).get('extension_solver', True) else 'Request'}{R}")
    print()

    invite_raw = input(f"  {P}›{R} Enter invite (code or URL): ").strip()
    if not invite_raw:
        print(f"  {RD}✗ No invite provided{R}")
        return
        
    nickname = input(f"  {P}›{R} Enter Nickname (leave blank for none): ").strip()
    if not nickname:
        nickname = None
        
    print(f"\n  {P}┌{R} Proxy Modes:")
    print(f"  {P}│{R} 1: Rotating (each request gets random proxy)")
    print(f"  {P}│{R} 2: Sticky (one proxy for all joins)")
    print(f"  {P}│{R} 3: Per-Token (each token gets assigned one proxy)")
    print(f"  {P}│{R} 4: None (no proxies)")
    mode_raw = input(f"  {P}└›{R} Select Proxy Mode (1-4, def 1): ").strip()
    proxy_mode = {"1": "rotating", "2": "sticky", "3": "per-token", "4": "none"}.get(mode_raw, "rotating")
    
    delay_min = 0
    delay_max = 0
    delay_input = input(f"\n  {P}›{R} Enter thread delay (min-max) or 0 for instant: ").strip()
    if delay_input and delay_input != "0":
        try:
            if "-" in delay_input:
                delay_min, delay_max = map(float, delay_input.split("-"))
            else:
                delay_min = delay_max = float(delay_input)
        except:
            pass

    invite = invite_raw
    for prefix in ["https://discord.gg/", "http://discord.gg/", "discord.gg/",
                    "https://discord.com/invite/", "http://discord.com/invite/"]:
        if invite.startswith(prefix):
            invite = invite[len(prefix):]
            break

    user_agent = random.choice(USER_AGENTS)

    print(f"\n  {P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
    print(f"  {D}│{R} Fetching invite context...")
    
    context_proxy = random.choice(proxy_list) if proxy_list else None
    xcontext = get_xcontext(invite, context_proxy)

    if xcontext:
        print(f"  {D}│{R} {G}✓{R} X-Context-Properties loaded")
    else:
        print(f"  {D}│{R} {Y}⚠{R} Context fetch failed — join may get 10008")

    print(f"  {D}│{R} Starting high-speed joiner with {W}{len(tokens)}{R} tokens...\n")

    token_proxies = {}
    if proxy_mode == "per-token":
        for i, t in enumerate(tokens):
            token_proxies[t] = proxy_list[i % len(proxy_list)] if proxy_list else None
    elif proxy_mode == "sticky":
        sticky_proxy = random.choice(proxy_list) if proxy_list else None
        for t in tokens:
            token_proxies[t] = sticky_proxy

    start_time = time.time()
    
    def join_worker(token):
        if proxy_mode == "rotating":
            proxy = random.choice(proxy_list) if proxy_list else None
        elif proxy_mode in ("per-token", "sticky"):
            proxy = token_proxies.get(token)
        else:
            proxy = None
            
        status = join_server(token, invite, proxy, user_agent, xcontext, nickname)
        out_file = None
        if status == "joined":
            out_file = "joined.txt"
        elif status == "timeout":
            out_file = "join_timeout.txt"
        elif status in ("failed", "invalid"):
            out_file = "join_failed.txt"

        if out_file:
            out_dir = os.path.join(PROJECT_ROOT, "output", "joiner")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, out_file)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(token + "\n")
            except Exception:
                pass

    from concurrent.futures import ThreadPoolExecutor, as_completed
    max_threads = min(config.get("threads", 100), len(tokens) if tokens else 1)
    
    # We stagger thread spawning slightly to prevent completely overwhelming network instantly if delay is set
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for token in tokens:
            futures.append(executor.submit(join_worker, token))
            if delay_max > 0:
                time.sleep(random.uniform(delay_min, delay_max))
                
        for future in as_completed(futures):
            pass

    elapsed = time.time() - start_time

    print(f"\n  {P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
    print(f"  {G}✓ Joined       : {joiner_stats['joined']}{R}")
    print(f"  {RD}✗ Failed       : {joiner_stats['failed']}{R}")
    print(f"  {RD}⊘ Invalid      : {joiner_stats['invalid']}{R}")
    print(f"  {C}⚡ Captchas     : {joiner_stats['captcha_solved']}{R}")
    print(f"  {D}  Time         : {elapsed:.1f}s{R}")
    print(f"  {P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
    print(f"\n  {G}✓{R} Output saved to {C}output/joiner/joined.txt{R}, {C}join_timeout.txt{R}, & {C}join_failed.txt{R}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {Y}›› Interrupted{R}")
    input(f"\n  {Y}Press Enter to return...{R}")
