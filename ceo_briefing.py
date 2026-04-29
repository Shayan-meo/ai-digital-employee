"""
CEO Briefing Generator — Gold Tier
Scans the vault every Sunday night and generates a Monday morning CEO briefing.
Saved to /Briefings/CEO_Briefing_YYYY-MM-DD.md

Usage:
    python ceo_briefing.py              # Run once immediately (for testing)
    python ceo_briefing.py --schedule   # Run on Sunday 22:00 schedule

Scheduled by scheduler.py automatically (Gold Tier).
"""

import argparse
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT       = Path(__file__).parent.resolve()
BRIEFINGS_DIR    = VAULT_ROOT / "Briefings"
DONE_DIR         = VAULT_ROOT / "Done"
LOGS_DIR         = VAULT_ROOT / "Logs"
PLANS_DIR        = VAULT_ROOT / "Plans"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
PENDING_DIR      = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR     = VAULT_ROOT / "Approved"

for d in (BRIEFINGS_DIR, LOGS_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / f"ceo_briefing_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ── Vault Scanner ──────────────────────────────────────────────────────────────

def count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return len([f for f in folder.iterdir() if f.is_file()])


def read_task_logs_this_week() -> list[dict]:
    """Read all task log entries from the past 7 days."""
    entries = []
    today = datetime.now().date()
    for i in range(7):
        day = today - timedelta(days=i)
        log_path = LOGS_DIR / f"{day}_task_log.md"
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            entries.append({"date": str(day), "content": content})
    return entries


def collect_done_files_this_week() -> list[dict]:
    """Collect tasks completed in the past 7 days from /Done."""
    tasks = []
    if not DONE_DIR.exists():
        return tasks
    cutoff = datetime.now() - timedelta(days=7)
    for f in DONE_DIR.glob("*.md"):
        if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff:
            tasks.append({
                "name": f.name,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "preview": f.read_text(encoding="utf-8")[:300],
            })
    return tasks


def collect_pending_items() -> list[str]:
    """List files currently waiting in /Pending_Approval."""
    if not PENDING_DIR.exists():
        return []
    return [f.name for f in PENDING_DIR.glob("*.md")]


def collect_needs_action_items() -> list[str]:
    """List files currently in /Needs_Action (backlog)."""
    if not NEEDS_ACTION_DIR.exists():
        return []
    return [f.name for f in NEEDS_ACTION_DIR.glob("*.md")]


def vault_snapshot() -> dict:
    """Full vault health snapshot."""
    return {
        "inbox":            count_files(VAULT_ROOT / "Inbox"),
        "needs_action":     count_files(NEEDS_ACTION_DIR),
        "pending_approval": count_files(PENDING_DIR),
        "approved":         count_files(APPROVED_DIR),
        "done":             count_files(DONE_DIR),
        "plans":            count_files(PLANS_DIR),
        "briefings":        count_files(BRIEFINGS_DIR),
    }


def get_odoo_accounting_summary() -> dict:
    """Fetch accounting summary from Odoo via JSON-RPC (Gold Tier)."""
    try:
        from odoo_mcp_server import OdooClient
        client = OdooClient()
        return client.get_account_balance_summary()
    except Exception as e:
        logger.warning(f"Odoo accounting unavailable: {e}")
        return {"error": str(e)}


# ── Claude Summary ─────────────────────────────────────────────────────────────

def call_claude(prompt: str) -> str:
    """Call the Claude CLI and return its text output."""
    import shutil
    import os

    # Find claude — check direct name then common npm location
    claude_cmd = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_cmd:
        npm_path = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
        if npm_path.exists():
            claude_cmd = str(npm_path)

    if not claude_cmd:
        logger.error("Claude CLI not found on PATH")
        return ""

    try:
        result = subprocess.run(
            [claude_cmd, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(VAULT_ROOT),
            shell=False,
        )
        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr[:200]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return ""
    except FileNotFoundError:
        logger.error("Claude CLI not found on PATH")
        return ""


def generate_ai_summary(done_tasks: list[dict], pending_items: list[str],
                         backlog: list[str], snapshot: dict) -> str:
    """Ask Claude to write a concise executive summary."""
    done_block = "\n".join(
        f"- {t['name']} (completed {t['modified']})" for t in done_tasks
    ) or "None"

    pending_block = "\n".join(f"- {p}" for p in pending_items) or "None"
    backlog_block  = "\n".join(f"- {b}" for b in backlog)  or "None"

    prompt = f"""You are the AI Employee generating a Monday CEO briefing.

## Vault data from the past 7 days:

### Completed tasks ({len(done_tasks)}):
{done_block}

### Currently pending human approval ({len(pending_items)}):
{pending_block}

### Current backlog in Needs_Action ({len(backlog)}):
{backlog_block}

### Vault health:
{json.dumps(snapshot, indent=2)}

Write a crisp, professional CEO briefing with these sections:
1. **Weekly Highlights** — what was accomplished (2-4 bullets)
2. **Bottlenecks / Blockers** — anything stuck or delayed
3. **Action Required** — items needing CEO decision this week
4. **System Health** — vault status in one sentence
5. **Recommended Focus** — top 1-2 priorities for the week

Keep it under 300 words. Be direct and actionable."""

    logger.info("Generating AI executive summary via Claude...")
    summary = call_claude(prompt)
    if not summary:
        summary = "_AI summary unavailable — Claude CLI not reachable. Review raw data above._"
    return summary


# ── Briefing Builder ───────────────────────────────────────────────────────────

def _format_accounting(data: dict) -> str:
    """Format Odoo accounting data for the briefing."""
    if "error" in data:
        return f"_Odoo unavailable: {data['error']}_"
    return (
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Total Receivable | ${data.get('total_receivable', 0):,.2f} |\n"
        f"| Total Payable | ${data.get('total_payable', 0):,.2f} |\n"
        f"| Net Position | ${data.get('net_position', 0):,.2f} |\n"
        f"| Open Invoices | {data.get('open_invoices', 0)} |\n"
        f"| Chart of Accounts | {data.get('total_accounts', 0)} accounts |"
    )


def build_briefing() -> Path:
    """Assemble the full CEO briefing and write it to /Briefings."""
    now        = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end   = now.strftime("%Y-%m-%d")
    monday     = (now + timedelta(days=(7 - now.weekday()) % 7 or 7)).strftime("%Y-%m-%d")

    logger.info("Collecting vault data...")
    done_tasks    = collect_done_files_this_week()
    pending_items = collect_pending_items()
    backlog       = collect_needs_action_items()
    snapshot      = vault_snapshot()
    logs          = read_task_logs_this_week()

    accounting = get_odoo_accounting_summary()
    ai_summary = generate_ai_summary(done_tasks, pending_items, backlog, snapshot)

    # ── Format briefing ────────────────────────────────────────────────────────
    done_section = ""
    for t in done_tasks:
        done_section += f"- **{t['name']}** _(completed {t['modified']})_\n"
    if not done_section:
        done_section = "- No tasks completed this week\n"

    pending_section = ""
    for p in pending_items:
        pending_section += f"- [ ] `{p}` — awaiting CEO approval\n"
    if not pending_section:
        pending_section = "- No items pending approval\n"

    backlog_section = ""
    for b in backlog:
        backlog_section += f"- `{b}`\n"
    if not backlog_section:
        backlog_section = "- Backlog clear\n"

    log_section = ""
    for entry in logs[:3]:  # Last 3 days of logs
        log_section += f"\n### {entry['date']}\n```\n{entry['content'][:400]}\n```\n"
    if not log_section:
        log_section = "_No task logs found for this week._"

    briefing = f"""# CEO Briefing — Week of {week_end}
> Auto-generated by AI Employee | For: Monday {monday}
> Coverage: {week_start} → {week_end}

---

## Executive Summary (AI-Generated)

{ai_summary}

---

## Completed This Week ({len(done_tasks)} tasks)

{done_section}
---

## Pending Your Approval ({len(pending_items)} items)

{pending_section}
---

## Current Backlog ({len(backlog)} items)

{backlog_section}
---

## Vault Health Snapshot

| Folder | Files |
|--------|-------|
| Inbox | {snapshot['inbox']} |
| Needs Action | {snapshot['needs_action']} |
| Pending Approval | {snapshot['pending_approval']} |
| Approved | {snapshot['approved']} |
| Done | {snapshot['done']} |
| Plans | {snapshot['plans']} |
| Briefings | {snapshot['briefings']} |

---

## Accounting Summary (Odoo)

{_format_accounting(accounting)}

---

## Recent Audit Logs (Last 3 Days)

{log_section}

---

_Generated at {now.strftime('%Y-%m-%d %H:%M:%S')} by ceo_briefing.py (Gold Tier)_
"""

    # ── Save to /Briefings ─────────────────────────────────────────────────────
    filename = f"CEO_Briefing_{week_end}.md"
    output_path = BRIEFINGS_DIR / filename

    # Avoid overwriting — append timestamp if collision
    if output_path.exists():
        output_path = BRIEFINGS_DIR / f"CEO_Briefing_{now.strftime('%Y%m%d_%H%M%S')}.md"

    output_path.write_text(briefing, encoding="utf-8")
    logger.info(f"CEO Briefing saved: {output_path}")
    return output_path


# ── Scheduled Mode ─────────────────────────────────────────────────────────────

def run_scheduled():
    """Loop and run every Sunday at 22:00."""
    import schedule as sched

    def job():
        logger.info("Sunday 22:00 — generating CEO briefing...")
        try:
            path = build_briefing()
            logger.info(f"Briefing complete: {path.name}")
        except Exception as e:
            logger.error(f"Briefing generation failed: {e}")

    sched.every().sunday.at("22:00").do(job)
    logger.info("CEO Briefing scheduler running — fires every Sunday at 22:00")

    while True:
        sched.run_pending()
        time.sleep(60)


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CEO Briefing Generator (Gold Tier)")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on Sunday 22:00 schedule instead of once",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        logger.info("Running CEO briefing generation now...")
        try:
            path = build_briefing()
            print(f"\nCEO Briefing generated: {path}")
        except Exception as e:
            logger.error(f"Failed: {e}")
            raise


if __name__ == "__main__":
    main()
