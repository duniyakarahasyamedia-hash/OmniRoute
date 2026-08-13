#!/usr/bin/env python3
"""Make one YouTube Short end-to-end.

Usage:
  python scripts/make_short.py --topic "अंटार्कटिका का रहस्य" [--no-upload] [--draft]
                               [--tts edge|gtts|silent] [--keep-clips] [--log DEBUG]

Examples:
  # Full run, uploads as private draft (default privacy from config)
  python scripts/make_short.py

  # One specific topic, no upload (just builds the video)
  python scripts/make_short.py --topic "मिस्र के पिरामिडों का रहस्य" --no-upload

  # Test run without network (silent voice, gradient backgrounds)
  python scripts/make_short.py --tts silent --no-upload
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import cli_logging, run_short  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="OmniRoute YouTube Shorts pipeline")
    ap.add_argument("--topic", default=None, help="Explicit topic (default: AI/template pick)")
    ap.add_argument("--no-upload", action="store_true", help="Skip YouTube upload")
    ap.add_argument("--public", action="store_true", help="Upload as public (else config privacy)")
    ap.add_argument("--tts", choices=["edge", "gtts", "openai", "silent"], default=None,
                    help="Override TTS backend")
    ap.add_argument("--keep-clips", action="store_true", help="Keep intermediate clips")
    ap.add_argument("--log", default="INFO", help="Log level (DEBUG/INFO/WARNING)")
    args = ap.parse_args()

    cli_logging(args.log)
    report = run_short(
        topic=args.topic,
        do_upload=not args.no_upload,
        privacy="public" if args.public else None,
        keep_clips=args.keep_clips,
        tts_override=args.tts,
    )
    print("\n✅ Short ready:")
    print(f"   📹 {report['video']}")
    print(f"   ⏱  {report['duration_s']}s | {report['streams']['w']}x{report['streams']['h']}")
    print(f"   📝 {report['metadata']['title']}")
    if report.get("upload", {}).get("url"):
        print(f"   🚀 {report['upload']['url']}")
    elif report.get("upload", {}).get("skipped"):
        print("   🚀 upload skipped (--no-upload)")
    else:
        print("   🚀 draft saved to output/upload_pending.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
