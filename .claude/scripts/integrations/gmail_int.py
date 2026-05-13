"""Gmail integration -- read-only.

Top tasks: pull unread, read recent thread, extract structured deadline info."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from google_auth import get_credentials  # noqa: E402


def _service():
    creds = get_credentials()
    if not creds:
        return None
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("google-api-python-client missing", file=sys.stderr)
        return None
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_body(payload: dict) -> str:
    """Walk MIME parts and pull the first text/plain body."""
    if not payload:
        return ""
    if payload.get("mimeType", "").startswith("text/plain"):
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        text = _decode_body(part)
        if text:
            return text
    return ""


def _summarise(svc, msg_id: str) -> dict:
    msg = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = _decode_body(msg.get("payload", {}))
    return {
        "id": msg_id,
        "thread_id": msg.get("threadId"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body[:4000],
    }


def list_unread(max_results: int = 25) -> list[dict]:
    svc = _service()
    if not svc:
        return []
    resp = svc.users().messages().list(userId="me", q="is:unread", maxResults=max_results).execute()
    return [_summarise(svc, m["id"]) for m in resp.get("messages", [])]


def list_recent(days: int = 7, max_results: int = 25) -> list[dict]:
    svc = _service()
    if not svc:
        return []
    resp = svc.users().messages().list(userId="me", q=f"newer_than:{days}d", maxResults=max_results).execute()
    return [_summarise(svc, m["id"]) for m in resp.get("messages", [])]


def get_thread(thread_id: str) -> dict:
    svc = _service()
    if not svc:
        return {"error": "no service"}
    thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    return {
        "id": thread["id"],
        "messages": [_summarise(svc, m["id"]) for m in thread.get("messages", [])],
    }


def handle_query(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="query.py gmail")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    p_un = sub.add_parser("unread")
    p_un.add_argument("--max", type=int, default=25)
    p_rc = sub.add_parser("recent")
    p_rc.add_argument("--days", type=int, default=7)
    p_rc.add_argument("--max", type=int, default=25)
    p_th = sub.add_parser("thread")
    p_th.add_argument("thread_id")
    args = parser.parse_args(argv)
    json_out = args.json

    if args.subcommand == "unread":
        rows = list_unread(args.max)
    elif args.subcommand == "recent":
        rows = list_recent(args.days, args.max)
    else:
        rows = [get_thread(args.thread_id)]

    if json_out:
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
    else:
        for r in rows:
            if "error" in r:
                print(f"!! {r['error']}")
                continue
            print(f"{r.get('date', '')}  <{r.get('from', '')}>")
            print(f"  Subject: {r.get('subject', '')}")
            print(f"  {r.get('snippet', '')[:200]}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(handle_query(sys.argv[1:]))
