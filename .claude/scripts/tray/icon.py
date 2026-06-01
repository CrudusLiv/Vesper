from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

_DIR = Path(__file__).resolve().parent
# Conventional names are checked first; otherwise the first image in this
# directory wins. Drop a PNG/ICO here and it's picked up automatically.
_CANDIDATES = ("vesper.png", "vesper.ico", "icon.png", "icon.ico")
_EXTS = (".png", ".ico")
_SIZE = (64, 64)


def _custom_icon_path() -> Path | None:
    for name in _CANDIDATES:
        p = _DIR / name
        if p.is_file():
            return p
    for p in sorted(_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in _EXTS:
            return p
    return None


def _status_colour(status: str) -> str:
    return "#22c55e" if status == "ok" else "#ef4444"


def _draw_circle(status: str) -> Image.Image:
    """64x64 circle: green for 'ok', red for anything else."""
    img = Image.new("RGBA", _SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=_status_colour(status))
    return img


def _apply_badge(img: Image.Image, status: str) -> Image.Image:
    """Normalise to _SIZE and stamp a status dot in the bottom-right corner.
    The white ring keeps the dot visible on both light and dark icons."""
    img = img.convert("RGBA")
    if img.size != _SIZE:
        img = img.resize(_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)
    cx, cy, r = 47, 47, 12
    draw.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill="white")
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_status_colour(status))
    return img


def make_icon(status: str = "ok") -> Image.Image:
    """Tray icon. Uses a custom image dropped in this directory if one exists
    (with a status dot overlaid), otherwise falls back to a drawn status
    circle (green=ok, red=error)."""
    path = _custom_icon_path()
    if path is not None:
        try:
            return _apply_badge(Image.open(path), status)
        except Exception:
            pass  # unreadable/corrupt file — fall back to the circle
    return _draw_circle(status)
