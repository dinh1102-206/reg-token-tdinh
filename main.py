import os
import sys
_BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
import primp
from colorama import Fore, Style
from PIL import Image
import asyncio
import websockets
from python_socks.async_.asyncio import Proxy
import requests
from stealth_requests import StealthSession
import base64
import json
import os
import platform
import random
import re
import string
import threading
import time
import uuid
import websocket
import ctypes
import sys
import imaplib
import email
from datetime import datetime
from urllib.parse import urlparse
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

P = "\033[38;2;121;3;255m"     
C = "\033[38;2;3;248;252m"     
G = "\033[38;2;68;255;0m"      
D = "\033[38;2;92;94;91m"      
R = "\033[0m"                  
class DEVSMailApi:
    BASE_URL = "https://api.cybertemp.xyz"
    def __init__(self, logger=None, forced_domain: str = None, api_key: str = None):
        self.created_emails = {}
        self.logger = logger
        self.forced_domain = forced_domain
        self.api_key = (api_key or os.getenv("CYBERTEMP_API_KEY", "")).strip()
        if not self.api_key:
            self.api_key = self._read_api_key_from_config()
        self.headers = {"X-API-KEY": self.api_key} if self.api_key else {}
    def _build_proxies(self, proxy: str = None):
        if proxy and "://" not in proxy:
            proxy = f"http://{proxy}"
        return {"http": proxy, "https": proxy} if proxy else None
    def _log(self, message: str):
        pass
    def _read_api_key_from_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return (cfg.get("devs_mail", {}).get("api_key") or "").strip()
        except Exception:
            return ""
    def get_domains(self):
        try:
            resp = requests.get(f"{self.BASE_URL}/getDomains", params={"type": "discord"}, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "domains" in data:
                    domains_list = data["domains"]
                elif isinstance(data, list):
                    domains_list = data
                else:
                    return []
                return [d.get("domain", d) if isinstance(d, dict) else d for d in domains_list]
        except:
            pass
        return []
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if email and '@' in email:
            created_email = email
        elif self.forced_domain:
            local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{local}@{self.forced_domain}"
        else:
            domains = self.get_domains()
            if not domains:
                domains = ["randommail.com"] 
            target_domain = random.choice(domains)
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{username}@{target_domain}"
        if not created_email:
            self._log("DEVSMail could not create an email")
            return None
        self.created_emails[created_email] = password or ""
        self._log(f"Prepared email: {created_email}")
        return created_email
    def get_verify_url(self, email: str, poll_interval: int = 3, timeout: int = 120, proxy: str = None):
        start_time = time.time()
        used_message_ids = set()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.BASE_URL}/getMail", params={"email": email}, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    messages = resp.json()
                    if isinstance(messages, list) and messages:
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id in used_message_ids:
                                continue
                            subject = msg.get("subject", "")
                            if "discord" in subject.lower() or "verify" in subject.lower() or "verif" in subject.lower():
                                html_body = msg.get("html", "") or msg.get("text", "") or ""
                                text_body = msg.get("text", "") or ""
                                combined = html_body + text_body
                                all_links = re.findall(r'https?://[^\s"\'<>]+', combined)
                                target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l and "blog." not in l]
                                if target_links:
                                    url = None
                                    if len(target_links) >= 2:
                                        second_url = target_links[1]
                                        if "verify" in second_url.lower() or "token=" in second_url.lower() or "click.discord.com" in second_url:
                                            url = second_url
                                    if not url:
                                        url = max(target_links, key=len)
                                    if "click.discord.com" in url:
                                        resolved = self._resolve_url(url, proxy=proxy)
                                        if resolved:
                                            return resolved
                                    return url
                                used_message_ids.add(msg_id)
            except Exception as e:
                self._log(f"Error reading inbox: {e}")
            time.sleep(poll_interval)
        self._log(f"Timeout waiting for verify URL in {email}")
        return None
    def _resolve_url(self, url: str, proxy: str = None) -> str:
        proxies = self._build_proxies(proxy)
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, proxies=proxies)
            final_url = resp.url
            if "discord.com/verify" in final_url:
                return final_url
        except Exception:
            pass
        return None
    def get_email_change_code(self, email: str, poll_interval: int = 3, timeout: int = 180, proxy: str = None, logger=None):
        """Poll the cybertemp inbox for Discord's email-change verification CODE
        (sent to the account's *current* address when changing a verified email).

        Returns the numeric code string, or None on timeout. If a Discord message
        arrives but no code can be parsed, the raw body is logged so the pattern
        can be tuned against a real sample."""
        def _emit(msg):
            if logger:
                try: logger(msg)
                except Exception: pass
        start_time = time.time()
        seen_ids = set()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.BASE_URL}/getMail", params={"email": email}, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    messages = resp.json()
                    if isinstance(messages, list) and messages:
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id in seen_ids:
                                continue
                            seen_ids.add(msg_id)
                            subject = (msg.get("subject", "") or "").lower()
                            sender = (msg.get("from", "") or msg.get("sender", "") or "").lower()
                            if not ("discord" in subject or "discord" in sender or "verif" in subject or "email" in subject or "code" in subject):
                                continue
                            body = (msg.get("text", "") or "") + " " + (msg.get("html", "") or "")
                            code = self._extract_change_code(body)
                            if code:
                                return code
                            _emit(f"[cybertemp] Discord mail received but no code parsed — raw body:\n{body[:800]}")
            except Exception as e:
                _emit(f"[cybertemp] inbox read error: {e}")
            time.sleep(poll_interval)
        return None
    @staticmethod
    def _extract_change_code(body: str):
        """Pull a Discord email-change verification code out of an email body.
        Discord sends a short numeric code (currently 6 digits); we accept 5-8
        digits and prefer a code that sits next to the word 'code'."""
        if not body:
            return None
        text = re.sub(r"<[^>]+>", " ", body)            # strip HTML tags
        text = text.replace("&nbsp;", " ").replace("​", "")
        # Prefer a code that appears right after the word "code"
        labelled = re.search(r"code[^0-9]{0,20}(\d[\d\s\-]{4,9}\d)", text, re.IGNORECASE)
        if labelled:
            digits = re.sub(r"\D", "", labelled.group(1))
            if 5 <= len(digits) <= 8:
                return digits
        # Otherwise fall back to the first standalone 5-8 digit run
        m = re.search(r"(?<!\d)(\d{5,8})(?!\d)", text)
        if m:
            return m.group(1)
        return None
class DuckMailAPI:
    BASE_URL = "https://api.duckmail.sbs"
    def __init__(self, password: str = ""):
        self.password = password or ''.join(random.choices(string.ascii_letters + string.digits, k=14))
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})
        self._bearer = None
        self._email = None
    def _domain(self) -> str:
        try:
            r = self.s.get(f"{self.BASE_URL}/domains", timeout=10)
            if r.status_code == 200:
                for m in r.json().get("hydra:member", []):
                    if m.get("ownerId") is None:
                        return m["domain"]
        except:
            pass
        return "duckmail.sbs"
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        domain = self._domain()
        addr = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@{domain}"
        pw = self.password
        r = self.s.post(f"{self.BASE_URL}/accounts", json={"address": addr, "password": pw, "expiresIn": 0}, timeout=10)
        if r.status_code != 201:
            return None
        token_r = self.s.post(f"{self.BASE_URL}/token", json={"address": addr, "password": pw}, timeout=10)
        if token_r.status_code != 200:
            return None
        self._bearer = token_r.json().get("token")
        self._email = addr
        return addr
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._bearer:
            return None
        headers = {"Authorization": f"Bearer {self._bearer}"}
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = self.s.get(f"{self.BASE_URL}/messages", headers=headers, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("hydra:member", []):
                        subj = (msg.get("subject", "") or "").lower()
                        sender = (msg.get("from", {}) or {}).get("address", "").lower()
                        if "verify" in subj or "discord" in sender or "noreply@discord" in sender:
                            detail = self.s.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers, timeout=10).json()
                            body = detail.get("text", "") or " ".join(detail.get("html", ""))
                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+',
                                        r'https://discord\.com/verify\?token=[^\s"\'<>]+',
                                        r'https://click\.discord\.com/[^\s"\'<>]+']:
                                m = re.search(pat, body, re.IGNORECASE)
                                if m:
                                    link = m.group(0).replace("&amp;", "&")
                                    self.s.delete(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers)
                                    return link
            except:
                pass
            time.sleep(poll_interval)
        return None

class TempMailLolAPI:
    BASE_URL = "https://api.tempmail.lol"
    def __init__(self):
        self._token = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/generate", timeout=10)
            if r.status_code == 200:
                data = r.json()
                self._token = data.get("token", "")
                return data.get("address", "")
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._token:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(f"{self.BASE_URL}/auth/{self._token}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for msg in data.get("email", []):
                        subject = msg.get("subject", "")
                        body = msg.get("body", "") or msg.get("html", "")
                        if "discord" in subject.lower() or "verify" in subject.lower():
                            all_links = re.findall(r'https?://[^\s"\'<>]+', body)
                            target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l]
                            if target_links:
                                return max(target_links, key=len)
            except:
                pass
            time.sleep(poll_interval)
        return None

class Hotmail007API:
    BASE_URL = "https://api.hotmail007.com"
    def __init__(self, client_key: str = ""):
        self.client_key = client_key
        self._email_data = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.client_key:
            return None
        for mail_type in ["outlook", "hotmail"]:
            try:
                r = requests.get(f"{self.BASE_URL}/api/mail/getMail",
                    params={"clientKey": self.client_key, "mailType": mail_type, "quantity": 1}, timeout=15, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("code") == 0 and data.get("data"):
                        parts = data["data"][0].split(":")
                        if len(parts) >= 2:
                            self._email_data = {"email": parts[0], "password": parts[1]}
                            return parts[0]
            except:
                pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None

class ZeusProvider:
    BASE_URL = "https://api.zeus-x.ru"
    def __init__(self, api_key: str = "", mail_type: str = "new"):
        self.api_key = api_key
        self.account_codes = ["HOTMAIL_TRUSTED_GRAPH_API", "OUTLOOK_TRUSTED_GRAPH_API"] if mail_type == "uhq" else ["HOTMAIL", "OUTLOOK"]
        self._email_data = None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            return None
        for code in self.account_codes:
            try:
                r = requests.get(f"{self.BASE_URL}/purchase",
                    params={"apikey": self.api_key, "accountcode": code, "quantity": 1}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("Code") == 0 and data.get("Data"):
                        accounts = data["Data"].get("Accounts", [])
                        if accounts:
                            item = accounts[0]
                            self._email_data = {
                                "email": item.get("Email", ""), 
                                "password": item.get("Password", ""),
                                "token": item.get("RefreshToken", ""),
                                "uuid": item.get("ClientId", "")
                            }
                            return item.get("Email", "")
            except:
                pass
        return None
        
    def get_access_token(self, refresh_token: str, client_id: str = None) -> str:
        try:
            cid = client_id or "d8fbe69d-15be-43fa-b204-5c5bc5a73ad7"
            if refresh_token.endswith("$"): 
                refresh_token = refresh_token[:-1]
            response = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": cid,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=30, verify=False,
            )
            return response.json().get("access_token")
        except:
            return None

    def get_verify_url(self, email_str: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._email_data:
            return None
            
        refresh_token = self._email_data.get("token", "")
        client_id = self._email_data.get("uuid", "")
        
        if refresh_token:
            access_token = self.get_access_token(refresh_token, client_id)
            if access_token:
                session = requests.Session()
                start_time = time.time()
                while time.time() - start_time < timeout:
                    for folder in ["inbox", "junkemail"]:
                        try:
                            response = session.get(
                                f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages",
                                headers={"Authorization": f"Bearer {access_token}"},
                                params={"$top": 10, "$orderby": "receivedDateTime desc", "$select": "subject,body,from"},
                                timeout=15, verify=False,
                            )
                            if response.status_code == 200:
                                emails = response.json().get("value", [])
                                for eml in emails:
                                    subject = eml.get("subject", "").lower()
                                    from_addr = eml.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                                    is_verify = ("verify" in subject or "confirm" in subject or "email" in subject) and ("discord" in from_addr or "noreply@discord.com" in from_addr)
                                    if is_verify:
                                        body_html = eml.get("body", {}).get("content", "")
                                        direct_match = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', body_html)
                                        if direct_match:
                                            return direct_match.group(0).replace("&amp;", "&")
                                        for pat in [r'https://click\.discord\.com/ls/click\?[^"\'\>\s]+', r'https://links\.discord\.com[^"\'\>\s]+']:
                                            for m in re.finditer(pat, body_html):
                                                url = m.group(0).replace("&amp;", "&")
                                                try:
                                                    r2 = session.get(url, allow_redirects=True, verify=False, timeout=10)
                                                    if "discord.com/verify" in r2.url:
                                                        return r2.url
                                                    found = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', r2.text)
                                                    if found:
                                                        return found.group(0).replace("&amp;", "&")
                                                except:
                                                    pass
                        except Exception:
                            pass
                    time.sleep(poll_interval)
                return None
                
        # Fallback to standard IMAP if no refresh token
        password = self._email_data.get("password")
        if not password:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout / 2: # Give it limited time for fallback
            try:
                mail = imaplib.IMAP4_SSL('outlook.office365.com')
                mail.login(email_str, password)
                for folder in ['inbox', 'Junk', '"Junk Email"']:
                    try:
                        status, count = mail.select(folder)
                        if status != 'OK': continue
                        status, messages = mail.search(None, '(ALL)')
                        if status == 'OK' and messages[0]:
                            for num in reversed(messages[0].split()):
                                res, msg_data = mail.fetch(num, '(RFC822)')
                                if res == 'OK':
                                    msg = email.message_from_bytes(msg_data[0][1])
                                    subject = str(msg.get("Subject", "")).lower()
                                    from_addr = str(msg.get("From", "")).lower()
                                    if "discord" in subject or "verify" in subject or "discord" in from_addr:
                                        body = ""
                                        if msg.is_multipart():
                                            for part in msg.walk():
                                                if part.get_content_type() in ["text/plain", "text/html"]:
                                                    try: body += part.get_payload(decode=True).decode(errors='ignore')
                                                    except: pass
                                        else:
                                            try: body = msg.get_payload(decode=True).decode(errors='ignore')
                                            except: pass
                                        if body:
                                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+', r'https://discord\.com/verify\?token=[^\s"\'<>]+', r'https://click\.discord\.com/[^\s"\'<>]+']:
                                                m = re.search(pat, body, re.IGNORECASE)
                                                if m: return m.group(0).replace("&amp;", "&")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[IMAP LOGIN FAILED] {e}", flush=True)
            time.sleep(poll_interval)
        return None

class DraxonoAPI:
    BASE_URL = "https://mail.draxono.in/api"
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key else {}
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/domains", headers=self.headers, timeout=10, verify=False)
            if r.status_code == 200:
                domains = r.json()
                if isinstance(domains, list) and domains:
                    domain = random.choice(domains)
                    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                    return f"{local}@{domain}"
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None


# =============================================================================
# ADB IP ROTATOR  (identical to req2.py)
# =============================================================================
class ADBRotator:
    def __init__(self):
        self.enabled = False
        self._fail_count = 0
        self._MAX_FAILS  = 5
        self._serial     = None
        self._airplane_fallback = False

    def _adb(self, *args, timeout: int = 10):
        import subprocess as _sp
        cmd = ['adb']
        if self._serial:
            cmd.extend(['-s', self._serial])
        cmd.extend(args)
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode == 0, r.stdout.strip()
        except Exception:
            return False, ''

    def is_device_connected(self) -> bool:
        import subprocess as _sp
        try:
            r = _sp.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
            for line in r.stdout.strip().splitlines()[1:]:
                if 'device' in line and 'offline' not in line:
                    if not self._serial:
                        self._serial = line.split()[0]
                    return True
        except Exception:
            pass
        return False

    def _get_external_ip(self):
        for url in ('https://api.ipify.org', 'https://ifconfig.me/ip'):
            try:
                r = requests.get(url, timeout=6)
                if r.status_code == 200 and r.text.strip():
                    return r.text.strip()
            except Exception:
                continue
        return None

    def _wait_for_interface(self, timeout: int = 15) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            ok, out = self._adb('shell', 'ip', 'route', 'get', '8.8.8.8')
            if ok and 'src' in out:
                return True
            time.sleep(1)
        return False

    def _data_off(self) -> bool:
        if self._airplane_fallback:
            ok, _ = self._adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable')
            return ok
        ok, _ = self._adb('shell', 'svc', 'data', 'disable')
        if not ok:
            self._airplane_fallback = True
            return self._data_off()
        return ok

    def _data_on(self) -> bool:
        if self._airplane_fallback:
            ok, _ = self._adb('shell', 'cmd', 'connectivity', 'airplane-mode', 'disable')
            return ok
        ok, _ = self._adb('shell', 'svc', 'data', 'enable')
        if not ok:
            self._airplane_fallback = True
            return self._data_on()
        return ok

    def rotate(self) -> bool:
        if not self.enabled:
            return False
        if not self.is_device_connected():
            log.warning('[ADB] Device not connected — cannot rotate')
            return False
        old_ip = self._get_external_ip() or 'unknown'
        log.adb(f'[ADB] Rotating IP (current: {old_ip})')
        self._data_off()
        time.sleep(4)
        self._data_on()
        time.sleep(2)
        self._wait_for_interface(timeout=20)
        for _ in range(20):
            time.sleep(2)
            new_ip = self._get_external_ip()
            if new_ip and new_ip != old_ip:
                log.adb(f'[ADB] New IP: {new_ip}')
                self._fail_count = 0
                return True
        self._fail_count += 1
        log.warning(f'[ADB] IP unchanged (attempt {self._fail_count}/{self._MAX_FAILS})')
        if self._fail_count >= self._MAX_FAILS:
            self.enabled = False
            log.error('[ADB] Sticky IP — ADB rotation DISABLED')
        return False


adb_rotator = ADBRotator()

# Mullvad VPN relay rotator — rotates the exit location between accounts so the
# external IP changes per generation even without ADB. The Mullvad CLI drives a
# system-wide daemon, so this affects the same tunnel start.py brought up.
# No-op unless mullvad.enabled + mullvad.rotate_on_cooldown are set in config.json.
try:
    from engine.mullvad import get_manager as _get_mullvad_manager
    mullvad_mgr = _get_mullvad_manager()
except Exception:
    mullvad_mgr = None


def _mullvad_should_rotate() -> bool:
    return bool(mullvad_mgr and mullvad_mgr.enabled and mullvad_mgr.rotate_on_cooldown)


def _mullvad_rotate():
    """Rotate the Mullvad relay location + reconnect. Safe to call standalone."""
    try:
        if _mullvad_should_rotate():
            mullvad_mgr.rotate_location(reconnect=True)
    except Exception as exc:
        log.warning(f'[MULLVAD] relay rotation failed: {exc}')

# Lock for generated_mails.txt writes
_GENERATED_MAILS_LOCK = threading.Lock()
_GENERATED_MAILS_PATH = Path(__file__).resolve().parent / 'output' / 'generated_mails.txt'

def _save_generated_mail(email: str, password: str):
    """Append cowmail email:password to output/generated_mails.txt."""
    try:
        _GENERATED_MAILS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _GENERATED_MAILS_LOCK:
            with open(_GENERATED_MAILS_PATH, 'a', encoding='utf-8') as fh:
                fh.write(f'{email}:{password}\n')
    except Exception:
        pass


class MailcowProvider:
    def __init__(self, mc_config: dict):
        self.config = mc_config
        # Support both "api_base" (full URL) and legacy "host" field
        api_base = mc_config.get("api_base", "").rstrip("/")
        host = mc_config.get("host", "").rstrip("/")
        if api_base:
            self.base_url = api_base
        elif host:
            self.base_url = host if host.startswith("http") else f"https://{host}"
        else:
            self.base_url = ""
        self.api_key = mc_config.get("api_key", "")
        self.imap_host = mc_config.get("imap_host", host.replace("https://", "").replace("http://", "") if host else "")
        self.imap_port = int(mc_config.get("imap_port", 993))
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self._created_email = None
        self._created_password = None

    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.base_url or not self.api_key:
            return None
        domain = self.config.get('domain', '')
        if not domain:
            return None
        for attempt in range(3):
            try:
                local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                addr  = f'{local}@{domain}'
                pw    = password or ''.join(random.choices(string.ascii_letters + string.digits, k=14))
                data  = {
                    'active':     '1',
                    'domain':     domain,
                    'local_part': local,
                    'name':       local,
                    'password':   pw,
                    'password2':  pw,
                    'quota':      '10',   # exact server per-mailbox cap; lower values timeout
                }
                r = requests.post(
                    f'{self.base_url}/add/mailbox',
                    json=data,
                    headers=self.headers,
                    timeout=25,
                    verify=False,
                )
                if r.status_code in (200, 201):
                    body = r.text.strip()
                    # Empty body on 200 = success (server quirk)
                    if not body:
                        self._created_email    = addr
                        self._created_password = pw
                        self._email_data       = {'password': pw}
                        _save_generated_mail(addr, pw)
                        return addr
                    resp_json = r.json()
                    if isinstance(resp_json, list):
                        if any(item.get('type') == 'success' for item in resp_json):
                            self._created_email    = addr
                            self._created_password = pw
                            self._email_data       = {'password': pw}
                            _save_generated_mail(addr, pw)
                            return addr
                        # Log the failure reason but keep retrying
                        err = resp_json[0].get('msg', r.text[:60]) if resp_json else r.text[:60]
                        _file_log(f'[Mail] Mailbox attempt {attempt+1}/3 failed: {err}')
                    else:
                        self._created_email    = addr
                        self._created_password = pw
                        self._email_data       = {'password': pw}
                        _save_generated_mail(addr, pw)
                        return addr
                else:
                    _file_log(f'[Mail] HTTP {r.status_code} on attempt {attempt+1}/3')
            except Exception as exc:
                _file_log(f'[Mail] Exception attempt {attempt+1}/3: {exc}')
            if attempt < 2:
                time.sleep(2)
        return None

    def get_verify_url(self, email_addr: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        import email as email_lib  # avoid shadowing the `email` module
        em = self._created_email or email_addr
        pw = self._created_password
        if not em or not pw or not self.imap_host:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                mail.login(em, pw)
                for folder in ["INBOX", "Junk", "Spam"]:
                    try:
                        status, _ = mail.select(folder)
                        if status != "OK":
                            continue
                        status, messages = mail.search(None, "ALL")
                        if status == "OK" and messages[0]:
                            for num in reversed(messages[0].split()):
                                res, msg_data = mail.fetch(num, "(RFC822)")
                                if res != "OK":
                                    continue
                                msg = email_lib.message_from_bytes(msg_data[0][1])
                                subject = str(msg.get("Subject", "")).lower()
                                from_addr = str(msg.get("From", "")).lower()
                                if "discord" in subject or "verify" in subject or "discord" in from_addr:
                                    body = ""
                                    if msg.is_multipart():
                                        for part in msg.walk():
                                            if part.get_content_type() in ["text/plain", "text/html"]:
                                                try:
                                                    body += part.get_payload(decode=True).decode(errors="ignore")
                                                except Exception:
                                                    pass
                                    else:
                                        try:
                                            body = msg.get_payload(decode=True).decode(errors="ignore")
                                        except Exception:
                                            pass
                                    if body:
                                        for pat in [
                                            r'https://discord\.com/verify\?token=[^\s"\'<>]+',
                                            r'https://discord\.com/verify/[^\s"\'<>]+',
                                            r'https://click\.discord\.com/[^\s"\'<>]+',
                                        ]:
                                            m = re.search(pat, body, re.IGNORECASE)
                                            if m:
                                                mail.logout()
                                                return m.group(0).replace("&amp;", "&")
                    except Exception:
                        pass
                mail.logout()
            except Exception:
                pass
            time.sleep(poll_interval)
        return None




class LutionAPI(ZeusProvider):
    BASE_URL = "https://api.lution.ee/v2"
    def __init__(self, api_key: str = "", category: str = "Microsoft"):
        self.api_key = api_key
        self.category = category
        self._email_data = None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            return None
        headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"category": self.category, "quantity": 1}
        for _ in range(5):
            try:
                r = requests.post(f"{self.BASE_URL}/email/buy", json=payload, headers=headers, timeout=10)
                if r.status_code == 200:
                    j = r.json()
                    data = j.get("data") or {}
                    emails = data.get("emails") or []
                    if emails:
                        e = emails[0]
                        self._email_data = {
                            "email": e.get("email", ""), 
                            "password": e.get("password", ""),
                            "token": e.get("graph_refresh_token", ""),
                            "uuid": e.get("thunderbird_client_id", "")
                        }
                        return e.get("email", "").lower()
            except:
                pass
            time.sleep(3)
        return None

def get_mail_provider():
    services = config.get("mail_services", {})
    if not services:
        devs_cfg = config.get("devs_mail", {})
        if devs_cfg.get("api_key"):
            return DEVSMailApi(logger=print, api_key=devs_cfg["api_key"]), "cybertemp"
        return None, None

    provider_order = ["duckmail", "cybertemp", "lution", "tempmail_lol", "hotmail007", "zeus", "draxono", "mailcow"]
    for name in provider_order:
        svc = services.get(name, {})
        if not svc.get("enabled", False):
            continue
        if name == "duckmail":
            return DuckMailAPI(password=svc.get("password", "")), name
        elif name == "cybertemp":
            return DEVSMailApi(logger=print, api_key=svc.get("api_key", "")), name
        elif name == "lution":
            return LutionAPI(api_key=svc.get("api_key", ""), category=svc.get("mailcode", "")), name
        elif name == "tempmail_lol":
            return TempMailLolAPI(), name
        elif name == "hotmail007":
            return Hotmail007API(client_key=svc.get("client_key", "")), name
        elif name == "zeus":
            return ZeusProvider(api_key=svc.get("api_key", "")), name
        elif name == "draxono":
            return DraxonoAPI(api_key=svc.get("api_key", "")), name
        elif name == "mailcow":
            return MailcowProvider(svc), name
    return None, None

class Solver:
    VPS_URL  = "https://9captcha-api.pridesmp.fun"                
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    def __init__(self, url, sitekey, rqdata="", user_agent="", proxy=None, api_key=""):
        self.url        = url
        self.sitekey    = sitekey
        self.rqdata     = rqdata
        self.user_agent = user_agent
        self.proxy      = proxy
        self.api_key    = api_key
        cap_cfg = config.get("9captcha", {})
        self.use_extension = cap_cfg.get("extension_solver", True)
        self.use_vps       = cap_cfg.get("req_solver", False)

    def _format_proxy(self):
        if self.proxy:
            return self.proxy
        return ""
    def _solve_extension(self, timeout=90):
        
        try:
            from engine.extension_browser import get_browser
            browser = get_browser()
            _file_log("[EXT] Solving via local browser + extension")
            token = browser.solve(
                sitekey=self.sitekey,
                url=self.url,
                rqdata=self.rqdata,
                user_agent=self.user_agent,
                timeout=timeout,
                proxy=self.proxy,
            )
            if token:
                return token, {}
            _file_log("[EXT] Extension solver returned no token")
            return None, None
        except ImportError:
            _file_log("[EXT] extension_browser.py not found or truedriver not installed")
            return None, None
        except Exception as e:
            _file_log(f"[EXT] Error: {e}")
            return None, None
    def _solve_vps(self, timeout=120, poll_interval=2):
        
        import urllib.request, urllib.error, json
        payload = {
            "key": self.api_key,
            "type": "hcaptcha_basic",
            "data": {
                "sitekey": self.sitekey,
                "siteurl": self.url,
                "proxy": self._format_proxy(),
                "rqdata": self.rqdata,
                "useragent": self.user_agent
            }
        }
        req = urllib.request.Request(
            f"{self.VPS_URL}/captcha/api/create_task",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': self.UA}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            resp_text = resp.read().decode('utf-8')
            resp_status = resp.getcode()
        except urllib.error.HTTPError as e:
            resp_status = e.code
            resp_text = e.read().decode('utf-8')
        if resp_status != 200:
            _file_log(f"[VPS] Server refused with HTTP {resp_status}")
            return None, None
        data = json.loads(resp_text)
        tid = data.get("task_id")
        if not tid:
            _file_log("[VPS] Missing Task ID")
            return None, None
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            try:
                req2 = urllib.request.Request(
                    f"{self.VPS_URL}/captcha/api/get_result/{tid}?key={self.api_key}",
                    headers={'User-Agent': self.UA}
                )
                r2 = urllib.request.urlopen(req2, timeout=10)
                if r2.getcode() == 200:
                    d = json.loads(r2.read().decode('utf-8'))
                    status = d.get("status")
                    if status == "solved":
                        return d.get("solution"), {}
                    if status == "error":
                        err_msg = d.get("error", "")
                        _file_log(f"[VPS] Solver error: {err_msg}")
                        if "rate-limit-exceeded" in str(err_msg).lower():
                            return "ERROR_RATELIMIT", None
                        if "ip-rejected" in str(err_msg).lower():
                            return "ERROR_IP_REJECTED", None
                        return None, None
            except Exception as e:
                _file_log(f"[VPS] Polling error: {e}")
        _file_log(f"[VPS] Timeout after {timeout}s for task {tid}")
        return None, None
    def solve(self, timeout=120, poll_interval=2):
        _file_log(f"Using Proxy: {self.proxy or 'None (Local IP)'}")
        _file_log(f"Solver config: extension={self.use_extension}, vps={self.use_vps}")
        if self.use_extension:
            _file_log("[EXT] Using extension / local browser solver")
            try:
                result = self._solve_extension(timeout)
                if result and result[0]:
                    return result
                _file_log("[EXT] Failed — try VPS if enabled")
            except Exception as e:
                _file_log(f"[EXT] Error: {e}")
        if self.use_vps and self.api_key:
            _file_log("[REQ] Using Req solver (request mode)")
            try:
                return self._solve_vps(timeout, poll_interval)
            except Exception as e:
                _file_log(f"[VPS] Error: {e}")
                return None, None
        if not self.use_extension and not self.use_vps:
            _file_log("[WARN] No solver enabled! Set extension_solver, req_solver, or manual_solve.")
        return None, None
        if self.use_vps:
            _file_log("[REQ] Using Req solver (request mode)")
            try:
                return self._solve_vps(timeout, poll_interval)
            except Exception as e:
                _file_log(f"[VPS] Error: {e}")
                return None, None
        _file_log("[WARN] No solver enabled! Set extension_solver or req_solver in config.")
        return None, None
config = {}
try:
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"Error loading config.json: {e}")

# Stealth mode: StealthSession uses browser-like TLS/header fingerprinting.
# Disabling it (config "stealth": false) falls back to a plain requests.Session.
STEALTH_ENABLED = config.get("stealth", True)
def make_session():
    if STEALTH_ENABLED:
        return StealthSession()
    s = requests.Session()
    s.verify = False
    return s

_logs_enabled = config.get("logs", False)
def _file_log(msg):
    if not _logs_enabled:
        return
    try:
        with open(os.path.join(os.path.dirname(__file__), "logs.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


# ── Multi-key pool ────────────────────────────────────────────────────────────────
class _KeyPool:
    """
    Thread-safe pool of 9captcha API keys.
    • Reads api_keys[] from config.json (falls back to single api_key).
    • check_and_rotate(): validates active key; if depleted, tries next.
    • mark_depleted():    called after a failed solve to trigger rotation.

    config.json example:
        "9captcha": {
            "api_keys": [
                "9cap-key-001",
                "9cap-key-002",
                "9cap-key-003"
            ],
            "extension_solver": true
        }
    """

    def __init__(self):
        cap_cfg = config.get("9captcha", {})
        self._vps = cap_cfg.get("vps_url", "https://9captcha-api.pridesmp.fun")
        # Support both list and single key
        keys = cap_cfg.get("api_keys", [])
        if not keys:
            single = cap_cfg.get("api_key", "").strip()
            keys = [single] if single else []
        self._keys   = [k.strip() for k in keys if k.strip()]
        self._idx    = 0
        self._lock   = threading.Lock()
        self._active = self._keys[0] if self._keys else ""
        self._last_rotation_fail = False

    def get_active(self) -> str:
        with self._lock:
            return self._active

    def total(self) -> int:
        return len(self._keys)

    def _write_active(self, key: str):
        """Update in-memory config + extension config file to activate a key."""
        try:
            config.setdefault("9captcha", {})["api_key"] = key
            # Write to config.json so extension_browser.sync_api_key() picks it up
            cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(cfg_path, "r", encoding="utf-8") as f:
                disk_cfg = json.load(f)
            disk_cfg.setdefault("9captcha", {})["api_key"] = key
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(disk_cfg, f, indent=4)
        except Exception:
            pass
        try:
            from engine.extension_browser import activate_key_in_extension
            activate_key_in_extension(key, self._vps)
        except Exception:
            pass

    def check_and_rotate(self, force: bool = False):
        """
        Validate active key balance.  If depleted (or force=True),
        scan remaining keys and activate the first one with credit > 0.
        Returns (active_key, credit) or (None, 0) if all exhausted.
        """
        from engine.extension_browser import check_key_balance
        with self._lock:
            n = len(self._keys)
            if n == 0:
                return None, 0
            # First check current key (unless caller is forcing a rotation)
            if not force:
                valid, credit = check_key_balance(self._active, self._vps)
                if valid and credit > 0.001:
                    return self._active, credit
            # Rotate through remaining keys
            for offset in range(1, n + 1):
                idx  = (self._idx + offset) % n
                key  = self._keys[idx]
                valid, credit = check_key_balance(key, self._vps)
                if valid and credit > 0.001:
                    old = self._active
                    self._idx    = idx
                    self._active = key
                    self._write_active(key)
                    self._last_rotation_fail = False
                    return key, credit
                # skip exhausted / unreachable key silently
            self._last_rotation_fail = True
            return None, 0

    def mark_depleted(self):
        """
        Called after a captcha solve failure.  Triggers rotation to the next
        valid key and returns (new_key, credit) or (None, 0).
        """
        return self.check_and_rotate(force=True)


_key_pool = _KeyPool()


verification_enabled = config.get("verification", {}).get("enabled", True)
gen_count = 0
gen_lock = threading.Lock()
stats_lock = threading.Lock()
stats = {
    'generated': 0,
    'verified': 0,
    'captcha_failed': 0,
    'captcha_solved': 0,
    'locked': 0,
    'valid': 0,
    'total': 0
}
class ProxyManager:
    def __init__(self, file_path="input/proxies.txt", resi_path="input/resi.txt"):
        self.file_path = file_path
        self.resi_path = resi_path
        self.lock = threading.Lock()
    def _pop_from_file(self, active_path):
        with self.lock:
            
            if not os.path.exists(active_path):
                return None
            try:
                with open(active_path, "r", encoding="utf-8") as f:
                    lines = [line for line in f if line.strip()]
                if not lines:
                    return None
                proxy = lines.pop(0).strip()
                with open(active_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if not line.endswith('\n'):
                            line += '\n'
                        f.write(line)
                user_pass = ""
                host_port = ""
                if "@" in proxy:
                    user_pass, host_port = proxy.split("@", 1)
                else:
                    host_port = proxy
                if "dataimpulse" in host_port.lower() and user_pass:
                    if ":" in user_pass:
                        user, pwd = user_pass.split(":", 1)
                        if "__session" not in user:
                            sess_id = uuid.uuid4().hex[:8]
                            user_pass = f"{user}__session_{sess_id}:{pwd}"
                import socket
                if ":" in host_port:
                    host, port = host_port.rsplit(":", 1)
                    try:
                        resolved_ip = socket.gethostbyname(host)
                        host_port = f"{resolved_ip}:{port}"
                    except Exception:
                        pass
                if user_pass:
                    proxy = f"{user_pass}@{host_port}"
                else:
                    proxy = host_port
                return proxy
            except Exception:
                return None
                
    def pop_top(self):
        return self._pop_from_file(self.file_path)
        
    def pop_resi(self):
        return self._pop_from_file(self.resi_path)

proxy_manager = ProxyManager()
from colorama import Fore, Style, init
from pystyle import Colors, Colorate, Center, Anime, System
init(autoreset=True)

# =============================================================================
# GRADIENT LOGGER  (identical to req2.py)
# =============================================================================
def _gradient_text(text: str, c1: tuple, c2: tuple) -> str:
    length = max(1, len(text) - 1)
    result = []
    for i, ch in enumerate(text):
        r = int(c1[0] + (c2[0] - c1[0]) * i / length)
        g = int(c1[1] + (c2[1] - c1[1]) * i / length)
        b = int(c1[2] + (c2[2] - c1[2]) * i / length)
        result.append(f'\033[38;2;{r};{g};{b}m{ch}')
    result.append('\033[0m')
    return ''.join(result)


class _Logger:
    _PAL = {
        'MAIL':    ((250,   5, 115), (255, 100, 180)),
        'CAPTCHA': ((255, 160,  30), (255,  80,   0)),
        'TOKEN':   ((  3, 248, 252), (  0, 180, 220)),
        'VERIFY':  (( 80, 200, 255), ( 20, 100, 240)),
        'SUCCESS': (( 80, 255, 120), (  0, 200,  80)),
        'LOCKED':  ((255,  80,  80), (200,  30,  30)),
        'WARN':    ((255, 230,  60), (240, 170,   0)),
        'ERROR':   ((255,  80,  80), (200,  30,  30)),
        'HUMAN':   ((160,  80, 255), (100,  20, 200)),
        'SESSION': ((120, 120, 120), ( 80,  80,  80)),
        'SAVE':    (( 80, 255, 120), (  0, 200,  80)),
        'ADB':     ((  0, 200, 255), (  0, 100, 220)),
        'PROXY':   ((160,  80, 255), (100,  20, 200)),
    }
    _LOG_LOCK = threading.Lock()

    def _ts(self) -> str:
        return datetime.now().strftime('%H:%M:%S')

    def _emit(self, tag: str, message: str):
        c1, c2 = self._PAL.get(tag, self._PAL['SESSION'])
        ts_col  = _gradient_text(f'[{self._ts()}]', (80, 80, 110), (140, 140, 180))
        tag_col = _gradient_text(f'[{tag}]', c1, c2)
        msg_col = _gradient_text(message, c1, c2)
        line = f'{ts_col} {tag_col} {msg_col}\033[0m'
        with self._LOG_LOCK:
            try:
                print(line)
            except UnicodeEncodeError:
                print(line.encode('ascii', 'ignore').decode('ascii'))

    def info(self, m: str):     self._emit('SESSION', m)
    def success(self, m: str):
        mu = m.upper()
        if 'LOCKED' in mu:             self._emit('LOCKED',  m)
        elif 'VERIFIED' in mu:         self._emit('VERIFY',  m)
        elif 'TOKEN' in mu:            self._emit('TOKEN',   m)
        elif any(x in mu for x in ('CAPTCHA', 'SOLVED')): self._emit('CAPTCHA', m)
        else:                          self._emit('SUCCESS', m)
    def warning(self, m: str):  self._emit('WARN',    m)
    def error(self, m: str):    self._emit('ERROR',   m)
    def mail(self, m: str):     self._emit('MAIL',    m)
    def captcha(self, m: str):  self._emit('CAPTCHA', m)
    def verify(self, m: str):   self._emit('VERIFY',  m)
    def adb(self, m: str):      self._emit('ADB',     m)
    def save(self, m: str):     self._emit('SAVE',    m)
    def human(self, m: str):    self._emit('HUMAN',   m)


log = _Logger()


class Log:
    """Thin shim — keeps existing Log.* call sites working via the gradient logger."""
    lock = _Logger._LOG_LOCK

    @staticmethod
    def _censor_token(token: str) -> str:
        parts = token.split('.')
        if len(parts) == 3:
            return f'{parts[0][:6]}******.{parts[1]}.*******{parts[2][-6:]}'
        return token[:15] + '******'

    @staticmethod
    def proxy_header(num, proxy):
        if not proxy:
            return
        censor = config.get('censor', True)
        if censor:
            if '@' in proxy:
                auth, hostport = proxy.rsplit('@', 1)
                user = auth.split(':')[0]
                proxy = f'{user[:6]}***:****@{hostport}'
            else:
                proxy = proxy[:10] + '***'
        log._emit('PROXY', f'Proxy → {proxy}')

    @staticmethod
    def generated(token):
        log.save(f'Generated  {Log._censor_token(token)}')
        with stats_lock:
            stats['generated'] += 1
            stats['total']     += 1

    @staticmethod
    def captcha_solved(time_n, token=''):
        tok = f' → {token[:40]}...' if token else ''
        log.captcha(f'Captcha solved in {time_n:.1f}s{tok}')
        with stats_lock:
            stats['captcha_solved'] += 1

    @staticmethod
    def solving(email):
        log.captcha('Solving captcha...')

    @staticmethod
    def captcha_failed():
        log.error('Captcha failed')
        with stats_lock:
            stats['captcha_failed'] += 1
            stats['total']          += 1

    @staticmethod
    def status(text):
        log.info(text)

    @staticmethod
    def error(text):
        log.error(text)

    @staticmethod
    def waiting(text):
        log.warning(text)

    @staticmethod
    def verified(token):
        log.verify(f'Verified  {Log._censor_token(token)}')
        with stats_lock:
            stats['verified'] += 1

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6897.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.127 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36",
]
_FIRST_NAMES = [
    'james', 'mary', 'john', 'patricia', 'robert', 'jennifer', 'michael', 'linda', 'william', 'elizabeth',
    'david', 'barbara', 'richard', 'susan', 'joseph', 'jessica', 'thomas', 'sarah', 'charles', 'karen',
    'christopher', 'lisa', 'daniel', 'nancy', 'matthew', 'betty', 'anthony', 'margaret', 'mark', 'sandra',
    'donald', 'ashley', 'steven', 'kimberly', 'paul', 'emily', 'andrew', 'donna', 'joshua', 'michelle',
    'kenneth', 'carol', 'kevin', 'amanda', 'brian', 'dorothy', 'george', 'melissa', 'timothy', 'deborah',
    'ronald', 'stephanie', 'edward', 'rebecca', 'jason', 'sharon', 'jeffrey', 'laura', 'ryan', 'cynthia',
    'jacob', 'kathleen', 'gary', 'amy', 'nicholas', 'angela', 'eric', 'shirley', 'jonathan', 'anna',
    'stephen', 'brenda', 'larry', 'pamela', 'justin', 'emma', 'scott', 'nicole', 'brandon', 'helen',
    'alex', 'sam', 'jay', 'riley', 'max', 'charlie', 'taylor', 'jordan', 'casey', 'drew', 'oliver', 'lucas',
    'mason', 'logan', 'ethan', 'aiden', 'jackson', 'liam', 'noah', 'elijah', 'mia', 'chloe', 'zoey', 'lily'
]

_LAST_NAMES = [
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
    'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin',
    'lee', 'perez', 'thompson', 'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson',
    'walker', 'young', 'allen', 'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores', 'green',
    'adams', 'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell', 'carter', 'roberts', 'gomez',
    'phillips', 'evans', 'turner', 'diaz', 'parker', 'cruz', 'edwards', 'collins', 'reyes', 'stewart',
    'morris', 'morales', 'murphy', 'cook', 'rogers', 'gutierrez', 'ortiz', 'morgan', 'cooper', 'peterson',
    'bailey', 'reed', 'kelly', 'howard', 'ramos', 'kim', 'cox', 'ward', 'richardson', 'watson', 'brooks',
    'chavez', 'wood', 'james', 'bennett', 'gray', 'mendoza', 'ruiz', 'hughes', 'price', 'alvarez', 'castillo'
]

_ADJECTIVES = [
    'cool', 'dark', 'wild', 'fast', 'chill', 'epic', 'real', 'true', 'fire', 'ice',
    'neon', 'void', 'zen', 'pro', 'ace', 'rad', 'dope', 'lit', 'raw', 'hype', 'super',
    'mega', 'ultra', 'hyper', 'quantum', 'cyber', 'retro', 'crypto', 'meta', 'stealth',
    'shadow', 'ghost', 'phantom', 'ninja', 'vortex', 'solar', 'lunar', 'cosmic', 'astral',
    'mystic', 'magic', 'lucky', 'happy', 'mad', 'crazy', 'lazy', 'sleepy', 'angry', 'sad',
    'good', 'bad', 'evil', 'holy', 'pure', 'dirty', 'clean', 'fresh', 'stale', 'sweet'
]

def _random_username() -> str:
    def _rand_suffix(lo=100, hi=99999): return str(random.randint(lo, hi))
    def _rand_str(k=4): return ''.join(random.choices(string.ascii_lowercase + string.digits, k=k))
    # config: username.prefix + digits  OR username_prefix
    try:
        cfg = globals().get("config") or {}
        uname_cfg = cfg.get("username") or {}
        prefix = (uname_cfg.get("prefix") or cfg.get("username_prefix") or "").strip()
        digits = int(uname_cfg.get("suffix_digits") or 4)
        digits = max(2, min(digits, 8))
    except Exception:
        prefix, digits = "", 4
    if prefix:
        # sanitize prefix for discord username rules
        p = "".join(c for c in prefix.lower() if c.isalnum() or c in "._")[:20]
        if not p:
            p = "user"
        return f"{p}{_rand_suffix(10**(digits-1), 10**digits - 1)}"
    patterns = [
        lambda: random.choice(_FIRST_NAMES) + random.choice(_LAST_NAMES)  + _rand_suffix(10, 99999),
        lambda: random.choice(_FIRST_NAMES) + '_' + random.choice(_LAST_NAMES) + _rand_suffix(100, 9999),
        lambda: random.choice(_ADJECTIVES)  + random.choice(_FIRST_NAMES)  + _rand_suffix(100, 9999),
        lambda: random.choice(_FIRST_NAMES) + '.' + random.choice(_LAST_NAMES) + _rand_suffix(1, 9999),
        lambda: random.choice(_FIRST_NAMES) + _rand_suffix(1000, 99999),
        lambda: random.choice(_LAST_NAMES)  + random.choice(_FIRST_NAMES)  + _rand_suffix(100, 9999),
        lambda: random.choice(_ADJECTIVES)  + '_' + random.choice(_FIRST_NAMES) + _rand_suffix(100, 9999),
        lambda: random.choice(_FIRST_NAMES) + '_' + _rand_str(4) + _rand_suffix(10, 999),
        lambda: _rand_str(5) + _rand_suffix(1000, 99999),
    ]
    return random.choice(patterns)()
def _random_password() -> str:
    
    base = ''.join(random.choices(string.ascii_letters, k=random.randint(6, 10)))
    digits = ''.join(random.choices(string.digits, k=random.randint(2, 4)))
    special = random.choice('!@#$%&*')
    pwd = base + digits + special
    return pwd
def _random_dob() -> str:
    
    year = random.randint(1994, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  
    return f"{year}-{month:02d}-{day:02d}"
def get_build_number(proxy=None):
    try:
        sess = make_session()
        if proxy:
            proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
            sess.proxies = {"http": proxy_url, "https": proxy_url}
        page = sess.get("https://discord.com/app").text
        assets = re.findall(r'src="/assets/([^"]+)"', page)
        for asset in reversed(assets):
            js = sess.get(f"https://discord.com/assets/{asset}").text
            if "buildNumber:" in js:
                return int(js.split('buildNumber:"')[1].split('"')[0]) 
    except Exception:
        pass
    return 519006
def build_super_properties(build_number, user_agent, chrome_version):
    payload = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": user_agent,
        "browser_version": f"{chrome_version}.0.0.0",
        "os_version": "10",
        "referrer": "https://discord.com/",
        "referring_domain": "discord.com",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": build_number,
        "client_event_source": None,
        "has_client_mods": False,
        "client_launch_id": str(uuid.uuid4()),
        "launch_signature": str(uuid.uuid4()),
        "client_heartbeat_session_id": str(uuid.uuid4()),
        "client_app_state": "focused",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()
def _build_sec_ch_ua(chrome_version):
    if chrome_version >= 133:
        return f'"Not:A-Brand";v="24", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
    return f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
def acquire_discord_cookies(session):
    session.get("https://discord.com")
    cookies = session.cookies.get_dict()
    dcfduid = cookies.get("__dcfduid")
    sdcfduid = cookies.get("__sdcfduid")
    return dcfduid, sdcfduid
def fetch_discord_fingerprint(session, dcfduid, sdcfduid, user_agent, chrome_version):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cookie": f"__dcfduid={dcfduid}; __sdcfduid={sdcfduid};",
        "sec-ch-ua": _build_sec_ch_ua(chrome_version),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": user_agent
    }
    session.headers = headers
    data = session.get("https://discord.com/api/v9/experiments")
    return data.json()["fingerprint"]
def build_headers(fingerprint, super_props, user_agent, chrome_version):
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/",
        "priority": "u=1, i",
        "sec-ch-ua": _build_sec_ch_ua(chrome_version),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": user_agent,
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "America/Los_Angeles",
        "x-fingerprint": fingerprint,
        "x-super-properties": super_props,
    }
def verify_token_integrity(session):
    try:
        r = session.get("https://discord.com/api/v9/users/@me")
        if r.status_code != 200:
            return "invalid"
        r2 = session.get("https://discord.com/api/v9/users/@me/settings")
        if r2.status_code == 200:
            return "Valid"
        elif r2.status_code == 403:
            return "locked"
    except Exception:
        pass
    return "invalid"
def export_credential(email, password, token, token_status, is_verified=False, is_humanized=False):
    """Save TOKEN ONLY to output/tokens.txt (absolute path next to main.py)."""
    try:
        base = Path(__file__).resolve().parent
    except Exception:
        base = Path.cwd()
    out_dir = base / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not token:
        print(f"[SAVE SKIP] empty token for {email}", flush=True)
        return
    path = out_dir / "tokens.txt"
    with open(path, "a", encoding="utf-8") as f:
        f.write(str(token).strip() + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    print(f"[SAVED] tokens.txt | {str(token)[:24]}...", flush=True)


class WebSocketClientKeepAlive:
    
    def __init__(self, token):
        self.token = token
        self._stop = threading.Event()
        self._thread = None
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self):
        self._stop.set()
    def _run(self):
        try:
            ws = websocket.WebSocket()
            ws.settimeout(10)
            ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
            hello = json.loads(ws.recv())
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Windows",
                        "browser": "Chrome",
                        "device": "",
                        "system_locale": "en-US",
                        "browser_user_agent": random.choice(USER_AGENTS),
                        "browser_version": "136.0.0.0",
                        "os_version": "10",
                        "referrer": "https://discord.com/",
                        "referring_domain": "discord.com",
                        "referrer_current": "",
                        "referring_domain_current": "",
                        "release_channel": "stable",
                        "client_build_number": get_build_number(),
                        "client_event_source": None,
                    },
                    "presence": {
                        "status": "online",
                        "since": 0,
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "client_state": {
                        "guild_versions": {},
                        "highest_last_message_id": "0",
                        "read_state_version": 0,
                        "user_guild_settings_version": -1,
                        "user_settings_version": -1,
                        "private_channels_version": "0",
                        "api_code_version": 0
                    }
                },
            }
            ws.send(json.dumps(identify))
            ready = False
            for _ in range(10):
                resp = json.loads(ws.recv())
                if resp.get("t") == "READY":
                    ready = True
                    break
                if resp.get("op") == 9:  
                    ws.close()
                    return
            if not ready:
                ws.close()
                return
            while not self._stop.is_set():
                ws.send(json.dumps({"op": 1, "d": None}))
                self._stop.wait(heartbeat_interval)
            ws.close()
        except Exception:
            pass
def process_hcaptcha(sitekey, rqdata, user_agent, proxy=None):
    """
    Solve hCaptcha using the active key.  On failure, automatically rotates
    through all keys in _key_pool until one succeeds or all are exhausted.
    """
    cap_cfg = config.get("9captcha", {})
    # Manual mode: no API key required, no key validation/rotation. The visible
    # browser is opened and we wait for the user to solve the captcha by hand.
    if cap_cfg.get("manual_solve", False):
        api_key = (cap_cfg.get("api_key") or "").strip()
        if not api_key:
            keys = cap_cfg.get("api_keys") or []
            api_key = (keys[0] if keys else "") or ""
        solver = Solver(
            url="https://discord.com/register",
            sitekey=sitekey,
            rqdata=rqdata,
            user_agent=user_agent,
            proxy=proxy,
            api_key=api_key,
        )
        solver.use_extension = True
        # VPS only as fallback when req_solver enabled
        solver.use_vps = bool(cap_cfg.get("req_solver", False) and api_key)
        return solver.solve(timeout=int(cap_cfg.get("manual_timeout", 300)))
    max_attempts = max(1, _key_pool.total())
    for attempt in range(max_attempts):
        solver_key = _key_pool.get_active()
        solver = Solver(
            url="https://discord.com/register",
            sitekey=sitekey,
            rqdata=rqdata,
            user_agent=user_agent,
            proxy=proxy,
            api_key=solver_key
        )
        result, cookies = solver.solve()
        if result:                               # success
            return result, cookies
        # Solve failed — check if it's a credit issue and try next key
        if attempt < max_attempts - 1:
            new_key, credit = _key_pool.mark_depleted()
            if not new_key:
                log.error('[KEY] All API keys depleted — add more keys to config.json → 9captcha.api_keys[]')
                break
            if new_key == solver_key:
                break  # same key came back (only 1 key) — not a credits problem
            log.warning(f'[KEY] Key #{attempt + 1} depleted — rotated to next key (credit: {credit})')
    return None, None
def generate_9DEVS_token(email, username, password, proxy=None, current_num=1, mail_api=None, mail_provider_name=None):
    masked_mail = f"{email[:4]}***@{email.split('@')[1]}" if '@' in email else email
    log.mail(f'[W{current_num}] Mail → {masked_mail}')

    if not mail_api:
        mail_api, mail_provider_name = get_mail_provider()
        if not mail_api:
            mail_api = DEVSMailApi(logger=print)
            mail_provider_name = "cybertemp (fallback)"
        
    session = make_session()
    if proxy:
        proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    user_agent = random.choice(USER_AGENTS)
    chrome_version_match = re.search(r"Chrome/(\d+)", user_agent)
    chrome_version = int(chrome_version_match.group(1)) if chrome_version_match else 136
    try:
        dcfduid, sdcfduid = acquire_discord_cookies(session)
        fingerprint = fetch_discord_fingerprint(session, dcfduid, sdcfduid, user_agent, chrome_version)
    except Exception as e:
        Log.error(f"fingerprint failed: {e}")
        if "timeout" in str(e).lower() or "(28)" in str(e):
            log.warning('Proxy timed out — moving to next proxy')
        return
    build_num = get_build_number(proxy)
    super_props = build_super_properties(build_num, user_agent, chrome_version)
    headers = build_headers(fingerprint, super_props, user_agent, chrome_version)
    session.headers.update(headers)
    time.sleep(random.uniform(2, 5))
    dob = _random_dob()
    # Fake registration preflight (warms up session, mimics real user behavior)
    if mail_provider_name not in ["zeus", "hotmail007", "lution"]:
        fake_user = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))
        fake_payload = {
            "fingerprint": fingerprint,
            "email": f"{fake_user}@outlook.com",
            "username": fake_user,
            "password": f"{fake_user}Ab1!@#",
            "date_of_birth": dob,
            "consent": True,
        }

        try:
            fake_res = session.post("https://discord.com/api/v9/auth/register", json=fake_payload)
            fake_json = fake_res.json()
            if fake_res.status_code == 429:
                retry_after = fake_json.get("retry_after", 60)
                Log.waiting(f"rate limited, waiting {retry_after:.0f}s...")
                time.sleep(retry_after + 1)
        except Exception:
            pass

    register_payload = {
        "fingerprint": fingerprint,
        "email": email,
        "username": username,
        "password": password,
        "invite": None,
        "date_of_birth": dob,
        "consent": True,
    }
    Log.status("Creating Acc..")
    res_json = {}
    for _reg_attempt in range(5):
        try:
            res = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
            res_json = res.json()
            if res.status_code == 429:
                retry_after = res_json.get("retry_after", 60)
                Log.waiting(f"rate limited, waiting {retry_after:.0f}s...")
                time.sleep(retry_after + 1)
                res = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
                res_json = res.json()
        except Exception as e:
            Log.error(f"Network error during registration (proxy timeout/dead): {e}")
            return
        # Check for Name Taken and retry with a new username
        _is_name_taken = False
        try:
            _errs = res_json.get('errors', {})
            if 'username' in _errs:
                for _e in _errs['username'].get('_errors', []):
                    if _e.get('code') == 'USERNAME_ALREADY_TAKEN':
                        _is_name_taken = True
                        break
        except Exception:
            pass
        if _is_name_taken:
            username = _random_username()
            register_payload["username"] = username
            log.warning(f'Name taken — retrying with {username} (attempt {_reg_attempt + 2}/5)')
            time.sleep(1)
            continue
        break  # not a name-taken error — proceed
    captcha_sitekey = res_json.get("captcha_sitekey")
    captcha_rqdata = res_json.get("captcha_rqdata")
    captcha_rqtoken = res_json.get("captcha_rqtoken")
    captcha_session_id = res_json.get("captcha_session_id")
    if not captcha_sitekey or not captcha_rqdata:
        if "token" in res_json:
            Log.status("Account created without captcha!")
            # The logic below expects a cap_token, but if we got a token early we should handle it
            pass
        else:
            err_msg = "Unknown Rate Limit or Global Ban"
            try:
                errors = res_json.get('errors', {})
                if 'username' in errors and '_errors' in errors['username']:
                    for e in errors['username']['_errors']:
                        if e.get('code') == 'USERNAME_ALREADY_TAKEN':
                            err_msg = "Name Taken"
                            break
            except Exception:
                pass
            Log.error(f"Registration Blocked: {err_msg}")
            return
    Log.solving(email)
    captcha_start = time.time()

    if not captcha_rqdata:
        Log.error('FATAL: Discord did not provide rqdata!')
    
    cap_token, cookies = process_hcaptcha(captcha_sitekey, captcha_rqdata, user_agent, proxy=proxy)
    if cap_token == "ERROR_RATELIMIT":
        Log.error("ip/proxy ratelimited by hCaptcha")
        return
    if cap_token == "ERROR_IP_REJECTED":
        Log.error("ip/proxy rejected by hCaptcha — your IP was flagged. Try a different proxy or use Extension solver.")
        return
    if not cap_token:
        Log.captcha_failed()
        return
    if cookies:
        for k, v in cookies.items():
            session.cookies.set(k, v)
    solve_time = time.time() - captcha_start
    Log.captcha_solved(solve_time, cap_token)
    session.headers.update({
        "x-captcha-key": cap_token,
        "x-captcha-rqtoken": captcha_rqtoken,
        "x-captcha-session-id": captcha_session_id,
    })
    response = None
    for attempt in range(3):
        try:
            response = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
            break
        except Exception:
            if attempt < 2:
                time.sleep(1)
            else:
                return
    try:
        res_data = response.json()
    except Exception as e:
        Log.error(f"Failed to read raw response / invalid JSON: {e}")
        return
    if 'token' not in res_data:
        err_str = "Registration Blocked"
        if res_data.get('captcha_key') == ['invalid-response']:
            err_str = "Discord Rejected Captcha Token (invalid-response)"
        elif res_data.get('message'):
            err_str = res_data.get('message')
        Log.error(f"Account Finalization Failed: {err_str}")
        return
    auth_token = res_data['token']
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    session.headers.update({"authorization": auth_token})
    time.sleep(random.uniform(3, 6))
    onliner = WebSocketClientKeepAlive(auth_token)
    onliner.start()
    if not verification_enabled:
        pre_verify_status = verify_token_integrity(session)
        is_humanized = False
        if config.get("humanizer", {}).get("enabled", False) and pre_verify_status.lower() == "valid":
            try:
                name_list = get_display_names()
                bio_list = load_file_lines(BIOS_FILE)
                pronouns_list = load_file_lines(PRONOUNS_FILE)
                av_files = load_avatar_files()
                hz = Humanizer(auth_token, proxy)
                success = hz.process(name_list, bio_list, pronouns_list, av_files, load_avatar_as_base64)
                if success:
                    hz_cfg = config.get("humanizer", {})
                    fields = []
                    if hz_cfg.get("bio"): fields.append("Bio ✓")
                    if hz_cfg.get("pronouns"): fields.append("Pronouns ✓")
                    if hz_cfg.get("hypesquad"): fields.append("HypeSquad ✓")
                    if hz_cfg.get("avatar"): fields.append("Avatar ✓")
                    if hz_cfg.get("display_name"): fields.append("Name ✓")
                    log.human(f'Humanized: {" | ".join(fields)}')
                    is_humanized = True
            except Exception as e:
                Log.error(f"humaniser module failed: {e}")
        export_credential(email, password, auth_token, pre_verify_status, is_verified=False, is_humanized=is_humanized)
        onliner.stop()
        return
    Log.waiting('waiting for verification email...')
    verify_url = mail_api.get_verify_url(email, 3, 180, proxy)
    if not verify_url:
        Log.error('verification email never arrived — saving as-is')
        token_status = verify_token_integrity(session)
        export_credential(email, password, auth_token, token_status)
        onliner.stop()
        return
    try:
        click_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'sec-ch-ua': _build_sec_ch_ua(chrome_version),
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent,
        }
        mail_token = None
        if "token=" in verify_url:
            mail_token = verify_url.split("token=")[-1].split("&")[0]
        if not mail_token:
            location = ""
            r1 = session.get(verify_url, headers=click_headers, allow_redirects=False)
            location = r1.headers.get("Location", "")
            if location:
                fragment = urlparse(location).fragment
                if fragment and "token=" in fragment:
                    mail_token = fragment.split("token=")[-1].split("&")[0]
            if not mail_token and location:
                r2 = session.get(location, headers=click_headers, allow_redirects=False)
                location2 = r2.headers.get("Location", "")
                if location2:
                    fragment2 = urlparse(location2).fragment
                    if fragment2 and "token=" in fragment2:
                        mail_token = fragment2.split("token=")[-1].split("&")[0]
        if not mail_token:
            token_status = verify_token_integrity(session)
            export_credential(email, password, auth_token, token_status)
            onliner.stop()
            return
    except Exception:
        token_status = verify_token_integrity(session)
        export_credential(email, password, auth_token, token_status)
        onliner.stop()
        return
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    time.sleep(random.uniform(1, 3))
    verify_res = session.post(
        "https://discord.com/api/v9/auth/verify",
        json={"token": mail_token}
    )
    verify_json = verify_res.json()
    if verify_json.get("captcha_sitekey"):
        Log.solving(email)
        verify_start = time.time()
        verify_cap_token, verify_cookies = process_hcaptcha(
            verify_json["captcha_sitekey"],
            verify_json.get("captcha_rqdata", ""),
            user_agent,
            proxy=proxy
        )
        if not verify_cap_token:
            Log.captcha_failed()
            token_status = verify_token_integrity(session)
            export_credential(email, password, auth_token, token_status)
            onliner.stop()
            return
        verify_solve_time = time.time() - verify_start
        Log.captcha_solved(verify_solve_time, verify_cap_token)
        if verify_cookies:
            for k, v in verify_cookies.items():
                session.cookies.set(k, v)
        session.headers.update({
            "x-captcha-key": verify_cap_token,
            "x-captcha-rqtoken": verify_json.get("captcha_rqtoken", ""),
            "x-captcha-session-id": verify_json.get("captcha_session_id", ""),
        })
        verify_res = session.post(
            "https://discord.com/api/v9/auth/verify",
            json={"token": mail_token}
        )
        verify_json = verify_res.json()
    new_token = verify_json.get('token')
    if new_token:
        auth_token = new_token
        session.headers.update({"authorization": auth_token})
        Log.verified(auth_token)
    else:
        Log.error(f"Verification response had no token: {str(verify_json)[:200]}")
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    token_status = verify_token_integrity(session)
    # W{n} done line
    ts_up = token_status.upper()
    if ts_up == 'VALID':
        log.success(f'[W{current_num}] #{current_num} → VALID')
    elif ts_up == 'LOCKED':
        log._emit('LOCKED', f'[W{current_num}] #{current_num} → LOCKED')
    else:
        log.warning(f'[W{current_num}] #{current_num} → {ts_up}')
    is_humanized = False
    if config.get("humanizer", {}).get("enabled", False) and token_status.lower() == "valid":
        try:
            name_list = get_display_names()
            bio_list = load_file_lines(BIOS_FILE)
            pronouns_list = load_file_lines(PRONOUNS_FILE)
            av_files = load_avatar_files()
            hz = Humanizer(auth_token, proxy)
            success = hz.process(name_list, bio_list, pronouns_list, av_files, load_avatar_as_base64)
            if success:
                hz_cfg = config.get("humanizer", {})
                fields = []
                if hz_cfg.get("bio"): fields.append("Bio ✓")
                if hz_cfg.get("pronouns"): fields.append("Pronouns ✓")
                if hz_cfg.get("hypesquad"): fields.append("HypeSquad ✓")
                if hz_cfg.get("avatar"): fields.append("Avatar ✓")
                if hz_cfg.get("display_name"): fields.append("Name ✓")
                log.human(f'Humanized: {" | ".join(fields)}')
                is_humanized = True
        except Exception as e:
            Log.error(f"humaniser module failed: {e}")
    export_credential(email, password, auth_token, token_status, is_verified=True, is_humanized=is_humanized)

    # AUTO JOIN — join dù VALID hay LOCKED (miễn có token)
    try:
        from engine.auto_join import auto_join_after_reg
        if auth_token:
            st = (token_status or "").upper() or "?"
            log.info(f'[W{current_num}] AUTO-JOIN start ({st})...')
            ok = auto_join_after_reg(auth_token, proxy=proxy if "proxy" in dir() else None)
            if ok:
                log.success(f'[W{current_num}] AUTO-JOIN OK ({st})')
            else:
                log.warning(f'[W{current_num}] AUTO-JOIN failed ({st})')
        else:
            log.warning(f'[W{current_num}] AUTO-JOIN skip — no token')
    except Exception as _aj_e:
        log.warning(f'[W{current_num}] AUTO-JOIN error: {_aj_e}')

    onliner.stop()
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
_async_loop = asyncio.new_event_loop()
_async_loop_thread = threading.Thread(target=_async_loop.run_forever, daemon=True)
_async_loop_thread.start()
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "engine" / "data"
INPUT_DIR = SCRIPT_DIR / "engine" / "input"
AVATARS_DIR = SCRIPT_DIR / "engine" / "avatar"
BANNERS_DIR = SCRIPT_DIR / "engine" / "banners"
TOKENS_FILE = INPUT_DIR / "tokens.txt"
PROXIES_FILE = INPUT_DIR / "proxies.txt"
BIOS_FILE = DATA_DIR / "bios.txt"
NAMES_FILE = DATA_DIR / "names.txt"

def get_display_names() -> list:
    """display_names from config (list) or names.txt"""
    try:
        cfg = globals().get("config") or {}
        names = cfg.get("display_names") or cfg.get("humanizer", {}).get("display_names") or []
        if isinstance(names, list) and names:
            return [str(n).strip() for n in names if str(n).strip()]
    except Exception:
        pass
    try:
        return load_file_lines(NAMES_FILE)
    except Exception:
        return []

PRONOUNS_FILE = DATA_DIR / "pronouns.txt"
SUCCESS_FILE = INPUT_DIR / "success.txt"
FAILED_FILE = INPUT_DIR / "failed.txt"
hz_config = config.get("humanizer", {})
MAX_THREADS = hz_config.get("max_threads", 3)
AVATAR_DIMENSION = hz_config.get("avatar_dimension", 256)
MAX_AVATAR_CACHE = hz_config.get("max_avatar_cache", 100)
UPDATE_DISPLAY_NAME = hz_config.get("display_name", True)
UPDATE_BIO = hz_config.get("bio", True)
UPDATE_PRONOUNS = hz_config.get("pronouns", True)
UPDATE_AVATAR = hz_config.get("avatar", True)
UPDATE_HYPESQUAD = hz_config.get("hypesquad", True)
RETRY_LIMIT = hz_config.get("retries", 3)
HYPESQUAD_HOUSES = {
    1: "Bravery",
    2: "Brilliance",
    3: "Balance"
}
DISCORD_API = "https://discord.com/api/v9"
DISCORD_GATEWAY = "wss://gateway.discord.gg/?v=9&encoding=json"
FALLBACK_BUILD_NUMBER = 519006
DISCORD_CLIENT_VERSION = "1.0.9171"
ELECTRON_VERSION = "34.5.1"
CHROME_VERSION_ELECTRON = "132"
DEFAULT_USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) discord/{DISCORD_CLIENT_VERSION} "
    f"Chrome/{CHROME_VERSION_ELECTRON}.0.0.0 Electron/{ELECTRON_VERSION} Safari/537.36"
)
def fetch_build_number() -> int:
    try:
        resp = primp.Client(verify=False).get("https://discord.com/login", timeout=10)
        if resp.status_code != 200:
            return FALLBACK_BUILD_NUMBER
        asset_urls = re.findall(r'/assets/([a-zA-Z0-9_-]+)\.js', resp.text)
        if not asset_urls:
            return FALLBACK_BUILD_NUMBER
        for asset_hash in reversed(asset_urls):
            try:
                js_resp = primp.Client(verify=False).get(
                    f"https://discord.com/assets/{asset_hash}.js",
                    timeout=10
                )
                if js_resp.status_code != 200:
                    continue
                match = re.search(r'buildNumber["\s:,]+(\d{4,7})', js_resp.text)
                if match:
                    return int(match.group(1))
            except Exception:
                continue
        return FALLBACK_BUILD_NUMBER
    except Exception:
        return FALLBACK_BUILD_NUMBER
BUILD_NUMBER = fetch_build_number()
def _random_uuid() -> str:
    return f"{random.randint(10000000, 99999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000000000, 999999999999)}"
def generate_super_properties(
    launch_id: str, signature: str, heartbeat_id: str, native_build: int
) -> str:
    return base64.b64encode(json.dumps({
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": DISCORD_CLIENT_VERSION,
        "os_version": "10.0.26100",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "has_client_mods": False,
        "browser_user_agent": DEFAULT_USER_AGENT,
        "browser_version": ELECTRON_VERSION,
        "client_build_number": BUILD_NUMBER,
        "native_build_number": native_build,
        "client_event_source": None,
        "client_launch_id": launch_id,
        "launch_signature": signature,
        "client_heartbeat_session_id": heartbeat_id,
    }, separators=(",", ":")).encode()).decode()
hz_proxy_manager = None
print_lock = threading.Lock()
file_lock = threading.Lock()
def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")
def _hlog(log_type: str, token: str, message: str):
    timestamp = get_timestamp()
    masked = mask_token(token)
    with print_lock:
        ts = f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL}"
        tok = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}Token : {Fore.CYAN}{masked}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
        if log_type == "SUCCESS":
            status = f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL}"
        elif log_type == "FAILED":
            status = f"{Fore.RED}[FAILED]{Style.RESET_ALL}"
        elif log_type == "WARN":
            status = f"{Fore.YELLOW}[WARN]{Style.RESET_ALL}"
        elif log_type == "INFO":
            status = f"{Fore.CYAN}[INFO]{Style.RESET_ALL}"
        else:
            status = f"[{log_type}]"
        if " : " in message and message.startswith("[") and message.endswith("]"):
            inner = message[1:-1]
            parts = inner.split(" : ", 1)
            if len(parts) == 2:
                desc, value = parts
                msg = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}{Fore.WHITE}{desc}{Style.RESET_ALL} : {Fore.CYAN}{value}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
            else:
                msg = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}{Fore.WHITE}{inner}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
        else:
            msg = message
        print(f"{ts} - {status} - {tok} → {msg}")
def log_simple(log_type: str, message: str):
    timestamp = get_timestamp()
    ts = f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL}"
    with print_lock:
        if log_type == "FAILED":
            print(f"{ts} - {Fore.RED}[FAILED]{Style.RESET_ALL} - {Fore.RED}{message}{Style.RESET_ALL}")
        elif log_type == "INFO":
            print(f"{ts} - {Fore.CYAN}[INFO]{Style.RESET_ALL} - {Fore.WHITE}{message}{Style.RESET_ALL}")
        else:
            print(f"{ts} - {message}")
def mask_token(token: str) -> str:
    if len(token) <= 20:
        return token[:10] + "****"
    return token[:10] + "****" + token[-10:]
def load_file_lines(file_path: Path) -> List[str]:
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
def append_to_file(file_path: Path, content: str):
    with file_lock:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')
def remove_token_from_file(file_path: Path, token: str):
    with file_lock:
        try:
            lines = file_path.read_text(encoding='utf-8').splitlines()
            new_lines = [l for l in lines if extract_token(l) != token.strip()]
            file_path.write_text('\n'.join(new_lines) + ('\n' if new_lines else ''), encoding='utf-8')
        except Exception:
            pass 
def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    hours = minutes // 60
    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    if minutes > 0:
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    return f"{seconds:.2f}s"
def is_valid_token(s: str) -> bool:
    if not s or len(s) < 50:
        return False
    parts = s.split('.')
    if len(parts) != 3:
        return False
    return all(re.match(r'^[A-Za-z0-9_-]+$', part) and len(part) > 0 for part in parts)
def extract_token(line: str) -> Optional[str]:
    line = line.strip()
    if not line:
        return None
    if is_valid_token(line):
        return line
    for delimiter in [':', '|', '\t', ' ']:
        if delimiter in line:
            parts = line.split(delimiter)
            for part in reversed(parts):
                part = part.strip()
                if is_valid_token(part):
                    return part
    return None
def load_tokens(file_path: Path) -> List[str]:
    lines = load_file_lines(file_path)
    tokens = []
    for line in lines:
        token = extract_token(line)
        if token:
            tokens.append(token)
    seen = set()
    deduped = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped
def load_avatar_files() -> List[Path]:
    if not AVATARS_DIR.exists():
        return []
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    return [f for f in AVATARS_DIR.iterdir() if f.suffix.lower() in valid_extensions]
DISCORD_AVATAR_MAX_BYTES = 1_000_000  
def load_avatar_as_base64(image_path: Path) -> Optional[str]:
    try:
        with Image.open(image_path) as img:
            is_png = image_path.suffix.lower() == '.png'
            if is_png:
                if img.mode == 'P':
                    img = img.convert('RGBA')
            else:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
            img = img.resize((AVATAR_DIMENSION, AVATAR_DIMENSION), Image.Resampling.LANCZOS)
            img_copy = img.copy()  
            def _encode(pil_img, fmt, quality=80) -> str:
                buf = BytesIO()
                kw = {"format": fmt}
                if fmt == "JPEG":
                    kw["quality"] = quality
                    kw["optimize"] = True
                pil_img.save(buf, **kw)
                buf.seek(0)
                return base64.b64encode(buf.read()).decode()
            img_format = 'PNG' if is_png else 'JPEG'
            b64 = _encode(img_copy, img_format)
            mime = 'image/png' if img_format == 'PNG' else 'image/jpeg'
            if len(b64) > DISCORD_AVATAR_MAX_BYTES:
                work_img = img_copy.convert('RGB') if img_copy.mode in ('RGBA', 'P', 'LA') else img_copy
                mime = 'image/jpeg'
                for quality in (80, 60, 40, 20):
                    b64 = _encode(work_img, 'JPEG', quality)
                    if len(b64) <= DISCORD_AVATAR_MAX_BYTES:
                        break
                else:
                    half = max(64, AVATAR_DIMENSION // 2)
                    work_img = work_img.resize((half, half), Image.Resampling.LANCZOS)
                    for quality in (80, 60, 40):
                        b64 = _encode(work_img, 'JPEG', quality)
                        if len(b64) <= DISCORD_AVATAR_MAX_BYTES:
                            break
                    else:
                        return None  
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None
def parse_proxy(proxy_string: str) -> Optional[str]:
    proxy = proxy_string.strip()
    if proxy.startswith('#'):
        return None
    if '://' in proxy:
        parsed = urlparse(proxy)
        if parsed.hostname and parsed.port:
            return proxy
        return None
    if '@' in proxy:
        at_idx = proxy.rfind('@')
        auth = proxy[:at_idx]
        hostport = proxy[at_idx + 1:]
        colon_idx = auth.find(':')
        if colon_idx == -1:
            return None
        user = auth[:colon_idx]
        password = auth[colon_idx + 1:]
        host_parts = hostport.rsplit(':', 1)
        if len(host_parts) != 2:
            return None
        host, port = host_parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    parts = proxy.split(':')
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    elif len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    return None
class Humanizer:
    def __init__(self, token: str, proxy: Optional[str] = None):
        self.token = token
        self.proxy = proxy
        self.client = primp.Client(
            verify=False,
            proxy=parse_proxy(proxy) if proxy else None
        )
        self.user_agent = DEFAULT_USER_AGENT
        self.session_id = None
        self.proxy_failed = False
        self.is_locked = False
        self.installation_id = f"{random.randint(10**18, 10**19 - 1)}.{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=22))}"
        self._launch_id = str(uuid.uuid4())
        self._signature = str(uuid.uuid4())
        self._heartbeat_id = str(uuid.uuid4())
        self._native_build = random.randint(65600, 65800)
        self._super_props = generate_super_properties(
            self._launch_id, self._signature, self._heartbeat_id, self._native_build
        )
    def get_fingerprint(self):
        try:
            r = self.client.get("https://discord.com/api/v9/experiments", timeout=30)
            if r.status_code == 200:
                return r.json().get("fingerprint")
        except:
            pass
        return None
    async def _send_identify(self, ws) -> bool:
        try:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if hello.get("op") != 10:
                return False
            identify_payload = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Windows",
                        "browser": "Discord Client",
                        "release_channel": "stable",
                        "client_version": DISCORD_CLIENT_VERSION,
                        "os_version": "10.0.26100",
                        "os_arch": "x64",
                        "app_arch": "x64",
                        "system_locale": "en-US",
                        "browser_user_agent": self.user_agent,
                        "browser_version": ELECTRON_VERSION,
                        "os_sdk_version": "26100",
                        "client_build_number": BUILD_NUMBER,
                        "native_build_number": self._native_build,
                        "client_event_source": None,
                        "design_id": 0
                    },
                    "presence": {
                        "status": "online",
                        "since": 0,
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "client_state": {
                        "guild_versions": {},
                        "highest_last_message_id": "0",
                        "read_state_version": 0,
                        "user_guild_settings_version": -1,
                        "user_settings_version": -1,
                        "private_channels_version": "0",
                        "api_code_version": 0
                    }
                }
            }
            await ws.send(json.dumps(identify_payload))
            return True
        except Exception:
            return False
    async def _wait_for_ready(self, ws) -> bool:
        for _ in range(12):     
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                op = msg.get("op")
                t = msg.get("t")
                if op == 11 or (op == 0 and t != "READY"):
                    continue
                if t == "READY":
                    self.session_id = msg["d"].get("session_id")
                    return True
                if op == 9:
                    return False
            except asyncio.TimeoutError:
                break
        return False
    async def update_account_with_live_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(self, "is_locked", False):
            return {"success": False, "error": "Token Locked"}
        headers = self.get_headers()
        loop = asyncio.get_event_loop()
        if "avatar" not in payload:
            direct = await loop.run_in_executor(None, lambda: self.update_user_profile(payload, headers))
            if direct.get("success") or direct.get("captcha") or direct.get("rate_limited"):
                return direct
            if not direct.get("unknown_session"):
                return direct
        async def _ws_patch(ws) -> Dict[str, Any]:
            if not await self._send_identify(ws):
                return {"success": False, "error": "Gateway IDENTIFY failed"}
            if not await self._wait_for_ready(ws):
                return {"success": False, "error": "Gateway READY timeout"}
            return await loop.run_in_executor(None, lambda: self.update_user_profile(payload, headers))
        try:
            extra_headers = {"User-Agent": self.user_agent}
            if self.proxy:
                proxy = Proxy.from_url(self.proxy)
                sock = await proxy.connect(dest_host="gateway.discord.gg", dest_port=443)
                async with websockets.connect(
                    DISCORD_GATEWAY,
                    additional_headers=extra_headers,
                    sock=sock,
                    server_hostname="gateway.discord.gg",
                    open_timeout=60,
                    close_timeout=10,
                    max_size=None   
                ) as ws:
                    return await _ws_patch(ws)
            else:
                async with websockets.connect(
                    DISCORD_GATEWAY,
                    additional_headers=extra_headers,
                    open_timeout=60,
                    close_timeout=10,
                    max_size=None   
                ) as ws:
                    return await _ws_patch(ws)
        except Exception as e:
            err_str = str(e)
            if not err_str:
                err_str = type(e).__name__
            if self.proxy and ("proxy" in err_str.lower() or "connect" in err_str.lower()):
                self.proxy_failed = True
            return {"success": False, "error": err_str}
    def update_account_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        max_retries = 2
        last_error = None
        for attempt in range(max_retries):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.update_account_with_live_session(payload), _async_loop
                )
                result = future.result()
                if result["success"]:
                    return result
                error = str(result.get("error", ""))
                if self._is_transient_error(error):
                    last_error = self._clean_error(error)
                    if proxy_manager and attempt < max_retries - 1:
                        new_proxy = proxy_manager.get_proxy()
                        if new_proxy:
                            self.proxy = new_proxy
                            self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                        continue
                return result
            except Exception as e:
                last_error = self._clean_error(str(e))
                if attempt < max_retries - 1 and proxy_manager:
                    new_proxy = proxy_manager.get_proxy()
                    if new_proxy:
                        self.proxy = new_proxy
                        self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                    continue
        return {"success": False, "error": last_error or "Max retries reached"}
    def _clean_error(self, error) -> str:
        error = str(error)
        if "RATE_LIMIT" in error or "rate limit" in error.lower() or "too often" in error.lower():
            return "Rate Limited"
        if "curl:" in error:
            if "(56)" in error:
                return "Proxy closed"
            elif "(28)" in error:
                return "Timeout"
            elif "(7)" in error:
                return "Proxy failed"
            else:
                match = re.search(r'curl: \((\d+)\)', error)
                if match:
                    return f"Curl {match.group(1)}"
        if "Unknown Session" in error:
            return "Bad session"
        if "received 4000" in error or "4000 (private" in error:
            return "Token locked / flagged (WS 4000)"
        if "received 4001" in error:
            return "Invalid token (WS 4001)"
        if "received 4004" in error:
            return "Auth failed (WS 4004)"
        if "received 4006" in error:
            return "Session invalid (WS 4006)"
        if "Unauthorized" in error or "401" in error:
            return "Unauthorized"
        if "captcha" in error.lower():
            return "Captcha"
        if "Invalid Form Body" in error:
            return "Invalid request"
        if "message" in error and "code" in error:
            match = re.search(r"'message': '([^']+)'", error)
            if match:
                msg = match.group(1)
                if len(msg) > 25:
                    return msg[:22] + "..."
                return msg
        if len(error) > 80:
            return error[:77] + "..."
        return error
    def get_headers(self) -> Dict[str, str]:
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": self.token,
            "content-type": "application/json",
            "user-agent": self.user_agent,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-US",
            "x-discord-timezone": "Asia/Calcutta",
            "x-installation-id": self.installation_id,
            "x-super-properties": self._super_props
        }
        fp = self.get_fingerprint()
        if fp:
            headers["x-fingerprint"] = fp
        return headers
    def _is_transient_error(self, error_str: str) -> bool:
        lower = error_str.lower()
        return any(kw in lower for kw in (
            "connection", "proxy", "timeout", "reset", "connect",
            "sending", "refused", "unreachable", "eof", "read error",
            "gateway ready", "gateway identify", "gateway",
            "no close frame", "connection closed", "websocket"
        ))
    def _solve_humanize_captcha(self, error_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """A humanize request was blocked by a captcha. Solve it (manual mode opens
        the browser and waits for the user) and return the x-captcha-* headers to
        retry the request with. Returns None if it could not be solved."""
        sitekey    = error_data.get("captcha_sitekey")
        rqdata     = error_data.get("captcha_rqdata", "")
        rqtoken    = error_data.get("captcha_rqtoken", "")
        session_id = error_data.get("captcha_session_id", "")
        if not sitekey:
            return None
        _hlog("WARN", self.token, "[Captcha needed — solve it in the browser window]")
        try:
            cap_token, _ = process_hcaptcha(sitekey, rqdata, self.user_agent, proxy=self.proxy)
        except Exception as e:
            _hlog("FAILED", self.token, f"[Captcha solve error : {str(e)[:30]}]")
            return None
        if not cap_token or cap_token in ("ERROR_RATELIMIT", "ERROR_IP_REJECTED"):
            _hlog("FAILED", self.token, "[Captcha solve failed]")
            return None
        _hlog("INFO", self.token, "[Captcha solved — continuing humanize]")
        cap_headers = {"x-captcha-key": cap_token}
        if rqtoken:
            cap_headers["x-captcha-rqtoken"] = rqtoken
        if session_id:
            cap_headers["x-captcha-session-id"] = session_id
        return cap_headers

    def _api_call_with_retry(self, method: str, url: str, data: Dict[str, Any],
                              headers: Dict[str, str], max_retries: int = 5) -> Dict[str, Any]:
        if getattr(self, "is_locked", False):
            return {"success": False, "error": "Token Locked"}
        last_result = None
        headers = dict(headers)            # local copy — lets us inject captcha headers on retry
        captcha_attempts = 0
        MAX_CAPTCHA_ATTEMPTS = 2
        for attempt in range(max_retries):
            if getattr(self, "is_locked", False):
                return {"success": False, "error": "Token Locked"}
            try:
                if method.upper() == "POST":
                    resp = self.client.post(url, headers=headers, json=data, timeout=60)
                else:
                    resp = self.client.patch(url, headers=headers, json=data, timeout=60)
                if resp.status_code in (200, 204):
                    try:
                        data = resp.json() if resp.text and resp.status_code == 200 else {}
                    except Exception:
                        data = {}
                    return {"success": True, "data": data}
                try:
                    error_data = resp.json() if resp.text and resp.text.strip() else {}
                except Exception:
                    error_data = {}
                if error_data.get("captcha_key"):
                    # A captcha is required to apply this profile change. In manual
                    # mode this opens the browser and waits for the user to solve it;
                    # once solved we retry the same request with the captcha headers
                    # so the next humanize step continues.
                    if captcha_attempts < MAX_CAPTCHA_ATTEMPTS:
                        cap_headers = self._solve_humanize_captcha(error_data)
                        if cap_headers:
                            captcha_attempts += 1
                            headers.update(cap_headers)
                            continue
                    return {"success": False, "captcha": True, "error": error_data}
                if resp.status_code == 400 and isinstance(error_data, dict):
                    code = error_data.get("code")
                    if code == 10020:
                        return {"success": False, "unknown_session": True, "error": "Unknown Session"}
                    errors = error_data.get("errors", {})
                    for field_errors in errors.values():
                        for err in field_errors.get("_errors", []):
                            if err.get("code") == "AVATAR_RATE_LIMIT":
                                return {"success": False, "rate_limited": True, "retry_after": 0, "error": "Avatar Rate Limited"}
                if resp.status_code == 429:
                    try:
                        ra_header = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                        ra_body = error_data.get("retry_after", 0) if isinstance(error_data, dict) else 0
                        retry_after = float(ra_header) if ra_header else float(ra_body or 0)
                    except (TypeError, ValueError):
                        retry_after = 0
                    wait_time = max(retry_after, 1.0)
                    time.sleep(wait_time)
                    continue  
                last_result = {"success": False, "error": error_data}
                if resp.status_code in (401, 403):
                    self.is_locked = True
                    return last_result
            except Exception as e:
                error_str = str(e)
                last_result = {"success": False, "error": error_str}
                if self.proxy and self._is_transient_error(error_str):
                    self.proxy_failed = True
                if self._is_transient_error(error_str) and proxy_manager and attempt < max_retries - 1:
                    new_proxy = proxy_manager.get_proxy()
                    if new_proxy:
                        self.proxy = new_proxy
                        self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                    continue
                if attempt >= max_retries - 1:
                    return last_result
        return last_result or {"success": False, "error": "Max retries reached"}
    def update_user_profile(self, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return self._api_call_with_retry("patch", f"{DISCORD_API}/users/@me", data, headers)
    def update_profile_fields(self, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return self._api_call_with_retry("patch", f"{DISCORD_API}/users/@me/profile", data, headers)
    def set_hypesquad(self, house_id: int, headers: Dict[str, str], retry_count: int = 0) -> Dict[str, Any]:
        time.sleep(random.uniform(2, 5))
        house_name = HYPESQUAD_HOUSES.get(house_id, "Unknown")
        try:
            check = self.client.get(
                f"{DISCORD_API}/users/@me",
                headers=headers,
                timeout=30
            )
            if check.status_code == 200:
                data = check.json()
                flags = data.get("flags", 0)
                if flags & 0xE:
                    existing_house = None
                    for hid, hname in HYPESQUAD_HOUSES.items():
                        if flags & (1 << hid):
                            existing_house = hname
                            break
                    if existing_house:
                        _hlog("INFO", self.token, f"[HypeSquad Already Set : {existing_house}]")
                        return {"success": True, "house_name": existing_house, "already_set": True}
        except Exception:
            pass
        res = self._api_call_with_retry(
            "post",
            f"{DISCORD_API}/hypesquad/online",
            {"house_id": house_id},
            headers,
            max_retries=2
        )
        if res.get("success"):
            return {"success": True, "house_name": house_name}
        if retry_count < RETRY_LIMIT:
            _hlog("WARN", self.token, f"[HypeSquad Retry : {retry_count + 1}/{RETRY_LIMIT} for {house_name}]")
            time.sleep(random.uniform(2.0, 4.0))
            return self.set_hypesquad(house_id, headers, retry_count + 1)
        return {"success": False, "error": f"HypeSquad {house_name} not applied - Account may already have a badge or is rate limited", "house_name": house_name}
    def process(self, names: List[str], bios: List[str], pronouns_list: List[str],
                avatar_files: List[Path], avatar_loader) -> bool:
        headers = self.get_headers()
        success = True
        parallel_tasks = []
        account_payload = {}
        avatar_name = None
        if UPDATE_AVATAR and avatar_files:
            avatar_path = random.choice(avatar_files)
            avatar_b64 = avatar_loader(avatar_path)
            if avatar_b64:
                account_payload["avatar"] = avatar_b64
                av_hash = hashlib.md5(avatar_b64[:100].encode()).hexdigest()
                now = datetime.now()
                now_str = now.strftime("%B {d}, %Y at {t}").format(
                    d=now.day,
                    t=now.strftime("%I:%M %p").lstrip("0")
                )
                account_payload["avatar_description"] = f"{av_hash}, added {now_str}"
                avatar_name = avatar_path.name
        display_name = None
        if UPDATE_DISPLAY_NAME and names:
            display_name = random.choice(names)
            account_payload["global_name"] = display_name
        if account_payload:
            parallel_tasks.append(("account", (account_payload, avatar_name, display_name)))
        profile_payload = {}
        bio = None
        if UPDATE_BIO and bios:
            bio = random.choice(bios)
            profile_payload["bio"] = bio
        pronouns = None
        if UPDATE_PRONOUNS and pronouns_list:
            pronouns = random.choice(pronouns_list)
            profile_payload["pronouns"] = pronouns
        if profile_payload:
            parallel_tasks.append(("profile", (profile_payload, bio, pronouns)))
        house_id = None
        house_name = None
        if UPDATE_HYPESQUAD:
            time.sleep(random.uniform(0, 3))
            house_id = random.choice([1, 2, 3])
            house_name = HYPESQUAD_HOUSES[house_id]
            parallel_tasks.append(("hypesquad", (house_id, house_name)))
        if parallel_tasks:
            def _run_field(task_type, value):
                if getattr(self, "is_locked", False):
                    return (task_type, {"success": False, "error": "Token Locked"}, value)
                h = headers.copy()
                if task_type == "account":
                    payload, _, _ = value
                    if "avatar" in payload:
                        return ("account", self.update_account_sync(payload), value)
                    else:
                        return ("account", self.update_user_profile(payload, h), value)
                elif task_type == "profile":
                    payload, _, _ = value
                    return ("profile", self.update_profile_fields(payload, h), value)
                elif task_type == "hypesquad":
                    hid, _ = value
                    return ("hypesquad", self.set_hypesquad(hid, h), value)
                return ("unknown", {"success": False, "error": "Unknown field type"}, value)
            with ThreadPoolExecutor(max_workers=len(parallel_tasks)) as field_executor:
                futures = [field_executor.submit(_run_field, tt, val) for tt, val in parallel_tasks]
                for future in as_completed(futures):
                    try:
                        task_type, result, values = future.result()
                    except Exception as e:
                        _hlog("FAILED", self.token, f"[Field Error : {str(e)[:30]}]")
                        success = False
                        continue
                    if task_type == "account":
                        _, aname, dname = values
                        if result["success"]:
                            pass
                        elif result.get("captcha"):
                            if aname: _hlog("WARN", self.token, "[Avatar Failed : Captcha]")
                            if dname: _hlog("WARN", self.token, "[Name Failed : Captcha]")
                            success = False
                        elif result.get("rate_limited"):
                            ra = result.get("retry_after", 0)
                            ra_str = f"{int(ra)}s" if ra else "unknown"
                            if aname: _hlog("WARN", self.token, f"[Avatar Failed : Rate Limited ({ra_str})]")
                            if dname: _hlog("WARN", self.token, f"[Name Failed : Rate Limited ({ra_str})]")
                            success = False
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            if aname: _hlog("FAILED", self.token, f"[Avatar Failed : {error_msg}]")
                            if dname: _hlog("FAILED", self.token, f"[Name Failed : {error_msg}]")
                            success = False
                    elif task_type == "profile":
                        _, bname, pname = values
                        if result["success"]:
                            pass
                        elif result.get("captcha"):
                            if bname: _hlog("WARN", self.token, "[Bio Failed : Captcha]")
                            if pname: _hlog("WARN", self.token, "[Pronouns Failed : Captcha]")
                            success = False
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            if bname: _hlog("FAILED", self.token, f"[Bio Failed : {error_msg}]")
                            if pname: _hlog("FAILED", self.token, f"[Pronouns Failed : {error_msg}]")
                            success = False
                    elif task_type == "hypesquad":
                        _, hsname = values
                        if result.get("success"):
                            applied_house = result.get("house_name", hsname)
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            _hlog("FAILED", self.token, f"[HypeSquad Failed : {hsname} - {error_msg}]")
                            success = False
        if self.proxy_failed and proxy_manager:
            proxy_manager.mark_bad(self.proxy)
        return success
def process_token(token: str, names: List[str], bios: List[str], pronouns_list: List[str],
                  avatar_files: List[Path], avatar_loader) -> bool:
    proxy = proxy_manager.get_proxy() if proxy_manager else None
    humanizer = Humanizer(token, proxy)
    try:
        return humanizer.process(names, bios, pronouns_list, avatar_files, avatar_loader)
    finally:
        if proxy_manager and proxy:
            proxy_manager.release_proxy(proxy)
def stats_updater():
    while True:
        time.sleep(2)
        with stats_lock:
            total = stats['total']
            gen = stats['generated']
            ver = stats['verified']
            cap_fail = stats['captcha_failed']
            cap_solved = stats['captcha_solved']
            locked = stats['locked']
            valid = stats['valid']
        gen_pct = (gen / total * 100) if total else 0
        ver_pct = (ver / total * 100) if total else 0
        cap_fail_pct = (cap_fail / total * 100) if total else 0
        cap_solved_pct = (cap_solved / total * 100) if total else 0
        locked_pct = (locked / total * 100) if total else 0
        valid_pct = (valid / total * 100) if total else 0
        current_time = datetime.now().strftime('%H:%M')
        title = f"tdinh reg | Gen: {gen} | EV: {ver} | Cap: {cap_solved}/{cap_fail} | Locked: {locked} | Invalid: {valid} | Total: {total}"
        ctypes.windll.kernel32.SetConsoleTitleW(title)
P = "\033[38;2;121;3;255m"     
C = "\033[38;2;3;248;252m"     
G = "\033[38;2;68;255;0m"      
D = "\033[38;2;92;94;91m"      
R = "\033[0m"                  
Y = "\033[38;2;255;200;50m"
def display_banner():
    if os.name == "nt":
        os.system("")
    os.system("cls" if os.name == "nt" else "clear")
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
if __name__ == "__main__":
    display_banner()
    cap_cfg     = config.get("9captcha", {})
    manual_mode = cap_cfg.get("manual_solve", False)
    ext_mode    = cap_cfg.get("extension_solver", True)
    vps_mode    = cap_cfg.get("req_solver", False)
    # Manual mode solves captchas by hand in a visible browser — no automatic
    # solver (9cap) is used, so force the auto modes off and skip all 9cap calls.
    if manual_mode:
        ext_mode = vps_mode = False
        print(f"  {D}│{R} {D}Solver:{R} {G}Manual (solve by hand in browser){R}")
    else:
        mode_str = []
        if ext_mode: mode_str.append("Extension")
        if vps_mode: mode_str.append("Request")
        print(f"  {D}│{R} {D}Solver:{R} {G}{' + '.join(mode_str) if mode_str else 'None!'}{R}")

    # ── Key pool startup validation ───────────────────────────────────────────
    # Manual mode needs no 9cap API key, so skip key checks and key-balance calls.
    if not manual_mode:
        _n_keys = _key_pool.total()
        if _n_keys == 0:
            print(f"  {Fore.RED}⚠ No 9Captcha API key set!{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}  Set 9captcha.api_key  OR  9captcha.api_keys[] in config.json{Style.RESET_ALL}")
            sys.exit(1)

        print(f"  {D}│{R} {C}Checking {_n_keys} key(s)...{R}")
        from engine.extension_browser import check_key_balance
        _startup_valid = False
        for _ki, _k in enumerate(_key_pool._keys):
            _valid, _credit = check_key_balance(_k, _key_pool._vps)
            _tag = f"Key #{_ki + 1}"
            _masked = f"{_k[:8]}...{_k[-6:]}" if len(_k) > 16 else _k
            if _valid and _credit > 0.001:
                print(f"  {D}│{R} {G}✓ {_tag} ({_masked}) — ${_credit:.3f}{R}")
                if not _startup_valid:        # activate first valid key
                    _key_pool._idx    = _ki
                    _key_pool._active = _k
                    _key_pool._write_active(_k)
                    _startup_valid = True
            elif _valid and _credit <= 0.001:
                print(f"  {D}│{R} {Y}⚠ {_tag} ({_masked}) — EMPTY ($0.000), skipping{R}")
            else:
                print(f"  {D}│{R} {Y}⚠ {_tag} ({_masked}) — unreachable / invalid, skipping{R}")

        if not _startup_valid:
            print(f"  {Fore.RED}⚠ FATAL: All {_n_keys} key(s) are depleted. Add credits or new keys!{Style.RESET_ALL}")
            sys.exit(1)

    if ext_mode or manual_mode:
        try:
            from engine.extension_browser import get_browser, sync_api_key
            print(f"  {D}│{R} {C}Initializing extension browser...{R}")
            # Manual mode uses the browser only as a window to solve by hand —
            # don't validate/sync a 9cap key (that would call the 9cap API).
            if not manual_mode:
                api_key_valid = sync_api_key()
                if not api_key_valid:
                    print(f"  {D}│{R} {Fore.RED}⚠ FATAL: Invalid 9Captcha API Key. Generator explicitly aborted!{R}")
                    sys.exit(1)
            print(f"  {D}│{R} {G}✓ Extension browser ready{R}")
        except SystemExit:
            raise
        except ImportError as e:
            print(f"  {D}│{R} {Fore.YELLOW}⚠ Extension browser unavailable: {e}{R}")
            print(f"  {D}│{R} {D}  pip install truedriver{R}")

        import atexit
        def cleanup_browser():
            try: get_browser().stop()
            except: pass
        atexit.register(cleanup_browser)


    if vps_mode:
        p_path = Path("input/proxies.txt")
        has_proxies = p_path.exists() and len(open(p_path).readlines()) > 0
        if not has_proxies:
            print(f"  {D}│{R} {Fore.RED}⚠ FATAL: Request solver does NOT work without proxies!{R}")
            print(f"  {D}│{R} {Fore.RED}  Our servers use datacenter IPs which Discord blocks.{R}")
            print(f"  {D}│{R} {Fore.YELLOW}  Please add quality residential proxies to input/proxies.txt{R}")
            print(f"  {D}│{R} {Fore.YELLOW}  Or switch to Extension solver in Settings >Extension solver.{R}")
            sys.exit(1)
            
    print()
    print(f'  {D}│{R} {C}Press Ctrl+X or Ctrl+C to force stop{R}')
    # ADB detection
    try:
        import subprocess as _sp
        _adb_out = _sp.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        _adb_devs = [l for l in _adb_out.stdout.strip().splitlines()[1:]
                     if 'device' in l and 'offline' not in l]
        if _adb_devs:
            adb_rotator.enabled = True
            adb_rotator._serial = _adb_devs[0].split()[0]
            print(f'  {D}│{R} {G}✓ ADB device found: {adb_rotator._serial} — IP rotation enabled{R}')
        else:
            print(f'  {D}│{R} {D}  ADB: no device detected — running without IP rotation{R}')
    except Exception:
        print(f'  {D}│{R} {D}  ADB: not available{R}')
    # Mullvad relay rotation status
    if mullvad_mgr and mullvad_mgr.enabled:
        if not mullvad_mgr.exe:
            print(f'  {D}│{R} {Fore.YELLOW}  Mullvad enabled but CLI not found — relay will NOT rotate{R}')
        elif mullvad_mgr.rotate_on_cooldown:
            print(f'  {D}│{R} {G}✓ Mullvad VPN enabled — relay rotates each account{R}')
        else:
            print(f'  {D}│{R} {D}  Mullvad VPN enabled (relay rotation off in config){R}')
    print()
    NUM_THREADS = int(config.get("threads", 1))
    semaphore = threading.Semaphore(NUM_THREADS)
    _stop_event = threading.Event()
    def _signal_handler(sig, frame):
        if not _stop_event.is_set():
            _stop_event.set()
            print(f"\n  {Fore.YELLOW}⚠ Halting generator immediately...{R}")
            os._exit(0)
    import signal
    signal.signal(signal.SIGINT, _signal_handler)
    try:
        import keyboard
        keyboard.add_hotkey('ctrl+x', lambda: _signal_handler(None, None))
    except Exception:
        pass
    stats_thread = threading.Thread(target=stats_updater, daemon=True)
    stats_thread.start()
    def worker(current_num):
        proxy = proxy_manager.pop_top()
        mail_api_temp, mail_provider_name_temp = get_mail_provider()
        if not mail_api_temp:
            mail_api_temp = DEVSMailApi(logger=print)
        email = mail_api_temp.create_account(proxy=proxy)
        if not email:
            Log.error('emails are not available')
            semaphore.release()
            return
        username = _random_username()
        mail_pass = None
        if hasattr(mail_api_temp, '_email_data') and isinstance(mail_api_temp._email_data, dict):
            mail_pass = mail_api_temp._email_data.get('password')
        elif hasattr(mail_api_temp, 'password') and mail_api_temp.password:
            mail_pass = mail_api_temp.password
        password = mail_pass if mail_pass else _random_password()
        try:
            generate_9DEVS_token(email, username, password, proxy, current_num, mail_api_temp, mail_provider_name_temp)
        finally:
            # 10-second cooldown between accounts
            log._emit('SESSION', '[Cooldown] Waiting 90s before next account...')
            time.sleep(90)
            # ADB IP rotation after cooldown
            if adb_rotator.enabled:
                threading.Thread(target=adb_rotator.rotate, daemon=True).start()
            # Mullvad relay rotation — synchronous so the new exit IP is live
            # before the slot is released and the next account starts.
            if _mullvad_should_rotate():
                _mullvad_rotate()
            semaphore.release()
    while not _stop_event.is_set():
        semaphore.acquire()
        if _stop_event.is_set():
            semaphore.release()
            break
        with gen_lock:
            gen_count += 1
            current_num = gen_count
        t = threading.Thread(target=worker, args=(current_num,), daemon=True)
        t.start()
    print(f"  {G}✓ Generator stopped cleanly.{R}")
