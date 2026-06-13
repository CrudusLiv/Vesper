"""Microsoft Outlook integration via Microsoft Graph API.

Auth: MSAL device-code flow (interactive on first run, token cached after).
Scopes: Mail.Read, Calendars.Read

Setup:
1. Register app in Azure Portal -> App registrations
2. Set Auth platform to "Mobile and desktop" with native redirect URI
3. Add delegated permissions: Mail.Read, Calendars.Read, User.Read
4. Add to .env:
     OUTLOOK_TENANT_ID=<Directory (tenant) ID>
     OUTLOOK_CLIENT_ID=<Application (client) ID>
5. pip install msal
6. First run: py query.py outlook auth  (device code flow)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import msal
except ImportError:
    msal = None  # type: ignore

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
TOKEN_FILE = PROJECT_DIR / ".claude" / "data" / "outlook_token.json"

SCOPES = ["Mail.Read", "Calendars.Read", "User.Read"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _is_configured() -> bool:
    return bool(
        os.environ.get("OUTLOOK_TENANT_ID")
        and os.environ.get("OUTLOOK_CLIENT_ID")
        and msal is not None
    )


def _get_app() -> "msal.PublicClientApplication":
    tenant_id = os.environ["OUTLOOK_TENANT_ID"]
    client_id = os.environ["OUTLOOK_CLIENT_ID"]
    cache = msal.SerializableTokenCache()
    if TOKEN_FILE.exists():
        cache.deserialize(TOKEN_FILE.read_text(encoding="utf-8"))
    return msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )


def _save_cache(app: "msal.PublicClientApplication") -> None:
    if app.token_cache.has_state_changed:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(app.token_cache.serialize(), encoding="utf-8")


def authenticate() -> str:
    """Run device-code flow and cache the token. Prints instructions to stdout."""
    if not _is_configured():
        raise RuntimeError("OUTLOOK_TENANT_ID and OUTLOOK_CLIENT_ID must be set in .env")
    app = _get_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Device flow init failed: {flow}")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")
    _save_cache(app)
    return result["access_token"]


def _get_token() -> str:
    app = _get_app()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(app)
            return result["access_token"]
    return authenticate()


def _graph_get(path: str) -> dict:
    token = _get_token()
    url = f"{GRAPH_BASE}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_unread(max_results: int = 25) -> list[dict]:
    """Return up to max_results unread messages from Inbox."""
    path = (
        f"/me/mailFolders/Inbox/messages"
        f"?$filter=isRead eq false"
        f"&$top={max_results}"
        f"&$select=id,subject,from,receivedDateTime,bodyPreview"
        f"&$orderby=receivedDateTime desc"
    )
    data = _graph_get(path)
    return [
        {
            "id": m["id"],
            "subject": m.get("subject") or "",
            "from": (m.get("from") or {}).get("emailAddress", {}).get("address", ""),
            "received": (m.get("receivedDateTime") or "")[:10],
            "snippet": (m.get("bodyPreview") or "")[:200],
        }
        for m in data.get("value", [])
    ]


def list_events(days: int = 14) -> list[dict]:
    """Return calendar events in the next N days."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = (
        f"/me/calendarView"
        f"?startDateTime={start_str}&endDateTime={end_str}"
        f"&$orderby=start/dateTime"
        f"&$select=subject,start,end,location,bodyPreview"
        f"&$top=50"
    )
    data = _graph_get(path)
    return [
        {
            "subject": e.get("subject") or "",
            "start": ((e.get("start") or {}).get("dateTime") or "")[:16].replace("T", " "),
            "end": ((e.get("end") or {}).get("dateTime") or "")[:16].replace("T", " "),
            "location": (e.get("location") or {}).get("displayName") or "",
            "snippet": (e.get("bodyPreview") or "")[:200],
        }
        for e in data.get("value", [])
    ]


def handle_query(argv: list[str]) -> int:
    """CLI handler for query.py dispatch.

    Subcommands:
        auth          -- run device-code flow (first time setup)
        mail [N]      -- list N unread emails (default 25)
        events [N]    -- list events in next N days (default 14)
    """
    if not _is_configured():
        print(
            "Outlook not configured.\n"
            "Set OUTLOOK_TENANT_ID and OUTLOOK_CLIENT_ID in .env, then run:\n"
            "  py query.py outlook auth",
            file=sys.stderr,
        )
        return 1

    use_json = "--json" in argv
    argv_clean = [a for a in argv if a != "--json"]
    cmd = argv_clean[0] if argv_clean else "mail"

    if cmd == "auth":
        try:
            authenticate()
            print("Authentication successful. Token cached.")
            return 0
        except RuntimeError as exc:
            print(f"Auth failed: {exc}", file=sys.stderr)
            return 1

    if cmd in ("mail", "unread"):
        n = int(argv_clean[1]) if len(argv_clean) > 1 and argv_clean[1].isdigit() else 25
        items = list_unread(max_results=n)
        if use_json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            if not items:
                print("No unread mail.")
            for m in items:
                print(f"[{m['received']}] {m['from']}: {m['subject']}")
                if m["snippet"]:
                    print(f"  {m['snippet'][:100]}")
        return 0

    if cmd in ("events", "calendar"):
        n = int(argv_clean[1]) if len(argv_clean) > 1 and argv_clean[1].isdigit() else 14
        items = list_events(days=n)
        if use_json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            if not items:
                print("No upcoming events.")
            for e in items:
                loc = f" @ {e['location']}" if e["location"] else ""
                print(f"[{e['start']}] {e['subject']}{loc}")
        return 0

    print(f"Unknown subcommand: {cmd}. Use: auth, mail [N], events [N]", file=sys.stderr)
    return 1
