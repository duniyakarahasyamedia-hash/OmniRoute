"""Shared helpers: ffmpeg binary resolution, media probing."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


def ffmpeg_bin() -> str:
    env = os.environ.get("FFMPEG_PATH")
    if env:
        return env
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


class FFmpegError(RuntimeError):
    pass


def run_ff(args: list[str], **kw) -> subprocess.CompletedProcess:
    """Run ffmpeg, raising FFmpegError with stderr tail on failure."""
    cmd = [ffmpeg_bin(), "-hide_banner", "-y"] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
        raise FFmpegError("ffmpeg failed:\n" + "\n".join(tail))
    return proc


def probe_duration(path) -> float:
    """Duration in seconds via ffmpeg stderr parse."""
    try:
        proc = run_ff(["-i", str(path), "-f", "null", "-"])
    except FFmpegError as exc:
        # `-f null -` can still succeed; if not, fall back to `-i` parse
        try:
            proc = run_ff(["-i", str(path)])
        except FFmpegError:
            log_probe_error(exc)
            return 0.0
    err = proc.stderr or ""
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
    if m:
        h, mi, s = m.groups()
        return int(h) * 3600 + int(mi) * 60 + float(s)
    return 0.0


def probe_streams(path) -> dict:
    """{'video': bool, 'audio': bool, 'w': int, 'h': int}"""
    out = {"video": False, "audio": False, "w": 0, "h": 0}
    try:
        proc = run_ff(["-i", str(path), "-f", "null", "-"])
    except FFmpegError:
        return out
    err = proc.stderr or ""
    out["video"] = re.search(r"Video:", err) is not None
    out["audio"] = re.search(r"Audio:", err) is not None
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        out["w"], out["h"] = int(m.group(1)), int(m.group(2))
    return out


def log_probe_error(exc: Exception) -> None:
    import logging

    logging.getLogger("omnishorts.utils").debug("probe failed: %s", exc)
