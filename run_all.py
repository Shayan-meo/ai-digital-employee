"""
Run All - Orchestrator that starts all vault watchers simultaneously.
Ralph Wiggum Persistence Loop (Gold Tier): auto-restarts any watcher that crashes.

Usage:
    python run_all.py
    Ctrl+C to stop all watchers gracefully.

Persistence behaviour:
    - Each watcher is monitored in its own guardian thread
    - If a watcher exits unexpectedly it is restarted after RESTART_DELAY seconds
    - After MAX_RESTARTS consecutive crashes the watcher is marked as failed and
      an incident report is written to /Logs
    - A clean Ctrl+C (SIGINT/SIGTERM) stops everything without restarting
"""

import subprocess
import sys
import signal
import threading
import os
import time
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).parent.resolve()
LOG_DIR = VAULT_ROOT / "Logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log"

# ── Persistence settings ───────────────────────────────────────────────────────
RESTART_DELAY = 5      # seconds to wait before restarting a crashed watcher
MAX_RESTARTS  = 10     # max consecutive restarts before giving up

# ── Watchers to launch ─────────────────────────────────────────────────────────
WATCHERS = [
    {"name": "Filesystem", "script": "filesystem_watcher.py"},
    {"name": "Gmail",      "script": "gmail_watcher.py"},
    {"name": "Approval",   "script": "approval_watcher.py"},
    {"name": "LinkedIn",   "script": "linkedin_watcher.py"},
    {"name": "Scheduler",  "script": "scheduler.py"},
    {"name": "Dashboard",  "script": "dashboard_updater.py",  "args": ["--watch"]},
    {"name": "LinkedIn",      "script": "linkedin_playwright.py",  "args": ["--watch"]},
    {"name": "SocialMedia",   "script": "social_media_watcher.py",  "args": ["--watch"]},
    {"name": "WhatsApp",      "script": "whatsapp_watcher.py",      "args": ["--watch"]},
    {"name": "WhatsAppSend",  "script": "whatsapp_playwright.py",   "args": ["--watch"]},
    {"name": "FacebookSend",  "script": "facebook_playwright.py",   "args": ["--watch"]},
]

# Shared shutdown flag — set to True on Ctrl+C to stop all guardian threads
_shutdown = threading.Event()

# Registry: name -> {"proc": Popen, "restarts": int, "failed": bool}
registry: dict[str, dict] = {}
registry_lock = threading.Lock()


# ── Logging ────────────────────────────────────────────────────────────────────

def log(msg: str):
    """Print timestamped message to terminal and daily log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp}  {msg}"
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def write_incident_report(name: str, script: str, restarts: int, exit_code: int):
    """Write a /Logs incident report when a watcher exceeds MAX_RESTARTS."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = LOG_DIR / f"incident_{name.lower()}_{ts}.md"
    content = f"""# Incident Report — {name} Watcher

- **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Script:** {script}
- **Consecutive restarts:** {restarts}
- **Last exit code:** {exit_code}
- **Status:** FAILED — exceeded MAX_RESTARTS ({MAX_RESTARTS})

## Action Required
The {name} watcher has crashed {restarts} times in a row.
Please check the watcher log for errors and restart manually:

    python {script}
"""
    report_path.write_text(content, encoding="utf-8")
    log(f"[INCIDENT] Report written: {report_path.name}")


# ── Process helpers ────────────────────────────────────────────────────────────

def stream_output(name: str, proc: subprocess.Popen):
    """Relay a watcher's stdout to the terminal with a label prefix."""
    try:
        for line in proc.stdout:
            text = line.rstrip()
            if text:
                sys.stdout.write(f"  [{name}] {text}\n")
                sys.stdout.flush()
    except (ValueError, OSError):
        pass


def launch(name: str, script: str, extra_args: list[str] | None = None) -> subprocess.Popen | None:
    """Start a single watcher process and wire up its output thread."""
    script_path = VAULT_ROOT / script
    if not script_path.exists():
        log(f"[ERROR] Script not found: {script_path}")
        return None

    python = sys.executable
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    cmd = [python, "-u", str(script_path)] + (extra_args or [])

    proc = subprocess.Popen(
        cmd,
        cwd=str(VAULT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    threading.Thread(
        target=stream_output,
        args=(name, proc),
        daemon=True,
    ).start()
    return proc


# ── Guardian thread ────────────────────────────────────────────────────────────

def guardian(name: str, script: str, extra_args: list[str] | None = None):
    """
    Ralph Wiggum persistence loop for one watcher.
    Keeps the watcher alive by restarting it after crashes.
    Stops cleanly when _shutdown is set.
    """
    consecutive = 0

    while not _shutdown.is_set():
        # ── Launch ─────────────────────────────────────────────────────────────
        proc = launch(name, script, extra_args)
        if proc is None:
            log(f"[{name}] Cannot start — script missing. Guardian exiting.")
            return

        with registry_lock:
            registry[name]["proc"] = proc

        log(f"[{name}] Started (PID {proc.pid}), restarts so far: {consecutive}")

        # ── Wait for process to finish ─────────────────────────────────────────
        while not _shutdown.is_set():
            try:
                proc.wait(timeout=2)
                break          # process exited
            except subprocess.TimeoutExpired:
                continue       # still running — loop back

        if _shutdown.is_set():
            # Clean shutdown — do not restart
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            log(f"[{name}] Stopped cleanly.")
            return

        # ── Unexpected exit ────────────────────────────────────────────────────
        exit_code = proc.returncode
        consecutive += 1

        with registry_lock:
            registry[name]["restarts"] = consecutive

        log(f"[{name}] Crashed (exit {exit_code}). Restart {consecutive}/{MAX_RESTARTS}.")

        if consecutive >= MAX_RESTARTS:
            with registry_lock:
                registry[name]["failed"] = True
            log(f"[{name}] FAILED — max restarts reached. Giving up.")
            write_incident_report(name, script, consecutive, exit_code)
            return

        # Back-off: wait before restarting (respects shutdown signal)
        _shutdown.wait(timeout=RESTART_DELAY)

    log(f"[{name}] Guardian exiting (shutdown requested).")


# ── Orchestrator ───────────────────────────────────────────────────────────────

def start_all():
    """Spawn a guardian thread for every watcher."""
    started = 0
    for w in WATCHERS:
        name, script = w["name"], w["script"]
        with registry_lock:
            registry[name] = {"proc": None, "restarts": 0, "failed": False}

        extra_args = w.get("args")
        t = threading.Thread(
            target=guardian,
            args=(name, script, extra_args),
            name=f"guardian-{name}",
            daemon=True,
        )
        t.start()
        started += 1
        log(f"Guardian started for: {name}")

    return started


def stop_all():
    """Signal all guardians to stop."""
    log("Shutdown requested — stopping all watchers...")
    _shutdown.set()


def status_line() -> str:
    """One-line summary of watcher health."""
    with registry_lock:
        parts = []
        for name, info in registry.items():
            proc = info["proc"]
            if info["failed"]:
                parts.append(f"{name}:FAILED")
            elif proc and proc.poll() is None:
                parts.append(f"{name}:OK")
            else:
                parts.append(f"{name}:restarting")
        return "  |  ".join(parts)


def signal_handler(sig, frame):
    log("Received shutdown signal.")
    stop_all()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60, flush=True)
    print("  AI EMPLOYEE VAULT - ORCHESTRATOR (Gold Tier)", flush=True)
    print("  Ralph Wiggum Persistence Loop active", flush=True)
    print(f"  Auto-restart: up to {MAX_RESTARTS}x per watcher", flush=True)
    print("=" * 60, flush=True)
    log(f"Vault root: {VAULT_ROOT}")

    count = start_all()
    if count == 0:
        log("No watchers started. Exiting.")
        sys.exit(1)

    print("=" * 60, flush=True)
    print(f"  {count} guardians running. Press Ctrl+C to stop.", flush=True)
    print("  Drop a file in /Inbox to see the full pipeline.", flush=True)
    print("=" * 60, flush=True)

    # ── Main monitor loop ──────────────────────────────────────────────────────
    STATUS_INTERVAL = 60   # print status every 60 s
    last_status = time.time()

    try:
        while not _shutdown.is_set():
            time.sleep(2)

            now = time.time()
            if now - last_status >= STATUS_INTERVAL:
                log(f"[STATUS] {status_line()}")
                last_status = now

            # Check if all guardians have given up
            with registry_lock:
                all_failed = all(info["failed"] for info in registry.values())
            if all_failed:
                log("[CRITICAL] All watchers have failed. Shutting down.")
                break

    except KeyboardInterrupt:
        pass
    finally:
        stop_all()
        # Give guardians a moment to terminate their child processes
        time.sleep(3)
        log("Orchestrator shutdown complete.")


if __name__ == "__main__":
    main()
