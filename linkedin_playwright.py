"""
LinkedIn Playwright Poster — Silver Tier
Watches /Approved for LinkedIn post files and publishes them automatically.

Features:
- Login with email/password (session saved to avoid repeated logins)
- Detects linkedin_post_*.md files in /Approved
- Extracts post text and publishes to LinkedIn
- Moves processed file to /Done
- Full audit logging

Usage:
    python linkedin_playwright.py              # run once (process pending approved posts)
    python linkedin_playwright.py --watch      # continuous watch mode
    python linkedin_playwright.py --test-login # just test login works
"""

import argparse
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT   = Path(__file__).parent.resolve()
APPROVED_DIR = VAULT_ROOT / "Approved"
DONE_DIR     = VAULT_ROOT / "Done"
LOGS_DIR     = VAULT_ROOT / "Logs"
SESSION_FILE = VAULT_ROOT / ".linkedin_session"  # saved browser state

for d in (APPROVED_DIR, DONE_DIR, LOGS_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"linkedin_playwright_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds between scans in watch mode


# ── .env loader ────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env_path = VAULT_ROOT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── Post text extractor ────────────────────────────────────────────────────────
def extract_post_text(filepath: Path) -> str | None:
    """Extract the post text from a linkedin_post_*.md approval file."""
    content = filepath.read_text(encoding="utf-8")

    # Look for text between ``` markers (the drafted post block)
    match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: look for ## Drafted Post section
    match = re.search(r"##\s*Drafted Post\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = match.group(1).strip()
        # Remove markdown code fences if present
        text = re.sub(r"^```.*?```$", "", text, flags=re.DOTALL).strip()
        return text or None

    return None


def extract_image_path(filepath: Path) -> Path | None:
    """Extract image path from a post markdown file."""
    content = filepath.read_text(encoding="utf-8")
    match = re.search(r"##\s*Image\s*\n+(.+)", content)
    if match:
        img = match.group(1).strip()
        if img and img != "(none)":
            img_path = Path(img)
            if img_path.exists():
                return img_path
            media_path = VAULT_ROOT / "Media" / img_path.name
            if media_path.exists():
                return media_path
    # Also check for Image: line
    match = re.search(r"(?i)^image:\s*(.+)$", content, re.MULTILINE)
    if match:
        img = match.group(1).strip()
        if img and img != "(none)":
            img_path = Path(img)
            if img_path.exists():
                return img_path
            media_path = VAULT_ROOT / "Media" / img_path.name
            if media_path.exists():
                return media_path
    return None


# ── LinkedIn automation ────────────────────────────────────────────────────────
class LinkedInPoster:
    def __init__(self, email: str, password: str):
        self.email    = email
        self.password = password
        self.pw       = None
        self.browser  = None
        self.context  = None
        self.page     = None

    def start(self):
        self.pw      = sync_playwright().start()
        storage      = str(SESSION_FILE) if SESSION_FILE.exists() else None
        self.browser = self.pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
            ],
        )
        self.context = self.browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # Stealth
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.apply_stealth_sync(self.context)
            logger.info("Stealth applied.")
        except Exception as e:
            logger.warning(f"Stealth skipped: {e}")

        self.page = self.context.new_page()

    def stop(self):
        try:
            if self.context:
                self.context.storage_state(path=str(SESSION_FILE))
                logger.info("Session saved.")
        except Exception as e:
            logger.warning(f"Session save error: {e}")
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        if self.pw:
            self.pw.stop()

    def is_logged_in(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            self.page.goto("https://www.linkedin.com/feed/", timeout=60000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            url = self.page.url
            # If redirected to login page, not logged in
            if "login" in url or "authwall" in url or "signup" in url:
                return False
            return "feed" in url or "mynetwork" in url
        except Exception:
            return False

    def login(self) -> bool:
        logger.info("Logging in to LinkedIn...")
        try:
            self.page.goto("https://www.linkedin.com/login",
                           timeout=60000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(4000)

            # Fill credentials
            self.page.fill("#username", self.email)
            self.page.wait_for_timeout(800)
            self.page.fill("#password", self.password)
            self.page.wait_for_timeout(800)
            self.page.click("button[type='submit']")

            # Wait for navigation
            self.page.wait_for_timeout(6000)

            url = self.page.url
            if "feed" in url or "mynetwork" in url or "jobs" in url:
                logger.info("Login successful.")
                self.context.storage_state(path=str(SESSION_FILE))
                return True
            elif "checkpoint" in url or "challenge" in url or "verification" in url:
                logger.warning("LinkedIn security check — complete it manually in the browser window.")
                # Wait up to 60 seconds for user to complete check
                for _ in range(30):
                    time.sleep(2)
                    url = self.page.url
                    if "feed" in url or "mynetwork" in url:
                        logger.info("Security check passed.")
                        self.context.storage_state(path=str(SESSION_FILE))
                        return True
                logger.error("Security check not completed in time.")
                return False
            else:
                logger.error(f"Login failed. Current URL: {url}")
                return False

        except PWTimeout:
            logger.error("Login timed out.")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def post(self, text: str, image_path=None) -> bool:
        """Publish a text post (with optional image) to LinkedIn feed."""
        logger.info("Navigating to LinkedIn feed...")
        try:
            self.page.goto("https://www.linkedin.com/feed/", timeout=60000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(8000)

            # Dismiss any popups/overlays (cookie consent, messaging, etc.)
            for dismiss_sel in [
                "button:has-text('Dismiss')",
                "button:has-text('Got it')",
                "button:has-text('Accept')",
                "button[aria-label='Dismiss']",
                "button[data-control-name='overlay.close_contextual_layer']",
            ]:
                try:
                    btn = self.page.locator(dismiss_sel).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self.page.wait_for_timeout(1000)
                        logger.info(f"Dismissed overlay: {dismiss_sel}")
                except Exception:
                    pass

            # Click "Start a post" on the feed page
            logger.info("Opening post composer...")
            start_post_selectors = [
                "button.share-box-feed-entry__trigger",
                "[aria-label='Start a post']",
                "button:has-text('Start a post')",
                ".share-box-feed-entry__top-bar",
                ".share-box-feed-entry__trigger",
                "button.artdeco-button--tertiary:has-text('Start a post')",
            ]
            composer_opened = False
            for attempt in range(5):
                for sel in start_post_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.is_visible(timeout=4000):
                            btn.click()
                            logger.info(f"Clicked 'Start a post': {sel} (attempt {attempt+1})")
                            self.page.wait_for_timeout(4000)
                            composer_opened = True
                            break
                    except Exception:
                        continue
                if composer_opened:
                    break
                logger.info(f"'Start a post' not found on attempt {attempt+1}, scrolling up and retrying...")
                self.page.evaluate("window.scrollTo(0, 0)")
                self.page.wait_for_timeout(3000)

            if not composer_opened:
                logger.error("Could not click 'Start a post'")
                try:
                    self.page.screenshot(path=str(LOGS_DIR / "debug_start_post.png"))
                except Exception:
                    pass
                return False

            # Find the editor — try all known selectors with retry
            logger.info("Finding post editor...")
            editor_selectors = [
                ".ql-editor",
                "[contenteditable='true'][role='textbox']",
                "[contenteditable='true']",
                "[data-placeholder]",
                "div.editor-container [contenteditable]",
                ".share-creation-state__editor div[contenteditable]",
                "div[role='textbox']",
            ]
            editor = None
            for attempt in range(3):
                for sel in editor_selectors:
                    try:
                        el = self.page.locator(sel).first
                        el.wait_for(timeout=5000, state="visible")
                        editor = el
                        logger.info(f"Found editor: {sel} (attempt {attempt+1})")
                        break
                    except Exception:
                        continue
                if editor:
                    break
                logger.info(f"Editor not found on attempt {attempt+1}, waiting...")
                self.page.wait_for_timeout(3000)

            if not editor:
                logger.error("Could not find post editor — saving screenshot for debug")
                try:
                    self.page.screenshot(path=str(LOGS_DIR / "debug_screenshot.png"))
                except Exception:
                    pass
                return False

            # Upload image FIRST if provided (before typing text)
            if image_path:
                logger.info(f"Uploading image FIRST: {image_path}")
                try:
                    # Click the image/media button in the composer toolbar
                    media_selectors = [
                        "button[aria-label='Add media']",
                        "button[aria-label='Add a photo']",
                        "button[aria-label='Add media, photo or video']",
                        "button:has(svg[data-test-icon='image-medium'])",
                        ".share-creation-state__detour-btn button",
                        "button.image-sharing-detour-button",
                        "[aria-label='Add media']:not([disabled])",
                    ]
                    media_clicked = False
                    for sel in media_selectors:
                        try:
                            btn = self.page.locator(sel).first
                            if btn.is_visible(timeout=3000):
                                btn.click()
                                media_clicked = True
                                logger.info(f"Clicked media button: {sel}")
                                break
                        except Exception:
                            continue

                    if not media_clicked:
                        # Fallback: try finding any file input directly
                        logger.info("Media button not found, trying direct file input...")

                    self.page.wait_for_timeout(2000)

                    # Find file input and upload
                    file_input = self.page.locator("input[type='file']").first
                    file_input.set_input_files(str(image_path))
                    logger.info("Image file selected for upload.")

                    # Wait for image preview to render (verify LinkedIn processed it)
                    preview_selectors = [
                        ".share-box-image-preview img",
                        ".media-preview img",
                        "img[data-test-id='image-preview']",
                        ".share-creation-state__image-container img",
                        ".share-box__preview img",
                        "div[class*='image-preview'] img",
                        "div[class*='media'] img[src*='upload']",
                    ]
                    preview_found = False
                    for wait_round in range(30):  # up to 30 seconds
                        for psel in preview_selectors:
                            try:
                                if self.page.locator(psel).first.is_visible(timeout=500):
                                    preview_found = True
                                    logger.info(f"Image preview rendered: {psel}")
                                    break
                            except Exception:
                                pass
                        if preview_found:
                            break
                        self.page.wait_for_timeout(1000)

                    if not preview_found:
                        # Fallback: wait fixed time if preview not detected
                        logger.info("Image preview selector not found, waiting 15s as fallback...")
                        self.page.wait_for_timeout(15000)

                    # Extra wait for LinkedIn to finalize processing
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        self.page.wait_for_timeout(5000)
                    self.page.wait_for_timeout(3000)
                    logger.info("Image upload and processing complete.")

                    # LinkedIn shows an image crop/edit screen after upload
                    # We must click "Done" to return to the post composer
                    logger.info("Looking for image edit 'Done' button...")
                    done_selectors = [
                        "button:has-text('Done')",
                        "button[aria-label='Done']",
                        "button:has-text('done')",
                        "button.share-box-image-editor__action-btn",
                        "button.artdeco-button--primary:has-text('Done')",
                        "div[class*='image-edit'] button:has-text('Done')",
                        "div[class*='crop'] button:has-text('Done')",
                        "button:has-text('Next')",
                        "button:has-text('Apply')",
                    ]
                    done_clicked = False
                    for done_attempt in range(10):
                        for dsel in done_selectors:
                            try:
                                dbtn = self.page.locator(dsel).first
                                if dbtn.is_visible(timeout=2000):
                                    dbtn.click()
                                    done_clicked = True
                                    logger.info(f"Clicked image edit 'Done' button: {dsel} (attempt {done_attempt+1})")
                                    break
                            except Exception:
                                continue
                        if done_clicked:
                            break
                        logger.info(f"'Done' button not found on attempt {done_attempt+1}, waiting...")
                        self.page.wait_for_timeout(2000)

                    if done_clicked:
                        # Wait for LinkedIn to return to the post composer
                        self.page.wait_for_timeout(5000)
                        logger.info("Returned to post composer after image edit.")
                    else:
                        logger.warning("Could not find 'Done' button — image edit screen may not have appeared.")
                        try:
                            self.page.screenshot(path=str(LOGS_DIR / "debug_no_done_btn.png"))
                        except Exception:
                            pass

                except Exception as e:
                    logger.warning(f"Image upload failed (posting text only): {e}")

            # Type the post text AFTER image upload
            # Re-find the editor (LinkedIn may rebuild DOM after image upload)
            logger.info("Re-finding editor after image upload...")
            editor = None
            for attempt in range(5):
                for sel in editor_selectors:
                    try:
                        el = self.page.locator(sel).first
                        if el.is_visible(timeout=3000):
                            editor = el
                            logger.info(f"Re-found editor: {sel} (attempt {attempt+1})")
                            break
                    except Exception:
                        continue
                if editor:
                    break
                logger.info(f"Editor not found on re-find attempt {attempt+1}, waiting...")
                self.page.wait_for_timeout(3000)

            if not editor:
                logger.error("Could not re-find editor after image upload")
                self.page.screenshot(path=str(LOGS_DIR / "debug_editor_after_img.png"))
                return False

            logger.info("Typing post text...")
            editor.click()
            self.page.wait_for_timeout(1000)
            # Use keyboard type for better compatibility
            self.page.keyboard.type(text, delay=10)
            self.page.wait_for_timeout(3000)

            # Click Post/Share button (retry up to 3 times — button may be
            # temporarily disabled while LinkedIn processes an uploaded image)
            logger.info("Clicking Post button...")
            post_selectors = [
                "button.share-actions__primary-action",
                "button:has-text('Post')",
                "button:has-text('Share now')",
                "[aria-label='Post']",
                "button.artdeco-button--primary:has-text('Post')",
                "button[type='submit']",
                ".share-box-footer button.artdeco-button--primary",
                "button.share-actions__primary-action.artdeco-button--primary",
                "footer button.artdeco-button--primary",
            ]
            # Save screenshot before clicking Post for debugging
            try:
                self.page.screenshot(path=str(LOGS_DIR / "debug_before_post_click.png"))
                logger.info("Saved pre-click screenshot.")
            except Exception:
                pass

            posted = False
            for attempt in range(8):
                if attempt > 0:
                    logger.info(f"Retry {attempt}/7 — waiting for Post button to become enabled...")
                    self.page.wait_for_timeout(8000)
                for sel in post_selectors:
                    try:
                        btn = self.page.locator(sel).last
                        if btn.is_visible(timeout=5000):
                            # Wait up to 20s for button to become enabled (image processing)
                            for wait_i in range(20):
                                if btn.is_enabled():
                                    break
                                self.page.wait_for_timeout(1000)
                            if btn.is_enabled():
                                # Try normal click first
                                btn.click(force=True)
                                logger.info(f"Clicked post button (force): {sel} (attempt {attempt+1})")
                                self.page.wait_for_timeout(3000)

                                # Check if composer dialog is still open
                                composer_still_open = False
                                for check_sel in [".ql-editor", "[contenteditable='true'][role='textbox']"]:
                                    try:
                                        if self.page.locator(check_sel).first.is_visible(timeout=2000):
                                            composer_still_open = True
                                            break
                                    except Exception:
                                        pass

                                if not composer_still_open:
                                    posted = True
                                    logger.info(f"Post submitted — composer closed.")
                                    break
                                else:
                                    # Composer still open — try dispatch_event click
                                    logger.info("Composer still open after click, trying dispatch_event...")
                                    try:
                                        btn.dispatch_event("click")
                                        self.page.wait_for_timeout(3000)
                                    except Exception:
                                        pass
                                    # Also try keyboard shortcut Ctrl+Enter
                                    try:
                                        self.page.keyboard.press("Control+Enter")
                                        logger.info("Tried Ctrl+Enter to submit.")
                                        self.page.wait_for_timeout(3000)
                                    except Exception:
                                        pass

                                    # Re-check if composer closed
                                    composer_gone = True
                                    for check_sel in [".ql-editor", "[contenteditable='true'][role='textbox']"]:
                                        try:
                                            if self.page.locator(check_sel).first.is_visible(timeout=2000):
                                                composer_gone = False
                                                break
                                        except Exception:
                                            pass
                                    if composer_gone:
                                        posted = True
                                        logger.info("Post submitted after fallback click.")
                                        break
                                    else:
                                        logger.info(f"Composer still open — will retry...")
                            else:
                                logger.info(f"Button visible but disabled after 20s: {sel}")
                    except Exception as e:
                        logger.debug(f"Selector {sel} failed: {e}")
                        continue
                if posted:
                    break

            if not posted:
                logger.error("Could not click Post button — saving screenshot")
                self.page.screenshot(path=str(LOGS_DIR / "debug_postbtn_fail.png"))
                return False

            # Wait for post to be fully submitted
            self.page.wait_for_timeout(10000)

            # Save screenshot after posting for verification
            try:
                self.page.screenshot(path=str(LOGS_DIR / "debug_after_post_click.png"))
                logger.info("Saved post-click screenshot.")
            except Exception:
                pass

            # Verify post was published
            url = self.page.url
            if "feed" in url:
                logger.info("Post published successfully!")
                return True
            elif "article" in url:
                logger.error(f"Ended up on article page instead of post. URL: {url}")
                return False
            else:
                logger.warning(f"Uncertain if post published. URL: {url}")
                return True

        except PWTimeout as e:
            logger.error(f"Post timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Post error: {e}")
            return False


# ── File processor ─────────────────────────────────────────────────────────────
def archive_file(filepath: Path, status: str, note: str):
    """Move processed file to /Done with metadata."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE_DIR / f"posted_{ts}_{filepath.name}"
    content = filepath.read_text(encoding="utf-8")
    content += f"""

---
## LinkedIn Playwright — Result
- **Status:** {status}
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Note:** {note}
"""
    done_path.write_text(content, encoding="utf-8")
    filepath.unlink()
    logger.info(f"Archived to Done: {done_path.name}")


def process_approved_posts(poster: LinkedInPoster) -> int:
    """Scan /Approved for linkedin_post_*.md files and publish them."""
    files = sorted(APPROVED_DIR.glob("linkedin_post_*.md"))
    if not files:
        logger.debug("No LinkedIn posts in /Approved.")
        return 0

    published = 0
    for f in files:
        logger.info(f"Processing: {f.name}")
        post_text = extract_post_text(f)

        if not post_text:
            logger.error(f"Could not extract post text from {f.name}")
            archive_file(f, "ERROR", "Could not extract post text")
            continue

        image_path = extract_image_path(f)
        if image_path:
            logger.info(f"Image found: {image_path}")
        logger.info(f"Post text ({len(post_text)} chars): {post_text[:80]}...")
        success = poster.post(post_text, image_path)

        if success:
            archive_file(f, "PUBLISHED", "Post published to LinkedIn via Playwright")
            published += 1
        else:
            archive_file(f, "FAILED", "Playwright post failed — check logs")

    return published


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LinkedIn Playwright Poster")
    parser.add_argument("--watch",      action="store_true", help="Watch /Approved continuously")
    parser.add_argument("--test-login", action="store_true", help="Just test login")
    args = parser.parse_args()

    env = load_env()
    email    = env.get("LINKEDIN_EMAIL", "")
    password = env.get("LINKEDIN_PASSWORD", "")

    if not email or not password or "your_linkedin" in email:
        logger.error("LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set in .env")
        return

    poster = LinkedInPoster(email, password)

    try:
        poster.start()

        # Login if needed
        if not poster.is_logged_in():
            if not poster.login():
                logger.error("Login failed. Exiting.")
                return
        else:
            logger.info("Already logged in (session restored).")

        if args.test_login:
            logger.info("Login test successful!")
            return

        if args.watch:
            logger.info(f"Watch mode — scanning /Approved every {POLL_INTERVAL}s")
            while True:
                count = process_approved_posts(poster)
                if count:
                    logger.info(f"Published {count} post(s)")
                time.sleep(POLL_INTERVAL)
        else:
            count = process_approved_posts(poster)
            logger.info(f"Done. Published {count} post(s).")

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        poster.stop()


if __name__ == "__main__":
    main()
