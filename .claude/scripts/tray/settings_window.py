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

from tray import config as tray_config, process_mgr, task_scheduler
from heartbeat import snapshot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_C = {
    "bg":             "#161618",
    "sidebar":        "#1a1a1c",
    "divider":        "#212123",
    "stripe_on":      "#3b82f6",
    "stripe_off":     "#2e2e36",
    "badge_green_bg": "#052e16",
    "badge_green_fg": "#4ade80",
    "badge_blue_bg":  "#0c1d3d",
    "badge_blue_fg":  "#93c5fd",
    "badge_off_fg":   "#505058",
    "nav_active_bg":  "#1e2d4a",
    "nav_active_bdr": "#3b82f6",
}

_NAV = [("🤖", "Status"), ("📋", "Tasks"), ("🔧", "Feats"), ("⏰", "Hours")]

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


def _fmt_time(raw: str) -> str:
    """Format a schtasks datetime string to 'Mon DD HH:MM', or return 'N/A'."""
    if not raw or raw == "N/A":
        return "N/A"
    try:
        from datetime import datetime
        return datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p").strftime("%b %d %H:%M")
    except ValueError:
        return raw


class SettingsWindow:
    def __init__(self) -> None:
        self.alive = False
        self._root: ctk.CTk | None = None
        self._task_widgets: dict = {}

    def lift(self) -> None:
        if self._root:
            self._root.lift()
            self._root.focus()

    def run(self) -> None:
        self.alive = True
        try:
            self._root = ctk.CTk()
            self._root.title("Vesper Settings")
            self._root.geometry("460x580")
            self._root.resizable(False, False)
            self._root.configure(fg_color=_C["bg"])
            self._root.protocol("WM_DELETE_WINDOW", self._on_close)

            sidebar = ctk.CTkFrame(self._root, width=64, fg_color=_C["sidebar"],
                                   corner_radius=0)
            sidebar.pack(side="left", fill="y")
            sidebar.pack_propagate(False)

            self._content = ctk.CTkFrame(self._root, fg_color=_C["bg"], corner_radius=0)
            self._content.pack(side="left", fill="both", expand=True)

            self._nav_btns: list[tuple[str, ctk.CTkButton]] = []
            self._sections: dict[str, ctk.CTkFrame] = {}

            self._build_sidebar(sidebar)
            self._build_sections()

            self._show_section("Status")
            self._poll_status()
            self._root.mainloop()
        finally:
            self.alive = False

    def _on_close(self) -> None:
        if self._root:
            self._root.destroy()

    # ── Sidebar nav ───────────────────────────────────────────────────────────

    def _build_sidebar(self, sidebar: ctk.CTkFrame) -> None:
        for icon, label in _NAV:
            btn = ctk.CTkButton(
                sidebar,
                text=f"{icon}\n{label}",
                width=56, height=64,
                fg_color="transparent",
                hover_color=_C["nav_active_bg"],
                text_color="gray",
                font=("Segoe UI", 8),
                corner_radius=6,
                border_width=0,
                command=lambda s=label: self._show_section(s),
            )
            btn.pack(padx=4, pady=2)
            self._nav_btns.append((label, btn))

    def _show_section(self, name: str) -> None:
        for sec_name, btn in self._nav_btns:
            if sec_name == name:
                btn.configure(fg_color=_C["nav_active_bg"], text_color="white",
                              border_width=1, border_color=_C["nav_active_bdr"])
            else:
                btn.configure(fg_color="transparent", text_color="gray", border_width=0)
        for sec_name, frame in self._sections.items():
            if sec_name == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    def _build_sections(self) -> None:
        cfg = tray_config.load()
        for sec_name in ("Status", "Tasks", "Feats", "Hours"):
            frame = ctk.CTkFrame(self._content, fg_color=_C["bg"], corner_radius=0)
            self._sections[sec_name] = frame
        self._build_status(self._sections["Status"])
        self._build_tasks(self._sections["Tasks"], cfg)
        self._build_feats(self._sections["Feats"], cfg)
        self._build_hours(self._sections["Hours"], cfg)

    def _build_tasks(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        pass

    def _build_feats(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        pass

    def _build_hours(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        pass

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

        for task_key, task_name in task_scheduler.TASK_NAMES.items():
            if task_key in self._task_widgets:
                self._update_task_card(task_key, task_scheduler.get_status(task_name))

        self._root.after(3000, self._poll_status)

    # ── Features tab ──────────────────────────────────────────────────────────

    _FEATURE_META = [
        ("inbox",               "Inbox Processing",      "Summarise files dropped in inbox/ each tick"),
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

        for task_key, label in [
            ("heartbeat", "Heartbeat"),
            ("reflect",   "Memory Reflect"),
            ("index",     "Index"),
        ]:
            self._build_task_card(parent, task_key, label, cfg)

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

    def _build_task_card(self, parent: ctk.CTkFrame, task_key: str, label: str, cfg: dict) -> None:
        task_name = task_scheduler.TASK_NAMES[task_key]

        card = ctk.CTkFrame(parent)
        card.pack(fill="x", padx=8, pady=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(header, text=label, font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(side="left")
        badge = ctk.CTkLabel(header, text="● …", text_color="gray")
        badge.pack(side="right")

        time_row = ctk.CTkFrame(card, fg_color="transparent")
        time_row.pack(fill="x", padx=12, pady=2)
        last_lbl = ctk.CTkLabel(time_row, text="Last: …", text_color="gray",
                                font=("Segoe UI", 10), anchor="w")
        last_lbl.pack(side="left")
        next_lbl = ctk.CTkLabel(time_row, text="Next: …", text_color="gray",
                                font=("Segoe UI", 10), anchor="w")
        next_lbl.pack(side="left", padx=(16, 0))

        ctrl = ctk.CTkFrame(card, fg_color="transparent")
        ctrl.pack(fill="x", padx=12, pady=(2, 8))

        sw = ctk.CTkSwitch(ctrl, text="Enabled",
                           command=lambda k=task_key: self._toggle_task(k))
        sw.pack(side="left")

        if task_key == "heartbeat":
            ctk.CTkLabel(ctrl, text="Every", fg_color="transparent").pack(side="left", padx=(16, 4))
            interval_entry = ctk.CTkEntry(ctrl, width=48)
            interval_entry.insert(0, str(cfg.get("heartbeat_interval_minutes", 30)))
            interval_entry.pack(side="left")
            ctk.CTkLabel(ctrl, text="min").pack(side="left", padx=(4, 8))
            ctk.CTkButton(ctrl, text="Save", width=50,
                          command=lambda e=interval_entry: self._save_interval(e)).pack(side="left", padx=(0, 8))
            ctk.CTkButton(ctrl, text="Run Now", width=80,
                          command=lambda n=task_name: self._run_task_now(n)).pack(side="left")

        self._task_widgets[task_key] = {"badge": badge, "last": last_lbl, "next": next_lbl, "switch": sw}
        self._update_task_card(task_key, task_scheduler.get_status(task_name))

    def _update_task_card(self, task_key: str, status: dict) -> None:
        w = self._task_widgets.get(task_key)
        if not w:
            return
        st = status["status"]
        color = "#22c55e" if st.lower() == "ready" else (
            "#ef4444" if st.lower() in ("disabled", "unknown") else "#f59e0b"
        )
        w["badge"].configure(text=f"● {st}", text_color=color)
        w["last"].configure(text=f"Last: {_fmt_time(status['last_run'])}")
        w["next"].configure(text=f"Next: {_fmt_time(status['next_run'])}")
        if status["enabled"]:
            w["switch"].select()
        else:
            w["switch"].deselect()

    def _toggle_task(self, task_key: str) -> None:
        task_name = task_scheduler.TASK_NAMES[task_key]
        status = task_scheduler.get_status(task_name)
        task_scheduler.set_enabled(task_name, not status["enabled"])

    def _save_interval(self, entry: ctk.CTkEntry) -> None:
        try:
            minutes = int(entry.get().strip())
        except ValueError:
            return
        cfg = tray_config.load()
        cfg["heartbeat_interval_minutes"] = minutes
        tray_config.save(cfg)
        task_scheduler.set_interval(task_scheduler.TASK_NAMES["heartbeat"], minutes)

    def _run_task_now(self, task_name: str) -> None:
        task_scheduler.run_now(task_name)

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
