# ============================================================
#  MoneyPrinterTurbo integration (bonus rendering engine)
#
#  Our main pipeline (scripts/make_short.py) is self-contained.
#  This bridge lets you ALSO render the same AI script with
#  MoneyPrinterTurbo (repos/MoneyPrinterTurbo) when you want
#  its material-matching / subtitle engine instead.
#
#  Setup:
#    1. cd repos/MoneyPrinterTurbo && cp config.example.toml config.toml
#    2. Apply the overrides in mpt_overrides.toml into config.toml
#       (LLM -> OmniRoute, portrait 9:16, Hindi edge-tts voice, keys)
#    3. Start MPT:  docker compose up  (or: uv run webui)
#    4. Run the bridge:
#       ../yt-shorts-automation/.venv/bin/python bridge_mpt.py \
#           --topic "मिस्र के पिरामिडों का रहस्य"
#
#  The bridge generates the script with OUR AI/template writer, then
#  submits it to MPT's API:  POST /api/v1/videos
# ============================================================
import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import CONFIG  # noqa: E402
from src.llm import LLMClient  # noqa: E402
from src.script_writer import ScriptWriter  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Bridge: our AI script -> MoneyPrinterTurbo render")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--api", default="http://127.0.0.1:8080/api/v1",
                    help="MPT API base (see MPT config listen_port)")
    args = ap.parse_args()

    llm = LLMClient(CONFIG.get("llm", {}))
    writer = ScriptWriter(CONFIG, llm)
    topic = writer.pick_topic(args.topic)
    script = writer.write_script(topic)
    print(f"📝 Script ready for: {topic}")

    payload = {
        "video_subject": topic,
        "video_script": " ".join([script["hook"]] + script["lines"] + [script["cta"]]),
        "video_terms": script["tags"][:5],
        "video_aspect": "竖屏 9:16（抖音/SHORTS）",
        "voice_name": CONFIG["tts"].get("voice", "hi-IN-MadhurNeural"),
        "subtitle_enabled": True,
    }
    print(f"🚀 POST {args.api}/videos")
    resp = requests.post(f"{args.api}/videos", json=payload, timeout=30)
    resp.raise_for_status()
    task = resp.json()
    print("✅ Task created:", task.get("task_id") or task)
    print("   Check progress: GET", f"{args.api}/tasks/{{task_id}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
