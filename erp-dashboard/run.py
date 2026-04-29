"""
ERP Dashboard Launcher
Starts Flask API (port 5001) + Vite dev server (port 5173)
Usage: python run.py
"""

import subprocess
import sys
import os
import signal
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

processes = []


def cleanup(sig=None, frame=None):
    print("\n[Launcher] Shutting down...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def main():
    print("=" * 60)
    print("  ERP Dashboard - Odoo 19 Live Data")
    print("=" * 60)
    print()

    # Start Flask API
    print("[1/2] Starting Flask API on http://localhost:5001 ...")
    flask_proc = subprocess.Popen(
        [sys.executable, "odoo_api.py"],
        cwd=BACKEND_DIR,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
    )
    processes.append(flask_proc)
    time.sleep(2)

    # Start Vite dev server
    print("[2/2] Starting Vite on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    vite_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
    )
    processes.append(vite_proc)

    print()
    print("=" * 60)
    print("  Dashboard: http://localhost:5173")
    print("  API:       http://localhost:5001/api/health")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if flask_proc.poll() is not None:
                print("[!] Flask API stopped unexpectedly")
                break
            if vite_proc.poll() is not None:
                print("[!] Vite dev server stopped unexpectedly")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
