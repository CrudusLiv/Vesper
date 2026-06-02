import pytest
from fastapi import HTTPException

from app.deps import require_auth


def test_correct_token_passes():
    # Should not raise.
    require_auth(authorization="Bearer test-secret")


def test_missing_token_rejected():
    with pytest.raises(HTTPException) as exc:
        require_auth(authorization=None)
    assert exc.value.status_code == 401


def test_wrong_token_rejected():
    with pytest.raises(HTTPException) as exc:
        require_auth(authorization="Bearer nope")
    assert exc.value.status_code == 401


def test_unset_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("API_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_auth(authorization="Bearer ")
    assert exc.value.status_code == 401
