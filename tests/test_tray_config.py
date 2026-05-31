from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    (tmp_path / ".claude" / "data").mkdir(parents=True)
    import importlib, tray.config
    importlib.reload(tray.config)


def test_load_returns_defaults_when_missing():
    from tray import config
    d = config.load()
    assert d["auto_start_bot"] is True
    assert d["active_hours_start"] == "09:00"
    assert d["active_hours_end"] == "22:00"
    assert d["features"]["inbox"] is True
    assert d["features"]["thread_chat"] is False


def test_load_returns_defaults_on_corrupt_json(tmp_path):
    (tmp_path / ".claude" / "data" / "tray_settings.json").write_text("not json", encoding="utf-8")
    from tray import config
    d = config.load()
    assert d["auto_start_bot"] is True


def test_save_and_load_roundtrip(tmp_path):
    from tray import config
    d = config.load()
    d["auto_start_bot"] = False
    d["features"]["inbox"] = False
    config.save(d)
    loaded = config.load()
    assert loaded["auto_start_bot"] is False
    assert loaded["features"]["inbox"] is False


def test_load_merges_missing_feature_keys(tmp_path):
    path = tmp_path / ".claude" / "data" / "tray_settings.json"
    path.write_text(json.dumps({"features": {"inbox": False}}), encoding="utf-8")
    from tray import config
    d = config.load()
    assert d["features"]["inbox"] is False
    assert d["features"]["gcal_sync"] is True   # default preserved for missing key


def test_heartbeat_interval_minutes_default():
    from tray import config
    d = config.load()
    assert d["heartbeat_interval_minutes"] == 30


def test_reflect_not_in_features():
    from tray import config
    d = config.load()
    assert "reflect" not in d["features"]
