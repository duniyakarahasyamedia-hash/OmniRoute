#!/usr/bin/env python3
"""Generate a subtle ambient background-music loop with ffmpeg (no downloads).
Drops assets/music/ambient.mp3. Replace with your own royalty-free track anytime."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import run_ff  # noqa: E402


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "assets" / "music" / "ambient.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    # soft pad: two detuned sines + slow tremolo + lowpass, 30s loop
    run_ff([
        "-f", "lavfi",
        "-i", "sine=frequency=110:sample_rate=44100:duration=30",
        "-f", "lavfi",
        "-i", "sine=frequency=164.81:sample_rate=44100:duration=30",
        "-f", "lavfi",
        "-i", "sine=frequency=220:sample_rate=44100:duration=30",
        "-filter_complex",
        "[0:a]volume=0.5[a0];[1:a]volume=0.3[a1];[2:a]volume=0.18[a2];"
        "[a0][a1][a2]amix=inputs=3:normalize=0,"
        "tremolo=f=0.15:d=0.6,lowpass=f=900,"
        "afade=t=in:st=0:d=3,afade=t=out:st=27:d=3,"
        "volume=0.8,aloop=loop=-1:size=2e+09[aout]",
        "-map", "[aout]", "-t", "30", "-c:a", "libmp3lame", "-q:a", "6",
        str(out),
    ])
    print(f"✅ ambient music → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
