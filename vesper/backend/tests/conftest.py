import os

import pytest


@pytest.fixture(autouse=True)
def _api_secret(monkeypatch):
    """Every test runs with a known API_SECRET so auth is deterministic."""
    monkeypatch.setenv("API_SECRET", "test-secret")
