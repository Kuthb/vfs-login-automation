"""
VFS Global Login Automation -- Selenium + undetected-chromedriver
Target: https://visa.vfsglobal.com/are/en/mlt/login

Usage:
    python login.py                  -- headed mode (default)
    python login.py --headless       -- tries headless first, falls back to headed
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

# ---------------- ARGUMENTS ----------------
parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true")
args = parser.parse_args()

# ---------------- CONFIG ----------------
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

USERNAME     = os.getenv("VFS_USERNAME") or config.get("username", "")
PASSWORD     = os.getenv("VFS_PASSWORD") or config.get("password", "")
HEADLESS     = args.headless or os.getenv("HEADLESS", "").lower() == "true" or config.get("headless", False)
TIMEOUT      = int(os.getenv("TIMEOUT_MS", config.get("timeout_ms", 30000))) // 1000
LOGIN_URL    = "https://visa.vfsglobal.com/are/en/mlt/login"
CAPTCHA_WAIT = 120

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-7s %(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "automation.log", encoding="utf-8"),
    ],
)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = logging.getLogger(__name__)


# ---------------- UTIL ----------------
def save_screenshot(driver, label):
    filename = f"{label}_{int(time.time() * 1000)}.png"
    filepath = SCREENSHOT_DIR / filename
    try:
        driver.save_screenshot(str(filepath))
        log.info(f"Screenshot saved -> {filepath}")
    except Exception as e:
        log.warning(f"Could not save screenshot ({label}): {e}")
    return str(filepath)


# ---------------- DRIVER ----------------
def build_driver(headless=False):
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,800")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")

    if headless:
        log.info("Launching in HEADLESS mode via undetected-chromedriver.")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    else:
        log.info("Launching in HEADED mode via undetected-chromedriver.")

    driver = uc.Chrome(options=options, headless=headless)
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    """)
    driver.implicitly_wait(5)
    return driver


# ---------------- HELPERS ----------------
def dismiss_cookie_consent(driver, wait):
    for by, sel in [
        (By.ID,    "onetrust-accept-btn-handler"),
        (By.XPATH, "//button[contains(text(),'Accept All Cookies')]"),
        (By.XPATH, "//button[contains(text(),'Accept')]"),
    ]:
        try:
            btn = wait.until(EC.element_to_be_clickable((by, sel)))
            btn.click()
            log.info("Cookie dismissed.")
            time.sleep(1)
            return
        except TimeoutException:
            continue
    log.info("No cookie consent -- continuing.")


def find_element_any(wait, selectors):
    for by, sel in selectors:
        try:
            return wait.until(EC.visibility_of_element_located((by, sel)))
        except TimeoutException:
            continue
    raise NoSuchElementException(f"No selector matched: {selectors}")


def wait_for_button_enabled(driver, timeout):
    log.info(f"Waiting up to {timeout}s for Sign In button (Turnstile)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            enabled = driver.execute_script("""
                const btn = document.querySelector('button.btn-brand-orange');
                return btn && !btn.disabled && !btn.classList.contains('mat-mdc-button-disabled');
            """)
            if enabled:
                log.info("Sign In button is now enabled.")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def click_sign_in(driver):
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button.btn-brand-orange")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.5)
        btn.click()
        log.info("Sign In button clicked.")
        return True
    except Exception:
        return False


def detect_login_result(driver):
    time.sleep(3)
    current_url = driver.current_url
    log.info(f"Post-login URL: {current_url}")

    if "/login" not in current_url:
        return {"success": True, "reason": "Redirected away from login page"}

    for el in driver.find_elements(By.CSS_SELECTOR, "[role='alert'], mat-error"):
        if el.is_displayed():
            text = el.text.strip()
            if len(text) > 5:
                return {"success": False, "reason": text}

    return {"success": False, "reason": "Still on login page"}


def is_cloudflare_blocked(driver):
    """Check if Cloudflare has blocked us with session expired page."""
    try:
        current_url = driver.current_url
        if "page-not-found" in current_url or "session" in current_url.lower():
            return True
        # Check page title or body for block indicators
        body = driver.find_element(By.TAG_NAME, "body").text
        if "Session Expired" in body or "session has expired" in body.lower():
            return True
        return False
    except Exception:
        return False


def attempt_login(driver, wait):
    """Core login logic -- returns True on success, raises Exception on failure."""

    driver.get(LOGIN_URL)
    log.info("Login page loaded.")
    time.sleep(8)

    # Check if Cloudflare blocked us
    if is_cloudflare_blocked(driver):
        raise Exception("Cloudflare blocked the session.")

    dismiss_cookie_consent(driver, WebDriverWait(driver, 5))

    # Check again after cookie dismissal
    if is_cloudflare_blocked(driver):
        raise Exception("Cloudflare blocked after cookie dismissal.")

    username = find_element_any(wait, [
        (By.ID,           "email"),
        (By.CSS_SELECTOR, "input[formcontrolname='username']"),
        (By.CSS_SELECTOR, "input[type='email']"),
    ])
    username.clear()
    time.sleep(0.4)
    username.send_keys(USERNAME)
    log.info("Username entered.")

    password = find_element_any(wait, [
        (By.ID,           "password"),
        (By.CSS_SELECTOR, "input[formcontrolname='password']"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ])
    password.clear()
    time.sleep(0.4)
    password.send_keys(PASSWORD)
    log.info("Password entered.")
    time.sleep(0.5)

    save_screenshot(driver, "before_login")

    # Wait for Turnstile to auto-solve
    button_ready = wait_for_button_enabled(driver, CAPTCHA_WAIT)
    if not button_ready:
        log.warning("Button not enabled within timeout -- proceeding anyway.")

    if not click_sign_in(driver):
        log.warning("Button click failed -- pressing Enter.")
        password.send_keys(Keys.RETURN)

    result = detect_login_result(driver)
    save_screenshot(driver, "login_success" if result["success"] else "login_failed")

    return result


# ---------------- MAIN ----------------
def run():
    if not USERNAME or not PASSWORD:
        log.error("Missing credentials.")
        sys.exit(1)

    log.info(f"Mode     : {'HEADLESS' if HEADLESS else 'HEADED'}")
    log.info(f"Timeout  : {TIMEOUT}s")
    log.info(f"Target   : {LOGIN_URL}")

    driver = None

    # Determine run modes
    # If --headless: try headless first, fall back to headed
    # If no flag: run headed only
    modes = ["headless", "headed"] if HEADLESS else ["headed"]

    for mode in modes:
        is_headless = (mode == "headless")

        if is_headless:
            log.info("--- Attempt 1: HEADLESS mode ---")
        else:
            if HEADLESS:
                log.info("--- Attempt 2: HEADED fallback (headless was blocked) ---")
            else:
                log.info("--- Running in HEADED mode ---")

        try:
            driver = build_driver(headless=is_headless)
            wait = WebDriverWait(driver, TIMEOUT)
            log.info("Browser launched.")

            result = attempt_login(driver, wait)

            if result["success"]:
                log.info(f"[OK] LOGIN SUCCESSFUL -- {result['reason']}")
                return True
            else:
                log.error(f"[FAIL] LOGIN FAILED -- {result['reason']}")
                # If headless failed, try headed
                if is_headless:
                    log.warning("Headless login failed -- switching to headed mode.")
                    driver.quit()
                    driver = None
                    continue
                return False

        except Exception as e:
            log.error(f"Error in {mode} mode: {e}")
            if driver:
                try:
                    save_screenshot(driver, f"error_{mode}")
                    driver.quit()
                except Exception:
                    pass
                driver = None

            if is_headless:
                log.warning("Headless blocked by Cloudflare -- switching to headed mode.")
                continue
            return False

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                log.info("Browser closed.")

    return False


if __name__ == "__main__":
    sys.exit(0 if run() else 1)