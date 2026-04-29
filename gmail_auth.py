"""One-time OAuth flow to generate refresh_token for Gmail API."""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

VAULT = Path(__file__).parent.resolve()
CLIENT_SECRET = VAULT / "gmail_credentials" / "client_secret_417782053239-tvsstg4e785ema77vq6b3s53uokfn34k.apps.googleusercontent.com.json"
CREDS_OUT = VAULT / "gmail_credentials" / "credentials.json"

flow = InstalledAppFlow.from_client_secrets_file(
    str(CLIENT_SECRET),
    scopes=[
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ],
)
print("\nBrowser will open for Google sign-in...")
print("If it doesn't, check the URL printed below.\n")
creds = flow.run_local_server(port=8090, open_browser=True, timeout_seconds=300)

data = {
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "refresh_token": creds.refresh_token,
}
CREDS_OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("credentials.json saved with refresh_token!")
