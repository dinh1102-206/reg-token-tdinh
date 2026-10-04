
import asyncio
import base64
import json
import os
import re
import threading
import time
import random
from pathlib import Path
BROWSER_WIDTH  = 400
BROWSER_HEIGHT = 580
MAX_CONCURRENT = 3
TASK_TIMEOUT   = 90       
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
EXTENSION_DIR = os.path.join(PROJECT_ROOT, "extension")
EXT_CONFIG_FILE = os.path.join(EXTENSION_DIR, "config.json")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<script src="https://js.hcaptcha.com/1/api.js?onload=hcaptchaOnLoad" async defer></script>
</head><body>
<div class="h-captcha" data-sitekey="SITE_KEY"></div>
</body></html>"""
def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def _resolve_solver_key(config=None):
    """Pick solver key: 9captcha.api_key → 9captcha.api_keys[0] → nopecha_key."""
    if config is None:
        config = _load_config()
    cap = config.get("9captcha") or {}
    key = (cap.get("api_key") or "").strip()
    if not key:
        keys = cap.get("api_keys") or []
        if keys:
            key = str(keys[0]).strip()
    if not key:
        key = str(config.get("nopecha_key") or "").strip()
    return key

def _write_extension_key(api_key: str) -> bool:
    """Write key into extension/config.json so the loaded extension picks it up."""
    try:
        os.makedirs(EXTENSION_DIR, exist_ok=True)
        ext_cfg = {}
        if os.path.exists(EXT_CONFIG_FILE):
            try:
                with open(EXT_CONFIG_FILE, "r", encoding="utf-8") as f:
                    ext_cfg = json.load(f) or {}
            except Exception:
                ext_cfg = {}
        ext_cfg["api_key"] = api_key
        # NopeCHA / 9cap extensions often also read these aliases
        ext_cfg["key"] = api_key
        ext_cfg["nopecha_key"] = api_key
        with open(EXT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(ext_cfg, f, indent=4)
        # verify
        with open(EXT_CONFIG_FILE, "r", encoding="utf-8") as f:
            check = json.load(f)
        ok = check.get("api_key") == api_key
        if ok:
            print(f"  [EXT] Key written → extension/config.json ({api_key[:6]}… len={len(api_key)})")
        return ok
    except Exception as e:
        print(f"  [EXT] Failed writing extension key: {e}")
        return False

def sync_api_key():
    
    config = _load_config()
    api_key = _resolve_solver_key(config)
    vps_url = config.get("9captcha", {}).get("vps_url", "https://9captcha-api.pridesmp.fun")
    if not api_key:
        print("  [EXT] No solver key (9captcha.api_key / api_keys / nopecha_key)")
        return False
    # Always inject into extension config first (works for NopeCHA + 9cap ext)
    _write_extension_key(api_key)
    try:
        import requests
        resp = requests.post(
            f"{vps_url}/captcha/api/activate",
            json={"api_key": api_key},
            timeout=10
        )
        data = resp.json()
        if not data.get("success"):
            print(f"  [EXT] ✗ Key validation failed: {data.get('error', 'Unknown')}")
            return False
        solver_key = data.get("solver_key", "")
        backend_url = data.get("backend_url", "https://9captcha-api.pridesmp.fun/captcha/api/ext")
        credit = data.get("credit", 0)
        if credit <= 0:
            print(f"  ✗ Key validation failed: Insufficient credits ({credit})")
            return False
        ext_cfg = {}
        if os.path.exists(EXT_CONFIG_FILE):
            try:
                with open(EXT_CONFIG_FILE, "r") as f:
                    ext_cfg = json.load(f)
            except Exception:
                pass
        ext_cfg["api_key"] = api_key
        with open(EXT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(ext_cfg, f, indent=4)
        return api_key
    except Exception as e:
        print(f"  [EXT] ✗ Key exchange failed: {e}")
        return None


def check_key_balance(api_key: str, vps_url: str = None):
    """
    Check balance for a specific API key without changing any config.
    Returns (is_valid: bool, credit: float).  credit=-1 means network error.
    NOTE: credit is kept as float — $0.952 must NOT be truncated to int(0).
    """
    if not vps_url:
        try:
            vps_url = _load_config().get("9captcha", {}).get(
                "vps_url", "https://9captcha-api.pridesmp.fun"
            )
        except Exception:
            vps_url = "https://9captcha-api.pridesmp.fun"
    try:
        import requests
        resp = requests.post(
            f"{vps_url}/captcha/api/activate",
            json={"api_key": api_key},
            timeout=10,
        )
        data = resp.json()
        if not data.get("success"):
            return False, 0.0
        credit = float(data.get("credit", 0))
        return True, credit
    except Exception:
        return False, -1.0


def activate_key_in_extension(api_key: str, vps_url: str = None):
    """
    Write a specific key into the extension config so the browser picks it up
    on next initialisation.  Returns True on success.
    """
    if not vps_url:
        try:
            vps_url = _load_config().get("9captcha", {}).get(
                "vps_url", "https://9captcha-api.pridesmp.fun"
            )
        except Exception:
            vps_url = "https://9captcha-api.pridesmp.fun"
    try:
        ext_cfg = {}
        if os.path.exists(EXT_CONFIG_FILE):
            with open(EXT_CONFIG_FILE, "r") as f:
                ext_cfg = json.load(f)
        ext_cfg["api_key"] = api_key
        with open(EXT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(ext_cfg, f, indent=4)
        return True
    except Exception:
        return False
def _is_token_like(value):
    if not isinstance(value, str):
        return False
    token = value.strip()
    if len(token) < 25:
        return False
    return bool(re.search(r"[A-Za-z0-9_.-]{25,}", token))
def _encode_base64(text):
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
class ExtensionBrowser:
    
    def __init__(self):
        self.browser = None
        self.browser_lock = asyncio.Lock()
        self.semaphore = None
        self._initialized = False
        self._loop = None
        self._loop_thread = None
        self._solve_count = 0
        self._clear_every = 5
        self._last_proxy = None
        self._proxy_user = None
        self._proxy_pass = None
    def _ensure_loop(self):
        
        if self._loop and self._loop.is_running():
            return
        def run():
            self._loop = asyncio.new_event_loop()
            self._loop.set_exception_handler(lambda loop, ctx: None)
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        self._loop_thread = threading.Thread(target=run, daemon=True)
        self._loop_thread.start()
        for _ in range(50):
            if self._loop and self._loop.is_running():
                break
            time.sleep(0.1)
    async def _stop_browser(self):
        if self.browser:
            try:
                await asyncio.wait_for(self.browser.stop(), timeout=3)
            except Exception:
                pass
            self.browser = None
            self._initialized = False
    async def _init_async(self, proxy=None):
        
        needs_restart = False
        if proxy != self._last_proxy and self._initialized:
            needs_restart = True
        if needs_restart:
            await self._stop_browser()
        if self._initialized and self.browser:
            return
        import truedriver as td
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        # Inject key into extension always (NopeCHA needs it even when browser is visible).
        # manual_solve only means "wait for human if auto fails" — still load key for auto-ext.
        _cfg = _load_config()
        _manual = (_cfg.get("9captcha") or {}).get("manual_solve", False)
        solver_key = sync_api_key()  # writes extension/config.json; may be False if no key
        if not solver_key:
            solver_key = _resolve_solver_key(_cfg)
            if solver_key:
                _write_extension_key(solver_key)
        if _manual and not solver_key:
            print("  [EXT] MANUAL — no key; solve by hand")
        extension_dir = os.path.abspath(EXTENSION_DIR)
        import hashlib
        import tempfile
        import shutil
        
        # Hash proxy to create a dedicated, persistent but isolated profile per IP.
        # This allows hCaptcha to build a trust session per-proxy without corrupting the Chrome extension worker!
        safe_proxy_id = hashlib.md5((proxy or "default").encode()).hexdigest()[:12]
        persist_profile = os.path.join(tempfile.gettempdir(), f"cap9_node_{safe_proxy_id}")
        
        browser_args = [
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--lang=en-US",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--remote-debugging-port=0",
            "--enable-unsafe-extension-debugging",
            "--no-sandbox",
            "--disable-features=CalculateNativeWinOcclusion",
            f"--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}",
            f"--user-data-dir={persist_profile}"
        ]
        ext_exists = os.path.exists(extension_dir) and Path(extension_dir).joinpath("manifest.json").exists()
        if ext_exists:
            browser_args.append(f"--disable-extensions-except={extension_dir}")
            browser_args.append(f"--load-extension={extension_dir}")
            browser_args.append(
                "--disable-features=DisableDisableExtensionsExceptCommandLineSwitch,DisableLoadExtensionCommandLineSwitch"
            )
        
        self._proxy_user = None
        self._proxy_pass = None
        # show_browser=true (default) -> visible window; false -> headless (hidden).
        # Manual solve always forces a visible window so the captcha can be solved.
        show_browser = _load_config().get("show_browser", True)
        _headless = False if _manual else (not show_browser)
        td_kwargs = {"browser_args": browser_args, "sandbox": False, "headless": _headless}
        if proxy:
            user_pwd = None
            server_str = proxy
            if "@" in proxy:
                user_pwd, server_str = proxy.split("@", 1)
            server_url = f"http://{server_str}" if "://" not in server_str else server_str
            if user_pwd and ":" in user_pwd:
                user, pwd = user_pwd.split(":", 1)
                self._proxy_user = user
                self._proxy_pass = pwd
                td_kwargs["proxy"] = {"server": server_url, "username": user, "password": pwd}
            else:
                td_kwargs["proxy"] = server_url
        self._last_proxy = proxy

        self.browser = await asyncio.wait_for(
            td.start(**td_kwargs),
            timeout=45,
        )
        self._initialized = True

        if solver_key and isinstance(solver_key, str):
            try:
                await self.browser.get(f"https://9captcha-api.pridesmp.fun/setup#key={solver_key}|base_api=https://9captcha-api.pridesmp.fun/captcha/api/ext")
                await asyncio.sleep(4)
            except Exception as e:
                print(f"  [EXT] ✗ Failed to inject API key into storage: {e}")
    async def _solve_async(self, sitekey, url, rqdata="", user_agent="", timeout=TASK_TIMEOUT, proxy=None):
        
        import truedriver as td
        from truedriver.cdp.fetch import HeaderEntry, RequestPattern, RequestStage
        from truedriver.cdp.network import ResourceType
        proxy_changed = proxy != self._last_proxy
        if not self._initialized or proxy_changed:
            await self._init_async(proxy=proxy)
        _cap_cfg = _load_config().get("9captcha", {})
        if _cap_cfg.get("manual_solve", False):
            timeout = max(timeout, int(_cap_cfg.get("manual_timeout", 300)))
            print(f"  [EXT] MANUAL MODE — solve the hCaptcha in the browser window (up to {timeout}s)...", flush=True)
        await self.semaphore.acquire()
        page = None
        target_base_url = url.split("?", 1)[0]
        template_body = HTML_TEMPLATE.replace("SITE_KEY", sitekey)
        # hcaptcha.html can live in engine/, project root, or Browser_solver/
        _candidates = [
            os.path.join(BASE_DIR, "hcaptcha.html"),
            os.path.join(PROJECT_ROOT, "hcaptcha.html"),
            os.path.join(PROJECT_ROOT, "Browser_solver", "hcaptcha.html"),
            os.path.join(os.path.dirname(PROJECT_ROOT), "Browser_solver", "hcaptcha.html"),
        ]
        hcap_html = ""
        hcap_path = None
        for _p in _candidates:
            if os.path.isfile(_p):
                hcap_path = _p
                break
        if hcap_path:
            try:
                hcap_html = Path(hcap_path).read_text(encoding="utf-8")
            except Exception:
                hcap_html = ""
        if not hcap_html or "hcaptcha template" in hcap_html:
            # Working minimal widget (not the stub)
            _rq = (rqdata or "").replace("\\", "\\\\").replace("'", "\\'")
            hcap_html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<script src='https://js.hcaptcha.com/1/api.js' async defer></script>"
                "<style>body{margin:0;min-height:100vh;display:flex;align-items:center;"
                "justify-content:center;background:#0e1013;color:#eee;font-family:system-ui}</style>"
                "</head><body><div class='h-captcha' data-sitekey='" + sitekey + "'"
                + (" data-rqdata='" + _rq + "'" if rqdata else "")
                + " data-callback='onSolved'></div>"
                "<script>function onSolved(t){window.__hcaptcha_token=t}</script>"
                "</body></html>"
            )
        if rqdata:
            hcap_html = hcap_html.replace('Dr = t', f'Dr = "{rqdata}"')
            hcap_html = hcap_html.replace('Zr = t', f'Zr = "{rqdata}"')
        try:
            page = await self.browser.get("about:blank")
            if user_agent:
                try:
                    await page.send(td.cdp.network.set_user_agent_override(user_agent=user_agent))
                except Exception:
                    pass
            async def request_handler(event):
                request_url = event.request.url
                handled = False
                try:
                    if request_url == url or request_url.startswith(target_base_url):
                        await page.send(td.cdp.fetch.fulfill_request(
                            request_id=event.request_id, response_code=200,
                            response_headers=[HeaderEntry("Content-Type", "text/html; charset=utf-8")],
                            body=_encode_base64(template_body),
                        ))
                        handled = True
                    elif "/static/hcaptcha.html" in request_url:
                        await page.send(td.cdp.fetch.fulfill_request(
                            request_id=event.request_id, response_code=200,
                            response_headers=[HeaderEntry("Content-Type", "text/html; charset=utf-8")],
                            body=_encode_base64(hcap_html),
                        ))
                        handled = True
                    if not handled:
                        await page.send(td.cdp.fetch.continue_request(request_id=event.request_id))
                except Exception:
                    pass
            handler_patterns = [
                RequestPattern(url_pattern=f"{target_base_url}*", request_stage=RequestStage.REQUEST, resource_type=ResourceType.DOCUMENT),
                RequestPattern(url_pattern="*static/hcaptcha.html*", request_stage=RequestStage.REQUEST, resource_type=ResourceType.DOCUMENT),
                RequestPattern(url_pattern="*api.js*", request_stage=RequestStage.REQUEST, resource_type=None),
            ]
            await page.send(td.cdp.fetch.enable(patterns=handler_patterns))
            page.add_handler(td.cdp.fetch.RequestPaused, request_handler)
            await page.get(url, timeout=10)
            try:
                await asyncio.wait_for(page.evaluate("""
                    Object.defineProperty(document, 'hidden', { get: () => false });
                    Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
                    document.dispatchEvent(new Event('visibilitychange'));
                """), timeout=3)
            except Exception:
                pass
            
            noise_seed = random.randint(1, 999999)
            await page.evaluate(f"""
                (function() {{
                    const seed = {noise_seed};
                    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(type) {{
                        const ctx = this.getContext('2d');
                        if (ctx) {{
                            const imgData = ctx.getImageData(0, 0, this.width, this.height);
                            for (let i = 0; i < imgData.data.length; i += 4) {{
                                imgData.data[i] = imgData.data[i] ^ ((seed + i) % 3);
                            }}
                            ctx.putImageData(imgData, 0, 0);
                        }}
                        return origToDataURL.apply(this, arguments);
                    }};
                    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                    CanvasRenderingContext2D.prototype.getImageData = function() {{
                        const imgData = origGetImageData.apply(this, arguments);
                        for (let i = 0; i < imgData.data.length; i += 4) {{
                            imgData.data[i] = imgData.data[i] ^ ((seed + i) % 3);
                        }}
                        return imgData;
                    }};
                }})();
            """)
            start = time.time()
            while time.time() - start < timeout:
                try:
                    token = await asyncio.wait_for(page.evaluate("hcaptcha.getResponse()"), timeout=2)
                    if token and _is_token_like(token):
                        elapsed = time.time() - start
                        try:
                            import requests
                            cfg = _load_config()
                            api_key = cfg.get("9captcha", {}).get("api_key", "")
                            vps_url = cfg.get("9captcha", {}).get("vps_url", "https://9captcha-api.pridesmp.fun")
                            if api_key:
                                requests.post(f"{vps_url}/captcha/api/report_extension", json={
                                    "api_key": api_key, "siteurl": url, "task_type": "hcaptcha_basic", "token": token
                                }, timeout=5)
                        except Exception:
                            pass  # non-critical telemetry — ignore timeouts
                        return token
                except Exception:
                    pass
                await asyncio.sleep(1)
            print(f"  [EXT] ✗ Timeout after {timeout}s")
            return None
        except Exception as e:
            print(f"  [EXT] ✗ Error: {e}")
            return None
        finally:
            self._solve_count += 1
            if page:
                if self._solve_count % self._clear_every == 0:
                    try:
                        await page.send(td.cdp.network.clear_browser_cookies())
                        await page.send(td.cdp.storage.clear_cookies())
                    except Exception:
                        pass
                try:
                    page.remove_handlers(td.cdp.fetch.RequestPaused, request_handler)
                    await page.send(td.cdp.fetch.disable())
                except Exception:
                    pass
                
            await self._stop_browser()
            self.semaphore.release()
    def solve(self, sitekey, url, rqdata="", user_agent="", timeout=TASK_TIMEOUT, proxy=None):
        
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self._solve_async(sitekey, url, rqdata, user_agent, timeout, proxy=proxy),
            self._loop,
        )
        try:
            return future.result(timeout=timeout + 10)
        except Exception as e:
            print(f"  [EXT] Solve error: {e}")
            return None
    def is_ready(self):
        return self._initialized and self.browser is not None

    def stop(self):
        if self.browser:
            try:
                future = asyncio.run_coroutine_threadsafe(self.browser.stop(), self._loop)
                future.result(timeout=5)
            except Exception:
                pass

_browsers = {}
def get_browser():
    import threading
    tid = threading.get_ident()
    if tid not in _browsers:
        _browsers[tid] = ExtensionBrowser()
    return _browsers[tid]


# ─── Selenium fallback when truedriver is missing ─────────────────
def _selenium_manual_solve(sitekey, url="", rqdata="", user_agent="", timeout=300, proxy=None):
    """Open Chrome via selenium/uc; user solves hCaptcha by hand; return token."""
    import tempfile
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://js.hcaptcha.com/1/api.js" async defer></script>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0e1013;color:#eee;font-family:system-ui,sans-serif}}
.box{{background:#16191f;border:1px solid #333;border-radius:12px;padding:28px;text-align:center}}
#status{{margin-top:14px;font-size:12px;color:#f2a541}}
#status.ok{{color:#35c9a5}}
</style>
</head><body>
<div class="box">
  <div style="margin-bottom:12px;font-size:14px">Solve hCaptcha (manual)</div>
  <div class="h-captcha" data-sitekey="{sitekey}" data-rqdata="{rqdata or ''}"
       data-callback="onSolved"></div>
  <div id="status">Waiting…</div>
</div>
<script>
function onSolved(t){{window.__tok=t;document.getElementById('status').textContent='OK';document.getElementById('status').className='ok'}}
setInterval(function(){{
  var el=document.querySelector('[name="h-captcha-response"]');
  if(el&&el.value&&el.value.length>20){{window.__tok=el.value;
    document.getElementById('status').textContent='OK';document.getElementById('status').className='ok'}}
}},500);
</script>
</body></html>"""
    fd, path = tempfile.mkstemp(suffix=".html", prefix="9devs_manual_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    file_url = "file:///" + path.replace("\\", "/")
    driver = None
    try:
        try:
            import undetected_chromedriver as uc
            opts = uc.ChromeOptions()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=480,700")
            if user_agent:
                opts.add_argument(f"--user-agent={user_agent}")
            if proxy:
                p = proxy if "://" in proxy else f"http://{proxy}"
                if "@" in p:
                    p = "http://" + p.split("@", 1)[1]
                opts.add_argument(f"--proxy-server={p}")
            driver = uc.Chrome(options=opts)
            print("  [EXT] Selenium fallback (undetected-chromedriver)", flush=True)
        except Exception as e1:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=480,700")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            if user_agent:
                opts.add_argument(f"--user-agent={user_agent}")
            if proxy:
                p = proxy if "://" in proxy else f"http://{proxy}"
                if "@" in p:
                    p = "http://" + p.split("@", 1)[1]
                opts.add_argument(f"--proxy-server={p}")
            driver = webdriver.Chrome(options=opts)
            print(f"  [EXT] Selenium fallback (selenium) — uc failed: {e1}", flush=True)

        driver.get(file_url)
        print(f"  [EXT] MANUAL — solve captcha in Chrome window (timeout {timeout}s)...", flush=True)
        deadline = time.time() + max(30, int(timeout))
        while time.time() < deadline:
            try:
                tok = driver.execute_script(
                    "return window.__tok || "
                    "(document.querySelector('[name=\"h-captcha-response\"]')||{}).value || '';"
                )
            except Exception:
                print("  [EXT] Browser closed", flush=True)
                return None
            if tok and len(str(tok)) > 20:
                print("  [EXT] Token captured (selenium)", flush=True)
                return str(tok)
            time.sleep(0.5)
        print("  [EXT] Timeout (selenium manual)", flush=True)
        return None
    except Exception as e:
        print(f"  [EXT] Selenium fallback error: {e}", flush=True)
        return None
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        try:
            os.unlink(path)
        except Exception:
            pass


class _SeleniumBrowserAdapter:
    """Drop-in adapter so get_browser().solve() works without truedriver."""
    def solve(self, sitekey, url, rqdata="", user_agent="", timeout=TASK_TIMEOUT, proxy=None):
        cfg = _load_config().get("9captcha", {})
        if cfg.get("manual_solve", False):
            timeout = max(timeout, int(cfg.get("manual_timeout", 300)))
        return _selenium_manual_solve(
            sitekey=sitekey, url=url, rqdata=rqdata,
            user_agent=user_agent, timeout=timeout, proxy=proxy,
        )
    def is_ready(self):
        return True
    def stop(self):
        pass


_HAS_TRUEDRIVER = None

def _check_truedriver():
    global _HAS_TRUEDRIVER
    if _HAS_TRUEDRIVER is None:
        try:
            import truedriver  # noqa: F401
            _HAS_TRUEDRIVER = True
        except ImportError:
            _HAS_TRUEDRIVER = False
            print("  [EXT] truedriver not installed → selenium manual fallback", flush=True)
            print("  [EXT] pip install truedriver   (optional, better stealth)", flush=True)
            print("  [EXT] pip install selenium undetected-chromedriver", flush=True)
    return _HAS_TRUEDRIVER


# Override get_browser to pick backend
_orig_get_browser = get_browser

def get_browser():
    if _check_truedriver():
        return _orig_get_browser()
    # one shared selenium adapter
    tid = "selenium"
    if tid not in _browsers:
        _browsers[tid] = _SeleniumBrowserAdapter()
    return _browsers[tid]
