#!/usr/bin/env python3
"""
make_story.py — build a story.json from plain text files (no JSON editing).

Use this when you have made (or will make) your own Veo clips in the Gemini app
and want to assemble them into a film with Hindi narration + subtitles — without
needing the Gemini API key at all.

Usage:
    # script.txt  : ek line = ek scene ki Hindi narration
    # prompts.txt : (optional) ek line = ek scene ka Veo prompt (English).
    #               Agar prompts.txt nahi diya to narration hi prompt ban jayega.

    python3 make_story.py --script script.txt --prompts prompts.txt \
        --title "मेरी फिल्म" --out storage/myfilm/story.json

Then put your Veo clips in storage/myfilm/shots/scene_01.mp4 ... and run:
    .venv/bin/python scripts/veo_film_pipeline.py \
        --out-dir storage/myfilm --skip-video
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _lines(path: str) -> list[str]:
    if not path:
        return []
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build story.json from text files")
    p.add_argument("--script", required=True, help="txt: one Hindi narration line per scene")
    p.add_argument("--prompts", default="", help="txt: one Veo prompt per scene (optional)")
    p.add_argument("--title", default="AI लघु फिल्म", help="film title")
    p.add_argument("--description", default="", help="YouTube description")
    p.add_argument("--tags", default="ai,shortfilm,hindi,cinematic", help="comma tags")
    p.add_argument("--style", default="cinematic, dramatic lighting, film grain")
    p.add_argument("--out", required=True, help="path to write story.json")
    args = p.parse_args(argv)

    narration = _lines(args.script)
    prompts = _lines(args.prompts)
    if not narration:
        print("ERROR: script.txt empty")
        return 2

    scenes = []
    for i, nar in enumerate(narration, 1):
        scenes.append({
            "scene": i,
            "shot": "SHOT",
            "veo_prompt": prompts[i - 1] if i - 1 < len(prompts) else nar,
            "narration_hi": nar,
        })

    story = {
        "title": args.title,
        "logline": narration[0],
        "style": args.style,
        "scenes": scenes,
        "metadata": {
            "title": args.title,
            "description": args.description or narration[0],
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"story.json written: {out}  ({len(scenes)} scenes)")
    print(f"Next: put clips at {out.parent / 'shots' / 'scene_01.mp4'} ... and run:")
    print(f"  .venv/bin/python scripts/veo_film_pipeline.py --out-dir {out.parent} --skip-video")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
