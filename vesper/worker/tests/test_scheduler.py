import subprocess
import sys

import schedule

import scheduler


def test_setup_schedule_registers_three_jobs():
    scheduler.setup_schedule(30)
    assert len(schedule.jobs) == 3
    units = sorted((j.interval, j.unit) for j in schedule.jobs)
    assert (1, "days") in units       # reflect, daily
    assert (10, "minutes") in units   # memory-index
    assert (30, "minutes") in units   # heartbeat


def test_setup_schedule_with_custom_interval():
    scheduler.setup_schedule(60)
    assert len(schedule.jobs) == 3
    units = sorted((j.interval, j.unit) for j in schedule.jobs)
    assert (1, "days") in units       # reflect, daily
    assert (10, "minutes") in units   # memory-index
    assert (60, "minutes") in units   # heartbeat with custom interval


def test_run_job_invokes_subprocess(monkeypatch, tmp_path):
    calls = {}

    class FakeProc:
        returncode = 0

    def fake_run(argv, cwd=None, env=None):
        calls["argv"] = argv
        calls["cwd"] = cwd
        calls["env"] = env
        return FakeProc()

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(subprocess, "run", fake_run)
    script = tmp_path / "x.py"
    rc = scheduler.run_job(script, env_extra={"HEARTBEAT_FORCE": "1"})
    assert rc == 0
    assert calls["argv"] == [sys.executable, str(script)]
    assert calls["cwd"] == str(tmp_path)
    assert calls["env"]["HEARTBEAT_FORCE"] == "1"


def test_check_sentinel_runs_forced_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    sentinel = tmp_path / ".claude" / "data" / "state" / "heartbeat-trigger"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("123")
    seen = {}

    def fake_run_job(script, env_extra=None):
        seen["script"] = script
        seen["env_extra"] = env_extra
        return 0

    monkeypatch.setattr(scheduler, "run_job", fake_run_job)
    assert scheduler.check_sentinel() is True
    assert not sentinel.exists()
    assert seen["env_extra"] == {"HEARTBEAT_FORCE": "1"}
    assert seen["script"].name == "heartbeat.py"


def test_check_sentinel_noop_when_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    called = {"n": 0}
    monkeypatch.setattr(scheduler, "run_job", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    assert scheduler.check_sentinel() is False
    assert called["n"] == 0


def test_load_heartbeat_interval_from_settings(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text(json.dumps({"heartbeat_interval_minutes": 60}), encoding="utf-8")
    assert scheduler._load_heartbeat_interval() == 60


def test_load_heartbeat_interval_default_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    # No settings file exists
    assert scheduler._load_heartbeat_interval() == 30


def test_load_heartbeat_interval_default_on_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text("invalid json", encoding="utf-8")
    assert scheduler._load_heartbeat_interval() == 30


def test_load_heartbeat_interval_default_on_bad_value(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    settings_dir = tmp_path / ".claude" / "data"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "tray_settings.json"
    settings_file.write_text(json.dumps({"heartbeat_interval_minutes": "not_a_number"}), encoding="utf-8")
    assert scheduler._load_heartbeat_interval() == 30
