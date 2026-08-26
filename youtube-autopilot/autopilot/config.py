"""Configuration loader: config.yaml + .env + path helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # youtube-autopilot/
ASSETS_DIR = ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
RUNS_DIR = ROOT / "runs"
STAGING_DIR = ASSETS_DIR / "staging"
CONFIG_PATH = ROOT / "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # env overrides (AP_ prefix, "__" separator: AP_IMAGES__PROVIDER=sandbox)
    for key, val in os.environ.items():
        if key.startswith("AP_") and "__" in key:
            parts = key[3:].lower().split("__")
            node = cfg
            for p in parts[:-1]:
                node = node.setdefault(p, {})
            node[parts[-1]] = val
    return cfg


def get(cfg: dict, dotted: str, default: Any = None) -> Any:
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def ffmpeg_bin() -> str:
    env = os.environ.get("FFMPEG_PATH")
    if env and os.path.exists(env):
        return env
    import shutil

    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("ffmpeg nahi mila — `pip install imageio-ffmpeg` karein ya FFMPEG_PATH set karein")


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def staging_dir(run_id: str) -> Path:
    return STAGING_DIR / run_id
