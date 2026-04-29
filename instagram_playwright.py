"""
Instagram Playwright Poster — Gold Tier
Watches /Approved for instagram_post_*.md files and publishes them automatically.

Features:
- Login with email/password (session saved to avoid repeated logins)
- Detects instagram_post_*.md files in /Approved
- Extracts post caption and publishes to Instagram
- Moves processed file to /Done
- Full audit logging

Usage:
    python instagram_playwright.py              # run once
    python instagram_playwright.py --watch      # continuous watch mode
    python instagram_playwright.py --test-login # just test login works

Message file format (/Approved/instagram_post_*.md):
    ## Post Content

    ```
    Your Instagram caption here.
    #hashtags
    ```
"""

import argparse
import logging
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
SESSION_FILE = VAULT_ROOT / ".instagram_session"

for d in (APPROVED_DIR, DONE_DIR, LOGS_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"instagram_playwright_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


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


# ── Image path extractor ──────────────────────────────────────────────────────
def extract_image_path(filepath: Path) -> Path | None:
    """Extract image path from ## Image section."""
    content = filepath.read_text(encoding="utf-8")
    match = re.search(r"##\s*Image\s*\n+(.+)", content)
    if match:
        img_path = Path(match.group(1).strip())
        if img_path.exists():
            return img_path
        # Try relative to Media folder
        media_path = VAULT_ROOT / "Media" / img_path.name
        if media_path.exists():
            return media_path
    # Fallback: first image in Media folder
    media_files = list((VAULT_ROOT / "Media").glob("*.jpg")) + \
                  list((VAULT_ROOT / "Media").glob("*.jpeg")) + \
                  list((VAULT_ROOT / "Media").glob("*.png"))
    if media_files:
        return media_files[0]
    return None


# ── Post text extractor ────────────────────────────────────────────────────────
def extract_post_text(filepath: Path) -> str | None:
    content = filepath.read_text(encoding="utf-8")

    # Between ``` markers
    match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # ## Post Content section
    match = re.search(r"##\s*Post Content\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip()
        return text or None

    # ## Drafted Post section
    match = re.search(r"##\s*Drafted Post\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip()
        return text or None

    # Double quotes
    match = re.search(r'"(.*?)"', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # ## Original Content section
    match = re.search(r"##\s*Original Content\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = re.sub(r'^"+|"+$', '', match.group(1).strip()).strip()
        return text or None

    return None


# ── Instagram automation ───────────────────────────────────────────────────────
class InstagramPoster:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.pw       = None
        self.browser  = None
        self.context  = None
        self.page     = None

    def start(self):
        self.pw      = sync_playwright().start()
        storage      = str(SESSION_FILE) if SESSION_FILE.exists() else None
        self.browser = self.pw.chromium.launch(headless=False)
        self.context = self.browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.new_page()

    def stop(self):
        if self.context:
            self.context.storage_state(path=str(SESSION_FILE))
            logger.info("Session saved.")
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    def is_logged_in(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            self.page.goto("https://www.instagram.com/", timeout=15000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)
            url = self.page.url
            if "login" in url or "accounts/login" in url:
                return False
            # Check for home feed indicator
            try:
                self.page.wait_for_selector("svg[aria-label='Home']", timeout=5000)
                return True
            except Exception:
                pass
            try:
                self.page.wait_for_selector("a[href='/']", timeout=3000)
                return True
            except Exception:
                pass
            return "instagram.com" in url and "login" not in url
        except Exception:
            return False

    def login(self) -> bool:
        logger.info("Logging in to Instagram...")
        try:
            self.page.goto("https://www.instagram.com/accounts/login/",
                           timeout=30000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)

            # Fill credentials
            self.page.fill("input[name='username']", self.username)
            self.page.wait_for_timeout(800)
            self.page.fill("input[name='password']", self.password)
            self.page.wait_for_timeout(800)
            self.page.click("button[type='submit']")
            self.page.wait_for_timeout(6000)

            url = self.page.url
            # Handle "Save login info" popup
            try:
                not_now = self.page.locator("button:has-text('Not now'), button:has-text('Not Now')").first
                if not_now.is_visible(timeout=4000):
                    not_now.click()
                    self.page.wait_for_timeout(2000)
            except Exception:
                pass

            # Handle notifications popup
            try:
                not_now2 = self.page.locator("button:has-text('Not Now')").first
                if not_now2.is_visible(timeout=3000):
                    not_now2.click()
                    self.page.wait_for_timeout(2000)
            except Exception:
                pass

            url = self.page.url
            if "login" not in url and "challenge" not in url:
                logger.info("Login successful.")
                self.context.storage_state(path=str(SESSION_FILE))
                return True
            elif "challenge" in url or "checkpoint" in url or "two_factor" in url:
                logger.warning("Instagram security check — complete it manually (90 sec).")
                for _ in range(45):
                    time.sleep(2)
                    url = self.page.url
                    if "login" not in url and "challenge" not in url:
                        logger.info("Security check passed.")
                        self.context.storage_state(path=str(SESSION_FILE))
                        return True
                logger.error("Security check not completed in time.")
                return False
            else:
                logger.error(f"Login failed. URL: {url}")
                return False

        except PWTimeout:
            logger.error("Login timed out.")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def post(self, text: str, image_path: Path = None) -> bool:
        """Publish an image post with caption to Instagram."""
        logger.info("Navigating to Instagram...")
        try:
            self.page.goto("https://www.instagram.com/", timeout=20000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)

            # Click the New Post / Create button
            logger.info("Looking for Create post button...")
            clicked = False
            # Try role-based selector first (most reliable for current IG UI)
            try:
                role_btn = self.page.get_by_role("link", name="New post Create")
                role_btn.wait_for(timeout=6000, state="visible")
                role_btn.click()
                clicked = True
                logger.info("Clicked create via role selector")
                self.page.wait_for_timeout(2000)
            except Exception:
                pass

            if not clicked:
                create_selectors = [
                    "[aria-label='New post Create']",
                    "[aria-label='New post']",
                    "svg[aria-label='New post']",
                    "a[href='/create/select/']",
                    "[aria-label='Create']",
                    "svg[aria-label='Create']",
                    "span:has-text('Create')",
                ]
                for sel in create_selectors:
                    try:
                        el = self.page.locator(sel).first
                        el.wait_for(timeout=4000, state="visible")
                        el.click()
                        clicked = True
                        logger.info(f"Clicked create: {sel}")
                        self.page.wait_for_timeout(2000)
                        break
                    except Exception:
                        continue

            if not clicked:
                logger.error("Could not find Create button — saving screenshot")
                self.page.screenshot(path=str(LOGS_DIR / "ig_debug_create.png"))
                return False

            # Resize image to 1080x1080 square before upload
            resized_path = _resize_image(image_path)
            logger.info(f"Uploading image: {resized_path}")
            try:
                file_input = self.page.locator("input[type='file']").first
                file_input.set_input_files(str(resized_path))
                self.page.wait_for_timeout(3000)
                logger.info("Image uploaded.")
            except Exception as e:
                logger.error(f"Image upload failed: {e}")
                self.page.screenshot(path=str(LOGS_DIR / "ig_debug_upload.png"))
                return False

            # Click Next button(s) to reach caption screen
            for step in ["crop", "filters", "caption"]:
                try:
                    # Try role-based first
                    next_btn = None
                    try:
                        next_btn = self.page.get_by_role("button", name="Next")
                        next_btn.wait_for(timeout=5000, state="visible")
                    except Exception:
                        next_btn = self.page.locator("button:has-text('Next'), div[role='button']:has-text('Next')").last
                    if next_btn and next_btn.is_visible(timeout=3000):
                        next_btn.click()
                        self.page.wait_for_timeout(2000)
                        logger.info(f"Clicked Next ({step})")
                except Exception:
                    pass

            # Find caption textarea
            logger.info("Looking for caption input...")
            caption_selectors = [
                "div[aria-label='Write a caption...']",
                "textarea[aria-label='Write a caption...']",
                "div[aria-label='Write a caption…']",
                "textarea[aria-label='Write a caption…']",
                "div[contenteditable='true']",
                "textarea[placeholder]",
            ]
            caption_el = None
            for sel in caption_selectors:
                try:
                    el = self.page.locator(sel).first
                    el.wait_for(timeout=5000, state="visible")
                    caption_el = el
                    logger.info(f"Found caption: {sel}")
                    break
                except Exception:
                    continue

            if not caption_el:
                logger.error("Could not find caption field — saving screenshot")
                self.page.screenshot(path=str(LOGS_DIR / "ig_debug_caption.png"))
                return False

            caption_el.click()
            self.page.wait_for_timeout(500)
            self.page.keyboard.type(text, delay=15)
            self.page.wait_for_timeout(2000)

            # Click Share button
            logger.info("Clicking Share button...")
            shared = False
            # Try role-based first
            try:
                share_role = self.page.get_by_role("button", name="Share")
                share_role.wait_for(timeout=5000, state="visible")
                if share_role.is_enabled():
                    share_role.click()
                    shared = True
                    logger.info("Clicked share via role selector")
            except Exception:
                pass

            if not shared:
                share_selectors = [
                    "button:has-text('Share')",
                    "div[role='button']:has-text('Share')",
                ]
                for sel in share_selectors:
                    try:
                        btn = self.page.locator(sel).last
                        if btn.is_visible(timeout=3000) and btn.is_enabled():
                            btn.click()
                            shared = True
                            logger.info(f"Clicked share: {sel}")
                            break
                    except Exception:
                        continue

            if not shared:
                logger.error("Could not find Share button — saving screenshot")
                self.page.screenshot(path=str(LOGS_DIR / "ig_debug_share.png"))
                return False

            self.page.wait_for_timeout(5000)
            logger.info("Post published successfully!")
            return True

        except PWTimeout as e:
            logger.error(f"Post timed out: {e}")
            self.page.screenshot(path=str(LOGS_DIR / "ig_debug_timeout.png"))
            return False
        except Exception as e:
            logger.error(f"Post error: {e}")
            return False


# ── Image resizer ─────────────────────────────────────────────────────────────
def _resize_image(image_path: Path) -> Path:
    """Resize image to 1080x1080 square (center crop) for Instagram."""
    try:
        from PIL import Image as PILImage
        img = PILImage.open(str(image_path)).convert("RGB")
        w, h = img.size
        # Center crop to square
        min_side = min(w, h)
        left = (w - min_side) // 2
        top  = (h - min_side) // 2
        img  = img.crop((left, top, left + min_side, top + min_side))
        img  = img.resize((1080, 1080), PILImage.LANCZOS)
        out_path = VAULT_ROOT / ".ig_resized.jpg"
        img.save(str(out_path), "JPEG", quality=95)
        logger.info("Image resized to 1080x1080.")
        return out_path
    except Exception as e:
        logger.warning(f"Could not resize image: {e} — using original")
        return image_path


# ── Placeholder image creator ──────────────────────────────────────────────────
def _create_placeholder_image(path: Path):
    """Create a minimal white JPEG as placeholder for Instagram posts."""
    try:
        from PIL import Image
        img = Image.new("RGB", (1080, 1080), color=(255, 255, 255))
        img.save(str(path), "JPEG")
        logger.info("Placeholder image created.")
    except ImportError:
        # Minimal valid JPEG bytes (1x1 white pixel)
        jpeg_bytes = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e'
            b'=\r\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
            b'\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03'
            b'\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12'
            b'!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1'
            b'\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJ'
            b'STUVWXYZ\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd7\xff\xd9'
        )
        path.write_bytes(jpeg_bytes)
        logger.info("Minimal placeholder image created (no PIL).")


# ── File processor ─────────────────────────────────────────────────────────────
def archive_file(filepath: Path, status: str, note: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE_DIR / f"ig_posted_{ts}_{filepath.name}"
    content = filepath.read_text(encoding="utf-8")
    content += f"""

---
## Instagram Playwright — Result
- **Status:** {status}
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Note:** {note}
"""
    done_path.write_text(content, encoding="utf-8")
    filepath.unlink()
    logger.info(f"Archived to Done: {done_path.name}")


def process_approved_posts(poster: InstagramPoster) -> int:
    files = sorted(APPROVED_DIR.glob("instagram_post_*.md"))
    if not files:
        logger.debug("No Instagram posts in /Approved.")
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
        if not image_path:
            logger.error(f"No image found for {f.name} — add image to /Media folder")
            archive_file(f, "ERROR", "No image found — add image to /Media folder")
            continue

        logger.info(f"Caption ({len(post_text)} chars): {post_text[:80]}...")
        logger.info(f"Image: {image_path}")
        success = poster.post(post_text, image_path)

        if success:
            archive_file(f, "PUBLISHED", "Post published to Instagram via Playwright")
            published += 1
        else:
            archive_file(f, "FAILED", "Playwright post failed — check logs and screenshots")

    return published


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Instagram Playwright Poster")
    parser.add_argument("--watch",      action="store_true", help="Watch /Approved continuously")
    parser.add_argument("--test-login", action="store_true", help="Just test login")
    args = parser.parse_args()

    env = load_env()
    username = env.get("INSTAGRAM_USERNAME", "")
    password = env.get("INSTAGRAM_PASSWORD", "")

    if not username or not password or "your_instagram" in username:
        logger.error("INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not set in .env")
        return

    poster = InstagramPoster(username, password)

    try:
        poster.start()

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
