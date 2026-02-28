"""
Gmail API access for the authenticated user.
Stores Google OAuth refresh tokens keyed by Auth0 user id (sub).
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail read-only scope
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

# Default path for storing refresh tokens (keyed by Auth0 sub)
DEFAULT_TOKEN_STORE_PATH = Path(os.getenv("GMAIL_TOKEN_STORE_PATH", ".gmail_tokens.json"))


def _load_token_store() -> dict[str, str]:
    """Load the token store from disk."""
    if not DEFAULT_TOKEN_STORE_PATH.exists():
        return {}
    try:
        with open(DEFAULT_TOKEN_STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_token_store(store: dict[str, str]) -> None:
    """Persist the token store to disk."""
    DEFAULT_TOKEN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_TOKEN_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


def get_refresh_token(auth0_sub: str) -> Optional[str]:
    """Return the stored Google refresh token for this Auth0 user, if any."""
    return _load_token_store().get(auth0_sub)


def store_refresh_token(auth0_sub: str, refresh_token: str) -> None:
    """Store a Google refresh token for the given Auth0 user."""
    store = _load_token_store()
    store[auth0_sub] = refresh_token
    _save_token_store(store)


def get_gmail_credentials(auth0_sub: str) -> Optional[Credentials]:
    """Build Google credentials for Gmail API from stored refresh token."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    refresh_token = get_refresh_token(auth0_sub)
    if not refresh_token:
        return None
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[GMAIL_READONLY_SCOPE],
    )
    return creds


def list_recent_emails(auth0_sub: str, max_results: int = 10) -> list[dict[str, Any]]:
    """
    Fetch the most recent emails for the user identified by auth0_sub.
    Returns a list of dicts with id, threadId, snippet, subject, from, date.
    """
    creds = get_gmail_credentials(auth0_sub)
    if not creds:
        return []

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])
    except HttpError as e:
        if e.resp.status == 401:
            # Token expired or revoked
            return []
        raise

    out: list[dict[str, Any]] = []
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            msg = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
            payload = msg.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            out.append({
                "id": msg_id,
                "threadId": msg.get("threadId", ""),
                "snippet": msg.get("snippet", ""),
                "subject": headers.get("subject", "(No subject)"),
                "from": headers.get("from", ""),
                "date": headers.get("date", ""),
            })
        except HttpError:
            continue
    return out


def is_gmail_configured() -> bool:
    """Return True if Google OAuth client id/secret are set."""
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
