"""
Social Post Helper — Called by Flask API as a subprocess.
Posts to a single platform using the Playwright scripts.

Usage:
  python social_post_helper.py <platform> <text_file> [image_path]

Writes result to stdout: POST_OK | POST_FAILED | LOGIN_FAILED
All debug/error output goes to stderr so Flask can capture both cleanly.
"""

import sys
import os
import traceback
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.parent.resolve()  # D:\AI_Employee_Vault
sys.path.insert(0, str(VAULT_ROOT))
os.chdir(str(VAULT_ROOT))

from dotenv import load_dotenv
load_dotenv(VAULT_ROOT / ".env")


def log(msg):
    """Print to stderr so it shows in Flask terminal."""
    print(f"[social_helper] {msg}", file=sys.stderr, flush=True)


def post_twitter(text, image_path):
    from twitter_playwright import TwitterPoster
    username = os.getenv("TWITTER_USERNAME", "")
    password = os.getenv("TWITTER_PASSWORD", "")
    email = os.getenv("TWITTER_EMAIL", "")
    log(f"Twitter — user={username}, has_image={image_path is not None}")
    if not username or not password:
        log("ERROR: TWITTER_USERNAME or TWITTER_PASSWORD not set in .env")
        return False, "Credentials missing in .env"

    poster = TwitterPoster(username, password, email)
    poster.start()
    try:
        if not poster.is_logged_in():
            log("Twitter — not logged in, attempting login...")
            if not poster.login():
                log("Twitter — LOGIN FAILED")
                return False, "LOGIN_FAILED"
            log("Twitter — login successful")
        else:
            log("Twitter — already logged in via session")

        ok = poster.tweet(text, image_path)
        log(f"Twitter — tweet result: {ok}")
        return ok, "POST_OK" if ok else "POST_FAILED"
    except Exception as e:
        log(f"Twitter — EXCEPTION: {e}")
        traceback.print_exc(file=sys.stderr)
        return False, str(e)
    finally:
        poster.stop()


def post_facebook(text, image_path):
    from facebook_playwright import FacebookPoster
    email = os.getenv("FACEBOOK_EMAIL", "")
    password = os.getenv("FACEBOOK_PASSWORD", "")
    log(f"Facebook — email={email}, has_image={image_path is not None}")
    if not email or not password:
        log("ERROR: FACEBOOK_EMAIL or FACEBOOK_PASSWORD not set in .env")
        return False, "Credentials missing in .env"

    poster = FacebookPoster(email, password)
    poster.start()
    try:
        if not poster.is_logged_in():
            log("Facebook — not logged in, attempting login...")
            if not poster.login():
                log("Facebook — LOGIN FAILED")
                return False, "LOGIN_FAILED"
            log("Facebook — login successful")
        else:
            log("Facebook — already logged in via session")

        ok = poster.post(text, image_path)
        log(f"Facebook — post result: {ok}")
        return ok, "POST_OK" if ok else "POST_FAILED"
    except Exception as e:
        log(f"Facebook — EXCEPTION: {e}")
        traceback.print_exc(file=sys.stderr)
        return False, str(e)
    finally:
        poster.stop()


def post_linkedin(text, image_path):
    from linkedin_playwright import LinkedInPoster
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    log(f"LinkedIn — email={email}, has_image={image_path is not None}")
    if not email or not password:
        log("ERROR: LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set in .env")
        return False, "Credentials missing in .env"

    poster = LinkedInPoster(email, password)
    poster.start()
    try:
        if not poster.is_logged_in():
            log("LinkedIn — not logged in, attempting login...")
            if not poster.login():
                log("LinkedIn — LOGIN FAILED")
                return False, "LOGIN_FAILED"
            log("LinkedIn — login successful")
        else:
            log("LinkedIn — already logged in via session")

        ok = poster.post(text, image_path)
        log(f"LinkedIn — post result: {ok}")
        return ok, "POST_OK" if ok else "POST_FAILED"
    except Exception as e:
        log(f"LinkedIn — EXCEPTION: {e}")
        traceback.print_exc(file=sys.stderr)
        return False, str(e)
    finally:
        poster.stop()


def post_instagram(text, image_path):
    from instagram_playwright import InstagramPoster
    username = os.getenv("INSTAGRAM_USERNAME", "")
    password = os.getenv("INSTAGRAM_PASSWORD", "")
    log(f"Instagram — user={username}, image={image_path}")
    if not username or not password:
        log("ERROR: INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not set in .env")
        return False, "Credentials missing in .env"

    if not image_path:
        log("ERROR: Instagram requires an image")
        return False, "Image required"

    poster = InstagramPoster(username, password)
    poster.start()
    try:
        if not poster.is_logged_in():
            log("Instagram — not logged in, attempting login...")
            if not poster.login():
                log("Instagram — LOGIN FAILED")
                return False, "LOGIN_FAILED"
            log("Instagram — login successful")
        else:
            log("Instagram — already logged in via session")

        ok = poster.post(text, image_path)
        log(f"Instagram — post result: {ok}")
        return ok, "POST_OK" if ok else "POST_FAILED"
    except Exception as e:
        log(f"Instagram — EXCEPTION: {e}")
        traceback.print_exc(file=sys.stderr)
        return False, str(e)
    finally:
        poster.stop()


POSTERS = {
    "twitter": post_twitter,
    "facebook": post_facebook,
    "linkedin": post_linkedin,
    "instagram": post_instagram,
}


def main():
    if len(sys.argv) < 3:
        print("Usage: social_post_helper.py <platform> <text_file> [image_path]", file=sys.stderr)
        print("RESULT:ERROR:Missing arguments")
        sys.exit(1)

    platform = sys.argv[1].lower()
    text_file = sys.argv[2]
    image_arg = sys.argv[3] if len(sys.argv) > 3 else ""

    # Read post text from file (avoids shell quoting issues)
    try:
        text = Path(text_file).read_text(encoding="utf-8").strip()
    except Exception as e:
        log(f"Cannot read text file {text_file}: {e}")
        print(f"RESULT:ERROR:Cannot read text file: {e}")
        sys.exit(1)

    image_path = Path(image_arg) if image_arg and Path(image_arg).exists() else None

    log(f"=== Starting {platform.upper()} post ===")
    log(f"Text ({len(text)} chars): {text[:80]}{'...' if len(text) > 80 else ''}")
    log(f"Image: {image_path or '(none)'}")

    poster_fn = POSTERS.get(platform)
    if not poster_fn:
        log(f"Unknown platform: {platform}")
        print(f"RESULT:ERROR:Unknown platform: {platform}")
        sys.exit(1)

    try:
        ok, msg = poster_fn(text, image_path)
        if ok:
            log(f"=== {platform.upper()} SUCCESS ===")
            print(f"RESULT:OK:{msg}")
        else:
            log(f"=== {platform.upper()} FAILED: {msg} ===")
            print(f"RESULT:FAILED:{msg}")
    except Exception as e:
        log(f"=== {platform.upper()} CRASHED: {e} ===")
        traceback.print_exc(file=sys.stderr)
        print(f"RESULT:ERROR:{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
