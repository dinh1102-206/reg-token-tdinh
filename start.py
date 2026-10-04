import os
import sys
# Ensure project root is on sys.path so "import engine" always works
_BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
import os
import sys
import json
import subprocess
import time
try:
    from engine.mullvad import ensure_vpn_for_tool
except Exception:
    def ensure_vpn_for_tool():
        pass
if os.name == "nt":
    os.system("")
P = "\033[38;2;121;3;255m"     
C = "\033[38;2;3;248;252m"     
G = "\033[38;2;68;255;0m"      
Y = "\033[38;2;252;248;3m"     
D = "\033[38;2;92;94;91m"      
W = "\033[97m"                 
RD = "\033[38;2;255;80;80m"    
R = "\033[0m"                  
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
def clear():
    os.system("cls" if os.name == "nt" else "clear")
def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)
def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
def banner():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print(f"""
  {P}┌───────────────────────────────────────────────┐
  │                                               │
  │  ████████╗██████╗ ██╗███╗   ██╗██╗  ██╗       │
  │  ╚══██╔══╝██╔══██╗██║████╗  ██║██║  ██║       │
  │     ██║   ██║  ██║██║██╔██╗ ██║███████║       │
  │     ██║   ██║  ██║██║██║╚██╗██║██╔══██║       │
  │     ██║   ██████╔╝██║██║ ╚████║██║  ██║       │
  │     ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝       │
  │                                               │
  │  {D}tdinh reg{P}                                    │
  │  {D}token generator{P}                               │
  │                                               │
  └───────────────────────────────────────────────┘{R}
""")
def start_checker():
    subprocess.run([sys.executable, "engine/checker.py"], cwd=os.path.dirname(os.path.abspath(__file__)))


def main_menu():
    while True:
        clear()
        banner()
        print(f"  {P}┌───────────────────────────────────────────────┐{R}")
        print(f"  {P}│{R}                                               {P}│{R}")
        print(f"  {P}│{R}   {C}[1]{R}  Start Generator                        {P}│{R}")
        print(f"  {P}│{R}   {C}[2]{R}  Settings                               {P}│{R}")
        print(f"  {P}│{R}   {C}[3]{R}  Proxy Checker                          {P}│{R}")
        print(f"  {P}│{R}   {C}[4]{R}  Setup {D}(Install Dependencies){R}           {P}│{R}")
        print(f"  {P}│{R}   {C}[5]{R}  Token Joiner                          {P}│{R}")
        print(f"  {P}│{R}   {C}[6]{R}  Token Checker                         {P}│{R}")
        print(f"  {P}│{R}   {C}[7]{R}  Token Onliner                         {P}│{R}")
        print(f"  {P}│{R}   {C}[8]{R}  Exit                                  {P}│{R}")
        print(f"  {P}│{R}                                               {P}│{R}")
        print(f"  {P}└───────────────────────────────────────────────┘{R}")
        print()
        choice = input(f"  {P}›{R} Select option: ").strip()
        if choice == "1":   start_generator()
        elif choice == "2": settings_menu()
        elif choice == "3": start_proxy_checker()
        elif choice == "4": setup()
        elif choice == "5": start_joiner()
        elif choice == "6": start_checker()
        elif choice == "7": start_onliner()
        elif choice == "8": sys.exit(0)
def start_proxy_checker():
    clear()
    ensure_vpn_for_tool()
    subprocess.run([sys.executable, "engine/proxy_checker.py"], cwd=BASE_DIR)
def start_joiner():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Token Joiner{R}                              {P}│{R}")
    print(f"  {P}├──────────────────────────────────────────┤{R}")
    print(f"  {P}│{R}                                          {P}│{R}")
    print(f"  {P}│{R}   {C}[1]{R}  Auth Joiner {G}(Recommended){R}          {P}│{R}")
    print(f"  {P}│{R}   {D}     OAuth2 guilds.join - No Captcha{R}   {P}│{R}")
    print(f"  {P}│{R}                                          {P}│{R}")
    print(f"  {P}│{R}   {C}[2]{R}  Link Joiner                        {P}│{R}")
    print(f"  {P}│{R}   {D}     Invite link based joining{R}          {P}│{R}")
    print(f"  {P}│{R}                                          {P}│{R}")
    print(f"  {P}│{R}   {C}[0]{R}  Back                                {P}│{R}")
    print(f"  {P}│{R}                                          {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    choice = input(f"  {P}›{R} Select joiner: ").strip()
    if choice == "1":
        start_auth_joiner()
    elif choice == "2":
        start_link_joiner()

def start_auth_joiner():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Starting Auth Joiner (OAuth2)...{R}          {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    auth_dir = os.path.join(BASE_DIR, "engine", "auth_joiner")
    if not os.path.exists(os.path.join(auth_dir, "src", "index.js")):
        print(f"  {RD}[!] Auth Joiner not found at {auth_dir}{R}")
        print(f"  {Y}›› Press Enter to return...{R}")
        input()
        return
    ensure_vpn_for_tool()
    subprocess.run(["node", "src/index.js"], cwd=auth_dir, shell=True)
    print(f"\n  {Y}›› Auth Joiner stopped. Press Enter to return...{R}")
    input()


def start_link_joiner():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Starting Link Joiner...{R}                   {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    ensure_vpn_for_tool()
    subprocess.run([sys.executable, "engine/joiner.py"], cwd=BASE_DIR)
    print(f"\n  {Y}›› Link Joiner stopped. Press Enter to return...{R}")
    input()

def start_onliner():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Starting Token Onliner...{R}                 {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    ensure_vpn_for_tool()
    subprocess.run([sys.executable, "engine/onliner.py"], cwd=BASE_DIR)
    print(f"\n  {Y}›› Onliner stopped. Press Enter to return...{R}")
    input()

def start_checker():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Starting Token Checker...{R}                 {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    ensure_vpn_for_tool()
    subprocess.run([sys.executable, "engine/checker.py"], cwd=BASE_DIR)
    print(f"\n  {Y}›› Checker stopped. Press Enter to return...{R}")
    input()
def start_generator():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Starting tdinh reg...{R}                        {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    print(f"  {D}›› Launching Token Generator...{R}")
    time.sleep(1)
    ensure_vpn_for_tool()
    print(f"  {G}✓  Generator starting...{R}\n")
    subprocess.run([sys.executable, "main.py"], cwd=BASE_DIR)
    print(f"\n  {Y}›› Generator stopped. Press Enter to return...{R}")
    input()
def settings_menu():
    while True:
        clear()
        cfg = load_config()
        cap_cfg = cfg.get("9captcha", {})
        mail_cfg = cfg.get("mail_services", {})
        verif_cfg = cfg.get("verification", {})
        hz = cfg.get("humanizer", {})
        ext_on = cap_cfg.get("extension_solver", True)
        vps_on = cap_cfg.get("req_solver", False)
        solver_mode = []
        if ext_on: solver_mode.append("Extension")
        if vps_on: solver_mode.append("Req")
        solver_str = " + ".join(solver_mode) if solver_mode else "None (auto)"
        # Find active mail provider
        active_mail = "None"
        for name in ["duckmail", "cybertemp", "tempmail_lol", "hotmail007", "lution", "zeus", "draxono", "mailcow"]:
            svc = mail_cfg.get(name, {})
            if svc.get("enabled", False):
                active_mail = name
                break
        print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
        print(f"  {P}│{R}  {C}tdinh reg Settings{R}                           {P}│{R}")
        print(f"  {P}├──────────────────────────────────────────┤{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}│{R}   {C}[1]{R}  Threads                              {P}│{R}")
        print(f"  {P}│{R}   {C}[2]{R}  9Captcha API Key                    {P}│{R}")
        print(f"  {P}│{R}   {C}[3]{R}  Mail Services                       {P}│{R}")
        print(f"  {P}│{R}   {C}[4]{R}  Verification {D}(on/off){R}               {P}│{R}")
        print(f"  {P}│{R}   {C}[5]{R}  Humanizer {D}(on/off){R}                  {P}│{R}")
        print(f"  {P}│{R}   {C}[s]{R}  Stealth Mode {D}(on/off){R}               {P}│{R}")
        print(f"  {P}│{R}   {C}[b]{R}  Show Browser {D}(on/off){R}               {P}│{R}")
        print(f"  {P}│{R}   {C}[m]{R}  Manual Captcha {D}(on/off){R}             {P}│{R}")
        print(f"  {P}│{R}   {C}[6]{R}  Solver URL {D}(Endpoint){R}              {P}│{R}")
        print(f"  {P}│{R}   {C}[7]{R}  Open config.json in editor          {P}│{R}")
        print(f"  {P}│{R}   {C}[8]{R}  Solver Mode {D}(Ext/Req){R}              {P}│{R}")
        print(f"  {P}│{R}   {C}[9]{R}  Mullvad VPN {D}(mode/account){R}          {P}│{R}")
        print(f"  {P}│{R}   {C}[0]{R}  Back                                {P}│{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}└──────────────────────────────────────────┘{R}\n")
        mv = cfg.get("mullvad", {})
        mv_acct = str(mv.get("account_number", "") or "")
        mv_acct_disp = (mv_acct[:4] + "***" + mv_acct[-4:]) if len(mv_acct) > 8 else (mv_acct or "Not set")
        print(f"  {P}│{R} {D}Current:{R}")
        print(f"  {P}│{R}   Threads:        {W}{cfg.get('threads', 1)}{R}")
        print(f"  {P}│{R}   Solver URL:     {W}{cap_cfg.get('url', 'https://9captcha-api.pridesmp.fun')[:20]}...{R}")
        print(f"  {P}│{R}   9Captcha API:   {W}{cap_cfg.get('api_key', 'Not set')[:8]}...{R}")
        print(f"  {P}│{R}   Mail Provider:  {G}{active_mail}{R}")
        print(f"  {P}│{R}   Verification:   {W}{verif_cfg.get('enabled', True)}{R}")
        print(f"  {P}│{R}   Humanizer:      {W}{hz.get('enabled', False)}{R}")
        print(f"  {P}│{R}   Solver Mode:    {G if ext_on else RD}Ext:{ext_on}{R} | {G if vps_on else RD}Req:{vps_on}{R}  ({solver_str})")
        print(f"  {P}│{R}   Mullvad VPN:    {G if mv.get('enabled') else RD}{mv.get('enabled', False)}{R}  (acct: {W}{mv_acct_disp}{R})")
        print(f"  {P}│{R}   Stealth Mode:   {G if cfg.get('stealth', True) else RD}{cfg.get('stealth', True)}{R}")
        print(f"  {P}│{R}   Show Browser:   {G if cfg.get('show_browser', True) else RD}{cfg.get('show_browser', True)}{R}")
        print(f"  {P}│{R}   Manual Captcha: {G if cap_cfg.get('manual_solve', False) else RD}{cap_cfg.get('manual_solve', False)}{R}")
        print()
        s = input(f"  {P}›{R} Select setting: ").strip().lower()
        if s == "1":
            v = input(f"  {D}›› Thread count: {R}").strip()
            try:
                cfg["threads"] = int(v)
                save_config(cfg)
                print(f"  {G}✓  Threads set to {v}{R}")
            except ValueError:
                print(f"  {Y}!  Invalid number{R}")
            time.sleep(1)
        elif s == "2":
            v = input(f"  {D}›› 9Captcha API key: {R}").strip()
            if "9captcha" not in cfg: cfg["9captcha"] = {}
            cfg["9captcha"]["api_key"] = v
            save_config(cfg)
            print(f"  {G}✓  9Captcha API key updated{R}")
            time.sleep(1)
        elif s == "3":
            mail_services_menu(cfg)
        elif s == "4":
            if "verification" not in cfg: cfg["verification"] = {}
            cfg["verification"]["enabled"] = not cfg["verification"].get("enabled", True)
            save_config(cfg)
            print(f"  {G}✓  Verification set to {cfg['verification']['enabled']}{R}")
            time.sleep(1)
        elif s == "5":
            hz["enabled"] = not hz.get("enabled", False)
            if hz["enabled"]:
                print(f"  {D}  Configure Humanizer options:{R}")
                for key in ["avatar", "bio", "pronouns", "display_name", "hypesquad"]:
                    v = input(f"  {D}››   {key}? (true/false, enter=keep): {R}").strip().lower()
                    if v in ("true", "false"):
                        hz[key] = v == "true"
            cfg["humanizer"] = hz
            save_config(cfg)
            print(f"  {G}✓  Humanizer set to {hz['enabled']}{R}")
            time.sleep(1)
        elif s == "6":
            v = input(f"  {D}›› Solver Endpoint URL: {R}").strip()
            if "9captcha" not in cfg: cfg["9captcha"] = {}
            cfg["9captcha"]["url"] = v
            save_config(cfg)
            print(f"  {G}✓  Solver URL updated{R}")
            time.sleep(1)
        elif s == "7":
            if os.name == "nt":
                os.system(f"notepad {CONFIG_FILE}")
            else:
                os.system(f"nano {CONFIG_FILE}")
        elif s == "8":
            print(f"\n  {P}┌── Solver Mode ──────────────────────────┐{R}")
            print(f"  {P}│{R}  {C}[1]{R}  Use Extension Solver                 {P}│{R}")
            print(f"  {P}│{R}  {C}[2]{R}  Use Request Solver                   {P}│{R}")
            print(f"  {P}│{R}  {C}[0]{R}  Back                                 {P}│{R}")
            print(f"  {P}└──────────────────────────────────────────┘{R}")
            sub = input(f"  {P}›{R} Select: ").strip()
            if "9captcha" not in cfg: cfg["9captcha"] = {}
            if sub == "1":
                cfg["9captcha"]["extension_solver"] = True
                cfg["9captcha"]["req_solver"] = False
                save_config(cfg)
                print(f"  {G}✓  Extension solver enabled (Req disabled){R}")
            elif sub == "2":
                cfg["9captcha"]["extension_solver"] = False
                cfg["9captcha"]["req_solver"] = True
                save_config(cfg)
                print(f"  {G}✓  Request solver enabled (Extension disabled){R}")
            time.sleep(1)
        elif s == "9":
            mullvad_menu(cfg)
        elif s == "s":
            cfg["stealth"] = not cfg.get("stealth", True)
            save_config(cfg)
            print(f"  {G}✓  Stealth Mode set to {cfg['stealth']}{R}")
            time.sleep(1)
        elif s == "b":
            cfg["show_browser"] = not cfg.get("show_browser", True)
            save_config(cfg)
            print(f"  {G}✓  Show Browser set to {cfg['show_browser']}{R}")
            time.sleep(1)
        elif s == "m":
            if "9captcha" not in cfg: cfg["9captcha"] = {}
            new_val = not cfg["9captcha"].get("manual_solve", False)
            cfg["9captcha"]["manual_solve"] = new_val
            if new_val:
                # Manual solving needs the visible extension browser path
                cfg["9captcha"]["extension_solver"] = True
                cfg["9captcha"]["req_solver"] = False
                cfg["show_browser"] = True
            save_config(cfg)
            print(f"  {G}✓  Manual Captcha set to {new_val}{R}")
            if new_val:
                print(f"  {D}   (Extension solver + Show Browser auto-enabled){R}")
            time.sleep(1.5)
        elif s == "0" or s == "":
            return

def mullvad_menu(cfg):
    """Submenu for Mullvad VPN auto-manager settings."""
    while True:
        clear()
        if "mullvad" not in cfg:
            cfg["mullvad"] = {}
        mv = cfg["mullvad"]
        acct = str(mv.get("account_number", "") or "")
        acct_disp = (acct[:4] + "***" + acct[-4:]) if len(acct) > 8 else (acct or "Not set")
        enabled = mv.get("enabled", False)
        print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
        print(f"  {P}│{R}  {C}Mullvad VPN{R}                               {P}│{R}")
        print(f"  {P}├──────────────────────────────────────────┤{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}│{R}   {C}[1]{R}  Mode {D}(on/off){R}        {(G+'ON ' if enabled else RD+'OFF')}{R}          {P}│{R}")
        print(f"  {P}│{R}   {C}[2]{R}  Account Number                      {P}│{R}")
        print(f"  {P}│{R}   {C}[3]{R}  Monitor Interval {D}(sec){R}             {P}│{R}")
        print(f"  {P}│{R}   {C}[4]{R}  Rotate On Cooldown {D}(on/off){R}        {P}│{R}")
        print(f"  {P}│{R}   {C}[0]{R}  Back                                {P}│{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}└──────────────────────────────────────────┘{R}\n")
        print(f"  {P}│{R}   Account:   {W}{acct_disp}{R}")
        print(f"  {P}│{R}   Interval:  {W}{mv.get('monitor_interval', 30)}s{R}")
        print(f"  {P}│{R}   Rotate:    {W}{mv.get('rotate_on_cooldown', True)}{R}")
        print()
        s = input(f"  {P}›{R} Select: ").strip()
        if s == "0" or s == "":
            return
        elif s == "1":
            mv["enabled"] = not mv.get("enabled", False)
            cfg["mullvad"] = mv
            save_config(cfg)
            print(f"  {G}✓  Mullvad VPN mode set to {mv['enabled']}{R}")
            time.sleep(1)
        elif s == "2":
            v = input(f"  {D}›› Mullvad account number: {R}").strip().replace(" ", "")
            mv["account_number"] = v
            cfg["mullvad"] = mv
            save_config(cfg)
            print(f"  {G}✓  Account number updated{R}")
            time.sleep(1)
        elif s == "3":
            v = input(f"  {D}›› Monitor interval (seconds): {R}").strip()
            try:
                mv["monitor_interval"] = max(10, int(v))
                cfg["mullvad"] = mv
                save_config(cfg)
                print(f"  {G}✓  Monitor interval set to {mv['monitor_interval']}s{R}")
            except ValueError:
                print(f"  {Y}!  Invalid number{R}")
            time.sleep(1)
        elif s == "4":
            mv["rotate_on_cooldown"] = not mv.get("rotate_on_cooldown", True)
            cfg["mullvad"] = mv
            save_config(cfg)
            print(f"  {G}✓  Rotate on cooldown set to {mv['rotate_on_cooldown']}{R}")
            time.sleep(1)

def mail_services_menu(cfg):
    """Submenu for managing mail service providers."""
    PROVIDER_NAMES = {
        "duckmail": "DuckMail",
        "cybertemp": "CyberTemp",
        "tempmail_lol": "TempMail.lol",
        "hotmail007": "Hotmail007",
        "lution": "Lution",
        "zeus": "Zeus",
        "draxono": "Draxono",
        "mailcow": "Mailcow",
    }
    PROVIDER_KEY_FIELD = {
        "duckmail": "password",
        "cybertemp": "api_key",
        "tempmail_lol": None,
        "hotmail007": "client_key",
        "lution": "api_key",
        "zeus": "api_key",
        "draxono": "api_key",
        "mailcow": "api_key",
    }
    provider_order = ["duckmail", "cybertemp", "tempmail_lol", "hotmail007", "lution", "zeus", "draxono", "mailcow"]
    while True:
        clear()
        if "mail_services" not in cfg:
            cfg["mail_services"] = {}
        ms = cfg["mail_services"]
        print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
        print(f"  {P}│{R}  {C}Mail Services{R}                             {P}│{R}")
        print(f"  {P}├──────────────────────────────────────────┤{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        for i, name in enumerate(provider_order, 1):
            svc = ms.get(name, {})
            enabled = svc.get("enabled", False)
            status = f"{G}ON{R}" if enabled else f"{RD}OFF{R}"
            label = PROVIDER_NAMES.get(name, name)
            print(f"  {P}│{R}   {C}[{i}]{R}  {label:<14} {status}                  {P}│{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}│{R}   {C}[8]{R}  Set API Key / Password              {P}│{R}")
        print(f"  {P}│{R}   {C}[9]{R}  Set Mailcode / Domain               {P}│{R}")
        print(f"  {P}│{R}   {C}[0]{R}  Back                                {P}│{R}")
        print(f"  {P}│{R}                                          {P}│{R}")
        print(f"  {P}└──────────────────────────────────────────┘{R}\n")
        # Show current key info
        for name in provider_order:
            svc = ms.get(name, {})
            if svc.get("enabled", False):
                key_field = PROVIDER_KEY_FIELD.get(name)
                if key_field:
                    val = svc.get(key_field, "")
                    masked = val[:6] + "***" if len(val) > 6 else val or "Not set"
                    if name == "lution":
                        dom = svc.get("mailcode", "Not set")
                        print(f"  {P}│{R}   {G}{PROVIDER_NAMES[name]}{R}: {D}{key_field}={masked} | mailcode={dom}{R}")
                    else:
                        print(f"  {P}│{R}   {G}{PROVIDER_NAMES[name]}{R}: {D}{key_field}={masked}{R}")
                else:
                    print(f"  {P}│{R}   {G}{PROVIDER_NAMES[name]}{R}: {D}No key needed{R}")
        print()
        s = input(f"  {P}›{R} Select: ").strip()
        if s == "0" or s == "":
            return
        elif s == "8":
            print(f"\n  {D}  Available providers:{R}")
            for i, name in enumerate(provider_order, 1):
                key_field = PROVIDER_KEY_FIELD.get(name)
                print(f"    {C}[{i}]{R} {PROVIDER_NAMES[name]} ({key_field or 'no key'})")
            idx = input(f"\n  {P}›{R} Select provider: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(provider_order):
                    name = provider_order[idx]
                    key_field = PROVIDER_KEY_FIELD.get(name)
                    if key_field:
                        v = input(f"  {D}›› {PROVIDER_NAMES[name]} {key_field}: {R}").strip()
                        if name not in ms: ms[name] = {"enabled": False}
                        ms[name][key_field] = v
                        if name == "lution":
                            mcode = input(f"  {D}›› Lution Mailcode: {R}").strip().lower()
                            if mcode: ms[name]["mailcode"] = mcode
                        cfg["mail_services"] = ms
                        save_config(cfg)
                        print(f"  {G}✓  {PROVIDER_NAMES[name]} {key_field} updated{R}")
                    else:
                        print(f"  {D}  {PROVIDER_NAMES[name]} does not require a key.{R}")
            except (ValueError, IndexError):
                print(f"  {Y}!  Invalid selection{R}")
            time.sleep(1)
        elif s == "9":
            print(f"\n  {D}  Available providers:{R}")
            domain_providers = [p for p in provider_order if p in ("lution", "mailcow")]
            for i, name in enumerate(domain_providers, 1):
                print(f"    {C}[{i}]{R} {PROVIDER_NAMES[name]}")
            idx = input(f"\n  {P}›{R} Select provider: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(domain_providers):
                    name = domain_providers[idx]
                    if name not in ms: ms[name] = {"enabled": False}
                    if name == "lution":
                        mcode = input(f"  {D}›› Lution Mailcode: {R}").strip().lower()
                        if mcode: ms[name]["mailcode"] = mcode
                    elif name == "mailcow":
                        dom = input(f"  {D}›› Mailcow Domain (e.g. yourdomain.com): {R}").strip()
                        ms[name]["domain"] = dom
                    cfg["mail_services"] = ms
                    save_config(cfg)
                    print(f"  {G}✓  {PROVIDER_NAMES[name]} setting updated{R}")
            except (ValueError, IndexError):
                print(f"  {Y}!  Invalid selection{R}")
            time.sleep(1)
        else:
            try:
                idx = int(s) - 1
                if 0 <= idx < len(provider_order):
                    name = provider_order[idx]
                    if name not in ms: ms[name] = {"enabled": False}
                    
                    if name == "lution" and not ms[name].get("mailcode"):
                        print(f"\n  {Y}! Lution Mailcode is missing!{R}")
                        mcode = input(f"  {D}›› Enter Lution Mailcode: {R}").strip().lower()
                        while not mcode:
                            mcode = input(f"  {D}›› Enter Lution Mailcode: {R}").strip().lower()
                        ms[name]["mailcode"] = mcode

                    # Toggle: disable all others, enable this one
                    for n in provider_order:
                        if n in ms:
                            ms[n]["enabled"] = (n == name)
                        elif n == name:
                            ms[n] = {"enabled": True}
                    cfg["mail_services"] = ms
                    save_config(cfg)
                    print(f"  {G}✓  {PROVIDER_NAMES[name]} enabled (others disabled){R}")
                    time.sleep(1)
            except ValueError:
                pass
def setup():
    clear()
    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}tdinh reg Setup{R}                              {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")
    print(f"  {D}›› Installing dependencies...{R}\n")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    os.system(f"pip install -r \"{req_path}\"")
    
    auth_dir = os.path.join(BASE_DIR, "engine", "auth_joiner")
    if os.path.exists(auth_dir):
        print(f"\n  {D}›› Installing Auth Joiner Node modules...{R}\n")
        subprocess.run(["npm", "i"], cwd=auth_dir, shell=True)

    print(f"\n  {G}✓  Setup complete!{R}\n")
    print(f"  {Y}Press Enter to return...{R}")
    input()
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n  {Y}›› Exiting...{R}")
        sys.exit(0)
