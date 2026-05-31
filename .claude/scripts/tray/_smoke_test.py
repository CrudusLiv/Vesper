"""Smoke-test: opens settings window, screenshots each section, exits."""
import os, sys, time, threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(PROJECT_DIR))

from tray.settings_window import SettingsWindow

win = SettingsWindow()
OUT = Path(__file__).parent

def _run_checks():
    time.sleep(2.5)  # wait for window to render

    root = win._root
    if not root:
        print("ERROR: root is None")
        return

    # Force on top
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()
    time.sleep(0.3)

    from PIL import ImageGrab

    def snap(name):
        root.update_idletasks()
        time.sleep(0.4)
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        bbox = (x, y, x + w, y + h)
        img = ImageGrab.grab(bbox=bbox)
        p = OUT / f"_smoke_{name}.png"
        img.save(str(p))
        print(f"  saved {p.name} ({w}x{h})")

    # Screenshot Status section (default)
    snap("status")

    # Switch to Tasks, screenshot
    root.after(0, lambda: win._show_section("Tasks"))
    time.sleep(0.5)
    snap("tasks")

    # Switch to Feats, screenshot
    root.after(0, lambda: win._show_section("Feats"))
    time.sleep(0.5)
    snap("feats")

    # Switch to Hours, screenshot
    root.after(0, lambda: win._show_section("Hours"))
    time.sleep(0.5)
    snap("hours")

    print("All screenshots saved.")
    root.quit()

t = threading.Thread(target=_run_checks, daemon=True)
t.start()
win.run()
