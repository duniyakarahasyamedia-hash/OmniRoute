"""Demo run — sandbox providers se poori pipeline test karo (koi API key nahi chahiye).

Use: ./.venv/bin/python scripts/stage_and_run_demo.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autopilot import config, pipeline  # noqa: E402

TOPIC = "भुतिया गुड़िया (demo)"
STORY_FILE = "demo/story_demo.json"
MODE = "both"

if __name__ == "__main__":
    cfg = config.load_config()
    run_id = pipeline.new_run_id(TOPIC, MODE)
    stage = config.staging_dir(run_id)
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree("assets/staging/demo", stage)
    print(f"Staging -> {stage}")
    manifest = pipeline.create_run(cfg, topic=TOPIC, mode=MODE,
                                   story_file=STORY_FILE, run_id=run_id)
    print(f"\n✅ Demo run complete: {manifest['id']}")
    for k, v in manifest.get("videos", {}).items():
        p = Path(v)
        print(f"   {k}: {v}  ({p.stat().st_size/1e6:.1f} MB)" if p.exists() else f"   {k}: MISSING")
