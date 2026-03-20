# VFS Global Login Automation — Selenium

Selenium 4 + Python login automation for the [VFS Global UAE–Malta portal](https://visa.vfsglobal.com/are/en/mlt/login).
Supports **headed** and **headless** Chrome, with screenshot capture, structured logging, and flexible credential management.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Selenium 4](https://selenium.dev) | Browser automation |
| [webdriver-manager](https://github.com/SergeyPirogov/webdriver_manager) | Auto-downloads matching ChromeDriver |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Loads `.env` credentials |
| Python 3.8+ | Runtime |

---

## Project Structure

```
vfs-selenium/
├── login.py          ← Main automation script
├── config.json       ← Runtime config (headless flag, timeout)
├── .env.example      ← Credential template
├── requirements.txt
├── .gitignore
└── screenshots/      ← Auto-created; stores PNG captures
    └── automation.log
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

> ChromeDriver is downloaded automatically by `webdriver-manager` — no manual install needed.

### 2. Set credentials

**Option A — Environment variables (recommended)**

```bash
export VFS_USERNAME="your_email@example.com"
export VFS_PASSWORD="your_password"
```

Or create a `.env` file (copied from `.env.example`):

```
VFS_USERNAME=your_email@example.com
VFS_PASSWORD=your_password
```

**Option B — config.json**

Fill `username` and `password` directly in `config.json`.
⚠️ Do not commit this file with credentials.

**Priority: env vars > .env file > config.json**

---

## Running the Script

### Headed mode (browser visible — default)

```bash
python login.py
```

### Headless mode (background — no visible browser)

```bash
python login.py --headless
# or
HEADLESS=true python login.py
```

### With inline credentials

```bash
VFS_USERNAME=you@email.com VFS_PASSWORD=secret python login.py --headless
```

---

## Configuration Reference

`config.json`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `username` | string | `""` | Login email |
| `password` | string | `""` | Password |
| `headless` | boolean | `false` | Run headless |
| `timeout_ms` | number | `30000` | Global timeout in ms |

---

## What the Script Does (Step by Step)

1. **Validates** credentials are present — exits early if missing
2. **Launches** Chrome via Selenium 4 (headed or headless)
3. **Navigates** to the VFS login URL
4. **Dismisses** cookie consent overlays automatically
5. **Locates** the username field using multiple fallback selectors
6. **Fills** username and password
7. **Captures** a `before_login` screenshot
8. **Clicks** the submit button (falls back to `Enter` key)
9. **Waits** for page staleness / navigation
10. **Detects** login result via URL change + DOM error/success scanning
11. **Captures** a `login_success` or `login_failed` screenshot
12. **Logs** to console + `automation.log`
13. **Exits** with code `0` (success) or `1` (failure)

---

## Screenshots

All screenshots are saved in `./screenshots/` with timestamped filenames:

```
screenshots/
├── before_login_1718000000000.png
├── login_success_1718000001234.png
└── login_failed_1718000001234.png
```

---

## Log Output Example

```
INFO     2025-06-10 12:00:01  Mode     : HEADED
INFO     2025-06-10 12:00:01  Timeout  : 30s
INFO     2025-06-10 12:00:01  Target   : https://visa.vfsglobal.com/are/en/mlt/login
INFO     2025-06-10 12:00:04  Browser launched.
INFO     2025-06-10 12:00:06  Login page loaded.
INFO     2025-06-10 12:00:06  No cookie consent overlay found — continuing.
INFO     2025-06-10 12:00:07  Username entered.
INFO     2025-06-10 12:00:07  Password entered.
INFO     2025-06-10 12:00:07  Screenshot saved → screenshots/before_login_xxx.png
INFO     2025-06-10 12:00:07  Submitting login form...
INFO     2025-06-10 12:00:10  Post-login URL: https://visa.vfsglobal.com/are/en/mlt/dashboard
INFO     2025-06-10 12:00:10  ✓ LOGIN SUCCESSFUL — Redirected away from login page
INFO     2025-06-10 12:00:10  Screenshot saved → screenshots/login_success_xxx.png
INFO     2025-06-10 12:00:10  Browser closed.
```

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Missing credentials | Logs error, exits before launching browser |
| Element not found | Multiple selector fallbacks tried first |
| Timeout | `TimeoutException` caught, error screenshot saved |
| WebDriver crash | `WebDriverException` caught, screenshot attempted |
| No submit button | Falls back to pressing `Enter` on password field |
| Any other exception | Caught generically, screenshot saved, clean exit |

---

## Demo Video Script (2–3 min)

1. **(0:00–0:20)** Show folder structure — highlight `login.py`, `config.json`, `.env.example`
2. **(0:20–0:50)** Walk through `login.py` — credential loading, selector strategy, screenshot + logging
3. **(0:50–1:20)** Run **headed**: `python login.py` — narrate as browser opens and fills form
4. **(1:20–1:50)** Run **headless**: `python login.py --headless` — show terminal logs only
5. **(1:50–2:20)** Open `screenshots/` — show before/after PNG captures
6. **(2:20–2:45)** Explain headed vs headless trade-offs and when to use each
7. **(2:45–3:00)** Wrap up: env vars, config, exit codes, log file
