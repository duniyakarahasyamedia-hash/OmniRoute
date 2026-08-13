"""Visual assets: gradient backgrounds, ASS captions (karaoke), cover card,
thumbnail and watermark — all rendered with libass+HarfBuzz for correct
Devanagari shaping."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from .tts import LineAudio
from .utils import run_ff

log = logging.getLogger("omnishorts.visuals")

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILY = "Noto Sans Devanagari"

# ASS colours are &HAABBGGRR
WHITE = "&H00FFFFFF"
YELLOW = "&H0000FFFF"
BLACK = "&H00000000"
ORANGE = "&H002255FF"
RED = "&H003333EE"
SOFT_BLACK = "&H96000000"

STYLE_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""


def _style(name: str, size: int, align: int, margin_v: int, primary=WHITE,
           secondary=YELLOW, outline=BLACK, bold=-1, outline_w=5, shadow=2,
           back=SOFT_BLACK) -> str:
    return (f"Style: {name},{FONT_FAMILY},{size},{primary},{secondary},{outline},{back},"
            f"{bold},0,0,0,100,100,0,0,1,{outline_w},{shadow},{align},60,60,{margin_v},1\n")


def _sanitize(text: str) -> str:
    return (text.replace("{", "").replace("}", "").replace("\n", " ").strip())


def _ts(ms: float) -> str:
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, cs = divmod(rem, 1000)
    return f"{h}:{m:02d}:{s:02d}.{cs // 10:02d}"


def _karaoke_text(words: list, start_ms: float) -> str:
    """Build ASS text with \\k tags from word timings (relative to start_ms)."""
    parts = []
    for w in words:
        s = max(0, w.start_ms - start_ms)
        e = max(s + 30, w.end_ms - start_ms)
        cs = max(1, round((e - s) / 10))
        parts.append(f"{{\\k{cs}}}{w.text} ")
    return "".join(parts)


@dataclass
class Caption:
    text: str
    start: float   # seconds (absolute)
    end: float
    style: str = "Caption"
    words: list = None  # optional word timings (absolute ms)


def build_captions_ass(captions: list[Caption], out_path: Path,
                       playres=(1080, 1920), cover_duration: float = 0.0,
                       cover_hook: str = "", watermark_text: str = "") -> Path:
    """Build the single ASS file for the whole video:
    cover-card events (0..cover_duration) + karaoke captions + watermark."""
    w, h = playres
    header = STYLE_HEADER.format(w=w, h=h)
    header += _style("Brand", 56, 8, 110, primary=YELLOW, outline=BLACK, outline_w=4)
    header += _style("CoverHook", 104, 5, 0, outline_w=7, shadow=4)
    header += _style("SubBadge", 66, 2, 190, primary=WHITE, outline=RED, outline_w=6)
    header += _style("Hook", 92, 8, 150, outline_w=6, shadow=3)
    header += _style("Caption", 76, 2, 430, outline_w=5, shadow=2)
    header += _style("CTA", 96, 2, 400, primary=YELLOW, secondary=WHITE,
                     outline=ORANGE, outline_w=6, shadow=3, bold=-1)
    header += _style("Wm", 40, 3, 46, primary=WHITE, outline=BLACK, outline_w=3,
                     shadow=1, back=BLACK)
    header += "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    lines = [header]
    # ---- cover card events (first COVER_DUR seconds) ----
    if cover_duration > 0:
        end = _ts(cover_duration * 1000)
        lines.append(
            f"Dialogue: 0,0:00:00.00,{end},Brand,,0,0,0,,{{\\fad(150,0)}}दुनिया का रहस्य"
        )
        if cover_hook:
            lines.append(
                f"Dialogue: 0,0:00:00.35,{end},CoverHook,,0,0,0,,"
                f"{{\\fad(150,100)}}{_sanitize(cover_hook)}"
            )
        lines.append(
            f"Dialogue: 0,0:00:00.60,{end},SubBadge,,0,0,0,,{{\\fad(150,0)}}सब्सक्राइब करें"
        )
    # ---- karaoke captions ----
    for cap in captions:
        text = _sanitize(cap.text)
        if not text:
            continue
        if cap.words:
            body = _karaoke_text(cap.words, cap.start * 1000)
        else:
            body = text
        fade = "\\fad(100,100)" if cap.style == "Hook" else ""
        lines.append(
            f"Dialogue: 0,{_ts(cap.start * 1000)},{_ts(cap.end * 1000)},{cap.style},"
            f",0,0,0,,{fade}{body}"
        )
    # ---- watermark (persistent, bottom-right) ----
    if watermark_text:
        lines.append(
            f"Dialogue: 0,0:00:01.50,1:00:00.00,Wm,,0,0,0,,{{\\fad(300,0)}}{_sanitize(watermark_text)}"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ------------------------------------------------------------- images
def make_gradient(out_path, size=(1080, 1920), seed=None) -> Path:
    """Dark cinematic gradient with radial glow — used as fallback background
    and base for cover card / thumbnail."""
    out_path = Path(out_path)
    rnd = random.Random(seed)
    w, h = size
    palettes = [
        ((15, 12, 41), (58, 26, 96), (255, 140, 40)),
        ((8, 14, 38), (20, 60, 90), (60, 200, 255)),
        ((20, 6, 20), (80, 20, 60), (255, 90, 140)),
        ((6, 24, 18), (10, 60, 50), (80, 255, 170)),
        ((18, 10, 4), (70, 40, 10), (255, 180, 60)),
    ]
    c1, c2, glow = palettes[rnd.randrange(len(palettes))]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for x in range(0, w, 4):
            for xx in range(x, min(x + 4, w)):
                px[xx, y] = (r, g, b)
    # radial glow
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = rnd.randrange(w // 4, 3 * w // 4), rnd.randrange(h // 5, h // 2)
    radius = int(max(w, h) * 0.75)
    for i in range(radius, 0, -8):
        alpha = int(26 * (1 - i / radius))
        od.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(*glow, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    # vignette
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    for i in range(int(min(w, h) * 0.65), 0, -10):
        vd.ellipse([w / 2 - i, h / 2 - i, w / 2 + i, h / 2 + i], fill=int(255 * (1 - i / (min(w, h) * 0.65))))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    img = Image.composite(img, dark, vig.point(lambda p: p * 0.5))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    return out_path


def make_thumbnail(hook: str, topic: str, out_path: Path) -> Path:
    """1280x720 thumbnail (long-form reuse) — gradient + ASS text via libass."""
    base = make_gradient(out_path.with_suffix(".png"), size=(1280, 720), seed=hash(topic) % 1000)
    w, h = 1280, 720
    header = STYLE_HEADER.format(w=w, h=h)
    header += _style("Thumb", 88, 5, 0, primary=YELLOW, outline=BLACK, outline_w=8, shadow=5)
    header += _style("ThumbBrand", 40, 8, 60, primary=WHITE, outline=BLACK, outline_w=4)
    header += "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    ass = out_path.parent / "thumb.ass"
    ass.write_text(
        header
        + f"Dialogue: 0,0:00:00.00,0:00:00.10,ThumbBrand,,0,0,0,,दुनिया का रहस्य\n"
        + f"Dialogue: 0,0:00:00.00,0:00:00.10,Thumb,,0,0,0,,{_sanitize(hook)}\n",
        encoding="utf-8",
    )
    run_ff([
        "-i", str(base),
        "-vf", f"ass={ass}:fontsdir={FONTS_DIR}",
        "-frames:v", "1", str(out_path),
    ])
    return out_path


def captions_from_audio(items: list, lines: list[LineAudio], pause: float,
                        hook_hold: float = 1.2, start_offset: float = 0.0) -> list[Caption]:
    """Build absolute-timed captions from per-line audio + word timings."""
    captions = []
    cursor = start_offset
    for item, la in zip(items, lines):
        words = None
        if la.words:
            words = [w for w in la.words]
        start = cursor
        end = cursor + la.duration
        if item["kind"] == "hook":
            style, end = "Hook", min(cursor + la.duration + hook_hold, cursor + 4.0)
        elif item["kind"] == "cta":
            style = "CTA"
        else:
            style = "Caption"
        captions.append(Caption(item["text"], start, end, style, words))
        cursor += la.duration + pause
    return captions


def segment_budget(durations: list[float], pause: float, max_total: float) -> list[float]:
    """Clip line durations so total speech fits under max_total."""
    total = sum(durations) + pause * (len(durations) - 1)
    if total <= max_total:
        return durations
    scale = (max_total - pause * (len(durations) - 1)) / sum(durations)
    return [d * max(0.6, scale) for d in durations]
