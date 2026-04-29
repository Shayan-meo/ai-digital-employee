"""
Social Media Watcher — Gold Tier
Watches /Needs_Action for social media post tasks.
Drafts posts for Twitter/X, Facebook, and Instagram.
Routes ALL drafts to /Pending_Approval — human must approve before posting.

Supported platforms:
    - Twitter/X  (keywords: twitter, tweet, x.com)
    - Facebook   (keywords: facebook, fb)
    - Instagram  (keywords: instagram, insta, ig)

Usage:
    python social_media_watcher.py          # run once
    python social_media_watcher.py --watch  # continuous watch every 60s
"""

import argparse
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT       = Path(__file__).parent.resolve()
NEEDS_ACTION     = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL = VAULT_ROOT / "Pending_Approval"
DONE             = VAULT_ROOT / "Done"
LOGS_DIR         = VAULT_ROOT / "Logs"

for d in (NEEDS_ACTION, PENDING_APPROVAL, DONE, LOGS_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"social_media_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds

# ── Platform detection ─────────────────────────────────────────────────────────
PLATFORMS = {
    "twitter": {
        "keywords": ["twitter", "tweet", "x.com", "post on x"],
        "label":    "Twitter/X",
        "limits":   "280 characters max. Punchy, use hashtags, emojis optional.",
    },
    "facebook": {
        "keywords": ["facebook", "fb", "facebook post"],
        "label":    "Facebook",
        "limits":   "No character limit. Conversational tone, can be longer. Use 1-3 hashtags.",
    },
    "instagram": {
        "keywords": ["instagram", "insta", "ig", "instagram post"],
        "label":    "Instagram",
        "limits":   "Caption up to 2200 chars. Visual storytelling tone. Use 5-10 hashtags at end.",
    },
}


def detect_platforms(content: str) -> list[str]:
    """Return list of platform keys detected in the task content."""
    content_lower = content.lower()
    found = []
    for platform, cfg in PLATFORMS.items():
        if any(kw in content_lower for kw in cfg["keywords"]):
            found.append(platform)
    # If content says "social media" or "all platforms" — include all
    if any(kw in content_lower for kw in ["social media", "all platforms", "everywhere"]):
        found = list(PLATFORMS.keys())
    return list(dict.fromkeys(found))  # deduplicate, preserve order


def is_social_media_task(content: str) -> bool:
    return bool(detect_platforms(content))


# ── Claude draft ───────────────────────────────────────────────────────────────
def find_claude() -> str | None:
    import shutil, os
    cmd = shutil.which("claude") or shutil.which("claude.cmd")
    if not cmd:
        npm = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
        if npm.exists():
            return str(npm)
    return cmd


def draft_post(platform: str, task_content: str) -> str:
    """Use Claude to draft a platform-specific post."""
    cfg = PLATFORMS[platform]
    handbook_path = VAULT_ROOT / "Company_Handbook.md"
    handbook = handbook_path.read_text(encoding="utf-8") if handbook_path.exists() else ""

    prompt = f"""You are an AI Employee writing a {cfg['label']} post for a business.

## Company Rules
{handbook}

## Post Guidelines for {cfg['label']}
{cfg['limits']}

## Task / Content to Post About
{task_content}

Write a compelling {cfg['label']} post that:
- Matches the platform tone and style
- Is professional and engaging
- Follows the character/length guidelines
- Includes relevant hashtags

Return ONLY the post text, nothing else."""

    claude = find_claude()
    if not claude:
        logger.warning("Claude CLI not found — using fallback draft")
        return f"[AUTO-DRAFT — {cfg['label']}]\n\n{task_content[:300]}\n\n#Business #AI #Automation"

    try:
        result = subprocess.run(
            [claude, "-p", prompt],
            capture_output=True, text=True, timeout=120, cwd=str(VAULT_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.error(f"Claude draft failed: {e}")

    return f"[AUTO-DRAFT — {cfg['label']}]\n\n{task_content[:300]}\n\n#Business #AI #Automation"


# ── Approval file creator ──────────────────────────────────────────────────────
def create_approval_file(source_file: Path, platform: str, draft: str, original: str) -> Path:
    """Create /Pending_Approval file for a platform post draft."""
    cfg = PLATFORMS[platform]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{platform}_post_{ts}_{source_file.stem}.md"
    path = PENDING_APPROVAL / filename

    content = f"""# {cfg['label']} Post — Pending Approval

## Metadata
- **Platform:** {cfg['label']}
- **Source Task:** {source_file.name}
- **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Watcher:** Social Media Watcher (Gold Tier)

## Instructions
1. Review the drafted post below
2. Edit if needed (modify text inside the ``` block)
3. Move this file to `/Approved` to publish, or delete to cancel

## Drafted Post

```
{draft}
```

## Original Task
{original}
"""
    path.write_text(content, encoding="utf-8")
    logger.info(f"Approval file created: Pending_Approval/{filename}")
    return path


def archive_task(source_file: Path, platforms: list[str]):
    """Move processed task to /Done."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE / source_file.name
    if done_path.exists():
        done_path = DONE / f"{source_file.stem}_{ts}{source_file.suffix}"

    content = source_file.read_text(encoding="utf-8")
    content += f"""

---
## Social Media Watcher — Processing Complete
- **Platforms detected:** {', '.join(PLATFORMS[p]['label'] for p in platforms)}
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status:** Drafts created in /Pending_Approval
"""
    done_path.write_text(content, encoding="utf-8")
    source_file.unlink()
    logger.info(f"Task archived: Done/{done_path.name}")


# ── Poll cycle ─────────────────────────────────────────────────────────────────
def poll_cycle() -> int:
    processed = 0
    for task_file in sorted(NEEDS_ACTION.glob("*.md")):
        try:
            # Skip email task files — they are handled by gmail_watcher
            if task_file.name.startswith("email_") or task_file.name.startswith("approved_"):
                continue

            content = task_file.read_text(encoding="utf-8")
            platforms = detect_platforms(content)
            if not platforms:
                continue

            logger.info(f"Social media task: {task_file.name} → {[PLATFORMS[p]['label'] for p in platforms]}")

            for platform in platforms:
                draft = draft_post(platform, content)
                create_approval_file(task_file, platform, draft, content)

            archive_task(task_file, platforms)
            processed += 1

        except Exception as e:
            logger.error(f"Error processing {task_file.name}: {e}")

    return processed


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Social Media Watcher (Gold Tier)")
    parser.add_argument("--watch", action="store_true", help="Watch continuously")
    args = parser.parse_args()

    logger.info("Social Media Watcher started (Gold Tier)")
    logger.info(f"Platforms: {', '.join(cfg['label'] for cfg in PLATFORMS.values())}")

    if args.watch:
        logger.info(f"Watch mode — polling every {POLL_INTERVAL}s")
        while True:
            try:
                count = poll_cycle()
                if count:
                    logger.info(f"Processed {count} social media task(s)")
            except Exception as e:
                logger.error(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)
    else:
        count = poll_cycle()
        logger.info(f"Done. Processed {count} task(s).")


if __name__ == "__main__":
    main()
