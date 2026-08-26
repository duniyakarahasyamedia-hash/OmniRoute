"""CLI — sab kuch yahin se control hota hai.

Examples:
  python -m autopilot make --topic "bhutiya gudiya"          # full + short banao
  python -m autopilot make --mode short --topic "siren head" # sirf short
  python -m autopilot make --story story.json                # apni story se
  python -m autopilot render --run-id RUN_ID                 # sirf render (dubara)
  python -m autopilot list
  python -m autopilot auth                                   # YouTube login
  python -m autopilot dashboard                              # review + upload UI
  python -m autopilot upload --run-id RUN_ID                 # approved run upload
  python -m autopilot daily                                  # har din auto video
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from . import config, pipeline

TOPIC_IDEAS = [
    "भुतिया गुड़िया (haunted doll)",
    "सायरन हेड (siren head)",
    "भूतिया अस्पताल (haunted hospital)",
    "जादूगर मिस्टर मीट (Mr Meat)",
    "जॉम्बी का हमला (zombie attack)",
    "पुराना घर बिकाऊ (old house sale)",
    "भूतिया स्कूल बस (haunted school bus)",
    "डरावना बंजी कॉर्ड (scary bungee)",
    "भूतिया झूला (haunted swing)",
    "डरावनी ग्रैनी (scary granny)",
    "भूतिया जंगल (haunted jungle)",
    "सपने में भुत (nightmare bhoot)",
]


def cmd_make(args) -> None:
    cfg = config.load_config()
    if args.topic and not args.no_topic_check:
        confirm = input(f"Topic: '{args.topic}' — isi pe story banau? (Enter=haan / n=nahi): ")
        if confirm.strip().lower() == "n":
            args.topic = random.choice(TOPIC_IDEAS)
            print(f"Naya topic: {args.topic}")
    manifest = pipeline.create_run(cfg, topic=args.topic, mode=args.mode, story_file=args.story)
    print(f"\n✅ Run ready: {manifest['id']}")
    for k, v in manifest.get("videos", {}).items():
        print(f"   {k}: {v}")
    print("\nReview + upload ke liye:  python -m autopilot dashboard")


def cmd_render(args) -> None:
    cfg = config.load_config()
    m = pipeline.load_manifest(args.run_id)
    from .render import render_full

    for mode in ("full", "short"):
        if m["videos"].get(mode) and Path(m["videos"][mode]).exists():
            print(f"Render kar raha hoon ({mode})...")
            story = json.loads((config.run_dir(args.run_id) / "story" / "story.json").read_text())
            dirs = pipeline.make_dirs(args.run_id)
            vf = pipeline._load_voice_from_disk(story, dirs)
            out = render_full(cfg, story, dirs, vf, mode)
            m["videos"][mode] = str(out)
            pipeline.save_manifest(m)
            print(f"   done: {out}")


def cmd_auth(args) -> None:
    from . import upload

    upload.oauth_authorize()


def cmd_upload(args) -> None:
    cfg = config.load_config()
    results = pipeline.upload_run(cfg, args.run_id, privacy=args.privacy)
    print(results)


def cmd_list(args) -> None:
    runs = pipeline.list_runs()
    if not runs:
        print("Koi run nahi. Pehle `python -m autopilot make` chalayein.")
        return
    for r in runs:
        vids = ", ".join(r.get("videos", {}).keys()) or "—"
        print(f"{r['id']}  [{r['status']}]  mode={r['mode']}  videos={vids}")


def cmd_dashboard(args) -> None:
    from . import dashboard

    cfg = config.load_config()
    dashboard.main(cfg)


def cmd_daily(args) -> None:
    """Daily auto-pilot: har N ghante me ek nayi video banao (review dashboard pe daal do)."""
    cfg = config.load_config()
    interval = args.interval * 3600
    used = []
    print(f"🔄 Daily autopilot ON — har {args.interval}h me nayi video banega. Ctrl+C se band.")
    while True:
        pool = [t for t in TOPIC_IDEAS if t not in used[-10:]]
        topic = random.choice(pool)
        used.append(topic)
        try:
            m = pipeline.create_run(cfg, topic=topic, mode=args.mode)
            print(f"✅ {m['id']} ready — dashboard pe approve karein")
        except Exception as e:  # noqa: BLE001
            print(f"❌ Fail: {e}")
        time.sleep(interval)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="autopilot", description="YouTube Autopilot — AI video pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("make", help="Nayi video banao")
    m.add_argument("--topic", default="", help="Story topic (Hindi/English)")
    m.add_argument("--mode", choices=["full", "short", "both"], default="both")
    m.add_argument("--story", default=None, help="pehle se likhi story.json file")
    m.add_argument("--no-topic-check", action="store_true", help="confirm prompt skip karo")
    m.set_defaults(fn=cmd_make)

    r = sub.add_parser("render", help="Run ko dubara render karo")
    r.add_argument("--run-id", required=True)
    r.set_defaults(fn=cmd_render)

    a = sub.add_parser("auth", help="YouTube OAuth login")
    a.set_defaults(fn=cmd_auth)

    u = sub.add_parser("upload", help="Approved run upload karo")
    u.add_argument("--run-id", required=True)
    u.add_argument("--privacy", default=None, choices=["private", "unlisted", "public"])
    u.set_defaults(fn=cmd_upload)

    l = sub.add_parser("list", help="Saare runs dikhao")
    l.set_defaults(fn=cmd_list)

    d = sub.add_parser("dashboard", help="Review/approve dashboard kholo")
    d.set_defaults(fn=cmd_dashboard)

    dl = sub.add_parser("daily", help="Har kuch ghante me auto video banao")
    dl.add_argument("--interval", type=float, default=12.0, help="ghante (default 12)")
    dl.add_argument("--mode", choices=["full", "short", "both"], default="both")
    dl.set_defaults(fn=cmd_daily)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
