#!/usr/bin/env python3
"""
run_film.py — ONE-COMMAND orchestrator for the whole AI film workflow.

    idea -> shot-list -> clips -> Hindi voiceover -> final.mp4 -> YouTube

Engines:
    veo    cinematic clips via Google Veo 3.1 API (paid API billing needed)
    wan21  cinematic clips via local open-source Wan2.1 (your GPU)
    mpt    faceless stock-footage video via MoneyPrinterTurbo (₹0)

Examples:
    # one cinematic film
    python3 run_film.py --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है"

    # faceless (free) video
    python3 run_film.py --idea "भारत के 5 रहस्यमयी स्थान" --engine mpt

    # batch of videos from a list file
    python3 run_film.py --batch ideas.txt --engine mpt --upload

    # cinematic + upload to YouTube (private by default)
    python3 run_film.py --idea "..." --upload --privacy unlisted
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
STORAGE = ROOT / "storage"
MPT_DIR = ROOT.parent / "repos" / "MoneyPrinterTurbo"
LOG_FILE = ROOT / "logs" / "runs.log"

DEFAULT_VOICE = "hi-IN-SwaraNeural-Female"  # MPT-style (with -Female/-Male)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{_dt.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _sh(cmd: list[str], cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    print("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run(
        [str(c) for c in cmd], cwd=str(cwd) if cwd else None,
        text=True, capture_output=capture,
    )


def _short_voice(voice: str) -> str:
    """'hi-IN-SwaraNeural-Female' -> 'hi-IN-SwaraNeural' (edge-tts style)."""
    return re.sub(r"-(Female|Male)$", "", voice)


_out_counter = 0


def _new_out_dir() -> Path:
    global _out_counter
    _out_counter += 1
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return STORAGE / f"film-{stamp}-{_out_counter:02d}"


def _mpt_python() -> list[str]:
    venv = MPT_DIR / ".venv" / "bin" / "python"
    if venv.exists():
        return [str(venv)]
    return ["uv", "run", "python"]


def _find_mpt_video(stdout: str) -> tuple[Path | None, Path | None]:
    """Parse MPT CLI's trailing JSON result line -> (final video, subtitle srt)."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = data.get("result") or {}
        vids = result.get("videos") or []
        if not vids:
            continue
        srt = result.get("subtitle_path") or ""
        return Path(vids[0]), (Path(srt) if srt else None)
    return None, None


# --------------------------------------------------------------------------- #
# engines
# --------------------------------------------------------------------------- #
def _engine_veo(idea: str, args: argparse.Namespace, out_dir: Path) -> Path:
    cmd = [
        sys.executable, str(SCRIPTS / "veo_film_pipeline.py"),
        "--idea", idea,
        "--num-scenes", str(args.num_scenes),
        "--aspect", args.aspect,
        "--voice", _short_voice(args.voice),
        "--duration", str(args.duration),
        "--out-dir", str(out_dir),
    ]
    if args.skip_video:
        cmd.append("--skip-video")
    if args.no_narration:
        cmd.append("--no-narration")
    r = _sh(cmd)
    if r.returncode != 0:
        raise RuntimeError("Veo pipeline failed")
    return out_dir / "final.mp4"


def _engine_wan21(idea: str, args: argparse.Namespace, out_dir: Path) -> Path:
    if not getattr(args, "ckpt_dir", ""):
        raise SystemExit("--ckpt-dir is required for --engine wan21")
    # 1) shot-list only
    _sh([
        sys.executable, str(SCRIPTS / "veo_film_pipeline.py"),
        "--idea", idea,
        "--num-scenes", str(args.num_scenes),
        "--aspect", args.aspect,
        "--out-dir", str(out_dir),
        "--skip-video", "--no-narration", "--no-assemble",
    ])
    # 2) local Wan2.1 clips + narration + assembly
    _sh([
        sys.executable, str(SCRIPTS / "wan21_film_pipeline.py"),
        "--story", str(out_dir / "story.json"),
        "--task", args.wan_task,
        "--ckpt-dir", args.ckpt_dir,
        "--aspect", args.aspect,
        "--voice", _short_voice(args.voice),
        "--out-dir", str(out_dir),
    ])
    return out_dir / "final.mp4"


def _engine_mpt(idea: str, args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    cmd = _mpt_python() + [
        "cli.py",
        "--video-subject", idea,
        "--video-language", "hi-IN",
        "--voice-name", args.voice,
        "--video-aspect", args.aspect,
        "--font-name", "Hind-Bold.ttf",
        "--subtitle-enabled",
        "--bgm-type", "random",
    ]
    r = _sh(cmd, cwd=MPT_DIR, capture=True)
    if r.returncode != 0:
        _log("MPT failed:\n" + (r.stdout or "")[-2000:] + "\n" + (r.stderr or "")[-2000:])
        raise RuntimeError("MoneyPrinterTurbo pipeline failed")
    video, srt = _find_mpt_video(r.stdout or "")
    if video is None:
        _log("could not parse MPT result video path")
    return video, srt


# --------------------------------------------------------------------------- #
# upload
# --------------------------------------------------------------------------- #
def _upload(final: Path, story: Path | None, srt: Path | None, args: argparse.Namespace) -> bool:
    if not final or not final.exists():
        _log(f"upload skipped: {final} missing")
        return False
    cmd = [
        sys.executable, str(SCRIPTS / "upload_youtube.py"),
        str(final), "--privacy", args.privacy,
    ]
    if story and story.exists():
        cmd += ["--metadata", str(story)]
    else:
        cmd += ["--title", final.stem]
    if srt and srt.exists():
        cmd += ["--captions", str(srt)]
    r = _sh(cmd)
    return r.returncode == 0


# --------------------------------------------------------------------------- #
# run one / batch
# --------------------------------------------------------------------------- #
def run_one(idea: str, args: argparse.Namespace) -> dict:
    _log(f"START idea={idea!r} engine={args.engine}")
    out_dir = _new_out_dir()
    story = srt = None

    if args.engine == "veo":
        final = _engine_veo(idea, args, out_dir)
        story, srt = out_dir / "story.json", out_dir / "subtitles.srt"
    elif args.engine == "wan21":
        final = _engine_wan21(idea, args, out_dir)
        story, srt = out_dir / "story.json", out_dir / "subtitles.srt"
    elif args.engine == "mpt":
        final, srt = _engine_mpt(idea, args)
    else:
        raise SystemExit(f"unknown engine: {args.engine}")

    uploaded = False
    if args.upload:
        uploaded = _upload(final, story, srt, args)

    _log(f"DONE final={final} uploaded={uploaded}")
    return {"final": final, "story": story, "srt": srt, "uploaded": uploaded}


def run_batch(args: argparse.Namespace) -> int:
    ideas = [
        ln.strip() for ln in Path(args.batch).read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not ideas:
        print(f"no ideas found in {args.batch}")
        return 2
    ok = 0
    for i, idea in enumerate(ideas, 1):
        _log(f"BATCH [{i}/{len(ideas)}]")
        try:
            run_one(idea, args)
            ok += 1
        except Exception as exc:  # keep going on failure
            _log(f"FAILED idea={idea!r}: {exc}")
        if args.sleep_between > 0 and i < len(ideas):
            _log(f"sleeping {args.sleep_between}s ...")
            time.sleep(args.sleep_between)
    _log(f"BATCH COMPLETE: {ok}/{len(ideas)} succeeded")
    return 0 if ok == len(ideas) else 1


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="One-command AI film workflow")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--idea", default="", help="single story idea")
    src.add_argument("--batch", default="", help="text file with one idea per line")

    p.add_argument("--engine", default="veo", choices=["veo", "wan21", "mpt"])
    p.add_argument("--upload", action="store_true", help="upload to YouTube after")
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    p.add_argument("--voice", default=DEFAULT_VOICE, help="MPT-style, e.g. hi-IN-SwaraNeural-Female")
    p.add_argument("--num-scenes", type=int, default=6)
    p.add_argument("--duration", type=int, default=8, help="Veo seconds per scene")
    p.add_argument("--skip-video", action="store_true", help="(veo) shot-list only, no Veo calls")
    p.add_argument("--no-narration", action="store_true", help="(veo) skip voiceover")
    p.add_argument("--wan-task", default="t2v-1.3B", choices=["t2v-1.3B", "t2v-14B", "i2v-14B"])
    p.add_argument("--ckpt-dir", default="", help="(wan21) path to Wan2.1 checkpoint dir")
    p.add_argument("--sleep-between", type=int, default=0, help="(batch) seconds between videos")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.batch:
        return run_batch(args)
    try:
        run_one(args.idea, args)
        return 0
    except Exception as exc:
        _log(f"FAILED idea={args.idea!r}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
