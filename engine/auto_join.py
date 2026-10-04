"""
Auto-join ngay sau khi reg thành công.
Hỗ trợ:
  1) OAuth2 bot join (kiểu Noirmiu) — cần bot id/secret/token + guild_id + bot đã trong server có CREATE_INSTANT_INVITE quyền add members qua oauth
  2) Invite link join — fallback nếu có invite_code

Config (config.json):
{
  "auto_join": {
    "enabled": true,
    "mode": "oauth",          // "oauth" | "invite" | "both"
    "guild_id": "SERVER_ID",
    "invite_code": "",        // discord.gg code, không cần URL
    "bot": {
      "id": "CLIENT_ID",
      "secret": "CLIENT_SECRET",
      "token": "BOT_TOKEN"
    },
    "redirect_uri": "http://localhost:3001"
  }
}
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    import requests as curl_requests  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"


def _load_cfg() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _session(proxy: Optional[str] = None):
    p = None
    if proxy:
        p_str = proxy if "://" in proxy else f"http://{proxy}"
        p = {"http": p_str, "https": p_str}
    try:
        return curl_requests.Session(impersonate="chrome120", proxies=p)
    except TypeError:
        s = curl_requests.Session()
        if p:
            s.proxies.update(p)
        return s


def _normalize_invite(code: str) -> str:
    code = (code or "").strip()
    for prefix in (
        "https://discord.gg/",
        "http://discord.gg/",
        "https://discord.com/invite/",
        "http://discord.com/invite/",
        "discord.gg/",
        "discord.com/invite/",
    ):
        if code.startswith(prefix):
            code = code[len(prefix) :]
    return code.split("?")[0].strip("/")


def join_invite(token: str, invite_code: str, proxy: Optional[str] = None) -> bool:
    invite = _normalize_invite(invite_code)
    if not invite:
        return False
    s = _session(proxy)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    }
    # gateway session_id optional — try without first
    r = s.post(
        f"https://discord.com/api/v9/invites/{invite}",
        json={},
        headers=headers,
        timeout=25,
    )
    if r.status_code in (200, 204):
        return True
    # captcha required — cannot auto without solver here
    if "captcha" in (r.text or "").lower():
        print(f"[AUTO-JOIN] invite needs captcha ({r.status_code})")
        return False
    print(f"[AUTO-JOIN] invite failed {r.status_code}: {(r.text or '')[:180]}")
    return False


def join_oauth(
    token: str,
    guild_id: str,
    bot_id: str,
    bot_secret: str,
    bot_token: str,
    redirect_uri: str = "http://localhost:3001",
    proxy: Optional[str] = None,
) -> bool:
    """Authorize guilds.join with user token then bot adds member."""
    if not all([token, guild_id, bot_id, bot_secret, bot_token]):
        print("[AUTO-JOIN] oauth missing bot/guild config")
        return False

    s = _session(proxy)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": ua,
    }

    params = {
        "client_id": bot_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "identify guilds.join",
    }
    # authorize
    body = {
        "permissions": "0",
        "authorize": True,
        "integration_type": 0,
        "location_context": {
            "guild_id": "10000",
            "channel_id": "10000",
            "channel_type": 10000,
        },
        "guild_id": str(guild_id),
    }
    try:
        r = s.post(
            "https://discord.com/api/v9/oauth2/authorize?" + urlencode(params),
            json=body,
            headers=headers,
            timeout=25,
        )
    except Exception as e:
        print(f"[AUTO-JOIN] oauth authorize error: {e}")
        return False

    if r.status_code != 200:
        print(f"[AUTO-JOIN] oauth authorize {r.status_code}: {(r.text or '')[:200]}")
        return False

    data = r.json() if r.text else {}
    location = data.get("location") or ""
    # extract code
    m = re.search(r"[?&]code=([^&]+)", location)
    if not m:
        # some responses return code field
        code = data.get("code")
        if not code:
            print(f"[AUTO-JOIN] no code in authorize response: {str(data)[:200]}")
            return False
    else:
        code = m.group(1)

    # exchange code
    try:
        tr = s.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": bot_id,
                "client_secret": bot_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=25,
        )
    except Exception as e:
        print(f"[AUTO-JOIN] token exchange error: {e}")
        return False

    if tr.status_code != 200:
        print(f"[AUTO-JOIN] token exchange {tr.status_code}: {(tr.text or '')[:200]}")
        return False

    access = tr.json().get("access_token")
    if not access:
        return False

    # user id
    me = s.get(
        "https://discord.com/api/v9/users/@me",
        headers={"Authorization": token},
        timeout=15,
    )
    if me.status_code != 200:
        print(f"[AUTO-JOIN] @me failed {me.status_code}")
        return False
    user_id = me.json().get("id")

    # bot add member
    try:
        put = s.put(
            f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}",
            json={"access_token": access},
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            timeout=25,
        )
    except Exception as e:
        print(f"[AUTO-JOIN] members.put error: {e}")
        return False

    if put.status_code in (201, 204):
        print(f"[AUTO-JOIN] oauth joined guild {guild_id}")
        return True
    # 201 created, 204 already member sometimes
    if put.status_code == 200:
        return True
    print(f"[AUTO-JOIN] members.put {put.status_code}: {(put.text or '')[:200]}")
    return False


def auto_join_after_reg(token: str, proxy: Optional[str] = None) -> bool:
    cfg = _load_cfg()
    aj = cfg.get("auto_join") or cfg.get("auth_joiner") or {}
    if aj.get("enabled") is False:
        return False

    # normalize shapes from noirmiu / auth_joiner
    bot = aj.get("bot") or {}
    guild_id = str(aj.get("guild_id") or aj.get("guildId") or (aj.get("data") or {}).get("guildId") or "")
    invite = aj.get("invite_code") or aj.get("invite") or ""
    mode = (aj.get("mode") or "oauth").lower()
    redirect = aj.get("redirect_uri") or (aj.get("web") or {}).get("url") or "http://localhost:3001"

    bot_id = str(bot.get("id") or "")
    bot_secret = str(bot.get("secret") or "")
    bot_token = str(bot.get("token") or "")

    ok = False
    if mode in ("oauth", "both", "auth") and guild_id and bot_id:
        ok = join_oauth(token, guild_id, bot_id, bot_secret, bot_token, redirect, proxy)
        if ok:
            return True
    if mode in ("invite", "both", "link") or (not ok and invite):
        if invite:
            ok = join_invite(token, invite, proxy)
    if not ok and not invite and not guild_id:
        print("[AUTO-JOIN] skip — set auto_join.guild_id (oauth) or auto_join.invite_code")
    return ok
