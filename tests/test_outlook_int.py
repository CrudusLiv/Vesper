"""Smoke tests for outlook_int — MSAL is mocked, no network calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "integrations"))

import integrations._env  # noqa: F401


def _make_msal_mock():
    msal_mock = MagicMock()
    cache_mock = MagicMock()
    cache_mock.has_state_changed = False
    cache_mock.serialize.return_value = "{}"
    msal_mock.SerializableTokenCache.return_value = cache_mock
    app_mock = MagicMock()
    app_mock.get_accounts.return_value = [{"username": "test@uni.edu"}]
    app_mock.acquire_token_silent.return_value = {"access_token": "fake_token"}
    app_mock.token_cache = cache_mock
    msal_mock.PublicClientApplication.return_value = app_mock
    return msal_mock, app_mock


def test_is_configured_false_without_env(monkeypatch):
    monkeypatch.delenv("OUTLOOK_TENANT_ID", raising=False)
    monkeypatch.delenv("OUTLOOK_CLIENT_ID", raising=False)
    import importlib
    import integrations.outlook_int as oi
    importlib.reload(oi)
    assert oi._is_configured() is False


def test_is_configured_false_without_msal(monkeypatch):
    monkeypatch.setenv("OUTLOOK_TENANT_ID", "t")
    monkeypatch.setenv("OUTLOOK_CLIENT_ID", "c")
    import importlib
    import integrations.outlook_int as oi
    # msal is None at module level when not installed
    original_msal = oi.msal
    try:
        oi.msal = None
        assert oi._is_configured() is False
    finally:
        oi.msal = original_msal


def test_list_unread_returns_list(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTLOOK_TENANT_ID", "fake-tenant")
    monkeypatch.setenv("OUTLOOK_CLIENT_ID", "fake-client")
    msal_mock, _ = _make_msal_mock()

    import importlib
    import integrations.outlook_int as oi
    importlib.reload(oi)
    oi.msal = msal_mock
    monkeypatch.setattr(oi, "TOKEN_FILE", tmp_path / "token.json")

    fake_response = json.dumps({"value": [
        {"id": "1", "subject": "Test", "from": {"emailAddress": {"address": "a@b.com"}},
         "receivedDateTime": "2026-06-13T10:00:00Z", "bodyPreview": "hello"},
    ]}).encode()

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value.read.return_value = fake_response
    mock_cm.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock_cm):
        items = oi.list_unread(max_results=5)

    assert len(items) == 1
    assert items[0]["subject"] == "Test"
    assert items[0]["from"] == "a@b.com"
    assert items[0]["received"] == "2026-06-13"


def test_handle_query_unconfigured(monkeypatch, capsys):
    monkeypatch.delenv("OUTLOOK_TENANT_ID", raising=False)
    monkeypatch.delenv("OUTLOOK_CLIENT_ID", raising=False)
    import importlib
    import integrations.outlook_int as oi
    importlib.reload(oi)
    oi.msal = None  # explicitly unconfigured
    rc = oi.handle_query(["mail"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "not configured" in captured.err.lower()
