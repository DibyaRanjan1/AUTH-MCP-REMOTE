#!/usr/bin/env python3
"""
One-time script to obtain a Gmail refresh token using your own OAuth client.

The token from Google OAuth Playground won't work with your GOOGLE_CLIENT_ID;
you must use this script (or your own flow) so the refresh token is issued
for your client.

Requirements:
  - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
  - In Google Cloud Console: OAuth client type "Desktop app" (or "Web application"
    with redirect URI http://localhost:8080/), and Gmail API enabled

Run from project root:
  uv run python scripts/get_gmail_refresh_token.py

Then paste the printed refresh_token into link_my_gmail when prompted by the MCP client.
"""

import os
import sys
from pathlib import Path

# Load .env from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env", file=sys.stderr)
    sys.exit(1)

# Desktop app style; run_local_server() uses http://localhost:8080/ by default
# Add that exact URI in Google Cloud Console → APIs & Services → Credentials → your OAuth client
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8080/"
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

def main():
    print("\n  Add this EXACT redirect URI in Google Cloud Console:\n")
    print(f"    {REDIRECT_URI}\n")
    print("  Steps:")
    print("  1. Go to https://console.cloud.google.com/apis/credentials")
    print("  2. Open your OAuth 2.0 Client ID (Desktop or Web application)")
    print("  3. Under 'Authorized redirect URIs' click ADD URI, paste the URL above (copy exactly)")
    print("  4. Click SAVE")
    print("  5. Then press Enter here to open the browser.\n")
    input("  Press Enter to continue... ")

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    flow.run_local_server(port=8080, redirect_uri_trailing_slash=True)
    creds = flow.credentials
    if not creds.refresh_token:
        print("No refresh_token in response. Try revoking app access at https://myaccount.google.com/permissions and run again.", file=sys.stderr)
        sys.exit(1)
    print("\n--- Refresh token (use with link_my_gmail) ---")
    print(creds.refresh_token)
    print("---")

if __name__ == "__main__":
    main()
