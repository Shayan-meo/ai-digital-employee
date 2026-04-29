"""
Ralph Wiggum Stop Hook — Gold Tier
Keeps Claude Code iterating until the current task is fully complete.

This hook intercepts Claude's stop event and checks if there are still
tasks in /Needs_Action. If so, it re-injects a prompt to continue working.

Completion detection:
  - File movement: task moved from /Needs_Action → /Done
  - Promise-based: Claude outputs TASK_COMPLETE marker
  - Empty queue: /Needs_Action folder is empty

Usage in .claude/settings.local.json:
  "hooks": {
    "Stop": [{ "type": "command", "command": "python ralph_wiggum_hook.py" }]
  }
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
DONE_DIR = VAULT_ROOT / "Done"
LOG_DIR = VAULT_ROOT / "Logs"
LOG_DIR.mkdir(exist_ok=True)

STATE_FILE = VAULT_ROOT / ".ralph_wiggum_state.json"
MAX_ITERATIONS = 10


def log(msg: str):
    """Log to file."""
    log_path = LOG_DIR / f"ralph_wiggum_{datetime.now():%Y-%m-%d}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp}  {msg}\n")


def get_state() -> dict:
    """Read current iteration state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"iteration": 0, "task": None, "started": None}


def save_state(state: dict):
    """Save iteration state."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_pending_tasks() -> list[str]:
    """Get list of .md files in /Needs_Action."""
    if not NEEDS_ACTION.exists():
        return []
    return [f.name for f in NEEDS_ACTION.glob("*.md")]


def main():
    """
    Stop hook entry point.
    Exit code 0 = allow stop (task complete)
    Exit code 1 = block stop (keep working) — prints new prompt to stdout
    """
    state = get_state()
    pending = get_pending_tasks()

    # Read stdin for Claude's last output (stop hook receives transcript)
    stdin_data = ""
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
        except Exception:
            pass

    # Check if Claude declared completion
    if "TASK_COMPLETE" in stdin_data:
        log(f"Task complete (promise marker found). Iterations: {state['iteration']}")
        save_state({"iteration": 0, "task": None, "started": None})
        sys.exit(0)

    # Check if max iterations reached
    if state["iteration"] >= MAX_ITERATIONS:
        log(f"Max iterations ({MAX_ITERATIONS}) reached. Allowing stop.")
        save_state({"iteration": 0, "task": None, "started": None})
        sys.exit(0)

    # Check if there are pending tasks
    if not pending:
        log("No pending tasks in /Needs_Action. Allowing stop.")
        save_state({"iteration": 0, "task": None, "started": None})
        sys.exit(0)

    # Still have work to do — block the stop and re-inject prompt
    state["iteration"] += 1
    if not state["started"]:
        state["started"] = datetime.now().isoformat()
    state["task"] = pending[0]
    save_state(state)

    log(f"Iteration {state['iteration']}/{MAX_ITERATIONS}. Pending: {pending}. Re-injecting prompt.")

    # Print the re-injection prompt to stdout
    prompt = (
        f"You still have {len(pending)} task(s) in /Needs_Action: {', '.join(pending[:3])}. "
        f"Continue processing. Read the next task file, create a plan, execute it, "
        f"and move the file to /Done when complete. "
        f"When ALL tasks are done, output TASK_COMPLETE."
    )
    print(prompt)
    sys.exit(1)


if __name__ == "__main__":
    main()
