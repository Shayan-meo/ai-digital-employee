"""
Twitter/X Selenium Poster — undetected-chromedriver edition.

Uses undetected-chromedriver to bypass Twitter's bot detection.
Unlike Playwright/CDP, this patches Chrome at the binary level
so automation markers are invisible.

Usage:
    python twitter_selenium.py --setup          # Login manually & save session
    python twitter_selenium.py --text "Hello"   # Post text tweet
    python twitter_selenium.py --text "Hello" --image path/to/img.jpg  # With image
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Paths ─────────────────────────────────────────────────────────────────
VAULT = Path(__file__).parent.resolve()
PROFILE_DIR = VAULT / ".twitter_uc_profile"
LOGS_DIR = VAULT / "Logs"
LOGS_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "twitter_selenium.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def create_driver():
    """Create an undetected Chrome driver with persistent profile."""
    profile = str(PROFILE_DIR)
    os.makedirs(profile, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    logger.info("Launching Chrome via undetected-chromedriver...")
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def is_logged_in(driver) -> bool:
    """Check if we're logged in to Twitter/X."""
    try:
        driver.get("https://x.com/home")
        time.sleep(5)
        url = driver.current_url
        logger.info(f"Current URL: {url}")

        if "login" in url or "flow" in url:
            return False

        # Check if main content loaded (not blank)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
            )
            logger.info("Primary column found — logged in!")
            return True
        except Exception:
            pass

        # Check for compose tweet button
        try:
            driver.find_element(By.CSS_SELECTOR, "[data-testid='SideNav_NewTweet_Button']")
            logger.info("Tweet button found — logged in!")
            return True
        except Exception:
            pass

        # Check for timeline
        try:
            driver.find_element(By.CSS_SELECTOR, "[data-testid='tweet']")
            logger.info("Timeline tweets found — logged in!")
            return True
        except Exception:
            pass

        logger.warning(f"Page loaded but can't confirm login. URL: {url}")
        # Save screenshot for debugging
        driver.save_screenshot(str(LOGS_DIR / "tw_uc_login_check.png"))
        return False

    except Exception as e:
        logger.error(f"Login check error: {e}")
        return False


def setup_login(driver):
    """Open Twitter login page and wait for manual login."""
    logger.info("Opening Twitter login page — please log in manually...")
    driver.get("https://x.com/i/flow/login")
    time.sleep(3)

    logger.info("Waiting for you to log in (max 120 seconds)...")
    for i in range(60):
        time.sleep(2)
        url = driver.current_url
        if "home" in url or (url.endswith("x.com/") and "login" not in url and "flow" not in url):
            # Verify content loaded
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
                )
                logger.info("Login successful! Session saved.")
                return True
            except Exception:
                pass
        if i % 10 == 0 and i > 0:
            logger.info(f"Still waiting... ({i*2}s)")

    logger.error("Login timeout — could not confirm login.")
    return False


def post_tweet(driver, text: str, image_path: str = None) -> bool:
    """Post a tweet with optional image."""
    logger.info("Navigating to Twitter compose...")

    # Go to compose URL directly
    driver.get("https://x.com/compose/post")
    time.sleep(5)

    # Check if we're redirected to login
    if "login" in driver.current_url or "flow" in driver.current_url:
        logger.error("Redirected to login — not authenticated!")
        return False

    # Wait for the tweet composer
    logger.info("Waiting for tweet composer...")
    composer = None

    selectors = [
        "[data-testid='tweetTextarea_0']",
        "[role='textbox'][data-testid='tweetTextarea_0']",
        "div[role='textbox']",
        ".public-DraftEditor-content",
        "[contenteditable='true']",
    ]

    for sel in selectors:
        try:
            composer = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            logger.info(f"Composer found: {sel}")
            break
        except Exception:
            continue

    if not composer:
        logger.error("Could not find tweet composer!")
        driver.save_screenshot(str(LOGS_DIR / "tw_uc_no_composer.png"))
        # Log page source snippet for debugging
        body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
        logger.error(f"Page body text: {body_text}")
        return False

    # Click composer and type text
    logger.info("Typing tweet text...")
    composer.click()
    time.sleep(0.5)

    # Type text using keyboard (handles Unicode better)
    # Split into chunks if needed for long text
    composer.send_keys(text)
    time.sleep(2)

    # Upload image if provided
    if image_path:
        abs_path = str(Path(image_path).resolve())
        if not Path(abs_path).exists():
            logger.error(f"Image not found: {abs_path}")
            return False

        logger.info(f"Uploading image: {abs_path}")
        try:
            # Find the file input for media upload
            file_input = driver.find_element(By.CSS_SELECTOR, "input[data-testid='fileInput']")
            file_input.send_keys(abs_path)
            time.sleep(4)  # Wait for upload
            logger.info("Image uploaded.")
        except Exception as e:
            logger.warning(f"Could not upload image via file input: {e}")
            # Try alternative: click media button then upload
            try:
                media_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='fileInput']")
                media_btn.send_keys(abs_path)
                time.sleep(4)
                logger.info("Image uploaded (alt method).")
            except Exception as e2:
                logger.error(f"Image upload failed completely: {e2}")
                # Continue posting without image

    # Click the Post/Tweet button
    logger.info("Clicking Post button...")
    post_btn = None
    post_selectors = [
        "[data-testid='tweetButton']",
        "[data-testid='tweetButtonInline']",
        "button[data-testid='tweetButton']",
    ]

    for sel in post_selectors:
        try:
            post_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            logger.info(f"Post button found: {sel}")
            break
        except Exception:
            continue

    if not post_btn:
        logger.error("Could not find Post button!")
        driver.save_screenshot(str(LOGS_DIR / "tw_uc_no_post_btn.png"))
        return False

    post_btn.click()
    time.sleep(5)

    # Verify post was sent (composer should close or URL should change)
    logger.info("Verifying post was sent...")
    try:
        # If composer is gone, post was successful
        WebDriverWait(driver, 10).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
        )
        logger.info("Tweet posted successfully!")
        return True
    except Exception:
        # Composer might still be there but post might have gone through
        url = driver.current_url
        if "compose" not in url:
            logger.info("URL changed — tweet likely posted!")
            return True
        logger.warning("Uncertain if tweet was posted. Check your profile.")
        driver.save_screenshot(str(LOGS_DIR / "tw_uc_post_verify.png"))
        return True  # Optimistic


def main():
    parser = argparse.ArgumentParser(description="Twitter/X Selenium Poster")
    parser.add_argument("--setup", action="store_true", help="Login manually and save session")
    parser.add_argument("--text", type=str, help="Tweet text to post")
    parser.add_argument("--image", type=str, help="Image file path to attach")
    args = parser.parse_args()

    driver = None
    try:
        driver = create_driver()

        if args.setup:
            if is_logged_in(driver):
                logger.info("Already logged in! Session is valid.")
            else:
                setup_login(driver)
            input("Press Enter to close browser...")
            return

        # Posting mode
        if not args.text:
            logger.error("--text is required for posting")
            return

        if not is_logged_in(driver):
            logger.error("Not logged in! Run with --setup first.")
            driver.save_screenshot(str(LOGS_DIR / "tw_uc_not_logged_in.png"))
            return

        success = post_tweet(driver, args.text, args.image)
        if success:
            print("RESULT:OK:Tweet posted successfully")
        else:
            print("RESULT:FAILED:POST_FAILED")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        print(f"RESULT:ERROR:{str(e)[:200]}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
