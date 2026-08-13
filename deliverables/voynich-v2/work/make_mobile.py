#!/usr/bin/env python3
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SOURCE = ROOT / "voynich-manuscript-v2.mp4"
OUTPUT = ROOT / "voynich-v2-mobile-compatible.mp4"
PASSLOG = REPO / ".cache" / "voynich-v2-render" / "mobile-pass"
VIDEO_FILTER = "scale=854:480:flags=lanczos,fps=24"
COMMON = [
    "-vf", VIDEO_FILTER, "-c:v", "libx264", "-preset", "slow",
    "-b:v", "145k", "-profile:v", "baseline", "-level", "3.0",
    "-pix_fmt", "yuv420p", "-g", "48", "-keyint_min", "24",
]

subprocess.run([
    FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE),
    *COMMON, "-pass", "1", "-passlogfile", str(PASSLOG), "-an", "-f", "null", "/dev/null",
], check=True)
subprocess.run([
    FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE),
    *COMMON, "-pass", "2", "-passlogfile", str(PASSLOG),
    "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2",
    "-movflags", "+faststart", str(OUTPUT),
], check=True)
for path in PASSLOG.parent.glob(PASSLOG.name + "*"):
    path.unlink(missing_ok=True)
print(f"{OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.1f} MiB)")
