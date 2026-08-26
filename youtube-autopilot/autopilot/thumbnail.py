"""Thumbnail generator — libass se Devanagari text render, 1920x1080."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance

from . import config


def _compose_bg(src: Path, out: Path, w: int = 1920, h: int = 1080) -> Path:
    img = Image.open(src).convert("RGB")
    # cover-crop
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    img = img.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    img = img.crop((x, y, x + w, y + h))
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.15)
    # dark gradient (bottom)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(overlay)
    for i in range(h):
        alpha = int(215 * (i / h) ** 2.2)
        dr.line([(0, i), (w, i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img.save(out)
    return out


def _ass_thumbnail(title: str, badge: str, fonts_dir: Path, w: int = 1920, h: int = 1080) -> str:
    title = title.replace("{", "(").replace("}", ")").replace("\n", " ")
    badge = badge.replace("{", "(").replace("}", ")").replace("\n", " ")
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,Noto Sans Devanagari,104,&H0011D7FF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,7,4,5,70,70,140,1
Style: B,Noto Sans Devanagari,54,&H00FFFFFF,&H000000FF,&H00FF0000,&H90000000,-1,0,0,0,100,100,0,0,1,4,3,2,60,60,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:30.00,T,,0,0,0,,{title}
Dialogue: 0,0:00:00.00,0:00:30.00,B,,0,0,0,,{badge}
"""


def make_thumbnail(cfg: dict, story: dict[str, Any], run_dirs: dict) -> Path:
    """Thumbnail banao (source image + title + badge). Returns PNG path."""
    src = run_dirs["images"] / "thumb_src.png"
    if not src.exists():
        raise FileNotFoundError(f"Thumbnail source nahi mili: {src}")
    bg = _compose_bg(src, run_dirs["thumb"] / "bg.png")
    title = story.get("series") or story.get("title", "")
    badge = f"SCARY STORY • Part {story.get('part', 1)}"
    ass = run_dirs["thumb"] / "thumb.ass"
    ass.write_text(_ass_thumbnail(title, badge, config.FONTS_DIR), encoding="utf-8")
    out = run_dirs["thumb"] / "thumbnail.png"
    cmd = [
        config.ffmpeg_bin(), "-hide_banner", "-y",
        "-i", str(bg),
        "-vf", f"subtitles={ass}:fontsdir={config.FONTS_DIR}",
        "-frames:v", "1", "-update", "1",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    return out
