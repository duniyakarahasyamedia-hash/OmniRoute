#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
VISUALS = ROOT / "visuals"
AUDIO = ROOT / "audio"
WORK = ROOT / "work"
CACHE = REPO / ".cache" / "voynich-v2-render"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 24
WIDTH, HEIGHT = 1920, 1080
MASTER_DURATION = 457.42
CHAPTER_FIRST = {1, 11, 20, 30, 39, 48, 58}
CHAPTER_LAST = {10, 19, 29, 38, 47, 57, 66}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def duration(path: Path) -> float:
    result = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read duration: {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def scene_filter(index: int, scene: dict[str, object]) -> str:
    image_name = str(scene["image"])
    is_card = image_name.startswith("3") or image_name.startswith("26-") or image_name.startswith("27-")
    frames = max(1, math.ceil(float(scene["duration"]) * FPS))
    if is_card:
        motion = (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#050a11,"
            "zoompan=z='min(zoom+0.000025,1.012)':x='iw/2-iw/zoom/2':"
            "y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=24"
        )
    else:
        mode = index % 4
        prefix = "scale=2112:1188:force_original_aspect_ratio=increase,crop=2112:1188,"
        if mode == 0:
            zoom = "z='min(zoom+0.00010,1.10)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
        elif mode == 1:
            zoom = "z='if(eq(on,0),1.10,max(1.0,zoom-0.00010))':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
        elif mode == 2:
            zoom = f"z='1.075':x='(iw-iw/zoom)*on/{frames}':y='ih/2-ih/zoom/2'"
        else:
            zoom = f"z='1.075':x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-ih/zoom/2'"
        motion = prefix + f"zoompan={zoom}:d=1:s=1920x1080:fps=24"
    effects = [motion, "format=yuv420p"]
    if index in CHAPTER_FIRST:
        effects.append("fade=t=in:st=0:d=0.30")
    if index in CHAPTER_LAST:
        start = max(0.0, float(scene["duration"]) - 0.30)
        effects.append(f"fade=t=out:st={start:.3f}:d=0.30")
    return ",".join(effects)


def render_scene(index: int, scene: dict[str, object]) -> Path:
    source = VISUALS / str(scene["image"])
    output = CACHE / f"scene-{index:02}.mp4"
    target = float(scene["duration"])
    if output.exists() and abs(duration(output) - target) < 0.07:
        print(f"Reuse {index:02}/66  {source.name}", flush=True)
        return output
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(source),
        "-t", f"{target:.4f}", "-vf", scene_filter(index, scene), "-r", str(FPS), "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(output),
    ])
    print(f"Render {index:02}/66  {source.name}  {target:.2f}s", flush=True)
    return output


def render_audio() -> Path:
    voice = AUDIO / "narration-master.m4a"
    output = CACHE / "audio-master.m4a"
    if output.exists() and abs(duration(output) - MASTER_DURATION) < 0.1:
        print("Reuse cinematic audio mix", flush=True)
        return output

    left = "0.0065*sin(2*PI*55*t)+0.0035*sin(2*PI*82.41*t)+0.002*sin(2*PI*110*t)"
    right = "0.0065*sin(2*PI*55.3*t)+0.0035*sin(2*PI*82.7*t)+0.002*sin(2*PI*110.4*t)"
    bed = f"aevalsrc={left}|{right}:s=48000:d={MASTER_DURATION}"
    texture = f"anoisesrc=color=pink:amplitude=0.004:s=48000:d={MASTER_DURATION}"
    impact_starts = [54.96, 112.99, 184.98, 250.18, 316.88, 388.95]
    terms = [f"if(between(t,{t:.2f},{t+1.4:.2f}),0.035*exp(-3.2*(t-{t:.2f}))*sin(2*PI*48*t),0)" for t in impact_starts]
    # Commas inside aevalsrc functions must be escaped from the lavfi parser.
    impact_expression = "+".join(terms).replace(",", r"\,")
    impacts = f"aevalsrc={impact_expression}:s=48000:d={MASTER_DURATION}"
    graph = (
        "[1:a]lowpass=f=520,aecho=0.8:0.65:35|70:0.18|0.10,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={MASTER_DURATION-5:.2f}:d=5[bed];"
        "[2:a]highpass=f=120,lowpass=f=1500,volume=0.42[texture];"
        "[3:a]lowpass=f=180,volume=1.0[impacts];"
        "[0:a][bed][texture][impacts]amix=inputs=4:duration=first:normalize=0,alimiter=limit=0.92[a]"
    )
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(voice),
        "-f", "lavfi", "-i", bed,
        "-f", "lavfi", "-i", texture,
        "-f", "lavfi", "-i", impacts,
        "-filter_complex", graph, "-map", "[a]",
        "-t", f"{MASTER_DURATION:.2f}", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(output),
    ])
    print("Rendered cinematic ambient mix + chapter impacts", flush=True)
    return output


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((WORK / "scene-plan.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, os.cpu_count() or 2)) as pool:
        futures = [pool.submit(render_scene, i, scene) for i, scene in enumerate(scenes, 1)]
        files = [future.result() for future in futures]

    concat = CACHE / "scenes.txt"
    concat.write_text("".join(f"file '{file}'\n" for file in files))
    visual = CACHE / "visual-base.mp4"
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visual)])
    print(f"Visual base: {duration(visual):.2f}s", flush=True)

    audio = render_audio()
    output = ROOT / "voynich-manuscript-v2.mp4"
    subtitle = (WORK / "titles-and-captions.ass").as_posix().replace("'", r"'\\''")
    video_filter = (
        f"subtitles='{subtitle}':fontsdir=/usr/share/fonts/truetype/dejavu,"
        f"fade=t=in:st=0:d=0.55,fade=t=out:st={MASTER_DURATION-1.2:.2f}:d=1.1"
    )
    passlog = CACHE / "master-pass"
    video_options = [
        "-vf", video_filter, "-map", "0:v:0", "-c:v", "libx264", "-preset", "medium",
        "-b:v", "1100k", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-g", str(FPS * 2),
    ]
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(visual),
        *video_options, "-pass", "1", "-passlogfile", str(passlog), "-an", "-f", "null", "/dev/null",
    ])
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(visual), "-i", str(audio),
        *video_options, "-map", "1:a:0", "-pass", "2", "-passlogfile", str(passlog),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(output),
    ])
    for pass_file in CACHE.glob(passlog.name + "*"):
        pass_file.unlink(missing_ok=True)
    print(f"FINAL {output}  {duration(output):.2f}s  {output.stat().st_size/1024/1024:.1f} MiB")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"FFmpeg failed: {exc.returncode}", file=sys.stderr)
        raise
