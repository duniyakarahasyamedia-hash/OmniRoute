"""Video composition with ffmpeg: per-segment clips (Ken Burns), concat,
voice+music audio mix, caption overlay, watermark."""
from __future__ import annotations

import logging
from pathlib import Path

from .utils import run_ff

log = logging.getLogger("omnishorts.composer")

W, H = 1080, 1920
FPS = 30


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def render_clip(segment: dict, idx: int, workdir: Path, keep: bool = False) -> Path:
    """Render one segment to clip_XX.mp4 (1080x1920@30, yuv420p, silent)."""
    src = segment.get("src")
    dur = float(segment["dur"])
    out = workdir / f"clip_{idx:02d}.mp4"
    if src is not None and _is_video(src):
        run_ff([
            "-i", str(src), "-t", f"{dur:.3f}",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                   f"crop={W}:{H},fps={FPS},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            str(out),
        ])
    else:
        img = src if src is not None else segment.get("image")
        gen_name = None
        if img is None:
            gen_name = workdir / f"gen_bg_{idx:02d}.png"
            from .visuals import make_gradient
            make_gradient(gen_name, size=(W, H), seed=idx)
            img = gen_name
        frames = int(dur * FPS)
        run_ff([
            "-loop", "1", "-framerate", str(FPS), "-i", str(img), "-t", f"{dur:.3f}",
            "-vf", f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
                   f"crop={W * 2}:{H * 2},"
                   f"zoompan=z='min(1.0+0.0006*in,1.12)':d=1:x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p",
            "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            str(out),
        ])
    if not keep and gen_name is not None and gen_name.exists():
        gen_name.unlink()
    return out


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    lst = out_path.parent / "concat_list.txt"
    lst.write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips),
                   encoding="utf-8")
    run_ff(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out_path)])
    return out_path


def mix_audio(voice_lines: list, pause: float, total_dur: float,
              music: Path | None, music_vol: float, out_path: Path,
              start_offset: float = 0.0) -> Path:
    """Mix per-line voice mp3s (with gaps) + optional looped background music."""
    cmd, filter_parts = [], []
    n = len(voice_lines)
    use_music = bool(music and music.exists())

    if use_music:
        cmd = ["-stream_loop", "-1", "-i", str(music)]  # input 0 = music
    cursor = start_offset
    for i, la in enumerate(voice_lines):
        delay_ms = int(cursor * 1000)
        cmd += ["-i", str(la.path)]                     # voice i = input i+1 (or i)
        idx = i + 1 if use_music else i
        filter_parts.append(f"[{idx}:a]adelay={delay_ms}:all=1[a{i}]")
        cursor += la.duration + pause

    voices_refs = "".join(f"[a{i}]" for i in range(n))
    filter_parts.append(f"{voices_refs}amix=inputs={n}:normalize=0[voice]")

    if use_music:
        fade_out_start = max(0.0, total_dur - 2.5)
        filter_parts.append(
            f"[0:a]volume={music_vol},afade=t=in:st=0:d=1.2,"
            f"afade=t=out:st={fade_out_start:.2f}:d=2.5[mus]"
        )
        filter_parts.append("[voice][mus]amix=inputs=2:normalize=0:duration=longest[aout]")
    else:
        filter_parts.append(f"[voice]apad,atrim=0:{total_dur:.3f}[aout]")

    cmd += ["-filter_complex", ";".join(filter_parts), "-t", f"{total_dur:.3f}",
            "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(out_path)]
    run_ff(cmd)
    return out_path


def finalize(concat_path: Path, subs_ass: Path, audio_mix: Path,
             total_dur: float, out_path: Path, fonts_dir: Path) -> Path:
    run_ff([
        "-i", str(concat_path),
        "-i", str(audio_mix),
        "-filter_complex",
        f"[0:v]ass={subs_ass}:fontsdir={fonts_dir}[vo]",
        "-map", "[vo]", "-map", "1:a",
        "-t", f"{total_dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p", "-r", str(FPS),
        str(out_path),
    ])
    return out_path


def compose(segments: list[dict], voice_lines: list, captions_ass: Path,
            music: Path | None, music_vol: float,
            workdir: Path, out_path: Path, keep_clips: bool = False,
            pause: float = 0.35, voice_start: float = 1.0) -> Path:
    """Full assembly. segments: [{'src': Path|None, 'dur': float}...]"""
    clips = []
    for i, seg in enumerate(segments):
        log.info("  [render] segment %d (%.1fs)", i + 1, seg["dur"])
        clip = render_clip(seg, i, workdir, keep=keep_clips)
        clips.append(clip)

    concat = concat_clips(clips, workdir / "concat.mp4")

    voice_total = sum(la.duration for la in voice_lines)
    voice_end = voice_start + voice_total + pause * (len(voice_lines) - 1)
    video_total = sum(s["dur"] for s in segments)
    total_dur = max(video_total, voice_end + 0.9)

    audio_mix = mix_audio(voice_lines, pause, total_dur, music, music_vol,
                          workdir / "audio_mix.m4a", start_offset=voice_start)

    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    finalize(concat, captions_ass, audio_mix, total_dur, out_path, fonts_dir)

    if not keep_clips:
        for f in list(workdir.glob("clip_*.mp4")) + [concat, audio_mix]:
            if f.exists():
                f.unlink()
    return out_path
