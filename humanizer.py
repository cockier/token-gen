import time
import base64
import hashlib
import inspect
import re
import uuid
import random
import threading
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse, quote

import primp
import websockets
from python_socks.async_.asyncio import Proxy
from PIL import Image

DISCORD_API      = "https://discord.com/api/v9"
DISCORD_GATEWAY  = "wss://gateway.discord.gg/?v=9&encoding=json"
FALLBACK_BUILD   = 519006
CLIENT_VERSION   = "1.0.9171"
ELECTRON_VERSION = "34.5.1"
CHROME_VERSION   = "132"
USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) discord/{CLIENT_VERSION} "
    f"Chrome/{CHROME_VERSION}.0.0.0 Electron/{ELECTRON_VERSION} Safari/537.36"
)

_HYPESQUAD = {1: "Bravery", 2: "Brilliance", 3: "Balance"}
_AVATAR_MAX = 1_000_000

_async_loop        = asyncio.new_event_loop()
_async_loop_thread = threading.Thread(target=_async_loop.run_forever, daemon=True)
_async_loop_thread.start()


def _fetch_build() -> int:
    try:
        resp = primp.Client(verify=False).get("https://discord.com/login", timeout=10)
        for h in reversed(re.findall(r'/assets/([a-zA-Z0-9_-]+)\.js', resp.text)):
            js = primp.Client(verify=False).get(f"https://discord.com/assets/{h}.js", timeout=10)
            m  = re.search(r'buildNumber["\s:,]+(\d{4,7})', js.text)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return FALLBACK_BUILD

BUILD_NUMBER = _fetch_build()


def _super_props(launch_id, sig, hb_id, native_build) -> str:
    return base64.b64encode(
        __import__("json").dumps({
            "os": "Windows", "browser": "Discord Client",
            "release_channel": "stable", "client_version": CLIENT_VERSION,
            "os_version": "10.0.26100", "os_arch": "x64", "app_arch": "x64",
            "system_locale": "en-US", "has_client_mods": False,
            "browser_user_agent": USER_AGENT, "browser_version": ELECTRON_VERSION,
            "client_build_number": BUILD_NUMBER, "native_build_number": native_build,
            "client_event_source": None,
            "client_launch_id": launch_id, "launch_signature": sig,
            "client_heartbeat_session_id": hb_id,
        }, separators=(",", ":")).encode()
    ).decode()


def _load_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def _load_avatar_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}]


def _avatar_to_b64(path: Path, dim: int = 256) -> Optional[str]:
    try:
        with Image.open(path) as img:
            is_png = path.suffix.lower() == ".png"
            img = img.convert("RGBA" if is_png else "RGB")
            img = img.resize((dim, dim), Image.Resampling.LANCZOS)
            buf = BytesIO()
            fmt  = "PNG" if is_png else "JPEG"
            mime = "image/png" if is_png else "image/jpeg"
            img.save(buf, format=fmt)
            b64 = base64.b64encode(buf.getvalue()).decode()
            if len(b64) > _AVATAR_MAX:
                work = img.convert("RGB")
                mime = "image/jpeg"
                for q in (80, 60, 40, 20):
                    buf = BytesIO()
                    work.save(buf, format="JPEG", quality=q, optimize=True)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    if len(b64) <= _AVATAR_MAX:
                        break
                else:
                    return None
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


class Humanizer:
    def __init__(self, token: str, proxy: Optional[str] = None):
        self.token      = token
        self.proxy      = proxy
        self.client     = primp.Client(verify=False, proxy=proxy or None)
        self.is_locked  = False
        self.proxy_failed = False
        self.session_id = None
        self._install_id = (
            f"{random.randint(10**18, 10**19 - 1)}."
            f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=22))}"
        )
        lid = str(uuid.uuid4()); sig = str(uuid.uuid4()); hb = str(uuid.uuid4())
        nb  = random.randint(65600, 65800)
        self._sp = _super_props(lid, sig, hb, nb)
        self._nb = nb

    def _headers(self) -> Dict[str, str]:
        h = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US", "authorization": self.token,
            "content-type": "application/json", "user-agent": USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-US", "x-discord-timezone": "America/New_York",
            "x-installation-id": self._install_id, "x-super-properties": self._sp,
        }
        try:
            r = self.client.get(f"{DISCORD_API}/experiments", timeout=15)
            fp = r.json().get("fingerprint") if r.status_code == 200 else None
            if fp:
                h["x-fingerprint"] = fp
        except Exception:
            pass
        return h

    def _api(self, method: str, url: str, data: dict, headers: dict, retries: int = 4) -> dict:
        if self.is_locked:
            return {"success": False, "error": "locked"}
        for attempt in range(retries):
            try:
                fn   = self.client.post if method == "post" else self.client.patch
                resp = fn(url, headers=headers, json=data, timeout=60)
                if resp.status_code in (200, 204):
                    try:    body = resp.json() if resp.status_code == 200 else {}
                    except: body = {}
                    return {"success": True, "data": body}
                try:    err = resp.json()
                except: err = {}
                if err.get("captcha_key"):
                    return {"success": False, "captcha": True}
                if resp.status_code == 429:
                    ra = float(resp.headers.get("retry-after") or err.get("retry_after") or 1)
                    time.sleep(max(ra, 1))
                    continue
                if resp.status_code in (401, 403):
                    self.is_locked = True
                    return {"success": False, "error": str(resp.status_code)}
                return {"success": False, "error": str(err)}
            except Exception as e:
                if attempt >= retries - 1:
                    return {"success": False, "error": str(e)}
        return {"success": False, "error": "max retries"}

    async def _ws_identify(self, ws) -> bool:
        try:
            hello = __import__("json").loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if hello.get("op") != 10:
                return False
            payload = {
                "op": 2, "d": {
                    "token": self.token, "capabilities": 16381,
                    "properties": {
                        "os": "Windows", "browser": "Discord Client",
                        "release_channel": "stable", "client_version": CLIENT_VERSION,
                        "os_version": "10.0.26100", "os_arch": "x64", "app_arch": "x64",
                        "system_locale": "en-US", "browser_user_agent": USER_AGENT,
                        "browser_version": ELECTRON_VERSION,
                        "client_build_number": BUILD_NUMBER,
                        "native_build_number": self._nb,
                        "client_event_source": None, "design_id": 0,
                    },
                    "presence": {"status": "online", "since": 0, "activities": [], "afk": False},
                    "compress": False,
                    "client_state": {
                        "guild_versions": {}, "highest_last_message_id": "0",
                        "read_state_version": 0, "user_guild_settings_version": -1,
                        "user_settings_version": -1, "private_channels_version": "0",
                        "api_code_version": 0,
                    },
                }
            }
            await ws.send(__import__("json").dumps(payload))
            for _ in range(12):
                msg = __import__("json").loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if msg.get("t") == "READY":
                    self.session_id = msg["d"].get("session_id")
                    return True
                if msg.get("op") == 9:
                    return False
        except Exception:
            pass
        return False

    async def _patch_with_ws(self, payload: dict, headers: dict) -> dict:
        loop = asyncio.get_event_loop()
        kw: dict = {"open_timeout": 60, "close_timeout": 10, "max_size": None}
        try:
            pk = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
        except Exception:
            pk = "extra_headers"
        kw[pk] = {"User-Agent": USER_AGENT}

        async def _do(ws):
            if not await self._ws_identify(ws):
                return {"success": False, "error": "ws identify failed"}
            return await loop.run_in_executor(
                None, lambda: self._api("patch", f"{DISCORD_API}/users/@me", payload, headers)
            )

        try:
            if self.proxy:
                px   = Proxy.from_url(self.proxy)
                sock = await px.connect(dest_host="gateway.discord.gg", dest_port=443)
                kw["sock"] = sock; kw["server_hostname"] = "gateway.discord.gg"
            async with websockets.connect(DISCORD_GATEWAY, **kw) as ws:
                return await _do(ws)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _patch_account(self, payload: dict, headers: dict) -> dict:
        if "avatar" not in payload:
            r = self._api("patch", f"{DISCORD_API}/users/@me", payload, headers)
            if r.get("success") or not r.get("unknown_session"):
                return r
        fut = asyncio.run_coroutine_threadsafe(
            self._patch_with_ws(payload, headers), _async_loop
        )
        return fut.result()

    def _patch_profile(self, payload: dict, headers: dict) -> dict:
        return self._api("patch", f"{DISCORD_API}/users/@me/profile", payload, headers)

    def _set_hypesquad(self, house_id: int, headers: dict) -> dict:
        time.sleep(random.uniform(1, 3))
        try:
            r = self.client.get(f"{DISCORD_API}/users/@me", headers=headers, timeout=20)
            if r.status_code == 200:
                flags = r.json().get("flags", 0)
                if flags & 0xE:
                    for hid, hn in _HYPESQUAD.items():
                        if flags & (1 << hid):
                            return {"success": True, "house": hn, "already": True}
        except Exception:
            pass
        r = self._api("post", f"{DISCORD_API}/hypesquad/online", {"house_id": house_id}, headers, retries=2)
        return {"success": r.get("success", False), "house": _HYPESQUAD[house_id]}

    def run(self, cfg: dict, avatar_folder: Path, data_dir: Path) -> bool:
        names    = _load_lines(data_dir / "names.txt")
        bios     = _load_lines(data_dir / "bios.txt")
        pronouns = _load_lines(data_dir / "pronouns.txt")
        avatars  = _load_avatar_files(avatar_folder)
        headers  = self._headers()
        tasks    = []

        acc_payload: dict = {}
        if cfg.get("avatar") and avatars:
            b64 = _avatar_to_b64(random.choice(avatars))
            if b64:
                acc_payload["avatar"] = b64
        if cfg.get("display_name") and names:
            acc_payload["global_name"] = random.choice(names)
        if acc_payload:
            tasks.append(("account", acc_payload))

        prof_payload: dict = {}
        if cfg.get("bio") and bios:
            prof_payload["bio"] = random.choice(bios)
        if cfg.get("pronouns") and pronouns:
            prof_payload["pronouns"] = random.choice(pronouns)
        if prof_payload:
            tasks.append(("profile", prof_payload))

        if cfg.get("hypesquad"):
            tasks.append(("hypesquad", random.randint(1, 3)))

        ok = True
        with ThreadPoolExecutor(max_workers=len(tasks) or 1) as ex:
            futs = {}
            for kind, val in tasks:
                if kind == "account":
                    futs[ex.submit(self._patch_account, val, headers)] = ("account", val)
                elif kind == "profile":
                    futs[ex.submit(self._patch_profile, val, headers)] = ("profile", val)
                elif kind == "hypesquad":
                    futs[ex.submit(self._set_hypesquad, val, headers)] = ("hypesquad", val)

            for fut in as_completed(futs):
                kind, val = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    ok = False
                    continue
                if not res.get("success"):
                    ok = False

        return ok
