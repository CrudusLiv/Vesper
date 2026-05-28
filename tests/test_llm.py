"""Tests for llm.py — config loading, Ollama backend, dispatcher."""
from __future__ import annotations

import importlib
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / ".claude" / "scripts"))


def _reload():
    import heartbeat.llm as m
    importlib.reload(m)
    m._config_cache = None
    return m


# --- Config loader ---

def test_config_missing_file_returns_defaults(tmp_path, monkeypatch):
    m = _reload()
    monkeypatch.setattr(m, "_CONFIG_PATH", tmp_path / "nonexistent.json")
    m._config_cache = None
    cfg = m._load_config()
    assert cfg["default_backend"] == "claude"
    assert cfg["routing"] == {}


def test_config_malformed_json_returns_defaults(tmp_path, monkeypatch):
    bad = tmp_path / "llm-config.json"
    bad.write_text("not json")
    m = _reload()
    monkeypatch.setattr(m, "_CONFIG_PATH", bad)
    m._config_cache = None
    cfg = m._load_config()
    assert cfg["default_backend"] == "claude"


def test_config_valid_json_merged_with_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "llm-config.json"
    cfg_file.write_text(json.dumps({
        "default_backend": "ollama",
        "routing": {"inbox_classify": {"backend": "ollama", "model": "qwen2.5:7b"}},
    }))
    m = _reload()
    monkeypatch.setattr(m, "_CONFIG_PATH", cfg_file)
    m._config_cache = None
    cfg = m._load_config()
    assert cfg["default_backend"] == "ollama"
    assert cfg["routing"]["inbox_classify"]["backend"] == "ollama"
    assert "claude" in cfg["backends"]  # preserved from defaults


def test_config_cached_after_first_load(tmp_path, monkeypatch):
    cfg_file = tmp_path / "llm-config.json"
    cfg_file.write_text(json.dumps({"default_backend": "ollama"}))
    m = _reload()
    monkeypatch.setattr(m, "_CONFIG_PATH", cfg_file)
    m._config_cache = None
    first = m._load_config()
    cfg_file.write_text(json.dumps({"default_backend": "claude"}))
    second = m._load_config()
    assert first is second  # cache hit — file change ignored


# --- Ollama backend ---

def _make_mock_resp(content: str):
    body = json.dumps({"message": {"content": content}}).encode()
    mock = MagicMock()
    mock.read.return_value = body
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_ollama_returns_content_when_up():
    m = _reload()
    m._config_cache = {
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {},
        "default_backend": "claude",
        "fallback_backend": None,
    }
    with patch("urllib.request.urlopen", return_value=_make_mock_resp("hello from ollama")):
        result = m._call_ollama("say hello", model="qwen2.5:7b")
    assert result == "hello from ollama"


def test_ollama_includes_system_prompt_as_first_message():
    m = _reload()
    m._config_cache = {
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {},
        "default_backend": "claude",
        "fallback_backend": None,
    }
    captured: dict = {}

    def capture(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        return _make_mock_resp("ok")

    with patch("urllib.request.urlopen", side_effect=capture):
        m._call_ollama("user prompt", system_prompt="be brief", model="qwen2.5:7b")

    msgs = captured["body"]["messages"]
    assert msgs[0] == {"role": "system", "content": "be brief"}
    assert msgs[1] == {"role": "user", "content": "user prompt"}


def test_ollama_lazy_starts_server_on_first_connection_error():
    m = _reload()
    m._config_cache = {
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {},
        "default_backend": "claude",
        "fallback_backend": None,
    }
    call_count: dict = {"n": 0}

    def urlopen_side(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise urllib.error.URLError("connection refused")
        return _make_mock_resp("started")

    with patch("urllib.request.urlopen", side_effect=urlopen_side), \
         patch.object(m, "_start_ollama_server") as mock_start:
        result = m._call_ollama("prompt", model="qwen2.5:7b")

    mock_start.assert_called_once()
    assert result == "started"


def test_ollama_returns_empty_string_after_two_failures():
    m = _reload()
    m._config_cache = {
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {},
        "default_backend": "claude",
        "fallback_backend": None,
    }
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")), \
         patch.object(m, "_start_ollama_server"):
        result = m._call_ollama("prompt", model="qwen2.5:7b")
    assert result == ""


# --- Dispatcher ---

def test_force_backend_env_overrides_routing(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {},
        "routing": {"inbox_classify": {"backend": "ollama", "model": "qwen2.5:7b"}},
    }
    monkeypatch.setenv("LLM_FORCE_BACKEND", "claude")
    backend, model = m._resolve_backend("inbox_classify")
    assert backend == "claude"
    assert model is None


def test_task_in_routing_table_uses_configured_backend(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {},
        "routing": {"inbox_classify": {"backend": "ollama", "model": "qwen2.5:7b"}},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)
    backend, model = m._resolve_backend("inbox_classify")
    assert backend == "ollama"
    assert model == "qwen2.5:7b"


def test_unknown_task_uses_default_backend(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {},
        "routing": {},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)
    backend, model = m._resolve_backend("nonexistent_task")
    assert backend == "claude"
    assert model is None


def test_no_task_uses_default_backend(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {},
        "routing": {},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)
    backend, model = m._resolve_backend(None)
    assert backend == "claude"
    assert model is None


def test_call_routes_ollama_task_to_ollama(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {"inbox_classify": {"backend": "ollama", "model": "qwen2.5:7b"}},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)

    with patch.object(m, "_call_ollama", return_value="classified") as mock_ollama, \
         patch.object(m, "_call_claude") as mock_claude:
        result = m.call("classify this", task="inbox_classify")

    mock_ollama.assert_called_once()
    mock_claude.assert_not_called()
    assert result == "classified"


def test_call_falls_back_to_claude_on_ollama_failure(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "ollama",
        "fallback_backend": "claude",
        "backends": {"ollama": {"base_url": "http://localhost:11434", "default_model": "qwen2.5:7b"}},
        "routing": {},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)

    with patch.object(m, "_call_ollama", return_value=""), \
         patch.object(m, "_call_claude", return_value="fallback result") as mock_claude:
        result = m.call("prompt", task="any_task")

    mock_claude.assert_called_once()
    assert result == "fallback result"


def test_call_no_task_uses_claude_by_default(monkeypatch):
    m = _reload()
    m._config_cache = {
        "default_backend": "claude",
        "fallback_backend": None,
        "backends": {},
        "routing": {},
    }
    monkeypatch.delenv("LLM_FORCE_BACKEND", raising=False)

    with patch.object(m, "_call_claude", return_value="answer") as mock_claude:
        result = m.call("question")

    mock_claude.assert_called_once()
    assert result == "answer"
