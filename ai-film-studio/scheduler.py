#!/usr/bin/env python3
"""
scheduler.py — daily auto-runner for the film pipeline.

Reads ideas from queue.txt, generates + uploads ONE video per invocation, and
records progress in done.txt. Designed to be called by cron once a day (or any
interval); --loop turns it into a self-running daemon.

Setup:
    1. cp queue.example.txt queue.txt   (put your ideas, one per line)
    2. cron (daily 7 AM):
          crontab -e
          0 7 * * * cd /home/user/OmniRoute/ai-film-studio && \
                    /usr/bin/python3 scheduler.py --engine mpt --upload >> logs/scheduler.log 2>&1
       or run as a daemon:
          python3 scheduler.py --engine mpt --upload --loop

Usage:
    python3 scheduler.py [--engine veo|wan21|mpt] [--upload] [--privacy private]
                         [--loop] [--interval-hours 24] [--once]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue.txt"
DONE = ROOT / "done.txt"
LOGS = ROOT / "logs"


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def _next_idea() -> str | None:
    queue = _read_lines(QUEUE)
    done = set(_read_lines(DONE))
    for idea in queue:
        if idea not in done:
            return idea
    return None


def _mark_done(idea: str) -> None:
    with DONE.open("a", encoding="utf-8") as fh:
        fh.write(idea + "\n")


def run_once(args: argparse.Namespace) -> int:
    from run_film import run_one  # sibling module

    idea = _next_idea()
    if idea is None:
        print("queue empty or all ideas processed. Add ideas to queue.txt "
              "(or clear done.txt to re-run).")
        return 0
    print(f"next idea: {idea!r}")
    try:
        run_one(idea, args)
        _mark_done(idea)
        return 0
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Daily auto-runner for AI film studio")
    p.add_argument("--engine", default="mpt", choices=["veo", "wan21", "mpt"])
    p.add_argument("--upload", action="store_true")
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    p.add_argument("--voice", default="hi-IN-SwaraNeural-Female")
    p.add_argument("--num-scenes", type=int, default=6)
    p.add_argument("--ckpt-dir", default="")
    p.add_argument("--wan-task", default="t2v-1.3B")
    p.add_argument("--loop", action="store_true", help="run forever, once per interval")
    p.add_argument("--interval-hours", type=int, default=24)
    args = p.parse_args(argv)

    LOGS.mkdir(exist_ok=True)

    if not args.loop:
        return run_once(args)

    while True:
        code = run_once(args)
        print(f"cycle finished (code={code}); sleeping {args.interval_hours}h ...")
        time.sleep(args.interval_hours * 3600)
        # queue.txt is re-read from disk on every cycle, so newly added
        # ideas are picked up automatically without a restart.


if __name__ == "__main__":
    raise SystemExit(main())
