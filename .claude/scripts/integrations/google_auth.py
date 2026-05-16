"""Shared Google OAuth2 -- used by Gmail and Calendar.

First run opens a browser for consent; subsequent runs use the cached
refresh token at .claude/data/google_token.json.

Setup:
1. Google Cloud Console -> enable Gmail API + Calendar API.
2. Credentials -> OAuth client ID -> Desktop app.
3. Download the JSON, save as .claude/data/google_credentials.json.

Both Gmail and Calendar scopes are requested up front so the user only
consents once. Read-only -- no compose, no event create/delete."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
CREDS_PATH = PROJECT_DIR / ".claude" / "data" / "google_credentials.json"
TOKEN_PATH = PROJECT_DIR / ".claude" / "data" / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_credentials():
    """Returns google.oauth2.credentials.Credentials, running OAuth on first use."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Google libs missing: py -m pip install -r .claude/requirements.txt", file=sys.stderr)
        return None

    if not CREDS_PATH.exists():
        print(
            f"OAuth client secret not found at {CREDS_PATH}.\n"
            "Download it from Google Cloud Console -> Credentials -> OAuth Desktop client.",
            file=sys.stderr,
        )
        return None

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds
