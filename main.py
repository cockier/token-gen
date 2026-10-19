import time
import requests
import os
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import json
import random
import string
import re
import base64
import asyncio
import signal
import atexit
import warnings
warnings.simplefilter("ignore", ResourceWarning)

def _silence_unraisable(ur):
    if ur.exc_type in (ResourceWarning, ValueError):
        return
    sys.__unraisablehook__(ur)

sys.unraisablehook = _silence_unraisable
import ctypes
import zipfile
import multiprocessing
import shutil
import itertools
import threading
import html as _html_mod
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

# ── kit (richer TUI library) ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit.logger import LogKit, Level
from kit.colors import Color, Gradient
from kit.styles import Style, BorderStyle

log = LogKit(
    name="GEN",
    name_gradient=Gradient.NEON,
    thread_safe=True,
)

try:
    import pygetwindow as gw
    import pyautogui
except ImportError:
    gw = None
    pyautogui = None

try:
    from notifypy import Notify
    _notify_available = True
except ImportError:
    _notify_available = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("nodriver").setLevel(logging.CRITICAL)
logging.getLogger("uc").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

import nodriver as uc
try:
    from humanizer import Humanizer as _Humanizer
    _HUMANIZER_AVAILABLE = True
except ImportError:
    _HUMANIZER_AVAILABLE = False

# ── NopeCHA extension ─────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
NOPECHA_ZIP     = os.path.join(BASE_DIR, "nopecha_extension.zip")
NOPECHA_DIR     = os.path.join(BASE_DIR, "nopecha")
NOPECHA_KEY = ""

if os.path.isfile(NOPECHA_ZIP) and not os.path.isdir(NOPECHA_DIR):
    with zipfile.ZipFile(NOPECHA_ZIP, "r") as zf:
        zf.extractall(NOPECHA_DIR)

nopecha_ext_path = None
if os.path.isdir(NOPECHA_DIR):
    for _item in os.listdir(NOPECHA_DIR):
        _cand = os.path.join(NOPECHA_DIR, _item)
        if os.path.isdir(_cand) and os.path.isfile(os.path.join(_cand, "manifest.json")):
            nopecha_ext_path = _cand
            break
    if not nopecha_ext_path and os.path.isfile(os.path.join(NOPECHA_DIR, "manifest.json")):
        nopecha_ext_path = NOPECHA_DIR

# ── Stdout filter ─────────────────────────────────────────────────────────────
class FilteredStdout:
    _blocked = ["successfully removed temp profile", "temp profile"]

    def __init__(self, original):
        self.original = original

    def write(self, text):
        if any(p in text.lower() for p in self._blocked):
            return
        self.original.write(text)

    def flush(self):
        self.original.flush()

    def __getattr__(self, attr):
        return getattr(self.original, attr)

sys.stdout = FilteredStdout(sys.stdout)

# ── Config ────────────────────────────────────────────────────────────────────
with open(os.path.join(BASE_DIR, "config.json"), "r") as _f:
    config = json.load(_f)

NOPECHA_KEY = config.get("nopecha_key", "")

os.makedirs("output", exist_ok=True)
TOKENS_FILE = os.path.join(BASE_DIR, "tokens.txt")

# ── Unused emails manager ─────────────────────────────────────────────────────
UNUSED_EMAILS_FILE = "unused_emails.txt"
_current_email_data = None
_email_saved_flag   = False


class UnusedEmailsManager:
    @staticmethod
    def save_unused_email(data: dict) -> bool:
        try:
            with open(UNUSED_EMAILS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
            return True
        except Exception:
            return False

    @staticmethod
    def get_unused_email() -> Optional[dict]:
        try:
            if not os.path.exists(UNUSED_EMAILS_FILE):
                return None
            with open(UNUSED_EMAILS_FILE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            if not lines:
                return None
            first, rest = lines[0], lines[1:]
            with open(UNUSED_EMAILS_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(rest) + ("\n" if rest else ""))
            return json.loads(first)
        except Exception:
            return None

    @staticmethod
    def count_unused_emails() -> int:
        try:
            if not os.path.exists(UNUSED_EMAILS_FILE):
                return 0
            with open(UNUSED_EMAILS_FILE, "r", encoding="utf-8") as f:
                return sum(1 for l in f if l.strip())
        except Exception:
            return 0


def _handle_exit(signum=None, frame=None):
    global _current_email_data, _email_saved_flag
    if _email_saved_flag or not _current_email_data:
        return
    try:
        UnusedEmailsManager.save_unused_email(_current_email_data)
        _email_saved_flag = True
    except Exception:
        pass
    if signum is not None:
        sys.exit(0)

signal.signal(signal.SIGINT,  _handle_exit)
signal.signal(signal.SIGTERM, _handle_exit)
atexit.register(_handle_exit)

# ── Proxy helpers ─────────────────────────────────────────────────────────────
def _load_proxies() -> List[str]:
    proxies = config.get("proxies", [])
    if not proxies:
        pfile = config.get("proxy_file", "proxies.txt")
        if os.path.isfile(pfile):
            with open(pfile) as f:
                proxies = [l.strip() for l in f if l.strip()]
    return proxies

def get_proxy() -> Optional[str]:
    if not config.get("use_proxy", False):
        return None
    proxies = _load_proxies()
    if not proxies:
        return None
    p = random.choice(proxies)
    if not p.startswith(("http://", "https://", "socks5://", "socks4://")):
        p = "http://" + p
    return p

def proxy_dict(proxy: Optional[str]) -> Optional[Dict]:
    return {"http": proxy, "https": proxy} if proxy else None

# ── Token / webhook helpers ───────────────────────────────────────────────────
def save_token(email: str, password: str, token: str):
    try:
        with open(TOKENS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{email}:{password}:{token}\n")
        log.success("Token saved → tokens.txt")
    except Exception as e:
        log.error(f"Failed to save token: {e}")

def send_webhook(email: str, password: str, token: str, status: str, elapsed: float, provider: str):
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        return
    try:
        embed = {
            "title": "✅ Token Generated" if token else "⚠️ Account Created (No Token)",
            "color": 0x00FF00 if status == "Email Verified" else 0xFFAA00,
            "fields": [
                {"name": "📧 Email",    "value": f"`{email}`",                                         "inline": False},
                {"name": "🔑 Password", "value": f"`{password}`",                                       "inline": True},
                {"name": "🎫 Token",    "value": f"`{token[:20]}...{token[-10:]}`" if token else "`N/A`","inline": False},
                {"name": "📌 Status",   "value": status,                                                "inline": True},
                {"name": "📬 Provider", "value": provider,                                              "inline": True},
                {"name": "⏱️ Time",     "value": f"{elapsed}s",                                        "inline": True},
            ],
            "footer":    {"text": config.get("webhook_footer", "regret.world")},
            "timestamp": datetime.utcnow().isoformat(),
        }
        requests.post(webhook_url, json={"embeds": [embed], "username": config.get("webhook_username", "regret.world")}, timeout=10)
    except Exception:
        pass

def send_notification(title, message):
    if not config.get("notify", False) or not _notify_available:
        return
    try:
        n = Notify()
        n.application_name = "rizzler"
        n.title   = title
        n.message = message
        icon = config.get("notification_icon")
        if icon and os.path.isfile(icon):
            n.icon = icon
        n.send()
    except Exception as e:
        log.error(f"Notification error: {e}")

def _resolve_click_url(raw_url: str) -> Optional[str]:
    url = _html_mod.unescape(raw_url)
    try:
        resp = requests.get(
            url, allow_redirects=False, timeout=15, verify=False,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
        )
        loc = resp.headers.get("Location", "")
        if "discord.com/verify" in loc:
            log.success("Resolved verify URL via redirect")
            return loc
        if loc:
            r2 = requests.get(loc, allow_redirects=True, timeout=15, verify=False)
            if "discord.com/verify" in r2.url:
                return r2.url
            m = re.search(r"https://discord\.com/verify\?token=[^\s\"'<>]+", r2.text)
            if m:
                return m.group(0)
    except Exception as e:
        log.warning(f"Redirect resolve error: {e}")
    try:
        resp = requests.get(url, allow_redirects=True, timeout=15, verify=False)
        if "discord.com/verify" in resp.url:
            return resp.url
        m = re.search(r"https://discord\.com/verify\?token=[^\s\"'<>]+", resp.text)
        if m:
            return m.group(0)
    except Exception:
        pass
    return None





# ── regret.world provider ─────────────────────────────────────────────────────
RW_BASE = "https://regret.world/api/v1"

class RegretWorldProvider:
    def __init__(self):
        self.key = config.get("rw_key", "")

    def _h(self):
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    _DOMAINS = ["regret.world", "hurtful.lol"]

    def get_email_account(self) -> Optional[Dict]:
        try:
            domain = random.choice(self._DOMAINS)
            r = requests.post(f"{RW_BASE}/inboxes", headers=self._h(), json={"domain": domain}, timeout=20)
            if r.status_code not in (200, 201):
                log.error(f"regret.world create failed: {r.status_code}")
                return None
            addr = r.json().get("address")
            if not addr:
                log.error("regret.world: no address in response")
                return None
            log.success(f"Inbox created: {addr}")
            return {"email": addr, "password": "", "token": "", "uuid": ""}
        except Exception as e:
            log.error(f"regret.world create error: {e}")
            return None

    def delete_inbox(self, addr: str):
        try:
            requests.delete(f"{RW_BASE}/inboxes/{addr}", headers=self._h(), timeout=10)
            log.info(f"Inbox deleted: {addr}")
        except Exception as e:
            log.warning(f"Inbox delete failed: {e}")

    def fetch_verification_url(self, email_data: Dict, timeout: int = 120) -> Optional[str]:
        addr  = email_data["email"]
        start = time.time()
        seen  = set()
        log.info("Polling regret.world inbox...")

        _click_pats = [
            r"https://click\.discord\.com/ls/click\?[^\s\"'<>]+",
            r"https://links\.discord\.com/ls/click\?[^\s\"'<>]+",
            r"https://discord\.com/verify\?token=[^\s\"'<>]+",
        ]

        while (time.time() - start) < timeout:
            try:
                r = requests.get(
                    f"{RW_BASE}/inboxes/{addr}/messages",
                    headers=self._h(), timeout=15,
                )
                if r.status_code == 200:
                    for msg in r.json().get("messages", []):
                        uid  = msg.get("uid")
                        frm  = str(msg.get("from", "")).lower()
                        subj = str(msg.get("subject", "")).lower()
                        if uid in seen or "discord" not in frm:
                            continue
                        seen.add(uid)
                        mr = requests.get(
                            f"{RW_BASE}/inboxes/{addr}/messages/{uid}",
                            headers=self._h(), timeout=15,
                        )
                        if mr.status_code != 200:
                            continue
                        body = mr.json()
                        text = body.get("text") or body.get("body") or ""
                        html = body.get("html") or ""
                        if isinstance(text, bytes):
                            text = text.decode("utf-8", errors="replace")
                        plain = text or _html_mod.unescape(html)

                        vline = re.search(r"Verify Email:\s*(https://[^\s]+)", plain)
                        if vline:
                            raw = vline.group(1).strip()
                            if "discord.com/verify" in raw:
                                log.success("Found verify link (plaintext)")
                                return raw
                            res = _resolve_click_url(raw)
                            if res:
                                return res

                        direct = re.search(r"https://discord\.com/verify\?token=[^\s\"'<>]+", plain)
                        if direct:
                            log.success("Found direct verify link")
                            return direct.group(0)

                        for pat in _click_pats[:2]:
                            m = re.search(pat, plain)
                            if m:
                                res = _resolve_click_url(m.group(0))
                                if res:
                                    return res

            except Exception as e:
                log.warning(f"regret.world poll error: {e}")

            elapsed = int(time.time() - start)
            if elapsed % 12 == 0 and elapsed:
                log.info(f"Polling inbox... ({elapsed}s)")
            time.sleep(3)

        log.warning("Verification link not found (timeout)")
        return None


def create_inbox(retries=5) -> Optional[Dict]:
    unused = UnusedEmailsManager.get_unused_email()
    if unused:
        log.info(f"Reusing saved email: {unused.get('email', '?')}")
        return unused
    if retries <= 0:
        log.error("Max retries reached for email generation")
        return None
    data = RegretWorldProvider().get_email_account()
    if data:
        return data
    log.warning(f"Failed to generate email — retrying ({retries} left)")
    send_notification("Notification", "Failed to generate mail — retrying...")
    time.sleep(1)
    return create_inbox(retries - 1)

# ── Browser helpers ───────────────────────────────────────────────────────────
_WD_PATCH = """
(function(){
  try { Object.defineProperty(navigator,'webdriver',{get:()=>undefined,configurable:true}); } catch(e){}

  var _cdc=['cdc_adoQpoasnfa76pfcZLmcfl_Array','cdc_adoQpoasnfa76pfcZLmcfl_Promise',
            'cdc_adoQpoasnfa76pfcZLmcfl_Symbol','$cdc_asdjflasutopfhvcZLmcfl_'];
  _cdc.forEach(function(k){try{delete window[k];}catch(e){}try{delete document[k];}catch(e){}});

  try { Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>8,configurable:true}); } catch(e){}
  try { Object.defineProperty(navigator,'deviceMemory',{get:()=>8,configurable:true}); } catch(e){}
  try { Object.defineProperty(navigator,'plugins',{get:()=>
    Object.assign([{name:'Chrome PDF Plugin'},{name:'Chrome PDF Viewer'},{name:'Native Client'}],{length:3}),
    configurable:true}); } catch(e){}
  try { Object.defineProperty(navigator,'languages',{get:()=>['en-US','en'],configurable:true}); } catch(e){}

  try {
    var _ia = {isInstalled:false,
      InstallState:{DISABLED:'disabled',INSTALLED:'installed',NOT_INSTALLED:'not_installed'},
      RunningState:{CANNOT_RUN:'cannot_run',READY_TO_RUN:'ready_to_run',RUNNING:'running'}};
    var _rt = {id:undefined,
      OnInstalledReason:{CHROME_UPDATE:'chrome_update',INSTALL:'install',UPDATE:'update'},
      PlatformArch:{ARM:'arm',ARM64:'arm64',X86_32:'x86-32',X86_64:'x86-64'},
      PlatformOs:{ANDROID:'android',CROS:'cros',LINUX:'linux',MAC:'mac',OPENBSD:'openbsd',WIN:'win'},
      connect:function(){},sendMessage:function(){}};
    window.chrome = window.chrome || {};
    window.chrome.app = window.chrome.app || _ia;
    window.chrome.runtime = window.chrome.runtime || _rt;
  } catch(e){}

  try { Object.defineProperty(document,'hasFocus',{value:function(){return true;},configurable:true}); } catch(e){}

  try {
    var _origPQ = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = function(p){
      if(p&&(p.name==='notifications'||p.name==='push'||p.name==='clipboard-read'||p.name==='clipboard-write'))
        return Promise.resolve({state:'denied',onchange:null});
      return _origPQ(p);
    };
  } catch(e){}
  try { if(window.Notification) Object.defineProperty(window,'Notification',{get:()=>({permission:'denied',requestPermission:()=>Promise.resolve('denied')}),configurable:true}); } catch(e){}

  try {
    if(window.outerWidth===0||window.outerHeight===0){
      Object.defineProperty(window,'outerWidth',{get:()=>window.innerWidth,configurable:true});
      Object.defineProperty(window,'outerHeight',{get:()=>window.innerHeight+88,configurable:true});
    }
  } catch(e){}
})();
"""

BROWSER_CONFIG = {
    "brave":     {"name": "Brave",         "paths": {"win32": ["C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe", "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"]}},
    "firefox":   {"name": "Firefox",       "paths": {"win32": ["C:\\Program Files\\Mozilla Firefox\\firefox.exe", "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"]}},
    "chrome":    {"name": "Chrome",        "paths": {"win32": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]}},
    "microsoft": {"name": "Edge",          "paths": {"win32": ["C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe", "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]}},
}

def activate_chrome_supreme_mode():
    if sys.platform != "win32" or not gw:
        return
    try:
        from ctypes import wintypes
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        SWP_FLAGS = 0x0002 | 0x0001 | 0x0040
        windows = (gw.getWindowsWithTitle("Brave") or
                   gw.getWindowsWithTitle("Microsoft Edge") or
                   gw.getWindowsWithTitle("Discord") or
                   gw.getWindowsWithTitle("Register"))
        if not windows:
            return
        hwnd = windows[0]._hWnd
        old  = ctypes.c_ulong()
        user32.SystemParametersInfoW(0x2000, 0, ctypes.byref(old), 0)
        user32.SystemParametersInfoW(0x2001, 0, 0, 0)
        cur = kernel32.GetCurrentThreadId()
        wth = user32.GetWindowThreadProcessId(hwnd, None)
        if cur != wth:
            user32.AttachThreadInput(cur, wth, True)
        user32.ShowWindow(hwnd, 9)
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, SWP_FLAGS)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_FLAGS)
        if cur != wth:
            user32.AttachThreadInput(cur, wth, False)
        user32.SystemParametersInfoW(0x2001, 0, old.value, 0)
    except Exception:
        pass

async def launch_browser(proxy: Optional[str] = None):
    btype  = config.get("browser", "brave")
    bcfg   = BROWSER_CONFIG.get(btype, BROWSER_CONFIG["brave"])
    exe    = next((p for p in bcfg["paths"]["win32"] if os.path.exists(p)), None)

    # randomise a realistic window size so every launch has a different geometry
    _w, _h = random.choice([
        (1280, 720), (1366, 768), (1440, 900), (1600, 900), (1920, 1080),
    ])

    args = [
        # removes navigator.webdriver without touching extension APIs
        "--disable-blink-features=AutomationControlled",

        # suppress CDP / devtools indicators
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",

        # kill every popup / dialog / overlay that can interrupt generation
        "--disable-notifications",
        "--disable-popup-blocking",          # lets our own windows open freely
        "--disable-save-password-bubble",
        "--disable-translate",
        "--disable-default-apps",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-features=Translate,AutofillServerCommunication,PrivacySandboxSettings4",
        "--disable-client-side-phishing-detection",
        "--disable-hang-monitor",
        "--disable-prompt-on-repost",
        "--disable-domain-reliability",
        "--disable-renderer-backgrounding",
        "--metrics-recording-only",
        "--safebrowsing-disable-auto-update",
        "--password-store=basic",
        "--use-mock-keychain",
        "--no-service-autorun",

        # realistic window
        f"--window-size={_w},{_h}",
        "--start-maximized",

        # keep language consistent with the en-US locale we send in headers
        "--lang=en-US",
        "--accept-lang=en-US",

        # hardware concurrency — fixed value looks less like a headless sandbox
        "--js-flags=--harmony",
    ]

    if proxy:
        args.append(f"--proxy-server={proxy}")
        log.info(f"Browser proxy: {proxy}")

    ext_paths = [nopecha_ext_path] if nopecha_ext_path and os.path.isdir(nopecha_ext_path) else []
    load_str  = ",".join(ext_paths)

    if ext_paths:
        log.info(f"NopeCHA ext path: {nopecha_ext_path}")
    else:
        log.warning("NopeCHA extension NOT found — captcha solving disabled")

    ext_args  = (
        [f"--load-extension={load_str}",
         f"--disable-extensions-except={load_str}",
         "--disable-features=DisableDisableExtensionsExceptCommandLineSwitch,DisableLoadExtensionCommandLineSwitch"]
        if ext_paths else []
    )

    import tempfile
    tmp_profile = tempfile.mkdtemp(prefix="rw_browser_")
    args.append(f"--user-data-dir={tmp_profile}")

    start_args = dict(headless=False, browser_args=[*ext_args, *args])
    if exe:
        start_args["browser_executable_path"] = exe
    else:
        log.warning(f"{bcfg['name']} not found, falling back to default")

    browser = await uc.start(**start_args)

    # patch navigator.webdriver = false and fill missing Chrome APIs
    # runs on every new document before any page JS sees it
    await browser.main_tab.send(uc.cdp.page.add_script_to_evaluate_on_new_document(
        source=_WD_PATCH
    ))

    return browser


async def _patch_page(pg):
    try:
        await pg.send(uc.cdp.runtime.evaluate(
            expression=_WD_PATCH,
            return_by_value=False,
            await_promise=False,
        ))
    except Exception:
        pass


_NAMES_FILE = os.path.join(BASE_DIR, "data", "names.txt")
_names_pool: list = []

def _load_names() -> list:
    global _names_pool
    if _names_pool:
        return _names_pool
    try:
        with open(_NAMES_FILE, "r", encoding="utf-8") as f:
            _names_pool = [l.strip() for l in f if l.strip()]
    except Exception:
        pass
    return _names_pool or ["".join(random.choices(string.ascii_letters, k=8))]

def generate_random_name() -> str:
    pool = _load_names()
    return random.choice(pool)

_UN_FIRST  = ["james","alex","ryan","tyler","jake","kyle","zack","cole","drew","sean",
               "mike","john","nick","luke","adam","eric","brad","chad","dean","troy",
               "liam","noah","owen","evan","ivan","leon","hugo","marc","theo","finn"]
_UN_LAST   = ["wilson","smith","jones","davis","moore","brown","clark","allen","scott",
               "king","hall","hill","reed","ward","ford","bell","gray","ross","wood",
               "lane","stone","nash","fox","cole","cash","duke","wade","hart","best"]
_UN_PRE    = ["xx_","x_","xX_","_","real_","its_","im_","itz_","iim_","lil_","og_",""]
_UN_SUF    = ["_xx","_x","_Xx","_","_irl","_real","_og","_lol","_xd","_tv","_yt",""]

def generate_username() -> str:
    first  = random.choice(_UN_FIRST)
    last   = random.choice(_UN_LAST)
    pre    = random.choice(_UN_PRE)
    suf    = random.choice(_UN_SUF)
    num    = str(random.randint(1, 9999)) if random.random() < 0.75 else ""
    sep    = random.choice(["_", "."])
    return f"{pre}{first}{sep}{last}{num}{suf}"

def generate_password() -> str:
    length = random.randint(12, 20)
    specials = "!@.#$%^&*-_+=?"
    pool = string.ascii_letters + string.digits + specials
    while True:
        pwd = "".join(random.choices(pool, k=length))
        # ensure at least one of each required category
        if (any(c.isupper() for c in pwd) and
            any(c.islower() for c in pwd) and
            any(c.isdigit() for c in pwd) and
            any(c in specials for c in pwd)):
            return pwd

def get_token_via_login_api(email: str, password: str, proxy: Optional[str] = None) -> Optional[str]:
    log.info("Requesting token via login API...")
    headers = {
        "authority": "discord.com", "scheme": "https", "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US",
        "content-type": "application/json", "origin": "https://discord.com",
        "referer": "https://discord.com/", "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Discord/1.0.9168 Chrome/132.0.6834.83 Electron/34.1.1 Safari/537.36",
        "x-debug-options": "bugReporterEnabled", "x-discord-locale": "en-US",
        "x-discord-timezone": "America/New_York",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MTcxIiwib3NfdmVyc2lvbiI6IjEwLjAuMjYxMDAiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJ4NjQiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBkaXNjb3JkLzEuMC45MTcxIENocm9tZS8xMzIuMC4wLjAgRWxlY3Ryb24vMzQuNS4xIFNhZmFyaS81MzcuMzYiLCJicm93c2VyX3ZlcnNpb24iOiIzNC41LjEiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjo1MTkwMDYsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjY1NzAwLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ==",
    }
    payload = {"login": email, "password": password, "undelete": False,
               "captcha_key": None, "login_source": None, "gift_code_sku_id": None}
    try:
        try:
            import tls_client
            sess = tls_client.Session(client_identifier="chrome_108")
            if proxy:
                sess.proxies = proxy_dict(proxy)
            resp = sess.post("https://discord.com/api/v9/auth/login", json=payload, headers=headers)
        except ImportError:
            resp = requests.post("https://discord.com/api/v9/auth/login", json=payload, headers=headers,
                                 timeout=15, proxies=proxy_dict(proxy))
        if resp.status_code == 200:
            token = resp.json().get("token")
            if token:
                log.success("Token retrieved")
                log.keyval("Token", f"{token[:15]}...{token[-15:]}")
                return token
            log.warning("Login OK but no token in response")
        else:
            log.warning(f"Login returned {resp.status_code}")
    except Exception as e:
        log.error(f"API login failed: {e}")
    return None

def check_token_verified(token: str, proxy: Optional[str] = None) -> bool:
    headers = {
        "authorization": token, "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.745 Chrome/138.0.7204.251 Electron/37.6.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled", "x-discord-locale": "en-US",
        "x-discord-timezone": "America/New_York",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MTcxIiwib3NfdmVyc2lvbiI6IjEwLjAuMjYxMDAiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJ4NjQiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBkaXNjb3JkLzEuMC45MTcxIENocm9tZS8xMzIuMC4wLjAgRWxlY3Ryb24vMzQuNS4xIFNhZmFyaS81MzcuMzYiLCJicm93c2VyX3ZlcnNpb24iOiIzNC41LjEiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjo1MTkwMDYsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjY1NzAwLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ==",
    }
    try:
        try:
            import tls_client
            sess = tls_client.Session(client_identifier="chrome_120")
            if proxy:
                sess.proxies = proxy_dict(proxy)
            resp = sess.get("https://discord.com/api/v9/users/@me", headers=headers)
        except Exception:
            resp = requests.get("https://discord.com/api/v9/users/@me", headers=headers,
                                timeout=10, proxies=proxy_dict(proxy))
        if resp.status_code == 200:
            return resp.json().get("verified", False)
    except Exception:
        pass
    return False

def account_ratelimit() -> int:
    try:
        hdrs = {
            "Content-Type": "application/json", "Host": "discord.com",
            "Origin": "https://discord.com", "Referer": "https://discord.com/register",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "X-Discord-Locale": "en-US", "X-Discord-Timezone": "Asia/Calcutta",
        }
        mailbaba = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=10))
        data = {
            "email": mailbaba + "@gmail.com",
            "password": config.get("discord_pass", "$TUSiCE2169#"),
            "date_of_birth": "2000-09-20", "username": mailbaba,
            "global_name": generate_random_name(), "consent": True,
            "captcha_service": "hcaptcha", "captcha_key": None,
            "invite": None, "promotional_email_opt_in": False, "gift_code_sku_id": None,
        }
        r = requests.post("https://discord.com/api/v9/auth/register", json=data, headers=hdrs)
        resp_data = r.json()
        if r.status_code == 429 or "retry_after" in resp_data:
            limit = resp_data.get("retry_after", 1)
            return int(float(limit)) + 1 if limit else 1
    except Exception as e:
        log.error(f"Ratelimit check crashed: {e}")
    return 1

def countdown_timer(duration: int):
    for i in range(duration):
        t = datetime.now().strftime("%H:%M:%S")
        c = Color.rgb(255, 180, 0)
        R = Color.RESET
        dim = Color.BRIGHT_BLACK
        sys.stdout.write(
            f"\r{dim}{t}{R} {c}[WRN]{R} Rate limited — waiting {i+1:02d}/{duration}s    "
        )
        sys.stdout.flush()
        time.sleep(1)
    print()

async def wait_for_token(page, email: str, password: str, timeout: int = 30, proxy: Optional[str] = None) -> Optional[str]:
    return get_token_via_login_api(email, password, proxy=proxy)

async def attach_phone_number(page, phone_number: str):
    try:
        await page.get("https://discord.com/channels/@me")
        await asyncio.sleep(5)
        settings_button = None
        try:
            settings_button = await page.select('button[aria-label="User Settings"]')
        except Exception:
            pass
        if not settings_button:
            try:
                settings_button = await page.find("User Settings", best_match=True)
            except Exception:
                settings_button = None
        if not settings_button:
            log.warning("Could not locate User Settings button")
            return
        await settings_button.click()
        await asyncio.sleep(2)
        try:
            mac = await page.find("My Account", best_match=True)
            await mac.click()
            await asyncio.sleep(2)
        except Exception:
            pass
        add_button = None
        try:
            add_button = await page.find("Add", best_match=True)
        except Exception:
            pass
        if add_button:
            await add_button.click()
            await asyncio.sleep(2)
        country_dropdown = None
        try:
            country_dropdown = await page.select('div[role="combobox"]')
        except Exception:
            try:
                country_dropdown = await page.find("Country", best_match=True)
            except Exception:
                pass
        if country_dropdown:
            await country_dropdown.click()
            await asyncio.sleep(1)
            try:
                opt = await page.find("Poland", best_match=True)
                if opt:
                    await opt.click()
                    await asyncio.sleep(1)
            except Exception:
                pass
        phone_input = None
        try:
            phone_input = await page.select('input[name="phone"]')
        except Exception:
            try:
                phone_input = await page.select('input[type="tel"]')
            except Exception:
                pass
        if not phone_input:
            log.warning("Could not locate phone input")
            return
        await phone_input.send_keys(phone_number)
        await asyncio.sleep(1)
        for text in ["Next", "Send", "Continue"]:
            try:
                btn = await page.find(text, best_match=True)
                if btn:
                    await btn.click()
                    break
            except Exception:
                pass
        await asyncio.sleep(2)
        c = Color.rgb(255, 180, 0)
        R = Color.RESET
        otp_code = input(f"  {c}[?]{R}  Enter OTP: ").strip()
        if not otp_code:
            log.warning("No OTP entered, skipping phone")
            return
        otp_input = None
        try:
            otp_input = await page.select('input[name="code"]')
        except Exception:
            try:
                otp_input = await page.select('input[type="tel"]')
            except Exception:
                pass
        if otp_input:
            await otp_input.send_keys(otp_code)
            await asyncio.sleep(1)
        try:
            verify_btn = await page.find("Verify", best_match=True)
            if verify_btn:
                await verify_btn.click()
                await asyncio.sleep(3)
        except Exception:
            pass
        log.success("Phone attachment flow done")
    except Exception as e:
        log.error(f"Phone attachment failed: {e}")

# ── Disboard server joiner ────────────────────────────────────────────────────
_DB_INVITE_CACHE:    list  = []
_DB_INVITE_CACHE_TS: float = 0
_DB_CACHE_TTL = 300

_SCRAPE_HDR = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
}

def _extract_codes(html: str) -> list:
    codes  = re.findall(r'discord\.gg/([A-Za-z0-9]+)', html)
    codes += re.findall(r'discord\.com/invite/([A-Za-z0-9]+)', html)
    return [c for c in codes if 4 <= len(c) <= 20]

def _scrape_disboard() -> list:
    out = []
    try:
        for pg in range(1, 5):
            r = requests.get(f"https://disboard.org/servers?page={pg}", headers=_SCRAPE_HDR, timeout=12)
            if r.status_code == 200:
                out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

def _scrape_discordme() -> list:
    out = []
    try:
        for pg in range(1, 4):
            r = requests.get(f"https://discord.me/servers/{pg}", headers=_SCRAPE_HDR, timeout=12)
            if r.status_code == 200:
                out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

def _scrape_discordscom() -> list:
    out = []
    try:
        for pg in range(1, 4):
            r = requests.get(f"https://discords.com/servers?page={pg}", headers=_SCRAPE_HDR, timeout=12)
            if r.status_code == 200:
                out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

def _scrape_disforge() -> list:
    out = []
    try:
        for pg in range(1, 4):
            r = requests.get(f"https://disforge.com/servers?page={pg}", headers=_SCRAPE_HDR, timeout=12)
            if r.status_code == 200:
                out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

def _scrape_discordlist() -> list:
    out = []
    try:
        r = requests.get("https://discordlist.gg/servers", headers=_SCRAPE_HDR, timeout=12)
        if r.status_code == 200:
            out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

def _scrape_topgg() -> list:
    out = []
    try:
        for pg in range(1, 4):
            r = requests.get(f"https://top.gg/servers?page={pg}", headers=_SCRAPE_HDR, timeout=12)
            if r.status_code == 200:
                out.extend(_extract_codes(r.text))
    except Exception:
        pass
    return out

_SCRAPERS = [
    _scrape_disboard,
    _scrape_discordme,
    _scrape_discordscom,
    _scrape_disforge,
    _scrape_discordlist,
    _scrape_topgg,
]

def _fetch_disboard_invites() -> list:
    global _DB_INVITE_CACHE, _DB_INVITE_CACHE_TS
    if _DB_INVITE_CACHE and time.time() - _DB_INVITE_CACHE_TS < _DB_CACHE_TTL:
        return _DB_INVITE_CACHE
    from concurrent.futures import ThreadPoolExecutor, as_completed
    invites = []
    with ThreadPoolExecutor(max_workers=len(_SCRAPERS)) as ex:
        futs = {ex.submit(fn): fn.__name__ for fn in _SCRAPERS}
        for fut in as_completed(futs):
            try:
                res = fut.result()
                invites.extend(res)
                if res:
                    log.info(f"Scraped {len(res)} invites from {futs[fut]}")
            except Exception:
                pass
    invites = list(set(invites))
    if invites:
        _DB_INVITE_CACHE    = invites
        _DB_INVITE_CACHE_TS = time.time()
        log.success(f"Invite pool: {len(invites)} unique codes")
    return invites

def join_random_server(token: str, proxy: Optional[str] = None) -> bool:
    pool = _fetch_disboard_invites()
    if not pool:
        log.warning("Disboard: no invites fetched")
        return False
    code = random.choice(pool)
    hdrs = {
        "accept": "*/*",
        "accept-language": "en-US",
        "authorization": token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": f"https://discord.com/invite/{code}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "America/New_York",
    }
    try:
        r = requests.post(
            f"https://discord.com/api/v9/invites/{code}",
            headers=hdrs, json={},
            proxies=proxy_dict(proxy), timeout=15,
        )
        if r.status_code in (200, 204):
            guild = r.json().get("guild", {}).get("name", code) if r.status_code == 200 else code
            log.success(f"Joined: {guild}")
            return True
        log.warning(f"Join failed {r.status_code} — {code}")
        return False
    except Exception as e:
        log.warning(f"Join error: {e}")
        return False


# ── Main registration flow ────────────────────────────────────────────────────
async def register_and_get_promo(is_last_instance=False, phone_number: Optional[str] = None):
    start_time = time.time()
    proxy = get_proxy()
    if proxy:
        log.info(f"Proxy: {proxy}")

    try:
        browser = await launch_browser(proxy=proxy)
        btype   = config.get("browser", "brave")
        log.info(f"Using {BROWSER_CONFIG.get(btype, {}).get('name', 'Browser')} browser")

        try:
            setup_page = await browser.get(f"https://nopecha.com/setup#{NOPECHA_KEY}")
            await _patch_page(setup_page)
            await asyncio.sleep(2.5)
            log.info(f"Solver initialized ({NOPECHA_KEY[:6]}***)")
        except Exception as e:
            log.warning(f"Solver setup failed: {e}")

        # realistic viewport — pick from common 16:9 / 16:10 resolutions
        _vw, _vh = random.choice([
            (1280, 720), (1366, 768), (1440, 900), (1600, 900), (1920, 1080),
        ])
        try:
            await browser.main_tab.send(uc.cdp.emulation.set_device_metrics_override(
                width=_vw, height=_vh, device_scale_factor=1.0, mobile=False,
            ))
        except Exception:
            pass

        # land on discord.com first — going straight to /register is a bot signal
        page = await browser.get("https://discord.com/")
        await _patch_page(page)
        await asyncio.sleep(random.uniform(0.4, 0.7))

        page = await browser.get("https://discord.com/register")
        await _patch_page(page)
        await asyncio.sleep(random.uniform(0.3, 0.5))

        email_data = create_inbox()
        if not email_data:
            log.error("Could not create inbox, aborting")
            return

        global _current_email_data, _email_saved_flag
        _current_email_data = email_data
        _email_saved_flag   = False

        inbox_id    = email_data["email"]
        inbox_token = generate_password()

        log.success("Mailbox ready")
        log.keyval("Email", inbox_id)
        log.keyval("Password", inbox_token)
        send_notification("Notification", "Mailbox generated.")

        global_name = generate_random_name()
        username    = generate_username()

        await page  # refresh document root — prevents stale node id after page re-render
        await asyncio.sleep(0.2)

        async def _hover_then_type(element, text: str):
            try:
                box = await element.get_position()
                cx  = int(box.x + box.width  * random.uniform(0.3, 0.7))
                cy  = int(box.y + box.height * random.uniform(0.3, 0.7))
                await page.send(uc.cdp.runtime.evaluate(
                    expression=f"document.dispatchEvent(new MouseEvent('mousemove',{{bubbles:true,clientX:{cx},clientY:{cy}}}));",
                    return_by_value=False, await_promise=False,
                ))
                await asyncio.sleep(random.uniform(0.03, 0.07))
            except Exception:
                pass
            await element.click()
            await asyncio.sleep(random.uniform(0.03, 0.06))
            for ch in text:
                await element.send_keys(ch)
                await asyncio.sleep(random.uniform(0.02, 0.06))
            await asyncio.sleep(random.uniform(0.05, 0.1))

        email_input = await page.select('input[name="email"]')
        await _hover_then_type(email_input, inbox_id)

        await asyncio.sleep(0.08)

        gn_input = await page.select('input[name="global_name"]')
        await _hover_then_type(gn_input, global_name)

        await asyncio.sleep(0.08)

        un_input = await page.select('input[name="username"]')
        await _hover_then_type(un_input, username)

        await asyncio.sleep(0.08)

        pw_input = await page.select('input[name="password"]')
        await _hover_then_type(pw_input, inbox_token)

        await asyncio.sleep(0.1)

        months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        month_elem = await page.select('div[aria-label="Month"]')
        await month_elem.click()
        await asyncio.sleep(0.2)
        month_opt = await page.find(random.choice(months), best_match=True)
        if month_opt:
            await month_opt.click()
        await asyncio.sleep(0.15)

        day_elem = await page.select('div[aria-label="Day"]')
        await day_elem.click()
        await asyncio.sleep(0.2)
        day_opt = await page.find(str(random.randint(1, 28)), best_match=True)
        if day_opt:
            await day_opt.click()
        await asyncio.sleep(0.15)

        random_year = random.randint(config.get("dob_year_min", 1995), config.get("dob_year_max", 2002))

        year_elem = await page.select('div[aria-label="Year"]')
        await year_elem.click()
        await asyncio.sleep(0.3)

        year_str = str(random_year)

        async def _raw_eval(expr: str):
            # bypass page.evaluate() — it calls DOM.getDocument internally which
            # triggers React to re-render and closes any open dropdown
            try:
                resp = await page.send(uc.cdp.runtime.evaluate(
                    expression=expr,
                    return_by_value=True,
                    await_promise=False,
                ))
                # resp is (RemoteObject, ExceptionDetails|None)
                if resp and resp[0]:
                    return resp[0].value
            except Exception:
                pass
            return None

        _year_expr = (
            "(function(){"
            "var t='%d';"
            "var lb=document.querySelector('[role=\"listbox\"]');"
            "if(!lb)return 'no_lb';"
            "var opts=lb.querySelectorAll('[role=\"option\"]');"
            "for(var i=0;i<opts.length;i++){"
            "if(opts[i].textContent.trim()===t){"
            "opts[i].click();return 'clicked:'+i;}}"
            "var sc=lb;"
            "var ch=lb.querySelectorAll('*');"
            "for(var j=0;j<ch.length;j++){"
            "var s=window.getComputedStyle(ch[j]);"
            "if((s.overflowY==='auto'||s.overflowY==='scroll')&&ch[j].scrollHeight>ch[j].clientHeight){"
            "sc=ch[j];break;}}"
            "sc.dispatchEvent(new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY:300,deltaMode:0}));"
            "sc.scrollTop+=300;"
            "return 'scroll:'+sc.scrollTop+':n'+opts.length;"
            "})()" % random_year
        )

        year_found = False
        for _s in range(80):
            val = await _raw_eval(_year_expr)
            if isinstance(val, str) and val.startswith('clicked'):
                year_found = True
                log.info(f"Year selected: {random_year}")
                break
            await asyncio.sleep(0.07)

        if not year_found:
            log.warning(f"Year {random_year} not found — aborting to prevent underage block")
            return

        await asyncio.sleep(0.15)

        try:
            await page.evaluate("""
                (() => {
                    const boxes = document.querySelectorAll('input[type="checkbox"]');
                    boxes.forEach(cb => { if (!cb.checked) { cb.click(); } });
                })()
            """)
            await asyncio.sleep(0.1)
        except Exception as _tos_err:
            log.warning(f"TOS checkbox JS: {_tos_err}")
            try:
                checkbox = await page.select('label[data-mana-component="checkbox"]')
                await checkbox.click()
            except Exception:
                pass

        await asyncio.sleep(0.1)

        create_btn = None
        try:
            create_btn = await page.select('button[type="submit"]')
        except Exception:
            pass
        if not create_btn:
            try:
                create_btn = await page.find("Create Account", best_match=True)
            except Exception:
                pass
        if create_btn:
            await asyncio.sleep(0.05)
            await create_btn.click()

        log.info("Registration form submitted")
        send_notification("Notification", "Waiting for captcha solve...")

        async def _get_current_url(pg) -> str:
            try:
                url = await pg.evaluate("window.location.href")
                if url:
                    return str(url)
            except Exception:
                pass
            try:
                return pg.url or ""
            except Exception:
                return ""

        async def _wait_for_captcha_solved(pg, timeout_seconds=300) -> bool:
            log.info("Waiting for captcha solve...")
            await asyncio.sleep(2)
            success_paths = ["discord.com/channels", "discord.com/app", "discord.com/login"]
            cur = await _get_current_url(pg)
            if any(x in cur for x in success_paths):
                log.success("No captcha — registration complete!")
                return True
            activate_chrome_supreme_mode()
            send_notification("CAPTCHA", "Auto-solving captcha...")
            log.info("Captcha solve in progress")
            start_cap = time.time()
            while (time.time() - start_cap) < timeout_seconds:
                cur = await _get_current_url(pg)
                if any(x in cur for x in success_paths):
                    log.success("Captcha solved!")
                    return True
                await asyncio.sleep(2)
            log.error(f"Captcha timeout ({timeout_seconds}s)")
            return False

        captcha_ok = await _wait_for_captcha_solved(page)
        if not captcha_ok:
            log.error("Captcha unsolvable — saving email for reuse")
            UnusedEmailsManager.save_unused_email(email_data)
            _email_saved_flag = True
            return

        await asyncio.sleep(0.3)

        max_wait          = 300
        start_wait        = time.time()
        registration_done = False
        three_dots_seen   = False

        cur = await _get_current_url(page)
        if any(x in cur for x in ["discord.com/login", "discord.com/app", "discord.com/channels"]):
            registration_done = True
            log.success("Registration completed")

        while not registration_done and time.time() - start_wait < max_wait:
            try:
                cur = await _get_current_url(page)
                if any(x in cur for x in ["discord.com/login", "discord.com/app", "discord.com/channels"]):
                    registration_done = True
                    log.success("Registration completed")
                    break
                phone_check = await page.select('input[name="phone"]')
                if phone_check:
                    log.warning("Phone verification required — account flagged")
                    break
                if not three_dots_seen:
                    try:
                        dots = await page.select('svg[width="25"][height="25"] circle[fill="#787878"]')
                        if dots and len(dots) >= 3:
                            three_dots_seen = True
                            log.info("Three dots detected — Discord processing")
                    except Exception:
                        pass
                if three_dots_seen:
                    try:
                        dots = await page.select('svg[width="25"][height="25"] circle[fill="#787878"]')
                        if not dots or len(dots) < 3:
                            three_dots_seen = False
                    except Exception:
                        pass
                await asyncio.sleep(0.5)
            except Exception as e:
                log.debug(f"Loop error: {e}")
                await asyncio.sleep(0.5)

        if not registration_done:
            log.warning("Registration timeout")
            return

        log.info("Fetching verification email...")
        mail_checker = RegretWorldProvider()
        verify_url = mail_checker.fetch_verification_url(email_data, timeout=120)
        mail_checker.delete_inbox(email_data["email"])

        verified = False
        status   = "Pending Verification"
        token    = None

        async def _extract_token_from_browser() -> Optional[str]:
            # pull token from Discord's localStorage — same session, no API fingerprint switch
            try:
                raw = await page.send(uc.cdp.runtime.evaluate(
                    expression=(
                        "(function(){"
                        "try{"
                        "var s=document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage;"
                        "var t=s.getItem('token');"
                        "if(t)return t.replace(/^\"|\"$/g,'');"
                        "}catch(e){}"
                        "try{"
                        "var k=Object.keys(localStorage);"
                        "for(var i=0;i<k.length;i++){"
                        "var v=localStorage.getItem(k[i]);"
                        "if(v&&v.length>50&&k[i]==='token')return v.replace(/^\"|\"$/g,'');"
                        "}"
                        "}catch(e){}"
                        "return null;"
                        "})()"
                    ),
                    return_by_value=True,
                    await_promise=False,
                ))
                if raw and raw[0] and raw[0].value:
                    return str(raw[0].value)
            except Exception:
                pass
            return None

        if verify_url:
            log.info("Opening verification link...")
            await page.get(verify_url)
            await asyncio.sleep(1.5)

            # try pulling token from browser localStorage first
            token = await _extract_token_from_browser()

            if not token:
                # fallback: poll login API
                verify_start = time.time()
                while time.time() - verify_start < 180:
                    temp_token = get_token_via_login_api(inbox_id, inbox_token, proxy=proxy)
                    if temp_token and check_token_verified(temp_token, proxy=proxy):
                        token = temp_token
                        break
                    await asyncio.sleep(5)

            if token:
                verified = True
                status   = "Email Verified"
                log.success("Account fully verified")
                await asyncio.sleep(0.2)
                if config.get("number_attacher", False) and phone_number:
                    await attach_phone_number(page, phone_number)
            else:
                log.warning("Verification timeout")
        else:
            log.error("No verification link found")
            status = "Pending (No Link)"
            token  = get_token_via_login_api(inbox_id, inbox_token, proxy=proxy)

    except Exception as e:
        import traceback
        log.error(f"Registration exception: {e}")
        log.error(traceback.format_exc())
        return
    finally:
        try:
            import shutil as _shutil
            _shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass

    _current_email_data = None
    total_time = round(time.time() - start_time, 2)

    _R  = Color.RESET
    _D  = Color.rgb(60, 60, 80)
    _K  = Color.rgb(110, 80, 180)
    _V  = Color.BRIGHT_WHITE
    _G  = Color.rgb(50, 220, 100)
    _W  = Color.rgb(255, 180, 0)

    def _kv(key: str, val: str, vc=None):
        vc = vc or _V
        print(f"  {_K}{key}{_R}  {_D}→{_R}  {vc}{val}{_R}")

    if token:
        log.success("Account + Token Generated")
        print(f"  {_D}{'─' * 44}{_R}")
        _kv("email   ", inbox_id)
        _kv("token   ", f"{token[:8]}...{token[-6:]}", Color.rgb(120, 220, 255))
        _kv("name    ", global_name)
        _kv("time    ", f"{total_time}s")
        _kv("status  ", status, _G)
        _kv("provider", "regret.world")
        print(f"  {_D}{'─' * 44}{_R}")
        save_token(inbox_id, inbox_token, token)
        send_webhook(inbox_id, inbox_token, token, status, total_time, "regret.world")

        hcfg = config.get("humanizer", {})
        if hcfg.get("enabled") and _HUMANIZER_AVAILABLE:
            try:
                log.info("Running humanizer...")
                _base = __import__("pathlib").Path(__file__).parent
                h = _Humanizer(token)
                ok = h.run(hcfg, _base / "avatar", _base / "data")
                if ok:
                    log.success("Humanizer done")
                else:
                    log.warning("Humanizer partial/failed")
            except Exception as _he:
                log.warning(f"Humanizer error: {_he}")

        if config.get("join_server", True):
            try:
                join_random_server(token, proxy=proxy)
            except Exception as _je:
                log.warning(f"Server join error: {_je}")
    else:
        log.warning("Account Created (No Token)")
        print(f"  {_D}{'─' * 44}{_R}")
        _kv("email   ", inbox_id)
        _kv("name    ", global_name)
        _kv("time    ", f"{total_time}s")
        _kv("status  ", status, _W)
        print(f"  {_D}{'─' * 44}{_R}")
        send_webhook(inbox_id, inbox_token, "", status, total_time, "regret.world")

    if not is_last_instance:
        if config.get("check_ratelimit", True):
            try:
                wait_time = account_ratelimit()
                send_notification("Notification", f"Ratelimited {wait_time}s")
                countdown_timer(wait_time)
            except Exception as e:
                log.error(f"Ratelimit check failed: {e}")
        else:
            delay = config.get("delay_between_runs", 5)
            if delay > 0:
                log.info(f"Waiting {delay}s before next account...")
                time.sleep(delay)


def run_register_and_get_promo(is_last_instance=False, phone_number=None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(register_and_get_promo(is_last_instance, phone_number))
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


# ── Brand palette ─────────────────────────────────────────────────────────────
POISON_GRAD   = [(18, 0, 45), (72, 0, 140), (140, 30, 240), (190, 80, 255)]
POISON_DARK   = [(10, 0, 28), (45, 0, 90),  (90, 0, 180)]
POISON_ACCENT = Color.rgb(190, 80,  255)
POISON_CYAN   = Color.rgb(110, 220, 255)
POISON_GREEN  = Color.rgb(50,  220, 100)
POISON_WARN   = Color.rgb(255, 160, 40)
POISON_ERR    = Color.rgb(255, 55,  80)
POISON_DIM    = Color.rgb(55,  35,  85)
POISON_BORDER = Color.rgb(75,  20,  140)
POISON_MID    = Color.rgb(140, 30,  240)
_R            = Color.RESET

_RW_ASCII = [
    r"██████╗ ███████╗ ██████╗ ██████╗ ███████╗████████╗",
    r"██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝",
    r"██████╔╝█████╗  ██║  ███╗██████╔╝█████╗     ██║   ",
    r"██╔══██╗██╔══╝  ██║   ██║██╔══██╗██╔══╝     ██║   ",
    r"██║  ██║███████╗╚██████╔╝██║  ██║███████╗   ██║   ",
    r"╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ",
]

_SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

def _tw() -> int:
    return shutil.get_terminal_size().columns

def _center_raw(text: str, width: int = 0) -> str:
    w   = width or _tw()
    raw = re.sub(r"\033\[[0-9;]*m", "", text)
    pad = max(0, (w - len(raw)) // 2)
    return " " * pad + text

def _spin_ok(label: str, duration: float = 0.5):
    frames = itertools.cycle(_SPINNER_FRAMES)
    end_at = time.time() + duration
    while time.time() < end_at:
        f = next(frames)
        sys.stdout.write(
            f"\r  {POISON_MID}{f}{_R}  {POISON_DIM}{label}{_R}          "
        )
        sys.stdout.flush()
        time.sleep(0.055)
    sys.stdout.write(
        f"\r  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}{label}{_R}          \n"
    )
    sys.stdout.flush()

def _type_line(text: str, delay: float = 0.012):
    parts = re.split(r"(\033\[[0-9;]*m)", text)
    for part in parts:
        if part.startswith("\033["):
            sys.stdout.write(part)
            sys.stdout.flush()
        else:
            for ch in part:
                sys.stdout.write(ch)
                sys.stdout.flush()
                time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def boot_sequence():
    os.system("cls" if os.name == "nt" else "clear")
    tw = _tw()
    print()

    n = len(_RW_ASCII)
    for i, raw_line in enumerate(_RW_ASCII):
        t      = i / max(n - 1, 1)
        seg    = min(int(t * (len(POISON_GRAD) - 1)), len(POISON_GRAD) - 2)
        lt     = t * (len(POISON_GRAD) - 1) - seg
        sr, sg, sb = POISON_GRAD[seg]
        er, eg, eb = POISON_GRAD[seg + 1]
        cr = int(sr + lt * (er - sr))
        cg = int(sg + lt * (eg - sg))
        cb = int(sb + lt * (eb - sb))
        colored  = f"{Color.rgb(cr, cg, cb)}{raw_line}{_R}"
        sys.stdout.write(_center_raw(colored, tw) + "\n")
        sys.stdout.flush()
        time.sleep(0.048)

    print()

    credits = (
        f"{POISON_DIM}discord token generator  ·  "
        f"{POISON_ACCENT}github.com/cockier{_R}"
        f"{POISON_DIM}  ·  "
        f"{POISON_CYAN}regret.world{_R}"
    )
    _type_line(_center_raw(credits, tw), delay=0.007)
    print()

    rule_w = min(tw, 70)
    rule_s = Color.multi_gradient("─" * rule_w, *POISON_GRAD)
    print(_center_raw(rule_s, tw))
    print()
    time.sleep(0.12)

    checks = [
        ("loading modules",             0.40),
        ("initialising browser engine", 0.52),
        ("connecting to mail services", 0.48),
        ("all systems ready",           0.32),
    ]
    for label, dur in checks:
        _spin_ok(label, dur)
        time.sleep(0.05)

    print()
    print(_center_raw(rule_s, tw))
    print()
    time.sleep(0.08)


def _prompt(text: str) -> str:
    return input(
        f"  {POISON_ACCENT}❯{_R}  {POISON_DIM}{text}{_R}  "
    ).strip()


def main():
    multiprocessing.freeze_support()
    boot_sequence()

    print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}regret.world{_R}  {Color.rgb(80,55,110)}disposable inbox{_R}")
    print()

    unused_count = UnusedEmailsManager.count_unused_emails()
    if unused_count > 0:
        print(f"  {POISON_ACCENT}↺{_R}  {POISON_DIM}{unused_count} cached email(s) — reusing first{_R}")
        print()

    _invite_future = None
    if config.get("join_server", True):
        import concurrent.futures as _cf
        _invite_executor = _cf.ThreadPoolExecutor(max_workers=1)
        _invite_future   = _invite_executor.submit(_fetch_disboard_invites)

    phone_number = None
    if config.get("number_attacher", False):
        phone_number = _prompt("mobile number  (otp required)")

    try:
        max_runs = int(_prompt("accounts to create"))
    except ValueError:
        print(f"  {POISON_WARN}!{_R}  {POISON_DIM}invalid — defaulting to 1{_R}")
        max_runs = 1

    if _invite_future is not None:
        try:
            _pool = _invite_future.result(timeout=30)
            if _pool:
                print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}{len(_pool)} invite codes{_R}  {POISON_DIM}server join ready{_R}")
            else:
                print(f"  {POISON_WARN}!{_R}  {POISON_DIM}no invite codes found — server join will be skipped{_R}")
        except Exception:
            print(f"  {POISON_WARN}!{_R}  {POISON_DIM}invite scrape timed out — server join will be skipped{_R}")
        print()

    print()
    tw = _tw()
    print(_center_raw(Color.multi_gradient("─" * min(tw, 70), *POISON_DARK), tw))
    print()

    run_count    = 0
    active_procs = []

    while True:
        active_procs = [p for p in active_procs if p.is_alive()]
        if len(active_procs) < 1 and (max_runs == 0 or run_count < max_runs):
            run_count += 1
            print(f"  {POISON_ACCENT}▸{_R}  {POISON_DIM}spawning account {_R}{Color.BRIGHT_WHITE}#{run_count}{_R}")
            try:
                is_last = max_runs != 0 and run_count == max_runs
                p = multiprocessing.Process(
                    target=run_register_and_get_promo,
                    args=(is_last, phone_number),
                )
                p.start()
                active_procs.append(p)
            except Exception as e:
                print(f"  {POISON_ERR}✗{_R}  {Color.BRIGHT_WHITE}process launch failed: {e}{_R}")
        if max_runs and run_count >= max_runs and not active_procs:
            break
        time.sleep(1)

    for p in active_procs:
        p.join(timeout=300)

    print()
    print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}all done{_R}")
    _prompt("press enter to exit")


if __name__ == "__main__":
    main()
