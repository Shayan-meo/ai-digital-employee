"""
Twitter/X Playwright Poster — v3 (Clean Rewrite)
==================================================
Dynamic Twitter poster with proper session persistence.

Features:
- Playwright native browser (no Chrome subprocess)
- Session saved via storage_state (login once, reuse forever)
- Stealth mode (playwright_stealth v2)
- Multi-step challenge handler (email / username / phone)
- Claude AI tweet generation (--generate)
- Full audit logging

Usage:
    python twitter_playwright.py --text "Hello world!"
    python twitter_playwright.py --text "My tweet" --image photo.jpg
    python twitter_playwright.py --generate --description "AI automation"
    python twitter_playwright.py --test-login
    python twitter_playwright.py --watch
"""

import argparse
import logging
import re
import subprocess
import shutil
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── Paths ─────────────────────────────────────────────────────────────────────
VAULT = Path(__file__).parent.resolve()
APPROVED_DIR = VAULT / "Approved"
DONE_DIR = VAULT / "Done"
LOGS_DIR = VAULT / "Logs"
MEDIA_DIR = VAULT / "Media"
SESSION_FILE = VAULT / ".twitter_session"

for d in (APPROVED_DIR, DONE_DIR, LOGS_DIR, MEDIA_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"twitter_playwright_{datetime.now():%Y-%m-%d}.log"
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
    env_path = VAULT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── Claude AI tweet generator ─────────────────────────────────────────────────
def generate_tweet(description: str) -> str | None:
    """Use Claude CLI to generate a tweet."""
    claude = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude:
        logger.error("Claude CLI not found on PATH")
        return None

    prompt = (
        f"Generate a professional, engaging tweet (max 280 characters) about: "
        f"{description}\n\n"
        f"Rules:\n"
        f"- Max 280 characters total\n"
        f"- Punchy, professional tone\n"
        f"- Include 2-4 relevant hashtags\n"
        f"- No quotes around the tweet\n"
        f"- Return ONLY the tweet text, nothing else"
    )

    try:
        result = subprocess.run(
            [claude, "-p", prompt],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            tweet = result.stdout.strip()[:280]
            logger.info(f"Claude generated ({len(tweet)} chars): {tweet[:80]}...")
            return tweet
        logger.error(f"Claude failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Claude error: {e}")
    return None


# ── Text extractors (for /Approved files) ─────────────────────────────────────
def extract_post_text(filepath: Path) -> str | None:
    content = filepath.read_text(encoding="utf-8")

    match = re.search(r"##\s*Post\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"##\s*Post Content\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        return re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip() or None

    match = re.search(r"##\s*Drafted Post\s*\n+(.*?)(?:\n##|\Z)", content, re.DOTALL)
    if match:
        return re.sub(r"^```.*?```$", "", match.group(1).strip(), flags=re.DOTALL).strip() or None

    return None


def extract_image_path(filepath: Path) -> Path | None:
    content = filepath.read_text(encoding="utf-8")
    match = re.search(r"##\s*Image\s*\n+(.+)", content)
    if match:
        img = match.group(1).strip()
        if img and img.lower() != "(none)":
            p = Path(img)
            if p.exists():
                return p
            mp = MEDIA_DIR / p.name
            if mp.exists():
                return mp
    match = re.search(r"(?i)^image:\s*(.+)$", content, re.MULTILINE)
    if match:
        img = match.group(1).strip()
        if img and img.lower() != "(none)":
            p = Path(img)
            if p.exists():
                return p
            mp = MEDIA_DIR / p.name
            if mp.exists():
                return mp
    return None


# ── Twitter Poster ────────────────────────────────────────────────────────────
class TwitterPoster:
    """Twitter/X poster with session persistence via storage_state."""

    def __init__(self, username: str, password: str, email: str = ""):
        self.username = username
        self.password = password
        self.email = email
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    def start(self):
        self.pw = sync_playwright().start()
        storage = str(SESSION_FILE) if SESSION_FILE.exists() else None

        self.browser = self.pw.chromium.launch(headless=False)
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
        logger.info(f"Browser started. Session: {'restored' if storage else 'fresh'}.")

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
        logger.info("Browser closed.")

    def _save_session(self):
        try:
            if self.context:
                self.context.storage_state(path=str(SESSION_FILE))
        except Exception:
            pass

    # ── Login check ───────────────────────────────────────────────────────────

    def is_logged_in(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            self.page.goto("https://x.com/home", timeout=30000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            url = self.page.url

            if "login" in url:
                return False

            # Look for logged-in indicators
            for sel in [
                "[data-testid='tweetTextarea_0']",
                "[data-testid='SideNav_AccountSwitcher_Button']",
                "[data-testid='AppTabBar_Home_Link']",
            ]:
                try:
                    if self.page.locator(sel).first.is_visible(timeout=3000):
                        logger.info(f"Logged in ({sel} found).")
                        return True
                except Exception:
                    continue

            if "x.com" in url and "login" not in url:
                logger.info("Logged in (on x.com, no login redirect).")
                return True

            return False
        except Exception as e:
            logger.warning(f"Session check error: {e}")
            return False

    # ── Login flow ────────────────────────────────────────────────────────────

    def login(self) -> bool:
        logger.info("Starting Twitter login...")
        try:
            self.page.goto("https://x.com/i/flow/login",
                           timeout=60000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(6000)

            # Step 1: Username
            logger.info("Entering username...")
            uname = self.page.locator(
                "input[autocomplete='username'], input[name='text'], input[type='text']"
            ).first
            uname.wait_for(timeout=20000, state="visible")
            uname.click()
            self.page.wait_for_timeout(500)

            # Use keyboard.type instead of fill (more reliable on Twitter)
            self.page.keyboard.type(self.username or self.email, delay=50)
            self.page.wait_for_timeout(1500)

            # Screenshot before clicking Next
            self.page.screenshot(path=str(LOGS_DIR / "tw_step1_username.png"))

            self.page.locator(
                "button:has-text('Next'), [role='button']:has-text('Next')"
            ).first.click()
            self.page.wait_for_timeout(5000)

            # Screenshot after Next
            self.page.screenshot(path=str(LOGS_DIR / "tw_step2_after_next.png"))
            logger.info(f"After username Next — URL: {self.page.url}")

            # Step 2: Check what screen we're on
            # Could be: password, challenge, or still username (error)
            for attempt in range(3):
                # Check password first
                try:
                    pw = self.page.locator(
                        "input[name='password'], input[type='password']")
                    if pw.first.is_visible(timeout=3000):
                        logger.info("Password field found directly.")
                        break
                except Exception:
                    pass

                # Handle challenge if present
                self._handle_one_challenge()
                self.page.wait_for_timeout(2000)

            # Step 3: Password
            logger.info("Entering password...")
            pw_input = self.page.locator(
                "input[name='password'], input[type='password'], "
                "input[autocomplete='current-password']"
            ).first

            try:
                pw_input.wait_for(timeout=15000, state="visible")
            except Exception:
                self.page.screenshot(path=str(LOGS_DIR / "tw_no_password.png"))
                logger.warning("Password field not visible — waiting longer...")
                self.page.wait_for_timeout(5000)
                try:
                    pw_input.wait_for(timeout=15000, state="visible")
                except Exception:
                    logger.error("Password field never appeared.")
                    # Manual fallback for password
                    logger.warning("Complete login manually in browser (3 min)...")
                    if self._wait_for_home(timeout=180):
                        logger.info("Manual login completed!")
                        self._save_session()
                        return True
                    return False

            pw_input.click()
            self.page.wait_for_timeout(500)
            self.page.keyboard.type(self.password, delay=30)
            self.page.wait_for_timeout(1500)

            self.page.locator(
                "button[data-testid='LoginForm_Login_Button'], button:has-text('Log in')"
            ).first.click()
            logger.info("Login button clicked...")
            self.page.wait_for_timeout(8000)

            # Step 4: Verify
            if "home" in self.page.url:
                logger.info("Login successful!")
                self._save_session()
                return True

            if self._wait_for_home(timeout=30):
                logger.info("Login successful!")
                self._save_session()
                return True

            # Manual fallback
            logger.warning("Auto-login incomplete — complete manually in browser (3 min)...")
            if self._wait_for_home(timeout=180):
                logger.info("Manual login completed!")
                self._save_session()
                return True

            logger.error("Login timed out.")
            return False

        except PWTimeout:
            logger.error("Page load timed out.")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def _handle_one_challenge(self):
        """Handle a single Twitter verification challenge (email/username/phone)."""
        # Check if there's a challenge input (ocfEnterTextTextInput)
        try:
            challenge = self.page.locator(
                "input[data-testid='ocfEnterTextTextInput']"
            ).first
            if not challenge.is_visible(timeout=3000):
                return
        except Exception:
            return

        prompt_text = self._get_page_text()
        logger.info(f"Challenge detected: {prompt_text[:100]}")

        # Pick value based on prompt
        if "phone" in prompt_text:
            candidates = [self.username, self.email]
        elif "email" in prompt_text:
            candidates = [self.email, self.username]
        elif "username" in prompt_text:
            candidates = [self.username, self.email]
        else:
            candidates = [self.email, self.username]

        for val in candidates:
            if not val:
                continue
            try:
                logger.info(f"  Challenge — trying: {val}")
                challenge.click()
                self.page.wait_for_timeout(300)
                challenge.fill("")
                self.page.wait_for_timeout(200)
                self.page.keyboard.type(val, delay=30)
                self.page.wait_for_timeout(1000)

                self.page.locator(
                    "[data-testid='ocfEnterTextNextButton'], button:has-text('Next')"
                ).first.click()
                self.page.wait_for_timeout(5000)

                # Did password appear?
                try:
                    if self.page.locator(
                        "input[name='password'], input[type='password']"
                    ).first.is_visible(timeout=3000):
                        logger.info("  Challenge solved — password visible.")
                        return
                except Exception:
                    pass

                # Did we move past challenge?
                try:
                    if not self.page.locator(
                        "input[data-testid='ocfEnterTextTextInput']"
                    ).first.is_visible(timeout=2000):
                        logger.info("  Challenge passed — moved to next screen.")
                        return
                except Exception:
                    logger.info("  Challenge passed.")
                    return

                logger.info("  Value rejected, trying next...")
            except Exception as e:
                logger.warning(f"  Challenge error: {e}")

    def _get_page_text(self) -> str:
        """Get visible text from page headings/spans for challenge detection."""
        try:
            return self.page.evaluate("""
                () => {
                    const texts = [];
                    document.querySelectorAll('h1, h2, h3, span').forEach(el => {
                        const t = el.textContent.trim();
                        if (t.length > 5 && t.length < 200) texts.push(t);
                    });
                    return texts.join(' ').toLowerCase();
                }
            """) or ""
        except Exception:
            return ""

    def _wait_for_home(self, timeout=30) -> bool:
        """Wait for redirect to home page."""
        for _ in range(timeout // 2):
            time.sleep(2)
            if "home" in self.page.url:
                return True
        return False

    # ── Tweet posting ─────────────────────────────────────────────────────────

    def tweet(self, text: str, image_path: Path = None) -> bool:
        logger.info(f"Posting tweet ({len(text)} chars)...")
        try:
            # Phase 1: Find composer
            editor = self._open_composer()
            if not editor:
                logger.error("Composer not found.")
                self.page.screenshot(path=str(LOGS_DIR / "tw_no_composer.png"))
                return False

            # Phase 2: Upload image
            if image_path and Path(image_path).exists():
                self._upload_image(image_path)

            # Phase 3: Type text
            tweet_text = text[:280]
            if len(text) > 280:
                logger.warning(f"Truncated to 280 chars (was {len(text)})")

            editor.click()
            self.page.wait_for_timeout(500)
            self.page.keyboard.type(tweet_text, delay=30)
            self.page.wait_for_timeout(2000)

            # Phase 4: Click Post
            if not self._click_post(editor):
                logger.error("Could not click Post button.")
                self.page.screenshot(path=str(LOGS_DIR / "tw_post_failed.png"))
                return False

            # Phase 5: Verify
            self.page.wait_for_timeout(3000)
            toast = self.page.locator("[data-testid='toast']").count()
            if toast > 0:
                logger.info("Tweet posted! (toast confirmed)")
                self._save_session()
                return True

            logger.info("Tweet posted! (assumed success)")
            self._save_session()
            return True

        except Exception as e:
            logger.error(f"Tweet error: {e}")
            return False

    def _open_composer(self):
        """Try multiple ways to open the tweet composer."""
        # Method 1: Home page inline composer
        try:
            self.page.goto("https://x.com/home", timeout=30000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(6000)
            editor = self._find_editor()
            if editor:
                return editor
        except Exception:
            pass

        # Method 2: Direct compose URL
        try:
            self.page.goto("https://x.com/compose/post", timeout=30000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            editor = self._find_editor()
            if editor:
                return editor
        except Exception:
            pass

        # Method 3: Click compose button from home
        try:
            self.page.goto("https://x.com/home", timeout=30000,
                           wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            for sel in [
                "[data-testid='SideNav_NewTweet_Button']",
                "a[href='/compose/post']",
                "[aria-label='Compose a post']",
            ]:
                try:
                    btn = self.page.locator(sel).first
                    btn.wait_for(timeout=4000, state="visible")
                    btn.click()
                    self.page.wait_for_timeout(4000)
                    editor = self._find_editor()
                    if editor:
                        return editor
                except Exception:
                    continue
        except Exception:
            pass

        # Method 4: Wait for manual intervention (60s)
        logger.warning("Auto-open failed — open composer manually in browser (60s)...")
        for _ in range(12):
            time.sleep(5)
            editor = self._find_editor()
            if editor:
                return editor

        return None

    def _find_editor(self):
        """Find tweet text editor."""
        for sel in [
            "[data-testid='tweetTextarea_0']",
            "div[role='textbox']",
            "div[contenteditable='true'][role='textbox']",
            "[aria-label='Post text']",
            "[aria-label='What is happening?!']",
        ]:
            try:
                el = self.page.locator(sel).first
                el.wait_for(timeout=4000, state="visible")
                logger.info(f"Editor found: {sel}")
                return el
            except Exception:
                continue
        return None

    def _upload_image(self, image_path):
        """Upload image to tweet."""
        logger.info(f"Uploading image: {image_path}")
        for sel in [
            "input[data-testid='fileInput']",
            "input[type='file']",
            "input[accept*='image']",
        ]:
            try:
                self.page.locator(sel).first.set_input_files(str(image_path))
                self.page.wait_for_timeout(3000)
                logger.info("Image uploaded.")
                return
            except Exception:
                continue
        logger.warning("Image upload failed.")

    def _click_post(self, editor) -> bool:
        """Try multiple strategies to click the Post button."""
        # Remove overlays first
        try:
            self.page.evaluate("""
                const layers = document.getElementById('layers');
                if (layers) {
                    layers.querySelectorAll('div').forEach(d => {
                        const style = window.getComputedStyle(d);
                        if (style.position === 'absolute' && d.children.length === 0)
                            d.style.pointerEvents = 'none';
                    });
                    layers.style.pointerEvents = 'none';
                }
            """)
            self.page.wait_for_timeout(500)
        except Exception:
            pass

        # Strategy 1: JS click testid buttons
        for testid in ["tweetButton", "tweetButtonInline"]:
            try:
                clicked = self.page.evaluate(f"""
                    const btn = document.querySelector('[data-testid="{testid}"]');
                    if (btn && !btn.disabled) {{ btn.click(); true; }} else {{ false; }}
                """)
                if clicked:
                    self.page.wait_for_timeout(5000)
                    return True
            except Exception:
                pass

        # Strategy 2: Playwright click
        for sel in [
            "[data-testid='tweetButton']",
            "[data-testid='tweetButtonInline']",
        ]:
            try:
                btn = self.page.locator(sel).last
                btn.wait_for(timeout=3000, state="visible")
                btn.click(timeout=5000)
                self.page.wait_for_timeout(5000)
                return True
            except Exception:
                continue

        # Strategy 3: Text-based
        try:
            btn = self.page.locator("//button[.//span[text()='Post']]").last
            btn.wait_for(timeout=3000, state="visible")
            btn.click(timeout=5000)
            self.page.wait_for_timeout(5000)
            return True
        except Exception:
            pass

        # Strategy 4: Ctrl+Enter
        try:
            editor.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.press("Control+Enter")
            self.page.wait_for_timeout(5000)
            return True
        except Exception:
            pass

        return False


# ── File processor ────────────────────────────────────────────────────────────
def archive_file(filepath: Path, status: str, note: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE_DIR / f"tw_posted_{ts}_{filepath.name}"
    content = filepath.read_text(encoding="utf-8")
    content += f"\n\n---\n## Twitter — Result\n- **Status:** {status}\n"
    content += f"- **Time:** {datetime.now():%Y-%m-%d %H:%M:%S}\n- **Note:** {note}\n"
    done_path.write_text(content, encoding="utf-8")
    filepath.unlink()
    logger.info(f"Archived: {done_path.name}")


def process_approved_tweets(poster: TwitterPoster) -> int:
    patterns = ["twitter_post_*.md", "social_post_*twitter*.md"]
    files = []
    for pattern in patterns:
        files.extend(APPROVED_DIR.glob(pattern))
    for f in APPROVED_DIR.glob("social_post_*_all_platforms.md"):
        if f not in files:
            files.append(f)
    files = sorted(set(files))

    if not files:
        return 0

    posted = 0
    for f in files:
        logger.info(f"Processing: {f.name}")
        text = extract_post_text(f)
        if not text:
            archive_file(f, "ERROR", "No post text found")
            continue
        image_path = extract_image_path(f)
        success = poster.tweet(text[:280], image_path)
        if success:
            archive_file(f, "POSTED", "Tweet posted via Playwright")
            posted += 1
        else:
            archive_file(f, "FAILED", "Tweet failed — check logs")
    return posted


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Twitter/X Poster")
    parser.add_argument("--text", "-t", help="Tweet text")
    parser.add_argument("--image", "-i", help="Image path")
    parser.add_argument("--generate", action="store_true",
                        help="Generate tweet with Claude AI")
    parser.add_argument("--description", "-d",
                        help="Description for Claude generation")
    parser.add_argument("--watch", action="store_true",
                        help="Watch /Approved continuously")
    parser.add_argument("--test-login", action="store_true",
                        help="Test login only")
    args = parser.parse_args()

    env = load_env()
    username = env.get("TWITTER_USERNAME", "")
    password = env.get("TWITTER_PASSWORD", "")
    email = env.get("TWITTER_EMAIL", "")

    if not username or not password:
        logger.error("TWITTER_USERNAME/PASSWORD not set in .env")
        return

    # Generate tweet
    text = args.text or ""
    if args.generate and args.description:
        generated = generate_tweet(args.description)
        if generated:
            text = generated
        else:
            logger.error("Generation failed")
            return
    elif args.generate and not args.description:
        logger.error("--generate requires --description")
        return

    poster = TwitterPoster(username, password, email)
    try:
        poster.start()

        if not poster.is_logged_in():
            if not poster.login():
                logger.error("Login failed.")
                return
        else:
            logger.info("Already logged in (session restored).")

        if args.test_login:
            logger.info("Login test passed!")
            return

        if text:
            image = Path(args.image) if args.image else None
            if image and not image.exists():
                media_img = MEDIA_DIR / image.name
                image = media_img if media_img.exists() else None
            success = poster.tweet(text, image)
            logger.info("Tweet posted!" if success else "Tweet failed.")
            return

        if args.watch:
            logger.info(f"Watch mode — every {POLL_INTERVAL}s")
            while True:
                count = process_approved_tweets(poster)
                if count:
                    logger.info(f"Posted {count} tweet(s)")
                time.sleep(POLL_INTERVAL)
        else:
            count = process_approved_tweets(poster)
            logger.info(f"Done. Posted {count} tweet(s).")

    except KeyboardInterrupt:
        logger.info("Stopped.")
    finally:
        poster.stop()


if __name__ == "__main__":
    main()
