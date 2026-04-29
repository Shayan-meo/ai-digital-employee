"""
Health Monitor — Platinum Tier
Checks all AI Employee processes every 5 minutes.
Restarts crashed processes, alerts via Obsidian file + optional email.

Features:
- Monitors: cloud_watcher, scheduler, vault_sync, odoo, health endpoints
- Auto-restart via PM2 or direct subprocess
- Writes health status to /Logs/health_status.json
- Creates alert files in /Needs_Action on critical failures
- Tracks uptime and failure history

Usage:
    python health_monitor.py              # run once
    python health_monitor.py --watch      # continuous (every 5 min)
    python health_monitor.py --status     # show current health
"""

import argparse
import json
import logging
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.resolve()
LOGS_DIR = VAULT_ROOT / "Logs"
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
LOGS_DIR.mkdir(exist_ok=True)

HEALTH_FILE = LOGS_DIR / "health_status.json"
CHECK_INTERVAL = 300  # 5 minutes

logger = logging.getLogger("health_monitor")
log_file = LOGS_DIR / f"health_monitor_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


# ── Service definitions ───────────────────────────────────────────────────────
SERVICES = [
    {
        "name": "cloud_watcher",
        "check_type": "process",
        "process_name": "cloud_watcher.py",
        "restart_cmd": "pm2 restart cloud_watcher",
        "critical": True,
    },
    {
        "name": "scheduler",
        "check_type": "process",
        "process_name": "scheduler.py",
        "restart_cmd": "pm2 restart scheduler",
        "critical": True,
    },
    {
        "name": "vault_sync",
        "check_type": "process",
        "process_name": "vault_sync.py",
        "restart_cmd": "pm2 restart vault_sync",
        "critical": False,
    },
    {
        "name": "odoo",
        "check_type": "http",
        "url": "http://localhost:8069/web/health",
        "fallback_cmd": "docker restart odoo19",
        "critical": True,
    },
    {
        "name": "health_endpoint",
        "check_type": "http",
        "url": "http://localhost:8765/health",
        "fallback_cmd": None,
        "critical": False,
    },
]


# ── Health checks ─────────────────────────────────────────────────────────────
def check_process_running(process_name: str) -> bool:
    """Check if a Python process is running."""
    try:
        # Try PM2 first
        result = subprocess.run(
            ["pm2", "jlist"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            pm2_list = json.loads(result.stdout)
            for proc in pm2_list:
                if proc.get("name") == process_name.replace(".py", ""):
                    return proc.get("pm2_env", {}).get("status") == "online"
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass

    # Fallback: check OS process list
    try:
        if shutil.which("tasklist"):
            # Windows
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=10
            )
            return process_name in result.stdout
        else:
            # Linux
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_http_health(url: str) -> bool:
    """Check if an HTTP endpoint responds."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status < 500
    except Exception:
        return False


def check_docker_container(container_name: str) -> bool:
    """Check if a Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def restart_service(service: dict) -> bool:
    """Attempt to restart a failed service."""
    cmd = service.get("restart_cmd") or service.get("fallback_cmd")
    if not cmd:
        return False

    logger.info(f"Restarting {service['name']}: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        success = result.returncode == 0
        if success:
            logger.info(f"{service['name']} restarted successfully.")
        else:
            logger.error(f"{service['name']} restart failed: {result.stderr}")
        return success
    except subprocess.TimeoutExpired:
        logger.error(f"{service['name']} restart timed out.")
        return False


# ── Main health check ─────────────────────────────────────────────────────────
def run_health_check() -> dict:
    """Run health checks on all services. Returns status dict."""
    timestamp = datetime.now().isoformat()
    results = {
        "timestamp": timestamp,
        "overall": "healthy",
        "services": {},
        "alerts": [],
    }

    for svc in SERVICES:
        name = svc["name"]
        check_type = svc["check_type"]
        healthy = False

        if check_type == "process":
            healthy = check_process_running(svc["process_name"])
        elif check_type == "http":
            healthy = check_http_health(svc["url"])
        elif check_type == "docker":
            healthy = check_docker_container(svc.get("container_name", name))

        status = "healthy" if healthy else "down"
        restarted = False

        if not healthy:
            logger.warning(f"Service DOWN: {name}")
            restarted = restart_service(svc)

            if svc.get("critical") and not restarted:
                results["overall"] = "degraded"
                alert_msg = f"CRITICAL: {name} is DOWN and restart failed"
                results["alerts"].append(alert_msg)
                logger.error(alert_msg)

        results["services"][name] = {
            "status": status,
            "check_type": check_type,
            "critical": svc.get("critical", False),
            "restarted": restarted,
            "checked_at": timestamp,
        }

        if healthy:
            logger.info(f"Service OK: {name}")

    # Save health status
    HEALTH_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Create alert file if critical failures
    if results["alerts"]:
        create_alert_file(results["alerts"])

    # Audit log
    try:
        from audit_logger import audit_log
        svc_summary = {k: v["status"] for k, v in results["services"].items()}
        audit_log("health_check", "health_monitor", svc_summary,
                  results["overall"], f"Health: {results['overall']}")
    except ImportError:
        pass

    return results


def create_alert_file(alerts: list):
    """Create an alert task in /Needs_Action for human attention."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    alert_file = NEEDS_ACTION / f"health_alert_{ts}.md"
    content = f"""# Health Alert — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Status: CRITICAL

The following services have failed and could not be auto-restarted:

"""
    for alert in alerts:
        content += f"- {alert}\n"

    content += f"""
## Action Required
Please check the affected services and restart manually if needed.

## Health Log
See: `Logs/health_monitor_{datetime.now().strftime('%Y-%m-%d')}.log`
See: `Logs/health_status.json`
"""
    alert_file.write_text(content, encoding="utf-8")
    logger.info(f"Alert file created: {alert_file.name}")


def show_status():
    """Display current health status."""
    if not HEALTH_FILE.exists():
        print("No health data yet. Run: python health_monitor.py")
        return

    data = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    print(f"\nHealth Status — {data['timestamp']}")
    print(f"Overall: {data['overall'].upper()}\n")
    print(f"{'Service':<20} {'Status':<10} {'Critical':<10} {'Restarted':<10}")
    print("-" * 50)
    for name, info in data.get("services", {}).items():
        print(f"{name:<20} {info['status']:<10} {'YES' if info['critical'] else 'no':<10} "
              f"{'YES' if info.get('restarted') else '-':<10}")

    if data.get("alerts"):
        print(f"\nAlerts:")
        for a in data["alerts"]:
            print(f"  ! {a}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Health Monitor — Platinum Tier")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring (every 5 min)")
    parser.add_argument("--status", action="store_true", help="Show current health status")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.watch:
        logger.info(f"Health monitor started — checking every {CHECK_INTERVAL}s")
        while True:
            try:
                results = run_health_check()
                logger.info(f"Overall: {results['overall']} | "
                           f"Services: {len(results['services'])}")
            except Exception as e:
                logger.error(f"Health check error: {e}")
            time.sleep(CHECK_INTERVAL)
    else:
        results = run_health_check()
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
