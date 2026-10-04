import time
import random
import re
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import cloudscraper

from main import Log, config

# Attempt to reuse properties builder from joiner
def extract_version(user_agent: str) -> str:
    m = re.search(r"Chrome/(\d+)", user_agent)
    return m.group(1) if m else "127"

def build_properties(user_agent: str) -> str:
    import base64
    import json
    version = extract_version(user_agent)
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

def get_base_headers(user_agent: str, token: str) -> dict:
    version = extract_version(user_agent)
    return {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "priority": "u=1, i",
        "referer": "https://discord.com/channels/@me",
        "sec-ch-ua": f'"Google Chrome";v="{version}", "Chromium";v="{version}", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": user_agent,
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "Europe/Berlin",
        "x-super-properties": build_properties(user_agent)
    }

class DetectBypass:
    def __init__(self, token: str, guildid: str, useragent: str, proxy: str | None = None, cfsession=None):
        p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
        self.session = curl_requests.Session(impersonate="chrome120", proxies={"http": p_str, "https": p_str} if p_str else None)
        self.cfsession = cfsession
        self.proxy = proxy
        self.token = token
        self.guildid = guildid
        self.headers = get_base_headers(useragent, token)

    def check_onboarding(self) -> bool | None:
        try:
            resp = self.session.get(f"https://discord.com/api/v9/guilds/{self.guildid}/onboarding", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return bool(data.get("enabled"))
        except:
            pass
        return None

    def check_rules(self) -> bool | None:
        try:
            resp = self.session.get(
                f"https://discord.com/api/v9/guilds/{self.guildid}/member-verification?with_guild=false&invite_code=",
                headers=self.headers, timeout=10
            )
            if resp.status_code == 200:
                return True
            if resp.status_code == 403:
                return False
        except:
            pass
        return None

    def extract_clientid(self, text: str) -> str | None:
        try:
            soup = BeautifulSoup(text, "html.parser")
            verify_link = soup.find("a", href=True, string=lambda s: s and "Verify" in s)
            if verify_link:
                href = verify_link.get("href", "")
                if "client_id=" in href:
                    return href.split("client_id=")[1].split("&")[0]
        except:
            pass
        return None

    def check_restorecord(self) -> str | bool | None:
        if not self.proxy or not self.cfsession:
            return False
        proxies = {"http": f"http://{self.proxy}", "https": f"http://{self.proxy}"}
        captcha_encounters = 0
        for _ in range(5):
            try:
                resp = self.cfsession.get(f"https://restorecord.com/verify/{self.guildid}", proxies=proxies, timeout=15)
                if resp.status_code in [307, 200]:
                    return self.extract_clientid(resp.text)
                if "Please complete the captcha to continue" in resp.text:
                    captcha_encounters += 1
                else:
                    break
            except:
                break
        if captcha_encounters == 5:
            Log._log("\033[38;2;252;248;3m⚠\033[0m", f"Restorecord detection hit Cloudflare")
            return False
        return False


class OnboardingBypass:
    def __init__(self, token: str, guildid: str, useragent: str, proxy: str | None = None):
        p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
        self.session = curl_requests.Session(impersonate="chrome120", proxies={"http": p_str, "https": p_str} if p_str else None)
        self.token = token
        self.guildid = guildid
        self.headers = get_base_headers(useragent, token)
        # Fix referer
        self.headers["referer"] = f"https://discord.com/channels/{self.guildid}/@home"

    def fetch_onboarding_data(self):
        try:
            resp = self.session.get(f"https://discord.com/api/v9/guilds/{self.guildid}/onboarding", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def bypass_onboarding(self):
        try:
            data = self.fetch_onboarding_data()
            if not data: return
            prompts = data.get("prompts", [])
            responses = []
            prompts_seen = {}
            responses_seen = {}
            current_time = int(time.time() * 1000)

            for prompt in prompts:
                pid = prompt.get("id")
                prompts_seen[pid] = current_time
                options = prompt.get("options", [])
                for opt in options:
                    responses_seen[opt.get("id")] = current_time
                if prompt.get("single_select"):
                    if prompt.get("required", False) or random.choice([True, False]):
                        if options:
                            responses.append(random.choice(options)["id"])
                else:
                    if not prompt.get("required", False):
                        if options:
                            selected = random.sample(options, k=random.randint(0, len(options)))
                            for o in selected:
                                responses.append(o["id"])
                    else:
                        for o in options:
                            responses.append(o["id"])
            if not responses:
                return

            resp = self.session.post(
                f"https://discord.com/api/v9/guilds/{self.guildid}/onboarding-responses",
                json={
                    "onboarding_responses": responses,
                    "onboarding_prompts_seen": prompts_seen,
                    "onboarding_responses_seen": responses_seen,
                },
                headers=self.headers,
                timeout=15
            )
            if resp.status_code == 200:
                Log._log("\033[38;2;68;255;0m✓\033[0m", f"{self.token[:20]}... → Bypassed Onboarding")
            else:
                Log._log("\033[38;2;255;80;80m✗\033[0m", f"Onboarding fail: {resp.text}")
        except Exception as e:
             Log._log("\033[38;2;255;80;80m✗\033[0m", f"Onboarding err: {e}")

class BypassRules:
    def __init__(self, token: str, guild_id: str, useragent: str, proxy: str | None = None):
        p_str = f"http://{proxy}" if proxy and "://" not in proxy else proxy
        self.session = curl_requests.Session(impersonate="chrome120", proxies={"http": p_str, "https": p_str} if p_str else None)
        self.token = token
        self.guild_id = guild_id
        self.headers = get_base_headers(useragent, token)

    def get_data(self):
        try:
            resp = self.session.get(f"https://discord.com/api/v9/guilds/{self.guild_id}/member-verification?with_guild=false&invite_code=", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                return d.get("version"), d.get("form_fields")
        except:
            pass
        return None, None

    def bypass_rules(self):
        try:
            version, form_fields = self.get_data()
            if not version: return
            resp = self.session.put(
                f"https://discord.com/api/v9/guilds/{self.guild_id}/requests/@me",
                headers=self.headers,
                json={"version": version, "form_fields": form_fields},
                timeout=15
            )
            if resp.status_code == 201:
                Log._log("\033[38;2;68;255;0m✓\033[0m", f"{self.token[:20]}... → Bypassed Rules")
            else:
                Log._log("\033[38;2;255;80;80m✗\033[0m", f"Rules fail: {resp.text}")
        except Exception as e:
            Log._log("\033[38;2;255;80;80m✗\033[0m", f"Rules err: {e}")

class RestoreCordBypass:
    def __init__(self, token: str, guild_id: str, client_id: str, useragent: str, proxy: str | None = None, cfsession=None):
        self.session = cfsession
        self.token = token
        self.guild_id = guild_id
        self.client_id = client_id
        self.useragent = useragent
        self.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

    def bypass(self):
        try:
            h = get_base_headers(self.useragent, self.token)
            h["X-Discord-Locale"] = "es-ES" 
            resp = self.session.post(
                "https://discord.com/api/v9/oauth2/authorize",
                params={
                    "client_id": self.client_id,
                    "response_type": "code",
                    "redirect_uri": "https://restorecord.com/api/callback",
                    "scope": "identify guilds.join",
                    "state": self.guild_id,
                },
                json={"permissions": "0", "authorize": True},
                headers=h,
                proxies=self.proxies,
                timeout=15
            )
            data = resp.json()
            if "location" not in data:
                return False
            answer = data["location"]
            for _ in range(5):
                r2 = self.session.get(answer, allow_redirects=True, proxies=self.proxies, timeout=15)
                if r2.status_code in [307, 200]:
                    Log._log("\033[38;2;68;255;0m✓\033[0m", f"{self.token[:20]}... → Restorecord Bypassed")
                    return True
                if r2.status_code == 403 and "Please complete the captcha" in r2.text:
                    continue
                return False
            return False
        except Exception as e:
            Log._log("\033[38;2;255;80;80m✗\033[0m", f"Restorecord err: {e}")
            return False
