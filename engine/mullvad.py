"""
Mullvad VPN auto-manager for 9DEVS.

Behaviour (driven by config.json -> "mullvad"):
  enabled            true/false  -> master on/off switch ("mode")
  account_number     the Mullvad account no used to log in automatically
  monitor_interval   seconds between background health checks
  rotate_on_cooldown rotate relay location when the API throttles a login

When a tool is started this module:
  * logs in automatically with the configured account number,
  * connects the tunnel,
  * if login reports "too many devices" -> revokes one device, then logs in,
  * if login is rate-limited / cooled down -> rotates the relay location,
  * runs a background monitor that, if the account gets logged out or the
    device is revoked by someone else, logs back in, disconnects, rotates the
    location and reconnects.

Everything is printed to the terminal with a [MULLVAD] tag.
"""

from logging import config
import os
import json
import shutil
import subprocess
import threading
import time

# ── ANSI colours (match start.py palette) ────────────────────────────────────
P  = "\033[38;2;121;3;255m"     # purple
C  = "\033[38;2;3;248;252m"     # cyan
G  = "\033[38;2;68;255;0m"      # green
Y  = "\033[38;2;252;248;3m"     # yellow
D  = "\033[38;2;92;94;91m"      # dim
RD = "\033[38;2;255;80;80m"     # red
R  = "\033[0m"

_BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG     = os.path.join(_BASE_DIR, "config.json")

# Reliable, widely-available exit countries used for rotation.
_FALLBACK_COUNTRIES = [
    "us","be","cz","gb", "de", "nl", "se", "fr", "ca","cy", "ch",
    "no", "dk", "fi", "es", "it", "bg","at", "be", "ie",
]


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str, colour: str = C):
    try:
        print(f"{D}[{_ts()}]{R} {P}[MULLVAD]{R} {colour}{msg}{R}", flush=True)
    except Exception:
        print(f"[{_ts()}] [MULLVAD] {msg}", flush=True)


def _load_config() -> dict:
    try:
        with open(_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _find_mullvad() -> str | None:
    """Locate the mullvad CLI executable."""
    found = shutil.which("mullvad")
    if found:
        return found
    for cand in (
        r"C:\Program Files\Mullvad VPN\resources\mullvad.exe",
        r"C:\Program Files (x86)\Mullvad VPN\resources\mullvad.exe",
        "/usr/bin/mullvad",
        "/usr/local/bin/mullvad",
    ):
        if os.path.exists(cand):
            return cand
    return None


class MullvadManager:
    def __init__(self):
        cfg = _load_config().get("mullvad", {})
        self.enabled            = bool(cfg.get("enabled", False))
        self.account            = str(cfg.get("account_number", "")).replace(" ", "").strip()
        self.monitor_interval   = int(cfg.get("monitor_interval", 30))
        self.rotate_on_cooldown = bool(cfg.get("rotate_on_cooldown", True))

        self.exe        = _find_mullvad()
        self._lock      = threading.RLock()       # serialise all CLI access
        self._monitor   = None
        self._stop      = threading.Event()
        self._countries = []
        self._loc_idx   = 0

    # ── low level CLI ────────────────────────────────────────────────────────
    def _run(self, args, timeout=60):
        """Run a mullvad CLI sub-command. Returns (rc, combined_output)."""
        if not self.exe:
            return 1, "mullvad cli not found"
        try:
            p = subprocess.run(
                [self.exe, *args],
                capture_output=True, text=True, timeout=timeout,
            )
            out = (p.stdout or "") + (p.stderr or "")
            return p.returncode, out.strip()
        except subprocess.TimeoutExpired:
            return 1, "timeout"
        except Exception as e:
            return 1, str(e)

    # ── state queries ────────────────────────────────────────────────────────
    def is_logged_in(self) -> bool:
        rc, out = self._run(["account", "get"])
        if rc != 0:
            return False
        return "not logged in" not in out.lower()

    def is_revoked(self) -> bool:
        """Device revoked by someone else -> daemon blocks with a revoked reason."""
        rc, out = self._run(["status", "-v"])
        low = out.lower()
        return ("revoked" in low) or ("not registered" in low) or ("device is offline" in low and "revoked" in low)

    def status_line(self) -> str:
        rc, out = self._run(["status"])
        return out.splitlines()[0].strip() if out else "unknown"

    def is_connected(self) -> bool:
        return self.status_line().lower().startswith("connected")

    # ── device management ────────────────────────────────────────────────────
    def _list_device_names(self):
        rc, out = self._run(["account", "list-devices"])
        if rc != 0:
            return []
        names = []
        for line in out.splitlines():
            line = line.strip()
            if not line or "devices on" in line.lower() or "device" == line.lower():
                continue
            # lines look like: "- laptop-name" or "laptop-name (uid)"
            line = line.lstrip("-").strip()
            name = line.split("(")[0].strip()
            if name:
                names.append(name)
        return names

    def revoke_one_device(self) -> bool:
        names = self._list_device_names()
        if not names:
            _log("Device list empty — nothing to revoke", Y)
            return False
        victim = names[0]
        _log(f"Account full ({len(names)} devices) — revoking '{victim}'", Y)
        rc, out = self._run(["account", "revoke-device", victim])
        if rc == 0:
            _log(f"Revoked device '{victim}'", G)
            return True
        _log(f"Failed to revoke '{victim}': {out[:120]}", RD)
        return False

    # ── location rotation ────────────────────────────────────────────────────
    def _ensure_countries(self):
        if self._countries:
            return
        rc, out = self._run(["relay", "list"], timeout=40)
        codes = []
        if rc == 0:
            for line in out.splitlines():
                # country lines start at column 0:  "Sweden (se)"
                if line and not line[0].isspace() and line.rstrip().endswith(")"):
                    code = line.rstrip()[-3:-1]
                    if code.isalpha():
                        codes.append(code.lower())
        self._countries = codes or list(_FALLBACK_COUNTRIES)

    def rotate_location(self, reconnect=True) -> bool:
        self._ensure_countries()
        if not self._countries:
            return False
        self._loc_idx = (self._loc_idx + 1) % len(self._countries)
        country = self._countries[self._loc_idx]
        _log(f"Rotating relay location -> {country.upper()}", P)
        self._run(["relay", "set", "location", country])
        if reconnect:
            return self.connect()
        return True

    # ── connect / disconnect ─────────────────────────────────────────────────
    def disconnect(self):
        self._run(["disconnect"])
        _log("Disconnected", D)

    def connect(self, timeout=30) -> bool:
        self._run(["connect"])
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.status_line()
            low = line.lower()
            if low.startswith("connected"):
                _log(f"Connected — {line}", G)
                return True
            if "blocked" in low or "error" in low:
                _log(f"Tunnel blocked: {line}", RD)
                return False
            time.sleep(2)
        _log("Connect timed out", Y)
        return False

    # ── login orchestration ──────────────────────────────────────────────────
    def login(self, max_attempts=6) -> bool:
        if not self.account:
            _log("No account_number set in config.json -> mullvad.account_number", RD)
            return False
        backoff = 5
        for attempt in range(1, max_attempts + 1):
            _log(f"Logging in (attempt {attempt}/{max_attempts})…", C)
            rc, out = self._run(["account", "login", self.account], timeout=60)
            low = out.lower()
            if rc == 0 and "too many devices" not in low:
                _log("Logged in successfully", G)
                return True

            if "too many devices" in low:
                if self.revoke_one_device():
                    time.sleep(2)
                    continue  # retry login immediately after freeing a slot
                _log("Could not free a device slot", RD)
                return False

            if any(k in low for k in ("too many requests", "throttle", "rate limit",
                                       "try again", "429", "cooldown")):
                _log(f"Login cooled down / rate-limited: {out[:100]}", Y)
                if self.rotate_on_cooldown:
                    self.rotate_location(reconnect=True)
                _log(f"Backing off {backoff}s before retry", D)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            _log(f"Login failed: {out[:120]}", RD)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        _log("Login giving up after max attempts", RD)
        return False

    # ── high level: bring the VPN fully up ───────────────────────────────────
    def ensure_connected(self) -> bool:
        if not self.enabled:
            return False
        if not self.exe:
            _log("Mullvad CLI not found — install Mullvad VPN or disable in config", RD)
            return False
        with self._lock:
            if self.is_revoked():
                _log("Device was revoked externally — re-logging in", Y)
                self._run(["account", "logout"])
            if not self.is_logged_in():
                if not self.login():
                    return False
            else:
                _log("Already logged in", D)
            ok = self.connect()
            if not ok and self.rotate_on_cooldown:
                _log("Initial connect failed — rotating location", Y)
                ok = self.rotate_location(reconnect=True)
            return ok

    # ── background monitor ───────────────────────────────────────────────────
    def _monitor_loop(self):
        _log(f"Health monitor started (every {self.monitor_interval}s)", D)
        while not self._stop.wait(self.monitor_interval):
            try:
                with self._lock:
                    if self.is_revoked():
                        _log("Account logged out / device revoked by someone else", RD)
                        self._run(["account", "logout"])
                        if self.login():
                            self.disconnect()
                            self.rotate_location(reconnect=True)
                        continue
                    if not self.is_logged_in():
                        _log("Session lost — logging back in", Y)
                        if self.login():
                            self.connect()
                        continue
                    if not self.is_connected():
                        _log("Tunnel dropped — reconnecting", Y)
                        if not self.connect() and self.rotate_on_cooldown:
                            self.rotate_location(reconnect=True)
            except Exception as e:
                _log(f"Monitor error: {e}", D)
        _log("Health monitor stopped", D)

    def start_monitor(self):
        if not self.enabled:
            return
        if self._monitor and self._monitor.is_alive():
            return
        self._stop.clear()
        self._monitor = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor.start()

    def stop_monitor(self):
        self._stop.set()


# ── module-level singleton + convenience entry point ─────────────────────────
_manager = None


def get_manager() -> MullvadManager:
    global _manager
    if _manager is None:
        _manager = MullvadManager()
    return _manager


def ensure_vpn_for_tool():
    """
    Called right before a tool is launched. If Mullvad mode is enabled in
    config.json this logs in, connects and starts the background monitor.
    No-op when disabled. Never raises — VPN problems must not crash the tool.
    """
    try:
        mgr = get_manager()
        if not mgr.enabled:
            return
        _log("VPN mode is ON — preparing tunnel before launch", C)
        mgr.ensure_connected()
        mgr.start_monitor()
    except Exception as e:
        _log(f"ensure_vpn_for_tool error: {e}", RD)



if __name__ == "__main__":
    # Manual test:  python engine/mullvad.py
    m = get_manager()
    m.enabled = True
    m.ensure_connected()
    print("status:", m.status_line())
