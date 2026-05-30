from __future__ import annotations
from PIL import Image, ImageDraw


def make_icon(status: str = "ok") -> Image.Image:
    """64x64 circle: green for 'ok', red for anything else."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colour = "#22c55e" if status == "ok" else "#ef4444"
    draw.ellipse([8, 8, 56, 56], fill=colour)
    return img
