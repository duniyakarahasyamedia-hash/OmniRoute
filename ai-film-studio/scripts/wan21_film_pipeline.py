#!/usr/bin/env python3
"""
Wan2.1 Film Pipeline — open-source (no per-video API cost) cinematic clips.

Uses the local repos/Wan2.1 to turn each scene's `veo_prompt` from story.json
into a video clip, then reuses the same narration + ffmpeg assembly as the Veo
pipeline. Requires a GPU (T2V-1.3B needs ~8 GB VRAM; 14B needs multi-GPU).

One-time Wan2.1 setup:
    cd repos/Wan2.1
    python -m pip install -r requirements.txt
    # download checkpoints (see repos/Wan2.1/README.md "Model Download")
    # e.g. Wan2.1-T2V-1.3B -> repos/Wan2.1/Wan2.1-T2V-1.3B

Usage:
    # 1. build a shot-list only (free, Gemini Flash) if you don't have one yet:
    python3 veo_film_pipeline.py --idea "..." --skip-video --no-narration
    # 2. generate clips locally with Wan2.1:
    python3 wan21_film_pipeline.py --story storage/film-xxxxxxxx/story.json \
        --task t2v-1.3B --ckpt-dir repos/Wan2.1/Wan2.1-T2V-1.3B
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
WAN_DIR = REPO_ROOT / "repos" / "Wan2.1"

# Wan2.1 generate.py size strings -> ffmpeg/Veo aspect used by the assembler
SIZE_BY_ASPECT = {"9:16": "720*1280", "16:9": "1280*720"}


def _run(cmd: list[str]) -> None:
    print("   $ " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(WAN_DIR))


def generate_clips(story: dict, task: str, ckpt_dir: str, aspect: str, out_dir: Path) -> list[Path]:
    size = SIZE_BY_ASPECT.get(aspect, "720*1280")
    shots_dir = out_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for sc in story.get("scenes", []):
        out = shots_dir / f"scene_{sc['scene']:02d}.mp4"
        if out.exists():
            print(f"scene {sc['scene']}: exists, skipping")
            paths.append(out)
            continue
        print(f"scene {sc['scene']}: {sc['shot']}")
        cmd = [
            sys.executable, "generate.py",
            "--task", task,
            "--size", size,
            "--ckpt_dir", ckpt_dir,
            "--prompt", sc["veo_prompt"],
            "--save_file", str(out.resolve()),
            "--t5_cpu",
            "--offload_model", "True",
        ]
        _run(cmd)
        if not out.exists():
            raise RuntimeError(f"Wan2.1 did not produce {out}")
        paths.append(out)
    return paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Wan2.1 local clip generation + assembly")
    p.add_argument("--story", required=True, help="path to story.json")
    p.add_argument("--task", default="t2v-1.3B",
                   choices=["t2v-1.3B", "t2v-14B", "i2v-14B", "t2i-14B"])
    p.add_argument("--ckpt-dir", required=True, help="path to Wan2.1 checkpoint dir")
    p.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    p.add_argument("--voice", default="hi-IN-SwaraNeural")
    p.add_argument("--out-dir", default="", help="defaults to story.json's dir")
    p.add_argument("--mpt-dir", default=str(REPO_ROOT / "repos" / "MoneyPrinterTurbo"))
    args = p.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import veo_film_pipeline as veo

    story_path = Path(args.story)
    story = json.loads(story_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir) if args.out_dir else story_path.parent

    print(f"[1/3] Generating clips via Wan2.1 ({args.task}) ...")
    clips = generate_clips(story, args.task, args.ckpt_dir, args.aspect, out_dir)

    print(f"[2/3] Hindi narration + voiceover ({args.voice}) ...")
    audio_paths = veo.build_narration(story["scenes"], args.voice, out_dir / "audio")
    voiceover = veo._concat_audio(audio_paths, out_dir / "audio" / "voiceover.m4a")
    veo.build_srt(story["scenes"], audio_paths, out_dir / "subtitles.srt")

    print("[3/3] Assembling final.mp4 ...")
    final = veo.assemble_final(
        clips, voiceover, args.aspect, out_dir / "final.mp4", out_dir / "work"
    )
    print(f"      DONE: {final}")
    mpt_cmds = veo.write_mpt_commands(
        story, out_dir, args.aspect, Path(args.mpt_dir), args.voice
    )
    print(f"MPT re-render command: {mpt_cmds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
