"""
WhatsApp send helper — called by the ERP Dashboard API.
Usage: python wa_send_helper.py <phone> <message>
Prints SENT_OK, SEND_FAILED, or LOGIN_FAILED to stdout.

This script handles the slow WhatsApp Web loading by using a longer
wait_login timeout. WhatsApp Web can take 2-3 minutes to fully load
and restore a saved session on slower connections.
"""

import sys
import os
import time

# Ensure the vault root is importable
vault_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, vault_root)

from whatsapp_playwright import WhatsApp


class DashboardWhatsApp(WhatsApp):
    """Extended WhatsApp class with longer timeouts for dashboard use."""

    def wait_login_extended(self, max_seconds=300):
        """Wait for login with long timeout — WhatsApp loads slowly under OBS/heavy load."""
        self.page.goto(
            "https://web.whatsapp.com",
            timeout=300_000,
            wait_until="domcontentloaded",
        )
        print(f"Page loaded, waiting up to {max_seconds}s for session restore...", flush=True)
        rounds = max_seconds // 5
        for i in range(rounds):
            self.page.wait_for_timeout(5000)
            if self._is_logged_in():
                print("Logged in from saved profile.", flush=True)
                return True
            elapsed = (i + 1) * 5
            if elapsed % 15 == 0:
                print(f"Still loading... {elapsed}/{max_seconds}s", flush=True)
        print(f"Login not detected within {max_seconds}s.", flush=True)
        return False


def main():
    if len(sys.argv) < 3:
        print("USAGE: python wa_send_helper.py <phone> <message>")
        sys.exit(1)

    phone = sys.argv[1]
    message = sys.argv[2]

    wa = DashboardWhatsApp()
    try:
        wa.open()
        # Give WhatsApp Web up to 5 minutes to fully load (handles OBS/heavy CPU)
        if not wa.wait_login_extended(max_seconds=300):
            print("LOGIN_FAILED")
            sys.exit(1)

        print("LOGIN_OK", flush=True)
        result = wa.send(phone, message)
        if result:
            print("SENT_OK")
        else:
            print("SEND_FAILED")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        wa.close()


if __name__ == "__main__":
    main()
