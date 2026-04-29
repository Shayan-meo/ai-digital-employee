"""
Facebook Playwright Poster — Fresh Build
Posts text + image to Facebook timeline via Playwright.

Usage:
    python facebook_playwright.py              # run once
    python facebook_playwright.py --watch      # continuous watch mode
    python facebook_playwright.py --test-login # just test login
"""

import argparse
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── Paths ─────────────────────────────────────────────────────────────────────
VAULT_ROOT   = Path(__file__).parent.resolve()
APPROVED_DIR = VAULT_ROOT / "Approved"
DONE_DIR     = VAULT_ROOT / "Done"
LOGS_DIR     = VAULT_ROOT / "Logs"
SESSION_FILE = VAULT_ROOT / ".facebook_session"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"

for d in (APPROVED_DIR, DONE_DIR, LOGS_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"facebook_playwright_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30


# ── .env loader ───────────────────────────────────────────────────────────────
def load_env() -> dict:
    env_path = VAULT_ROOT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── Post text extractor ──────────────────────────────────────────────────────
def extract_post_text(filepath: Path) -> str | None:
    content = filepath.read_text(encoding="utf-8")
    match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"##\s*Post Content\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip()
        return text or None
    match = re.search(r"##\s*Drafted Post\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        text = re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip()
        return text or None
    match = re.search(r'"(.*?)"', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_image_path(filepath: Path) -> Path | None:
    content = filepath.read_text(encoding="utf-8")
    for pattern in [r"##\s*Image\s*\n+(.+)", r"(?i)^image:\s*(.+)$"]:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            img = match.group(1).strip()
            if img and img != "(none)":
                p = Path(img)
                if p.exists():
                    return p
                p2 = VAULT_ROOT / "Media" / p.name
                if p2.exists():
                    return p2
    return None


# ── Facebook automation ───────────────────────────────────────────────────────
class FacebookPoster:
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
            self.page.goto("https://www.facebook.com/", timeout=15000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)
            url = self.page.url
            if "login" in url or "checkpoint" in url:
                return False
            try:
                self.page.wait_for_selector("[aria-label='Create a post']", timeout=5000)
                return True
            except Exception:
                pass
            return "facebook.com" in url and "login" not in url
        except Exception:
            return False

    def login(self) -> bool:
        logger.info("Logging in to Facebook...")
        try:
            self.page.goto("https://www.facebook.com/login",
                           timeout=30000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(2000)
            self.page.fill("#email", self.email)
            self.page.wait_for_timeout(800)
            self.page.fill("#pass", self.password)
            self.page.wait_for_timeout(800)
            self.page.click("button[name='login']")
            self.page.wait_for_timeout(6000)
            url = self.page.url
            if "checkpoint" in url or "two_step" in url:
                logger.warning("Security check — complete it manually.")
                for _ in range(45):
                    time.sleep(2)
                    url = self.page.url
                    if "login" not in url and "checkpoint" not in url:
                        logger.info("Security check passed.")
                        self.context.storage_state(path=str(SESSION_FILE))
                        return True
                logger.error("Security check not completed in time.")
                return False
            elif "login" not in url:
                logger.info("Login successful.")
                self.context.storage_state(path=str(SESSION_FILE))
                return True
            else:
                logger.error(f"Login failed. URL: {url}")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    # ── CORE: Post with text + image ──────────────────────────────────────────
    def post(self, text: str, image_path=None) -> bool:
        """
        Key fix: Upload image FIRST, then type text.
        This ensures text goes into the ACTIVE composer dialog
        (which may change after image upload).

        1. Go to facebook.com
        2. Click "What's on your mind?" to open composer
        3. If image: upload via hidden file input FIRST
        4. Wait for new dialog to settle
        5. Find textbox in the ACTIVE dialog and type text
        6. Click Post
        """
        page = self.page
        logger.info("Navigating to Facebook home...")
        try:
            page.goto("https://www.facebook.com/", timeout=20000,
                       wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Step 1: Click composer to open dialog
            logger.info("Opening post composer...")
            composer_clicked = False
            for sel in [
                "[aria-label=\"What's on your mind?\"]",
                "[aria-label='Create a post']",
                "span:has-text(\"What's on your mind\")",
            ]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(timeout=5000, state="visible")
                    el.click()
                    composer_clicked = True
                    logger.info(f"Clicked composer: {sel}")
                    break
                except Exception:
                    continue

            if not composer_clicked:
                logger.error("Could not open composer")
                page.screenshot(path=str(LOGS_DIR / "fb_err_composer.png"))
                return False

            page.wait_for_timeout(5000)

            # Step 2: Upload image FIRST (before typing text)
            if image_path:
                logger.info(f"Uploading image FIRST: {image_path}")
                try:
                    file_inputs = page.locator("input[type='file'][accept*='image']")
                    count = file_inputs.count()
                    if count > 0:
                        file_inputs.first.set_input_files(str(image_path))
                        logger.info("Image uploaded via image file input")
                    else:
                        file_inputs = page.locator("input[type='file']")
                        count = file_inputs.count()
                        if count > 0:
                            file_inputs.first.set_input_files(str(image_path))
                            logger.info("Image uploaded via generic file input")
                        else:
                            logger.warning("No file input found — posting text only")

                    # Wait for image to fully load and dialog to settle
                    # Need extra time for overlay/processing to finish
                    page.wait_for_timeout(12000)
                    logger.info("Image upload done, dialog should be settled now")

                except Exception as e:
                    logger.warning(f"Image upload failed: {e} — will post text only")

            # Step 3: Find the LAST (active) dialog — Facebook renders 2 dialogs,
            # image goes to the 2nd one, so we must target the LAST dialog always.
            logger.info("Finding the LAST (active) dialog...")
            dialog_count = page.evaluate("""() => {
                return document.querySelectorAll('[role="dialog"]').length;
            }""")
            logger.info(f"Found {dialog_count} dialog(s) on page")

            # Use .last on all selectors to always target the 2nd/last dialog
            # This is the one that has the image and is actually active

            # Step 4: Find textbox in the LAST dialog
            logger.info("Finding textbox in LAST dialog...")
            textbox = None
            for attempt in range(3):
                for sel in [
                    "[role='dialog'] div[contenteditable='true'][role='textbox']",
                    "[role='dialog'] div[contenteditable='true']",
                    "div[contenteditable='true'][role='textbox']",
                ]:
                    try:
                        loc = page.locator(sel)
                        count = loc.count()
                        if count > 0:
                            # ALWAYS pick the LAST one — that's the active dialog
                            el = loc.last
                            el.wait_for(timeout=8000, state="visible")
                            textbox = el
                            logger.info(f"Found textbox: {sel} [last of {count}] (attempt {attempt+1})")
                            break
                    except Exception:
                        continue
                if textbox:
                    break
                logger.info(f"Textbox not found on attempt {attempt+1}, waiting...")
                page.wait_for_timeout(3000)

            if not textbox:
                logger.error("Could not find textbox")
                page.screenshot(path=str(LOGS_DIR / "fb_err_textbox.png"))
                return False

            # Step 5: Focus the textbox in the LAST dialog via JS and type text
            logger.info("Focusing textbox in LAST dialog and typing text...")

            # JS: target the LAST dialog's textbox (not first!)
            page.evaluate("""() => {
                const dialogs = document.querySelectorAll('[role="dialog"]');
                const lastDialog = dialogs[dialogs.length - 1];
                let editor = null;
                if (lastDialog) {
                    editor = lastDialog.querySelector("div[contenteditable='true'][role='textbox']")
                          || lastDialog.querySelector("div[contenteditable='true']");
                }
                if (!editor) {
                    // Fallback: get the last textbox on the page
                    const allEditors = document.querySelectorAll("div[contenteditable='true'][role='textbox']");
                    editor = allEditors[allEditors.length - 1];
                }
                if (editor) {
                    editor.scrollIntoView({block: 'center'});
                    editor.click();
                    editor.focus();
                    const sel = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }""")
            page.wait_for_timeout(1500)

            # Also click via Playwright with force on the LAST textbox
            try:
                textbox.click(timeout=3000, force=True)
                logger.info("Textbox clicked with force (last dialog)")
            except Exception:
                logger.info("Force click skipped, relying on JS focus")

            page.wait_for_timeout(1000)

            # Type text
            page.keyboard.type(text, delay=30)
            page.wait_for_timeout(2000)

            # Verify text ended up in the LAST dialog's textbox
            typed_text = page.evaluate("""() => {
                const dialogs = document.querySelectorAll('[role="dialog"]');
                const lastDialog = dialogs[dialogs.length - 1];
                let editor = null;
                if (lastDialog) {
                    editor = lastDialog.querySelector("div[contenteditable='true'][role='textbox']")
                          || lastDialog.querySelector("div[contenteditable='true']");
                }
                if (!editor) {
                    const allEditors = document.querySelectorAll("div[contenteditable='true'][role='textbox']");
                    editor = allEditors[allEditors.length - 1];
                }
                return editor ? editor.innerText.trim() : '';
            }""")

            if len(typed_text) < 10:
                logger.warning(f"Text not in LAST dialog (got '{typed_text[:50]}'), injecting via JS...")
                # Fallback: insert text directly into the LAST dialog's editor
                page.evaluate("""(txt) => {
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    const lastDialog = dialogs[dialogs.length - 1];
                    let editor = null;
                    if (lastDialog) {
                        editor = lastDialog.querySelector("div[contenteditable='true'][role='textbox']")
                              || lastDialog.querySelector("div[contenteditable='true']");
                    }
                    if (!editor) {
                        const allEditors = document.querySelectorAll("div[contenteditable='true'][role='textbox']");
                        editor = allEditors[allEditors.length - 1];
                    }
                    if (editor) {
                        editor.focus();
                        editor.innerHTML = '';
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, txt);
                    }
                }""", text)
                page.wait_for_timeout(2000)
                logger.info("Text injected via JS fallback into LAST dialog")
            else:
                logger.info(f"Text verified in LAST dialog ({len(typed_text)} chars)")

            # Step 6: Click Post button — also target the LAST dialog's button
            logger.info("Clicking Post button in LAST dialog...")
            posted = False
            for sel in [
                "div[aria-label='Post'][role='button']",
                "div[role='button']:has-text('Post')",
                "button:has-text('Post')",
            ]:
                try:
                    loc = page.locator(sel)
                    count = loc.count()
                    if count > 0:
                        # LAST button = the one in the active/last dialog
                        btn = loc.last
                        if btn.is_visible(timeout=5000) and btn.is_enabled():
                            btn.click()
                            posted = True
                            logger.info(f"Clicked Post: {sel} [last of {count}]")
                            break
                except Exception:
                    continue

            if not posted:
                logger.error("Could not find Post button")
                page.screenshot(path=str(LOGS_DIR / "fb_err_postbtn.png"))
                return False

            page.wait_for_timeout(5000)
            logger.info("Post published successfully!")
            return True

        except Exception as e:
            logger.error(f"Post error: {e}")
            page.screenshot(path=str(LOGS_DIR / "fb_err_general.png"))
            return False


# ── File processor ────────────────────────────────────────────────────────────
def archive_file(filepath: Path, status: str, note: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE_DIR / f"fb_posted_{ts}_{filepath.name}"
    content = filepath.read_text(encoding="utf-8")
    content += f"""

---
## Facebook Playwright — Result
- **Status:** {status}
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Note:** {note}
"""
    done_path.write_text(content, encoding="utf-8")
    filepath.unlink()
    logger.info(f"Archived to Done: {done_path.name}")


def process_approved_posts(poster: FacebookPoster) -> int:
    files = sorted(APPROVED_DIR.glob("facebook_post_*.md"))
    files += sorted(NEEDS_ACTION_DIR.glob("*facebook_post_*.md"))
    if not files:
        return 0

    published = 0
    for f in files:
        logger.info(f"Processing: {f.name}")
        post_text = extract_post_text(f)
        if not post_text:
            logger.error(f"Could not extract text from {f.name}")
            archive_file(f, "ERROR", "Could not extract post text")
            continue

        image_path = extract_image_path(f)
        if image_path:
            logger.info(f"Image: {image_path}")
        logger.info(f"Text ({len(post_text)} chars): {post_text[:80]}...")

        if poster.post(post_text, image_path):
            archive_file(f, "PUBLISHED", "Post published to Facebook")
            published += 1
        else:
            archive_file(f, "FAILED", "Post failed — check logs")

    return published


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Facebook Playwright Poster")
    parser.add_argument("--watch",      action="store_true")
    parser.add_argument("--test-login", action="store_true")
    args = parser.parse_args()

    env = load_env()
    email    = env.get("FACEBOOK_EMAIL", "")
    password = env.get("FACEBOOK_PASSWORD", "")

    if not email or not password or "your_facebook" in email:
        logger.error("FACEBOOK_EMAIL or FACEBOOK_PASSWORD not set in .env")
        return

    poster = FacebookPoster(email, password)

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
            logger.info(f"Watch mode — scanning every {POLL_INTERVAL}s")
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
