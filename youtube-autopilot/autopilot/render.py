"""Video rendering — scenes, subtitles, music mix, final encode (16:9 full + 9:16 Shorts)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from . import config

GAP = 0.35  # scenes ke beech silence


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg fail:\n$ {' '.join(cmd)}\n{proc.stderr[-3000:]}")


def _zoompan_filter(action: str, dur_frames: int, w: int, h: int, pw: int, ph: int) -> str:
    """Image ko pre-scale karke zoom/pan karne wala filter chain."""
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    z = {
        "zoom_in": "min(zoom+0.0012,1.18)",
        "zoom_out": "if(lte(on,1),1.18,max(zoom-0.0012,1.0))",
        "pan_left": "1.12",
        "pan_right": "1.12",
    }.get(action, "min(zoom+0.0012,1.18)")
    if action == "pan_left":
        x = f"(iw-iw/zoom)*(1-on/{max(dur_frames-1,1)})"
        y = cy
    elif action == "pan_right":
        x = f"(iw-iw/zoom)*(on/{max(dur_frames-1,1)})"
        y = cy
    else:
        x, y = cx, cy
    return (
        f"scale={pw}:{ph},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={dur_frames}:s={w}x{h}:fps={fps},"
        f"setsar=1"
    )


fps = 25


def scene_video(cfg: dict, image: Path, voice: Path, dur_total: float, action: str,
                idx: int, out_dir: Path, mode: str) -> Path:
    """Ek scene ki clip: image zoom/pan + narration audio. Returns mp4 path."""
    vcfg = cfg.get("video", {})
    if mode == "short":
        w, h = vcfg.get("short_width", 1080), vcfg.get("short_height", 1920)
        pw, ph = 1620, 2880
    else:
        w, h = vcfg.get("width", 1920), vcfg.get("height", 1080)
        pw, ph = 2400, 1350

    frames = max(int(dur_total * fps), 2)
    zf = _zoompan_filter(action, frames, w, h, pw, ph)
    out = out_dir / f"scene_{idx:02d}.mp4"
    cmd = [
        config.ffmpeg_bin(), "-hide_banner", "-y",
        "-loop", "1", "-framerate", "25", "-i", str(image),
        "-i", str(voice),
        "-filter_complex",
        f"[0:v]{zf}[v];[1:a]apad[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{dur_total:.3f}",
        "-c:v", "libx264", "-preset", vcfg.get("preset", "veryfast"),
        "-crf", str(vcfg.get("crf", 20)), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-r", "25",
        str(out),
    ]
    _run(cmd)
    return out


def concat_videos(clips: list[Path], out: Path) -> Path:
    lst = out.parent / "concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve()}'" for c in clips) + "\n", encoding="utf-8")
    _run([config.ffmpeg_bin(), "-hide_banner", "-y", "-f", "concat", "-safe", "0",
          "-i", str(lst), "-c", "copy", str(out)])
    return out


def build_ass(cfg: dict, story: dict[str, Any], timings: list[tuple[int, float, float]],
              out: Path, mode: str) -> Path:
    """Scene-wise Hindi subtitles ka .ass file banao."""
    vcfg = cfg.get("video", {})
    scfg = cfg.get("subtitles", {})
    if mode == "short":
        w, h = vcfg.get("short_width", 1080), vcfg.get("short_height", 1920)
        fs = int(scfg.get("fontsize", 46) * 1.9)
        margin_v = int(h * 0.16)
    else:
        w, h = vcfg.get("width", 1920), vcfg.get("height", 1080)
        fs = int(scfg.get("fontsize", 46))
        margin_v = int(h * 0.11)
    color = scfg.get("color", "&H0000D7FF&")
    font = scfg.get("font", "NotoSansDevanagari-700.ttf")
    font_name = "Noto Sans Devanagari"

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Sub,{font_name},{fs},{color},&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,3,2,60,60,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def ts(x: float) -> str:
        hh = int(x // 3600)
        mm = int(x % 3600 // 60)
        ss = x % 60
        return f"{hh}:{mm:02d}:{ss:05.2f}"

    for sid, start, end in timings:
        scene = next((s for s in story["scenes"] if int(s["id"]) == sid), None)
        if not scene:
            continue
        text = scene["narration_hi"].replace("\n", " ").replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Sub,,0,0,0,,{text}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def finalize(cfg: dict, base: Path, music: Path, ass: Path, out: Path,
             voice_volume: float = 1.0) -> Path:
    """Music mix + subtitles burn — final single encode."""
    vcfg = cfg.get("video", {})
    mvol = float(cfg.get("music", {}).get("volume", 0.14))
    cmd = [
        config.ffmpeg_bin(), "-hide_banner", "-y",
        "-i", str(base), "-i", str(music),
        "-filter_complex",
        f"[0:v]subtitles={ass}:fontsdir={config.FONTS_DIR}[v];"
        f"[0:a]volume={voice_volume}[n];"
        f"[1:a]volume={mvol}[m];"
        f"[n][m]amix=inputs=2:duration=first:normalize=0,"
        f"aformat=channel_layouts=stereo[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", vcfg.get("preset", "veryfast"),
        "-crf", str(vcfg.get("crf", 20)), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        str(out),
    ]
    _run(cmd)
    return out


def render_full(cfg: dict, story: dict[str, Any], run_dirs: dict,
                voice_files: list[tuple[int, Path, float]], mode: str = "full") -> Path:
    """Poori video render karo. Returns final mp4 path."""
    gap = float(cfg.get("video", {}).get("gap", GAP))
    clips, timings = [], []
    t = 0.0
    for sid, vpath, dur in voice_files:
        scene = next((s for s in story["scenes"] if int(s["id"]) == sid), None)
        img = run_dirs["images"] / f"scene_{sid:02d}.png"
        total = dur + gap
        clip = scene_video(cfg, img, vpath, total, scene["action"], sid, run_dirs["clips"], mode)
        clips.append(clip)
        timings.append((sid, t, t + dur))
        t += total

    base = concat_videos(clips, run_dirs[mode] / "base.mp4")
    music = run_dirs["music"] / "bgm.wav"
    if not music.exists():
        from .music import make_music

        make_music(t, music, cfg.get("music", {}))
    ass = build_ass(cfg, story, timings, run_dirs[mode] / "subs.ass", mode)
    final = finalize(cfg, base, music, ass, run_dirs[mode] / f"{mode}.mp4")
    return final
