#!/usr/bin/env python3
"""Run the pipeline N times — once, or on a schedule.

Usage:
  python scripts/run_all.py --count 3                    # make 3 shorts now
  python scripts/run_all.py --every 3600 --count 10      # every hour, 10 total
  python scripts/run_all.py --once --no-upload           # single test run
  python scripts/run_all.py --forever --every 86400      # daily forever (Ctrl+C to stop)

Alternative schedulers:
  - cron:  0 10 * * * cd /path/yt-shorts-automation && .venv/bin/python scripts/make_short.py >> output/cron.log 2>&1
  - n8n:   import n8n/workflow_omniroute_shorts.json (cron + executeCommand)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import cli_logging, run_short  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk / scheduled shorts runner")
    ap.add_argument("--count", type=int, default=1, help="How many shorts to make")
    ap.add_argument("--every", type=int, default=0,
                    help="Delay between runs in seconds (0 = run all now)")
    ap.add_argument("--forever", action="store_true", help="Run until interrupted")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--log", default="INFO")
    args = ap.parse_args()

    cli_logging(args.log)
    made = 0
    while True:
        print(f"\n{'='*60}\n▶ Run #{made + 1} — {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")
        try:
            report = run_short(do_upload=not args.no_upload)
            made += 1
            print(f"✅ #{made}: {report['video']}")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Run #{made + 1} failed: {exc}")
        if args.forever:
            time.sleep(args.every or 3600)
        elif made >= args.count:
            break
        elif args.every:
            print(f"… sleeping {args.every}s")
            time.sleep(args.every)
    return 0


if __name__ == "__main__":
    sys.exit(main())
