"""Diagnose widget heights in the settings window."""
import os, sys, time, threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(PROJECT_DIR))

from tray.settings_window import SettingsWindow

win = SettingsWindow()

def _diag():
    time.sleep(2.5)
    root = win._root
    if not root:
        return
    root.update_idletasks()

    def dump_children(widget, indent=0):
        prefix = "  " * indent
        name = type(widget).__name__
        try:
            w = widget.winfo_width()
            h = widget.winfo_height()
            x = widget.winfo_x()
            y = widget.winfo_y()
            print(f"{prefix}{name}: x={x} y={y} w={w} h={h}")
        except Exception:
            print(f"{prefix}{name}: (error)")
        for child in widget.winfo_children():
            dump_children(child, indent + 1)

    print("\n=== STATUS SECTION ===")
    status_frame = win._sections.get("Status")
    if status_frame:
        dump_children(status_frame)

    print("\n=== FEATS SECTION ===")
    # Switch to Feats to force layout
    root.after(0, lambda: win._show_section("Feats"))
    time.sleep(0.3)
    root.update_idletasks()
    feats_frame = win._sections.get("Feats")
    if feats_frame:
        dump_children(feats_frame)

    root.quit()

t = threading.Thread(target=_diag, daemon=True)
t.start()
win.run()
