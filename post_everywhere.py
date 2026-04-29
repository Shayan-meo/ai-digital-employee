"""
Universal Social Media Poster
==============================
Post text + optional image to ALL platforms with one command.
Directly calls each platform's Playwright poster — no manual steps needed.

Usage:
  python post_everywhere.py --text "Hello world!" --image photo.jpg
  python post_everywhere.py --file my_post.md
  python post_everywhere.py --text "Just text, no image"
  python post_everywhere.py --file my_post.md --platforms linkedin,twitter

Platforms: linkedin, twitter, facebook, instagram, whatsapp
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.resolve()
APPROVED = VAULT / "Approved"
DONE = VAULT / "Done"
LOGS = VAULT / "Logs"

for d in (APPROVED, DONE, LOGS):
    d.mkdir(exist_ok=True)

ALL_PLATFORMS = ["linkedin", "twitter", "facebook", "instagram"]

# ── Logging ──────────────────────────────────────────────────────────────────
log_file = LOGS / f"post_everywhere_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("post_everywhere")


# ── .env loader ──────────────────────────────────────────────────────────────
def load_env() -> dict:
    env_path = VAULT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── Read post from markdown file ─────────────────────────────────────────────
def read_post_file(path: Path) -> tuple[str, str]:
    """Read a markdown post file. Returns (text, image_path)."""
    content = path.read_text(encoding="utf-8")
    image = ""
    text_lines = []

    for line in content.strip().splitlines():
        if line.strip().lower().startswith("image:"):
            image = line.split(":", 1)[1].strip()
        elif line.strip().startswith("!["):
            m = re.search(r"\((.+?)\)", line)
            if m:
                image = m.group(1)
        else:
            text_lines.append(line)

    return "\n".join(text_lines).strip(), image


# ── Platform posters ─────────────────────────────────────────────────────────

def post_linkedin(text: str, image: str, env: dict) -> bool:
    """Post to LinkedIn using linkedin_playwright.py."""
    log.info("=" * 50)
    log.info("LINKEDIN — Starting...")
    try:
        from linkedin_playwright import LinkedInPoster
    except ImportError:
        log.error("linkedin_playwright.py not found!")
        return False

    email = env.get("LINKEDIN_EMAIL", "")
    password = env.get("LINKEDIN_PASSWORD", "")
    if not email or not password:
        log.error("LINKEDIN_EMAIL/PASSWORD not set in .env")
        return False

    poster = LinkedInPoster(email, password)
    try:
        poster.start()
        if not poster.is_logged_in():
            if not poster.login():
                log.error("LinkedIn login failed.")
                return False
        else:
            log.info("LinkedIn: already logged in.")

        image_path = Path(image) if image and Path(image).exists() else None
        success = poster.post(text, image_path)
        if success:
            log.info("LINKEDIN — Posted successfully!")
        else:
            log.error("LINKEDIN — Post failed.")
        return success
    except Exception as e:
        log.error("LINKEDIN error: %s", e)
        return False
    finally:
        poster.stop()


def post_facebook(text: str, image: str, env: dict) -> bool:
    """Post to Facebook using facebook_playwright.py."""
    log.info("=" * 50)
    log.info("FACEBOOK — Starting...")
    try:
        from facebook_playwright import FacebookPoster
    except ImportError:
        log.error("facebook_playwright.py not found!")
        return False

    email = env.get("FACEBOOK_EMAIL", "")
    password = env.get("FACEBOOK_PASSWORD", "")
    if not email or not password:
        log.error("FACEBOOK_EMAIL/PASSWORD not set in .env")
        return False

    poster = FacebookPoster(email, password)
    try:
        poster.start()
        if not poster.is_logged_in():
            if not poster.login():
                log.error("Facebook login failed.")
                return False
        else:
            log.info("Facebook: already logged in.")

        image_path = Path(image) if image and Path(image).exists() else None
        success = poster.post(text, image_path)
        if success:
            log.info("FACEBOOK — Posted successfully!")
        else:
            log.error("FACEBOOK — Post failed.")
        return success
    except Exception as e:
        log.error("FACEBOOK error: %s", e)
        return False
    finally:
        poster.stop()


def post_twitter(text: str, image: str, env: dict) -> bool:
    """Post to Twitter/X using twitter_playwright.py."""
    log.info("=" * 50)
    log.info("TWITTER/X — Starting...")
    try:
        from twitter_playwright import TwitterPoster
    except ImportError:
        log.error("twitter_playwright.py not found!")
        return False

    username = env.get("TWITTER_USERNAME", "")
    password = env.get("TWITTER_PASSWORD", "")
    email = env.get("TWITTER_EMAIL", "")
    if not username or not password:
        log.error("TWITTER_USERNAME/PASSWORD not set in .env")
        return False

    image_path = Path(image) if image and Path(image).exists() else None

    poster = TwitterPoster(username, password, email)
    try:
        poster.start()
        if not poster.is_logged_in():
            if not poster.login():
                log.error("Twitter login failed.")
                return False
        else:
            log.info("Twitter: already logged in.")

        success = poster.tweet(text, image_path)
        if success:
            log.info("TWITTER/X — Posted successfully!")
        else:
            log.error("TWITTER/X — Post failed.")
        return success
    except Exception as e:
        log.error("TWITTER error: %s", e)
        return False
    finally:
        poster.stop()


def post_instagram(text: str, image: str, env: dict) -> bool:
    """Post to Instagram using instagram_playwright.py."""
    log.info("=" * 50)
    log.info("INSTAGRAM — Starting...")

    image_path = Path(image) if image and Path(image).exists() else None
    if not image_path:
        # Instagram requires an image — check Media folder
        media = VAULT / "Media"
        if media.exists():
            imgs = list(media.glob("*.jpg")) + list(media.glob("*.jpeg")) + list(media.glob("*.png"))
            if imgs:
                image_path = imgs[0]
                log.info("Using image from Media: %s", image_path.name)

    if not image_path:
        log.error("Instagram requires an image! Provide --image or add one to /Media.")
        return False

    try:
        from instagram_playwright import InstagramPoster
    except ImportError:
        log.error("instagram_playwright.py not found!")
        return False

    username = env.get("INSTAGRAM_USERNAME", "")
    password = env.get("INSTAGRAM_PASSWORD", "")
    if not username or not password:
        log.error("INSTAGRAM_USERNAME/PASSWORD not set in .env")
        return False

    poster = InstagramPoster(username, password)
    try:
        poster.start()
        if not poster.is_logged_in():
            if not poster.login():
                log.error("Instagram login failed.")
                return False
        else:
            log.info("Instagram: already logged in.")

        success = poster.post(text, image_path)
        if success:
            log.info("INSTAGRAM — Posted successfully!")
        else:
            log.error("INSTAGRAM — Post failed.")
        return success
    except Exception as e:
        log.error("INSTAGRAM error: %s", e)
        return False
    finally:
        poster.stop()


def post_whatsapp(text: str, image: str, env: dict) -> bool:
    """Send WhatsApp message directly to a contact using whatsapp_playwright.py."""
    log.info("=" * 50)
    log.info("WHATSAPP — Starting...")

    contact = env.get("WHATSAPP_DEFAULT_CONTACT", "")
    if not contact:
        log.error("WHATSAPP_DEFAULT_CONTACT not set in .env — add a phone number or contact name")
        log.info("Example: WHATSAPP_DEFAULT_CONTACT=03278448829")
        return False

    try:
        from whatsapp_playwright import WhatsApp
    except ImportError:
        log.error("whatsapp_playwright.py not found!")
        return False

    wa = WhatsApp()
    try:
        wa.open()
        if not wa.wait_login(max_seconds=30):
            log.error("WhatsApp not logged in. Run: python whatsapp_playwright.py --setup")
            return False

        success = wa.send(contact, text)
        if success:
            log.info("WHATSAPP — Message sent to %s!", contact)
        else:
            log.error("WHATSAPP — Send failed to %s.", contact)
        return success
    except Exception as e:
        log.error("WHATSAPP error: %s", e)
        return False
    finally:
        wa.close()


# ── Platform dispatcher ──────────────────────────────────────────────────────
POSTERS = {
    "linkedin":  post_linkedin,
    "twitter":   post_twitter,
    "facebook":  post_facebook,
    "instagram": post_instagram,
    "whatsapp":  post_whatsapp,
}


def log_action(text: str, platforms: list[str], results: dict):
    """Log the posting action."""
    task_log = LOGS / f"{datetime.now():%Y-%m-%d}_task_log.md"
    with open(task_log, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%H:%M} | **Post Everywhere**\n")
        f.write(f"  - Text: {text[:80]}...\n")
        for p, ok in results.items():
            status = "OK" if ok else "FAILED"
            f.write(f"  - {p}: {status}\n")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Post to all social media platforms at once")
    ap.add_argument("--text", "-t", help="Post text content")
    ap.add_argument("--image", "-i", help="Path to image file")
    ap.add_argument("--file", "-f", help="Read post from a markdown file")
    ap.add_argument(
        "--platforms", "-p",
        default=",".join(ALL_PLATFORMS),
        help=f"Comma-separated platforms (default: all). Options: {','.join(ALL_PLATFORMS)}",
    )
    args = ap.parse_args()

    # Get text content
    text = ""
    image = args.image or ""

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        text, file_image = read_post_file(path)
        if file_image and not image:
            image = file_image
    elif args.text:
        text = args.text
    else:
        print("Error: Provide --text or --file")
        ap.print_help()
        sys.exit(1)

    if not text.strip():
        print("Error: Post text is empty")
        sys.exit(1)

    if image and not Path(image).exists():
        log.warning("Image file not found: %s", image)

    platforms = [p.strip().lower() for p in args.platforms.split(",")]
    env = load_env()

    print()
    log.info("Post Everywhere — Starting")
    log.info("Platforms: %s", ", ".join(platforms))
    log.info("Text: %s%s", text[:80], "..." if len(text) > 80 else "")
    log.info("Image: %s", image or "(none)")
    print()

    results = {}
    for platform in platforms:
        poster_fn = POSTERS.get(platform)
        if not poster_fn:
            log.warning("Unknown platform: %s — skipping", platform)
            continue

        try:
            ok = poster_fn(text, image, env)
            results[platform] = ok
        except Exception as e:
            log.error("%s crashed: %s", platform.upper(), e)
            results[platform] = False

        # Small pause between platforms to avoid rate limits
        time.sleep(2)

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    log.info("=" * 50)
    log.info("RESULTS:")
    for platform, ok in results.items():
        status = "OK" if ok else "FAILED"
        log.info("  %-12s %s", platform, status)

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    log.info("Total: %d/%d platforms posted successfully.", passed, total)

    log_action(text, platforms, results)


if __name__ == "__main__":
    main()
