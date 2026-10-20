"""voice/test_runner.py — parses pytest's summary line."""
from __future__ import annotations

from unittest.mock import MagicMock

from voice.test_runner import _parse_summary, describe_failure, run_test_suite


def test_parse_summary_all_passed():
    assert _parse_summary("== 42 passed in 3.21s ==") == {"passed": 42, "failed": 0, "errors": 0}


def test_parse_summary_with_failures():
    assert _parse_summary("== 2 failed, 40 passed in 3.21s ==") == {"passed": 40, "failed": 2, "errors": 0}


def test_parse_summary_with_errors():
    assert _parse_summary("== 1 failed, 2 passed, 3 errors in 1s ==") == {"passed": 2, "failed": 1, "errors": 3}


def test_parse_summary_no_tests_collected():
    assert _parse_summary("== no tests ran in 0.01s ==") == {"passed": 0, "failed": 0, "errors": 0}


def test_run_test_suite_ok_when_all_pass(monkeypatch, tmp_path):
    fake = MagicMock(returncode=0, stdout="== 5 passed in 1.0s ==\n", stderr="")
    monkeypatch.setattr("voice.test_runner.subprocess.run", lambda *a, **k: fake)
    result = run_test_suite(tmp_path)
    assert result["ok"] is True and result["passed"] == 5 and result["failures"] == []


def test_run_test_suite_reports_failing_names_and_saves_log(monkeypatch, tmp_path):
    out = ("FAILED tests/test_a.py::test_x - assert 1 == 2\n"
           "ERROR tests/test_b.py - ImportError\n"
           "== 1 failed, 4 passed, 1 error in 1.0s ==\n")
    fake = MagicMock(returncode=1, stdout=out, stderr="warn")
    monkeypatch.setattr("voice.test_runner.subprocess.run", lambda *a, **k: fake)
    log = tmp_path / "run.log"
    result = run_test_suite(tmp_path, log_path=log)
    assert result["ok"] is False
    assert result["failures"] == ["tests/test_a.py::test_x", "tests/test_b.py"]
    assert result["errors"] == 1
    assert "ImportError" in log.read_text(encoding="utf-8")


def test_run_test_suite_not_ok_on_collection_error_with_no_failures(monkeypatch, tmp_path):
    fake = MagicMock(returncode=2, stdout="ERROR tests/test_b.py\n== 1 error in 0.1s ==\n", stderr="")
    monkeypatch.setattr("voice.test_runner.subprocess.run", lambda *a, **k: fake)
    assert run_test_suite(tmp_path)["ok"] is False


def test_describe_failure_names_tests_and_log():
    msg = describe_failure({"failed": 4, "errors": 0, "exit_code": 1, "log": "C:/d/last.log",
                            "failures": [f"tests/test_a.py::t{i}" for i in range(4)]})
    assert "test_a.py::t0" in msg and "(+1 more)" in msg and "C:/d/last.log" in msg


def test_describe_failure_surfaces_launch_error():
    assert "TimeoutExpired" in describe_failure({"error": "TimeoutExpired: 300s"})


def test_run_test_suite_handles_subprocess_error(monkeypatch, tmp_path):
    def _boom(*a, **k):
        raise OSError("py not found")
    monkeypatch.setattr("voice.test_runner.subprocess.run", _boom)
    result = run_test_suite(tmp_path)
    assert result["ok"] is False
