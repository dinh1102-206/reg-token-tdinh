import tls_client
import base64
import random
import time
import re
import os
from typing import Optional, Dict, Callable, Tuple, List
from functools import wraps
from datetime import datetime, timezone
P = "\033[38;2;121;3;255m"
C = "\033[38;2;3;248;252m"
G = "\033[38;2;68;255;0m"
Y = "\033[38;2;252;248;3m"
D = "\033[38;2;92;94;91m"
W = "\033[97m"
RD = "\033[38;2;255;80;80m"
R = "\033[0m"
session = tls_client.Session(
    client_identifier="chrome120", random_tls_extension_order=True
)
def print_banner():
    if os.name == "nt":
        os.system("")
    print(f"\n  {P}┌───────────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}                                               {P}│{R}")
    print(f"  {P}│{R}   █████╗ ██████╗ ███████╗██╗   ██╗███████╗    {P}│{R}")
    print(f"  {P}│{R}  ██╔══██╗██╔══██╗██╔════╝██║   ██║██╔════╝    {P}│{R}")
    print(f"  {P}│{R}  ╚██████║██║  ██║█████╗  ██║   ██║███████╗    {P}│{R}")
    print(f"  {P}│{R}   ╚═══██║██║  ██║██╔══╝  ╚██╗ ██╔╝╚════██║    {P}│{R}")
    print(f"  {P}│{R}   █████╔╝██████╔╝███████╗ ╚████╔╝ ███████║    {P}│{R}")
    print(f"  {P}│{R}   ╚════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝    {P}│{R}")
    print(f"  {P}│{R}                                               {P}│{R}")
    print(f"  {P}│{R}  9DEVS Token Checker                          {P}│{R}")
    print(f"  {P}│{R}  Fast · Stealth · Reliable                    {P}│{R}")
    print(f"  {P}│{R}                                               {P}│{R}")
    print(f"  {P}└───────────────────────────────────────────────┘{R}\n")
print_banner()
print(f"  {G}✓{R} Token Checker Started")
print(f"  {Y}››{R} Validating output tokens...\n")
def exit_program():
    input(f"\n  {D}›› Press Enter to return...{R}")
    return
def ensure_directory_structure():
    for d in ["input", "output", "output/token_chkr", "output/token_chkr/categories"]:
        os.makedirs(d, exist_ok=True)
    for f in ["tokens.txt", "proxies.txt"]:
        path = os.path.join("input", f)
        if not os.path.exists(path):
            open(path, "a").close()
ensure_directory_structure()
def strip_ansi(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)
def visual_width(text):
    clean_text = strip_ansi(text)
    emoji_count = len(re.findall(r"[\U0001F000-\U0001FFFF\u2600-\u27BF]", clean_text))
    return len(clean_text) + emoji_count
try:
    proxies_path = (
        "input/proxies.txt" if os.path.exists("input/proxies.txt") else "proxies.txt"
    )
    with open(proxies_path, "r") as f:
        all_proxies = [line.strip() for line in f.readlines() if line.strip()]
        original_proxy_count = len(all_proxies)
        proxies = list(dict.fromkeys(all_proxies))
        if duplicate_count := original_proxy_count - len(proxies):
            print(f"  {D}›› Removed {duplicate_count} duplicate proxies{R}")
except FileNotFoundError:
    print(f"  {Y}›› proxies.txt not found. Running in proxyless mode.{R}")
    proxies = []
except Exception as e:
    print(f"  {RD}✗ Error loading proxies: {e}{R}")
    proxies = []
def format_proxy(proxy_str: str) -> Optional[str]:
    if not proxy_str or proxy_str.isspace():
        return None
    try:
        if "@" in proxy_str:
            auth, address = proxy_str.split("@")
            user, password = auth.split(":", 1)
            ip, port = address.split(":", 1)
            return f"http://{user}:{password}@{ip}:{port}"
        elif proxy_str.count(":") == 3:
            ip, port, user, password = proxy_str.split(":")
            return f"http://{user}:{password}@{ip}:{port}"
        elif proxy_str.count(":") == 1:
            return f"http://{proxy_str}"
        return None
    except Exception:
        return None
def get_random_proxy() -> Optional[str]:
    if not proxies:
        return None
    return random.choice(proxies)
def retry_request(max_retries: int = 3, retry_delay: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            while retries < max_retries:
                try:
                    response = func(*args, **kwargs)
                    if hasattr(response, "status_code") and response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        print(
                            f"{Fore.YELLOW}[RATE LIMITED] Retrying after {retry_after}s ({retries+1}/{max_retries})"
                        )
                        time.sleep(retry_after)
                        retries += 1
                        continue
                    return response
                except Exception as e:
                    last_exception = e
                    retries += 1
                    wait_time = retry_delay * (2 ** (retries - 1))
                    time.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator
def format_token_id(token: str) -> str:
    if token and len(token) > 10:
        return f"{token[:4]}...{token[-4:]}"
    elif token and len(token) > 0:
        return f"{token[:4]}.."
    else:
        return "Unknown***"
@retry_request(max_retries=6, retry_delay=1.0)
def check_token(token: str, proxy: Optional[str] = None) -> Dict:
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    response = session.get(
        "https://discord.com/api/v9/users/@me", headers=headers, proxy=proxy
    )
    if response.status_code == 200:
        user_data = response.json()
        guilds_response = session.get(
            "https://discord.com/api/v9/users/@me/guilds", headers=headers, proxy=proxy
        )
        guilds_count = (
            len(guilds_response.json()) if guilds_response.status_code == 200 else 0
        )
        dm_channels_response = session.get(
            "https://discord.com/api/v9/users/@me/channels", headers=headers, proxy=proxy
        )
        dm_channels_count = (
            len(dm_channels_response.json()) if dm_channels_response.status_code == 200 else 0
        )
        billing_response = session.get(
            "https://discord.com/api/v9/users/@me/billing/payment-sources",
            headers=headers,
            proxy=proxy,
        )
        has_billing = (
            len(billing_response.json()) > 0
            if billing_response.status_code == 200
            else False
        )
        user_id = token.split(".")[0]
        user_id = base64.urlsafe_b64decode(user_id + "==").decode("utf-8")
        try:
            user_id = int(user_id)  
            timestamp = (user_id >> 22) + 1420070400000
            creation_date = datetime.fromtimestamp(timestamp / 1000.0).strftime(
                "%Y-%m-%d"
            )
        except Exception:
            creation_date = "Unknown"
        return {
            "valid": True,
            "username": f"{user_data.get('username')}",
            "email": user_data.get("email", "No Email"),
            "phone": user_data.get("phone", "No Phone"),
            "verified": user_data.get("verified", False),
            "mfa_enabled": user_data.get("mfa_enabled", False),
            "guilds_count": guilds_count,
            "dm_channels_count": dm_channels_count,
            "has_billing": has_billing,
            "creation_date": creation_date,
            "id": user_data.get("id", "Unknown"),
            "nitro": user_data.get("premium_type", 0),
            "token": token,
        }
    else:
        return {
            "valid": False,
            "status_code": response.status_code,
            "error": response.text if hasattr(response, "text") else "Unknown error",
        }
def print_token_status(token_num: str, token_id: str, status: str, details: str):
    print(f"  {D}{token_num:<7}{R} │ {W}{token_id}{R} │ {status:<18}{R} │ {D}{details}{R}")
def save_token_to_category_file(token: str, category: str):
    with open(f"output/token_chkr/categories/{category}.txt", "a") as f:
        f.write(f"{token}\n")
def save_detailed_token_info(token_info: Dict):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("output/token_chkr/detailed_tokens.txt", "a", encoding="utf-8") as f:
        f.write(f"=== Token Details [{timestamp}] ===\n")
        f.write(f"Token: {token_info['token']}\n")
        f.write(f"Username: {token_info['username']}\n")
        f.write(f"User ID: {token_info['id']}\n")
        f.write(f"Email: {token_info['email']}\n")
        f.write(f"Phone: {token_info['phone']}\n")
        f.write(f"Creation Date: {token_info['creation_date']}\n")
        f.write(f"Servers: {token_info['guilds_count']}\n")
        f.write(f"DM Channels: {token_info['dm_channels_count']}\n")
        f.write(f"Verified: {token_info['verified']}\n")
        f.write(f"MFA Enabled: {token_info['mfa_enabled']}\n")
        f.write(f"Has Billing: {token_info['has_billing']}\n")
        f.write(f"Nitro Type: {token_info['nitro']}\n")
        f.write("=" * 50 + "\n\n")
    token = token_info["token"]
    if token_info["verified"]:
        save_token_to_category_file(token, "email_verified")
    if token_info["phone"] and token_info["phone"] != "No Phone":
        save_token_to_category_file(token, "phone_verified")
    if token_info["mfa_enabled"]:
        save_token_to_category_file(token, "2fa")
    if token_info["has_billing"]:
        save_token_to_category_file(token, "billing")
    if token_info["nitro"] > 0:
        save_token_to_category_file(token, "nitro")
    try:
        creation_year = token_info["creation_date"].split("-")[0]
        if (
            creation_year.isdigit()
            and 2012 <= int(creation_year) <= datetime.now().year
        ):
            save_token_to_category_file(token, creation_year)
    except:
        pass
    save_token_to_category_file(token, "unlocked")
def process_token_result(
    token: str, result: Dict, token_id: str
) -> Tuple[str, str, bool]:
    if result["valid"]:
        status = f"{G}✓ VALID       "
        nitro_info = f" | Nitro: Yes" if result["nitro"] > 0 else ""
        creation_year = (
            result["creation_date"].split("-")[0]
            if "-" in result["creation_date"]
            else result["creation_date"]
        )
        details = f"{result['username']} | Servers: {result['guilds_count']} | DMs: {result['dm_channels_count']} | {creation_year}{nitro_info}"
        if result["has_billing"]:
            details += " | Has Billing"
        with open("output/token_chkr/valid_tokens.txt", "a") as f:
            f.write(f"{token}\n")
        save_detailed_token_info(result)
        return status, details, True
    else:
        if result.get("status_code") == 401:
            status = f"{RD}✗ INVALID     "
            details = "Invalid token"
        elif result.get("status_code") == 403:
            status = f"{RD}⊘ LOCKED      "
            details = "Token locked"
            save_token_to_category_file(token, "locked")
        elif result.get("status_code") == 429:
            status = f"{Y}⚡ RATELIMIT   "
            details = "Rate limited"
        else:
            status = f"{RD}✗ ERROR       "
            details = f"Status: {result.get('status_code', 'Unknown')}"
        with open("output/token_chkr/invalid_tokens.txt", "a") as f:
            f.write(f"{token}\n")
            return status, details, False
def is_proxy_error(error):
    return any(x in str(error).lower() for x in ["timeout", "refused", "connection", "proxy", "socket", "eoferror"])
def check_token_with_proxy_fallback(
    token: str,
    initial_proxy: Optional[str],
    use_proxies: bool,
    max_proxy_attempts: int = 3,
) -> Dict:
    proxy_attempts = 0
    tried_proxies = set()
    if initial_proxy:
        tried_proxies.add(initial_proxy)
    current_proxy = initial_proxy
    while proxy_attempts < max_proxy_attempts:
        try:
            result = check_token(token, current_proxy)
            return result
        except Exception as e:
            if (
                use_proxies
                and proxies
                and is_proxy_error(e)
                and proxy_attempts < max_proxy_attempts - 1
            ):
                proxy_attempts += 1
                available_proxies = [
                    p for p in proxies if format_proxy(p) not in tried_proxies
                ]
                if not available_proxies and proxies:
                    available_proxies = proxies
                if available_proxies:
                    new_proxy = format_proxy(random.choice(available_proxies))
                    tried_proxies.add(new_proxy)
                    current_proxy = new_proxy
                    continue
            raise
def setup_token_checking(
    tokens: List[str], use_proxies: bool, parallel_mode: bool = False, threads: int = 1
) -> None:
    print(f"\n  {P}┌───────────────────────────────────────────────┐{R}")
    if parallel_mode:
        print(f"  {D}›› Checking {len(tokens)} tokens using {threads} threads{R}")
    else:
        print(f"  {D}›› Checking {len(tokens)} tokens{R}")
    print(f"  {D}›› {'Using proxies' if use_proxies else 'Running in proxyless mode'}{R}")
    print(f"  {P}└───────────────────────────────────────────────┘{R}\n")
def check_tokens_sequential(tokens: List[str], use_proxies: bool):
    valid_count = 0
    invalid_count = 0
    setup_token_checking(tokens, use_proxies)
    for i, token in enumerate(tokens):
        token_id = format_token_id(token)
        proxy = format_proxy(get_random_proxy()) if use_proxies and proxies else None
        token_num = f"{i+1}/{len(tokens)}"
        try:
            result = check_token_with_proxy_fallback(token, proxy, use_proxies)
            status, details, is_valid = process_token_result(token, result, token_id)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
        except Exception as e:
            invalid_count += 1
            if use_proxies and is_proxy_error(e):
                status = f"{Y}⚠️ PROXY ERR   "
                details = "Connection failed, token status unknown"
            else:
                status = f"{RD}✗ ERROR       "
                details = f"Error: {type(e).__name__}"
            with open("output/token_chkr/invalid_tokens.txt", "a") as f:
                f.write(f"{token}\n")
        print_token_status(token_num, token_id, status, details)
        time.sleep(0.5)
    print(
        f"\n  {G}✓{R} Checking complete: {C}{valid_count} valid{R} | {RD}{invalid_count} invalid{R}"
    )
def check_tokens_parallel(tokens: List[str], use_proxies: bool, num_threads: int):
    import threading
    from queue import Queue
    valid_count = 0
    invalid_count = 0
    lock = threading.Lock()
    token_queue = Queue()
    display_counter = 0  
    for token in tokens:
        token_queue.put(token)
    setup_token_checking(tokens, use_proxies, True, num_threads)
    def worker():
        nonlocal valid_count, invalid_count, display_counter
        while True:
            with lock:
                if token_queue.empty():
                    break
                token = token_queue.get(block=False)
            token_id = format_token_id(token)
            proxy = (
                format_proxy(get_random_proxy()) if use_proxies and proxies else None
            )
            try:
                result = check_token_with_proxy_fallback(token, proxy, use_proxies)
                status, details, is_valid = process_token_result(
                    token, result, token_id
                )
                with lock:
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                    display_counter += 1 
                    print_token_status(
                        f"{display_counter}/{len(tokens)}", token_id, status, details
                    )
            except Exception as e:
                with lock:
                    invalid_count += 1
                    if use_proxies and is_proxy_error(e):
                        status = f"{Y}⚠️ PROXY ERR   "
                        details = "Connection failed, token status unknown"
                    else:
                        status = f"{RD}✗ ERROR       "
                        details = f"Error: {type(e).__name__}"
                    with open("output/token_chkr/invalid_tokens.txt", "a") as f:
                        f.write(f"{token}\n")
                    display_counter += 1 
                    print_token_status(
                        f"{display_counter}/{len(tokens)}", token_id, status, details
                    )
            time.sleep(0.1)
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker)
        t.daemon = True
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print(
        f"\n  {G}✓{R} Checking complete: {C}{valid_count} valid{R} | {RD}{invalid_count} invalid{R}"
    )
def main():
    if os.name == "nt":
        os.system("")
    try:
        for file_path in [
            "output/token_chkr/valid_tokens.txt",
            "output/token_chkr/invalid_tokens.txt",
            "output/token_chkr/detailed_tokens.txt",
        ]:
            try:
                open(file_path, "w").close()
            except:
                pass
        tokens_path = "output/email_verified.txt"
        if not os.path.exists(tokens_path):
            tokens_path = "output/tokens.txt"
        with open(tokens_path, "r", encoding="utf-8") as f:
            all_lines = [line.strip() for line in f.readlines() if line.strip()]
            all_tokens = []
            for line in all_lines:
                parts = line.split(":")
                if len(parts) >= 3:
                    all_tokens.append(":".join(parts[2:]))
                else:
                    all_tokens.append(line)
            tokens = list(dict.fromkeys(all_tokens))
            if not tokens:
                print(f"  {RD}✗ No tokens found in output{R}")
                return exit_program()
            print(f"  {G}✓{R} Loaded {C}{len(tokens)}{R} tokens from {D}{tokens_path}{R}")
        use_proxies = False
        if proxies:
            use_proxies = True
            print(f"  {G}✓{R} Using {C}{len(proxies)}{R} proxies")
        else:
            print(f"  {Y}›› No proxies found, running in proxyless mode{R}")
        use_parallel = True
        num_threads = min(10, len(tokens))
        print(f"  {G}✓{R} Starting turbo mode with {num_threads} threads")
        check_tokens_parallel(tokens, use_proxies, num_threads)
        print(f"\n  {G}✓{R} Results saved to {C}output/token_chkr/{R}")
    except Exception as e:
        print(f"  {RD}✗ An error occurred: {e}{R}")
    return exit_program()
if __name__ == "__main__":
    main()
