from __future__ import annotations
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import tkinter as tk
import customtkinter as ctk

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))

from tray import config as tray_config, process_mgr, task_scheduler
from heartbeat import snapshot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_C = {
    "bg":             "#1c1c20",
    "sidebar":        "#222227",
    "divider":        "#26262b",
    "stripe_on":      "#6d8fd6",
    "stripe_off":     "#33333a",
    "badge_green_bg": "#1a2e22",
    "badge_green_fg": "#7fd6a0",
    "badge_blue_bg":  "#202a3d",
    "badge_blue_fg":  "#a9c2ec",
    "badge_off_fg":   "#5c5c66",
    "nav_active_bg":  "#2a3142",
    "nav_active_bdr": "#6d8fd6",
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
        return datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p").strftime("%b %d %H:%M")
    except ValueError:
        return raw


class SettingsWindow:
    def __init__(self) -> None:
        self.alive = False
        self._root: ctk.CTk | None = None
        self._task_widgets: dict = {}
        self._nav_btns: list[tuple[str, ctk.CTkButton]] = []
        self._sections: dict[str, ctk.CTkFrame] = {}
        self._content: ctk.CTkFrame | None = None
        self._bot_badge: ctk.CTkLabel = None  # type: ignore[assignment]
        self._bot_btn: ctk.CTkButton = None  # type: ignore[assignment]
        self._last_tick_badge: ctk.CTkLabel = None  # type: ignore[assignment]
        self._next_tick_badge: ctk.CTkLabel = None  # type: ignore[assignment]
        self._start_entry: ctk.CTkEntry = None  # type: ignore[assignment]
        self._end_entry: ctk.CTkEntry = None  # type: ignore[assignment]

    def lift(self) -> None:
        if self._root:
            self._root.lift()
            self._root.focus()

    def run(self) -> None:
        self.alive = True
        try:
            self._root = ctk.CTk()
            self._root.title("Vesper Settings")
            self._root.geometry("460x300")
            self._root.resizable(False, False)
            self._root.configure(fg_color=_C["bg"])
            self._root.protocol("WM_DELETE_WINDOW", self._on_close)

            sidebar = ctk.CTkFrame(self._root, width=64, fg_color=_C["sidebar"],
                                   corner_radius=0)
            sidebar.pack(side="left", fill="y")
            sidebar.pack_propagate(False)

            self._content = ctk.CTkFrame(self._root, fg_color=_C["bg"], corner_radius=0)
            self._content.pack(side="left", fill="both", expand=True)

            self._nav_btns = []
            self._sections = {}

            self._build_sidebar(sidebar)
            self._build_sections()

            self._show_section("Status")
            self._root.after(10, self._fit_window)
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
                width=52, height=58,
                fg_color="transparent",
                hover_color=_C["nav_active_bg"],
                text_color="#8a8a94",
                font=("Segoe UI", 10),
                corner_radius=14,
                border_width=0,
                command=lambda s=label: self._show_section(s),
            )
            btn.pack(padx=6, pady=4)
            self._nav_btns.append((label, btn))

    def _show_section(self, name: str) -> None:
        if name not in self._sections:
            return
        for sec_name, btn in self._nav_btns:
            if sec_name == name:
                btn.configure(fg_color=_C["nav_active_bg"], text_color="#eaeaf0",
                              border_width=0)
            else:
                btn.configure(fg_color="transparent", text_color="#8a8a94", border_width=0)
        for sec_name, frame in self._sections.items():
            if sec_name == name:
                frame.pack(fill="x")
            else:
                frame.pack_forget()
        if self._root:
            self._root.after(10, self._fit_window)

    def _fit_window(self) -> None:
        if not self._root:
            return
        self._root.update_idletasks()
        # Sidebar needs at least 4 nav buttons; content drives the height
        nav_min = len(_NAV) * 72 + 16
        h = max(self._root.winfo_reqheight(), nav_min)
        self._root.geometry(f"460x{h}")

    def _build_sections(self) -> None:
        cfg = tray_config.load()
        for _, sec_name in _NAV:
            frame = ctk.CTkFrame(self._content, fg_color=_C["bg"], corner_radius=0)
            self._sections[sec_name] = frame
        self._build_status(self._sections["Status"])
        self._build_tasks(self._sections["Tasks"], cfg)
        self._build_feats(self._sections["Feats"], cfg)
        self._build_hours(self._sections["Hours"], cfg)

    def _build_tasks(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        self._task_widgets = {}

        # Heartbeat — expanded row (no toggle; Run Now + interval controls instead)
        hb_name = task_scheduler.TASK_NAMES["heartbeat"]
        hb_status = task_scheduler.get_status(hb_name)
        stripe_color = _C["stripe_on"] if hb_status["enabled"] else _C["stripe_off"]
        row, stripe = self._make_stripe_row(parent, stripe_color=stripe_color)

        content = ctk.CTkFrame(row, fg_color="transparent", corner_radius=0)
        content.pack(side="left", fill="both", expand=True, padx=(14, 16), pady=(10, 8))

        line1 = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        line1.pack(fill="x")
        ctk.CTkLabel(line1, text="Heartbeat", font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(side="left")
        hb_badge = ctk.CTkLabel(line1, text="● …", text_color="gray",
                                font=("Segoe UI", 10))
        hb_badge.pack(side="left", padx=(8, 0))

        line2 = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        line2.pack(fill="x", pady=(2, 0))
        hb_last = ctk.CTkLabel(line2, text="Last: …", text_color="gray",
                               font=("Segoe UI", 10), anchor="w")
        hb_last.pack(side="left")
        ctk.CTkLabel(line2, text=" → ", text_color="gray",
                     font=("Segoe UI", 10)).pack(side="left")
        hb_next = ctk.CTkLabel(line2, text="Next: …", text_color="gray",
                               font=("Segoe UI", 10), anchor="w")
        hb_next.pack(side="left")

        line3 = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        line3.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(line3, text="▶ Run Now", width=84, height=28, corner_radius=14,
                      command=lambda: self._run_task_now(hb_name)).pack(side="left")
        interval_entry = ctk.CTkEntry(line3, width=40, height=28, corner_radius=10)
        interval_entry.insert(0, str(cfg.get("heartbeat_interval_minutes", 30)))
        interval_entry.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(line3, text="min", font=("Segoe UI", 10)).pack(side="left", padx=(4, 0))
        ctk.CTkButton(line3, text="Save", width=50, height=28, corner_radius=14,
                      command=lambda e=interval_entry: self._save_interval(e)).pack(side="left", padx=(6, 0))

        self._task_widgets["heartbeat"] = {
            "badge": hb_badge, "last": hb_last, "next": hb_next,
            "switch": None, "stripe": stripe,
        }
        self._update_task_card("heartbeat", hb_status)

        # Reflect and Index — single-line rows with toggles
        self._build_simple_task_row(parent, "reflect", "Memory Reflect")
        self._build_simple_task_row(parent, "index", "Index", divider=False)

    def _build_simple_task_row(self, parent: ctk.CTkFrame, task_key: str,
                               label: str, divider: bool = True) -> None:
        task_name = task_scheduler.TASK_NAMES[task_key]
        status = task_scheduler.get_status(task_name)
        stripe_color = _C["stripe_on"] if status["enabled"] else _C["stripe_off"]
        row, stripe = self._make_stripe_row(parent, stripe_color=stripe_color, divider=divider)

        sw = ctk.CTkSwitch(row, text="",
                           command=lambda k=task_key: self._toggle_task(k))
        sw.pack(side="right", padx=16)

        content = ctk.CTkFrame(row, fg_color="transparent", corner_radius=0)
        content.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=12)

        line1 = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        line1.pack(fill="x")
        ctk.CTkLabel(line1, text=label, font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(side="left")
        badge = ctk.CTkLabel(line1, text="● …", text_color="gray",
                             font=("Segoe UI", 10))
        badge.pack(side="left", padx=(8, 0))

        self._task_widgets[task_key] = {
            "badge": badge, "last": None, "next": None,
            "switch": sw, "stripe": stripe,
        }
        self._update_task_card(task_key, status)

    def _build_feats(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        feats = cfg.get("features", {})
        for i, (key, name, desc) in enumerate(self._FEATURE_META):
            is_last = i == len(self._FEATURE_META) - 1
            row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
            row.pack(fill="x")

            sw = ctk.CTkSwitch(row, text="",
                               command=lambda k=key: self._toggle_feature(k))
            sw.pack(side="right", padx=16)

            content = ctk.CTkFrame(row, fg_color="transparent", corner_radius=0)
            content.pack(side="left", fill="both", expand=True, padx=16, pady=12)
            ctk.CTkLabel(content, text=name, font=("Segoe UI", 12, "bold"),
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(content, text=desc, text_color="gray",
                         font=("Segoe UI", 10), anchor="w").pack(anchor="w")

            if feats.get(key, True):
                sw.select()
            else:
                sw.deselect()

            if not is_last:
                div = ctk.CTkFrame(parent, height=1, fg_color=_C["divider"], corner_radius=0)
                div.pack(fill="x")
                div.pack_propagate(False)

    def _build_hours(self, parent: ctk.CTkFrame, cfg: dict) -> None:
        # Active Window sub-section label
        hdr = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(hdr, text="Active Window", font=("Segoe UI", 11, "bold"),
                     text_color="gray", anchor="w").pack(anchor="w")

        # Time inputs
        time_row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        time_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(time_row, text="Start", font=("Segoe UI", 10)).pack(side="left")
        self._start_entry = ctk.CTkEntry(time_row, width=64, height=30, corner_radius=10,
                                         placeholder_text="09:00")
        self._start_entry.insert(0, cfg.get("active_hours_start", "09:00"))
        self._start_entry.pack(side="left", padx=(6, 12))
        ctk.CTkLabel(time_row, text="End", font=("Segoe UI", 10)).pack(side="left")
        self._end_entry = ctk.CTkEntry(time_row, width=64, height=30, corner_radius=10,
                                       placeholder_text="22:00")
        self._end_entry.insert(0, cfg.get("active_hours_end", "22:00"))
        self._end_entry.pack(side="left", padx=(6, 12))
        ctk.CTkButton(time_row, text="Save Hours", width=84, height=30, corner_radius=15,
                      command=self._save_hours).pack(side="left")

        # Divider before startup rows
        div = ctk.CTkFrame(parent, height=1, fg_color=_C["divider"], corner_radius=0)
        div.pack(fill="x")
        div.pack_propagate(False)

        # Startup sub-section label
        hdr2 = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        hdr2.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(hdr2, text="Startup", font=("Segoe UI", 11, "bold"),
                     text_color="gray", anchor="w").pack(anchor="w")

        # Auto-start Bot row
        auto_on = cfg.get("auto_start_bot", True)
        row_auto, _ = self._make_stripe_row(
            parent,
            stripe_color=_C["stripe_on"] if auto_on else _C["stripe_off"],
        )
        auto_sw = ctk.CTkSwitch(row_auto, text="", command=self._toggle_auto_start)
        auto_sw.pack(side="right", padx=16)
        content_a = ctk.CTkFrame(row_auto, fg_color="transparent", corner_radius=0)
        content_a.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=12)
        ctk.CTkLabel(content_a, text="Auto-start Bot", font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(anchor="w")
        if auto_on:
            auto_sw.select()

        # Start with Windows row
        startup_on = cfg.get("start_with_windows", True)
        row_startup, _ = self._make_stripe_row(
            parent,
            stripe_color=_C["stripe_on"] if startup_on else _C["stripe_off"],
            divider=False,
        )
        startup_sw = ctk.CTkSwitch(row_startup, text="", command=self._toggle_startup)
        startup_sw.pack(side="right", padx=16)
        content_s = ctk.CTkFrame(row_startup, fg_color="transparent", corner_radius=0)
        content_s.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=12)
        ctk.CTkLabel(content_s, text="Start with Windows", font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(anchor="w")
        if startup_on:
            startup_sw.select()

    # ── Row helper ────────────────────────────────────────────────────────────

    def _make_stripe_row(self, parent: ctk.CTkFrame,
                         stripe_color: str = "",
                         divider: bool = True) -> tuple[tk.Frame, tk.Frame]:
        """Return (row_frame, stripe_frame). Pack toggle (side='right') then content into row_frame."""
        if not stripe_color or stripe_color == "transparent":
            stripe_color = _C["stripe_off"]
        # tk.Frame avoids CTkFrame's internal expand behavior that causes rows to absorb
        # the full parent height when a fill="y" child is present.
        row = tk.Frame(parent, bg=_C["bg"])
        row.pack(fill="x")
        stripe = tk.Frame(row, width=3, bg=stripe_color)
        stripe.pack(side="left", fill="y")
        stripe.pack_propagate(False)
        if divider:
            div = tk.Frame(parent, height=1, bg=_C["divider"])
            div.pack(fill="x")
            div.pack_propagate(False)
        return row, stripe

    # ── Status tab ────────────────────────────────────────────────────────────

    def _build_status(self, parent: ctk.CTkFrame) -> None:
        # Bot row
        row, _ = self._make_stripe_row(parent, stripe_color=_C["bg"])
        self._bot_btn = ctk.CTkButton(row, text="Stop", width=68, height=30,
                                      corner_radius=15,
                                      fg_color="#5a1216", hover_color="#7f1d1d",
                                      command=self._toggle_bot)
        self._bot_btn.pack(side="right", padx=16)
        self._bot_badge = ctk.CTkLabel(row, text="● Checking…", text_color="gray",
                                       font=("Segoe UI", 10))
        self._bot_badge.pack(side="right", padx=10)
        content = ctk.CTkFrame(row, fg_color="transparent", corner_radius=0)
        content.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=14)
        ctk.CTkLabel(content, text="Discord Bot", font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(anchor="w")

        # Last tick row
        row2, _ = self._make_stripe_row(parent, stripe_color=_C["bg"])
        self._last_tick_badge = ctk.CTkLabel(
            row2, text="…", fg_color=_C["badge_blue_bg"],
            text_color=_C["badge_blue_fg"], corner_radius=11,
            font=("Segoe UI", 10), padx=10, pady=4,
        )
        self._last_tick_badge.pack(side="right", padx=16)
        content2 = ctk.CTkFrame(row2, fg_color="transparent", corner_radius=0)
        content2.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=14)
        ctk.CTkLabel(content2, text="Last tick", font=("Segoe UI", 11),
                     anchor="w").pack(anchor="w")

        # Next tick row
        row3, _ = self._make_stripe_row(parent, stripe_color=_C["bg"], divider=False)
        self._next_tick_badge = ctk.CTkLabel(
            row3, text="…", fg_color=_C["badge_green_bg"],
            text_color=_C["badge_green_fg"], corner_radius=11,
            font=("Segoe UI", 10), padx=10, pady=4,
        )
        self._next_tick_badge.pack(side="right", padx=16)
        content3 = ctk.CTkFrame(row3, fg_color="transparent", corner_radius=0)
        content3.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=14)
        ctk.CTkLabel(content3, text="Next tick", font=("Segoe UI", 11),
                     anchor="w").pack(anchor="w")

    def _toggle_bot(self) -> None:
        if process_mgr.bot_status() == "running":
            process_mgr.stop_bot()
        else:
            process_mgr.start_bot()

    def _poll_status(self) -> None:
        if not self._root or not self.alive:
            return

        # Bot badge + button
        status = process_mgr.bot_status()
        if status == "running":
            self._bot_badge.configure(text="● Running", text_color=_C["badge_green_fg"])
            self._bot_btn.configure(text="Stop", fg_color="#450a0a", hover_color="#7f1d1d")
        else:
            self._bot_badge.configure(text="● Stopped", text_color="#ef4444")
            self._bot_btn.configure(text="Start", fg_color="#14532d", hover_color="#166534")

        # Last tick badge
        snap = snapshot.load_state() or {}
        ts = snap.get("heartbeat_ran_at") or snap.get("timestamp") or 0
        if ts:
            mins = int((time.time() - float(ts)) // 60)
            self._last_tick_badge.configure(text=f"{mins}m ago")
        else:
            self._last_tick_badge.configure(text="N/A")

        # Next tick badge (from heartbeat task scheduler)
        hb_status = task_scheduler.get_status(task_scheduler.TASK_NAMES["heartbeat"])
        next_raw = hb_status.get("next_run", "N/A")
        try:
            dt = datetime.strptime(next_raw, "%m/%d/%Y %I:%M:%S %p")
            next_text = dt.strftime("%H:%M")
        except Exception:
            next_text = next_raw if next_raw and next_raw != "N/A" else "N/A"
        self._next_tick_badge.configure(text=next_text)

        # Task cards
        for task_key, task_name in task_scheduler.TASK_NAMES.items():
            if task_key in self._task_widgets:
                self._update_task_card(task_key, task_scheduler.get_status(task_name))

        self._root.after(3000, self._poll_status)

    # ── Features tab ──────────────────────────────────────────────────────────

    _FEATURE_META = [
        ("inbox",               "Inbox",       "Process dropped files each tick"),
        ("gcal_sync",           "GCal Sync",   "Push deadlines to calendar"),
        ("thread_chat",         "Thread Chat", "Reply in Discord threads"),
        ("toast_notifications", "Toast",       "Desktop notifications"),
    ]

    def _toggle_feature(self, key: str) -> None:
        cfg = tray_config.load()
        feats = cfg.setdefault("features", {})
        feats[key] = not feats.get(key, True)
        tray_config.save(cfg)

    # ── Schedule tab ──────────────────────────────────────────────────────────

    def _update_task_card(self, task_key: str, status: dict) -> None:
        w = self._task_widgets.get(task_key)
        if w is None:
            return
        st = status["status"]
        color = _C["badge_green_fg"] if st.lower() == "ready" else (
            _C["badge_off_fg"] if st.lower() in ("disabled", "unknown") else "#f59e0b"
        )
        w["badge"].configure(text=f"● {st}", text_color=color)
        if w["last"] is not None:
            w["last"].configure(text=f"Last: {_fmt_time(status['last_run'])}")
        if w["next"] is not None:
            w["next"].configure(text=f"Next: {_fmt_time(status['next_run'])}")
        if w["switch"] is not None:
            if status["enabled"]:
                w["switch"].select()
            else:
                w["switch"].deselect()
        w["stripe"].configure(bg=_C["stripe_on"] if status["enabled"] else _C["stripe_off"])

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
