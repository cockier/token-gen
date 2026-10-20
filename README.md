<div align="center">
need help? dm @wrathiest on discord
update at 100 stars ❤️

**Browser Automation Framework** — headless account provisioning with CAPTCHA solving and disposable email integration.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square&logo=windows)
![Anti-detect](https://img.shields.io/badge/Anti--detect-stealth%20profile-green?style=flat-square)
![Email API](https://img.shields.io/badge/Email-regret.world-8b5cf6?style=flat-square)
![CAPTCHA](https://img.shields.io/badge/CAPTCHA-NopeCHA-orange?style=flat-square)
![Detection](https://img.shields.io/badge/Detection-undetected-brightgreen?style=flat-square)

</div>

---

## ✦ Overview

Browser is a modular browser automation framework built on [nodriver](https://github.com/ultrafunkamsterdam/nodriver) — a true undetected Chrome driver with no CDP fingerprint leakage. It handles full account provisioning workflows end-to-end: disposable email generation, CAPTCHA solving, form submission, and behavioral humanization.

Powered by the **[regret.world](https://regret.world) email API** — ephemeral inboxes on demand, instant message polling, zero setup.

---

## ✦ Features

```
✓  Undetected browser core (nodriver / UC)      no automation fingerprint
✓  Isolated temp profiles per session           zero cross-run contamination
✓  NopeCHA extension integration                hCaptcha + reCaptcha solved
✓  regret.world email API                       instant disposable inboxes
✓  Dynamic username generation                  human-pattern usernames
✓  Secure password generation                   12–20 char, mixed specials
✓  Display name generation from word lists      reads data/names.txt
✓  Behavioral humanizer                         avatar, bio, pronouns, HypeSquad
✓  Proxy support                                HTTP/SOCKS via proxies.txt
✓  Webhook reporting                            results delivered on complete
✓  Multi-browser support                        chrome, microsoft edge
✓  Rate-limit aware                             configurable delay between runs
```

---

## ✦ File Structure

```
browser gen/
├── main.py                    ← entry point, full automation loop
├── config.json                ← runtime config (API keys, toggles, delays)
│
├── data/
│   ├── names.txt              ← display name word list
│   ├── pack.ico               ← notification icon
│   └── proxies.txt            ← one proxy per line (host:port or user:pass@host:port)
│
├── nopecha/
│   └── nopecha_extension/     ← MV3 Chrome extension for CAPTCHA solving
│       └── manifest.json
│
└── README.md
```

---

## ✦ Email API — regret.world

Browser uses [**regret.world**](https://regret.world) for disposable inboxes. No IMAP setup, no third-party relay — just an API key and you're provisioning inboxes instantly.

```python
# what happens under the hood
POST /api/v1/inboxes         # create inbox on regret.world or hurtful.lol
GET  /api/v1/inboxes/{addr}/messages          # poll for new mail
GET  /api/v1/inboxes/{addr}/messages/{uid}    # read message body
DELETE /api/v1/inboxes/{addr}                 # clean up after use
```

**Get your API key at [regret.world](https://regret.world)** — free tier included, premium plans available.

---

## ✦ Setup

### Requirements

- Python 3.10+
- Google Chrome or Microsoft Edge installed
- [NopeCHA](https://nopecha.com) API key
- [regret.world](https://regret.world) API key

### Install dependencies

```bash
pip install nodriver requests
```

### Configure

Edit `config.json`:

```jsonc
{
  "rw_key": "rw_your_key_here",       // regret.world API key
  "nopecha_key": "your_nopecha_key",  // NopeCHA API key
  "browser": "chrome",                // "chrome" or "microsoft"
  "delay_between_runs": 5,            // seconds between each run
  "use_proxy": false,                 // set true + populate proxies.txt
  "humanizer": {
    "enabled": true,
    "avatar": true,
    "bio": true,
    "pronouns": true,
    "hypesquad": true
  }
}
```

### Run

```bash
python main.py
```

---

## ✦ How It Works

```
1. Pull temp inbox from regret.world API
2. Spawn isolated Chrome/Edge with temp --user-data-dir
3. Load NopeCHA extension for automatic CAPTCHA handling
4. Fill registration form with generated username, password, display name
5. Poll inbox for verification email via regret.world
6. Extract verification link, navigate, confirm
7. Run humanizer pass (avatar, bio, etc.) if enabled
8. Report result via webhook (if configured)
9. Clean up temp profile, delete inbox
```

---

## ✦ Anti-Detection

- **nodriver** — patches Chrome DevTools Protocol detection at the source; no `navigator.webdriver`, no CDP leakage
- **Isolated profiles** — fresh `--user-data-dir` per run; no shared cookies, history, or extension state bleeds between sessions
- **NopeCHA** — loaded as a real Chrome extension (MV3), not injected script; indistinguishable from a user-installed solver
- **Human-pattern usernames** — `xx_james_wilson317xx` format, not random strings
- **Behavioral timing** — configurable delays, humanizer passes mimic real user behavior

---

## ✦ Proxy Support

Add proxies to `data/proxies.txt`, one per line:

```
host:port
user:pass@host:port
```

Enable in `config.json`: `"use_proxy": true`

---

## ✦ Get an Email API Key

> **[regret.world](https://regret.world)** — disposable inboxes via REST API.  
> Free tier. Premium plans for higher volume.  
> Domains: `regret.world`, `hurtful.lol`, `larping.baby`, `reapsed.lol`, `reapsed.wtf`, `edr4fun.lol` and much more.

---

<div align="center">
<sub>built for researchers, testers, and automation engineers</sub>
</div>


`creds to kanishk for the base, was pretty ass but ive improved it drastically.`
