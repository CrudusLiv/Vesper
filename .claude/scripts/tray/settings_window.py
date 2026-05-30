from __future__ import annotations
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import customtkinter as ctk

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))

from tray import config as tray_config, process_mgr
from heartbeat import snapshot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_WINDOW_LOCK = threading.Lock()
_current: "SettingsWindow | None" = None


def open_settings() -> None:
    """Open the settings window; focus it if already open. Call from any thread."""
    global _current
    with _WINDOW_LOCK:
        if _current is not None and _current.alive:
            _current.lift()
            return
        win = SettingsWindow()
        _current = win
    threading.Thread(target=win.run, daemon=True).start()


class SettingsWindow:
    def __init__(self) -> None:
        self.alive = False
        self._root: ctk.CTk | None = None

    def lift(self) -> None:
        if self._root:
            self._root.lift()
            self._root.focus()

    def run(self) -> None:
        self.alive = True
        try:
            self._root = ctk.CTk()
            self._root.title("Vesper Settings")
            self._root.geometry("440x540")
            self._root.resizable(False, False)
            self._root.protocol("WM_DELETE_WINDOW", self._on_close)

            tabs = ctk.CTkTabview(self._root, width=420)
            tabs.pack(fill="both", expand=True, padx=10, pady=10)
            tabs.add("Status")
            tabs.add("Features")
            tabs.add("Schedule")

            self._build_status(tabs.tab("Status"))
            self._build_features(tabs.tab("Features"))
            self._build_schedule(tabs.tab("Schedule"))

            self._poll_status()
            self._root.mainloop()
        finally:
            self.alive = False

    def _on_close(self) -> None:
        if self._root:
            self._root.destroy()

    # ── Status tab ────────────────────────────────────────────────────────────

    def _build_status(self, parent: ctk.CTkFrame) -> None:
        bot_frame = ctk.CTkFrame(parent)
        bot_frame.pack(fill="x", padx=8, pady=(12, 6))
        ctk.CTkLabel(bot_frame, text="🤖  Discord Bot", anchor="w",
                     font=("Segoe UI", 13, "bold")).pack(side="left", padx=12, pady=10)
        self._bot_badge = ctk.CTkLabel(bot_frame, text="● Checking…", text_color="gray")
        self._bot_badge.pack(side="right", padx=(0, 12))
        self._bot_btn = ctk.CTkButton(bot_frame, text="Stop", width=64,
                                      fg_color="#450a0a", hover_color="#7f1d1d",
                                      command=self._toggle_bot)
        self._bot_btn.pack(side="right", padx=(0, 6))

        hb_frame = ctk.CTkFrame(parent)
        hb_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(hb_frame, text="💓  Heartbeat", anchor="w",
                     font=("Segoe UI", 13, "bold")).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(hb_frame, text="Run now", width=80,
                      command=self._run_heartbeat_now).pack(side="right", padx=12)

        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=8, pady=6)
        self._tick_label = ctk.CTkLabel(info_frame, text="Loading…",
                                        text_color="gray", anchor="w", justify="left")
        self._tick_label.pack(padx=12, pady=8, anchor="w")

    def _toggle_bot(self) -> None:
        if process_mgr.bot_status() == "running":
            process_mgr.stop_bot()
        else:
            process_mgr.start_bot()

    def _run_heartbeat_now(self) -> None:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_DIR)}
        subprocess.Popen(
            [sys.executable, str(PROJECT_DIR / ".claude" / "scripts" / "heartbeat.py")],
            cwd=str(PROJECT_DIR), env=env,
        )

    def _poll_status(self) -> None:
        if not self._root or not self.alive:
            return
        status = process_mgr.bot_status()
        if status == "running":
            self._bot_badge.configure(text="● Running", text_color="#22c55e")
            self._bot_btn.configure(text="Stop", fg_color="#450a0a", hover_color="#7f1d1d")
        else:
            self._bot_badge.configure(text="● Stopped", text_color="#ef4444")
            self._bot_btn.configure(text="Start", fg_color="#14532d", hover_color="#166534")

        snap = snapshot.load_state() or {}
        ts = snap.get("heartbeat_ran_at") or snap.get("timestamp") or 0
        if ts:
            mins = int((time.time() - float(ts)) // 60)
            err_keys = [k for k, v in snap.items() if isinstance(v, dict) and "error" in v]
            tick_text = f"Last tick: {mins}m ago  •  {'✓ ok' if not err_keys else '✗ errors'}"
        else:
            tick_text = "No tick data yet"
        self._tick_label.configure(text=tick_text)

        self._root.after(3000, self._poll_status)

    # ── Features tab ──────────────────────────────────────────────────────────

    _FEATURE_META = [
        ("inbox",               "Inbox Processing",      "Summarise files dropped in inbox/ each tick"),
        ("reflect",             "Memory Reflect",        "memory_reflect.py (wired when enabled)"),
        ("gcal_sync",           "GCal Sync",             "Push deadlines to Google Calendar"),
        ("thread_chat",         "Thread Chat",           "Reply in Discord forum threads"),
        ("toast_notifications", "Toast Notifications",   "Desktop toasts for Discord pings"),
    ]

    def _build_features(self, parent: ctk.CTkFrame) -> None:
        cfg = tray_config.load()
        feats = cfg.get("features", {})
        for key, name, desc in self._FEATURE_META:
            row = ctk.CTkFrame(parent)
            row.pack(fill="x", padx=8, pady=4)
            text_col = ctk.CTkFrame(row, fg_color="transparent")
            text_col.pack(side="left", padx=12, pady=8, fill="x", expand=True)
            ctk.CTkLabel(text_col, text=name, anchor="w",
                         font=("Segoe UI", 12, "bold")).pack(anchor="w")
            ctk.CTkLabel(text_col, text=desc, anchor="w",
                         text_color="gray", font=("Segoe UI", 10)).pack(anchor="w")
            sw = ctk.CTkSwitch(row, text="", width=46,
                               command=lambda k=key: self._toggle_feature(k))
            sw.pack(side="right", padx=12)
            if feats.get(key, True):
                sw.select()
            else:
                sw.deselect()

    def _toggle_feature(self, key: str) -> None:
        cfg = tray_config.load()
        feats = cfg.setdefault("features", {})
        feats[key] = not feats.get(key, True)
        tray_config.save(cfg)

    # ── Schedule tab ──────────────────────────────────────────────────────────

    def _build_schedule(self, parent: ctk.CTkFrame) -> None:
        cfg = tray_config.load()

        hours_frame = ctk.CTkFrame(parent)
        hours_frame.pack(fill="x", padx=8, pady=(12, 6))
        ctk.CTkLabel(hours_frame, text="Active Hours",
                     font=("Segoe UI", 12, "bold"), anchor="w").pack(padx=12, pady=(8, 2), anchor="w")
        ctk.CTkLabel(hours_frame, text="Heartbeat won't fire outside this window",
                     text_color="gray", font=("Segoe UI", 10), anchor="w").pack(padx=12, anchor="w")
        time_row = ctk.CTkFrame(hours_frame, fg_color="transparent")
        time_row.pack(padx=12, pady=8, anchor="w")
        ctk.CTkLabel(time_row, text="Start").pack(side="left")
        self._start_entry = ctk.CTkEntry(time_row, width=64, placeholder_text="09:00")
        self._start_entry.insert(0, cfg.get("active_hours_start", "09:00"))
        self._start_entry.pack(side="left", padx=(6, 12))
        ctk.CTkLabel(time_row, text="End").pack(side="left")
        self._end_entry = ctk.CTkEntry(time_row, width=64, placeholder_text="22:00")
        self._end_entry.insert(0, cfg.get("active_hours_end", "22:00"))
        self._end_entry.pack(side="left", padx=6)
        ctk.CTkButton(time_row, text="Save", width=60,
                      command=self._save_hours).pack(side="left", padx=8)

        interval_frame = ctk.CTkFrame(parent)
        interval_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(interval_frame, text="Heartbeat Interval", anchor="w",
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(interval_frame, text="30 min  (set in Task Scheduler)",
                     text_color="gray").pack(side="right", padx=12)

        auto_frame = ctk.CTkFrame(parent)
        auto_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(auto_frame, text="Auto-start Bot on Launch", anchor="w",
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=12, pady=10)
        auto_sw = ctk.CTkSwitch(auto_frame, text="", command=self._toggle_auto_start)
        auto_sw.pack(side="right", padx=12)
        if cfg.get("auto_start_bot", True):
            auto_sw.select()

        startup_frame = ctk.CTkFrame(parent)
        startup_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(startup_frame, text="Start with Windows", anchor="w",
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=12, pady=10)
        startup_sw = ctk.CTkSwitch(startup_frame, text="", command=self._toggle_startup)
        startup_sw.pack(side="right", padx=12)
        if cfg.get("start_with_windows", True):
            startup_sw.select()

    def _save_hours(self) -> None:
        cfg = tray_config.load()
        cfg["active_hours_start"] = self._start_entry.get().strip() or "09:00"
        cfg["active_hours_end"] = self._end_entry.get().strip() or "22:00"
        tray_config.save(cfg)

    def _toggle_auto_start(self) -> None:
        cfg = tray_config.load()
        cfg["auto_start_bot"] = not cfg.get("auto_start_bot", True)
        tray_config.save(cfg)

    def _toggle_startup(self) -> None:
        cfg = tray_config.load()
        enabled = not cfg.get("start_with_windows", True)
        cfg["start_with_windows"] = enabled
        tray_config.save(cfg)
        _set_windows_startup(enabled)


def _set_windows_startup(enabled: bool) -> None:
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    tray_app = PROJECT_DIR / ".claude" / "scripts" / "tray_app.py"
    cmd = f'"{pythonw}" "{tray_app}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, "VesperTray", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "VesperTray")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as exc:
        print(f"_set_windows_startup failed: {exc}", file=sys.stderr)
