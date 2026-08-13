"""Config loading: config.yaml + .env + env overrides."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    # 1) defaults from config.yaml
    cfg_path = Path(os.environ.get("CONFIG_PATH", ROOT / "config.yaml"))
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    # 2) .env overrides
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # 3) environment variable overrides (highest priority)
    env_map = {
        "OMNIROUTE_BASE_URL": ("llm", "base_url"),
        "OMNIROUTE_API_KEY": ("llm", "api_key"),
        "OMNIROUTE_MODEL": ("llm", "model"),
        "OPENAI_API_KEY": ("llm", "api_key_override"),
        "PEXELS_API_KEY": ("media", "pexels_api_key"),
        "PIXABAY_API_KEY": ("media", "pixabay_api_key"),
        "TTS_BACKEND": ("tts", "backend"),
        "TTS_VOICE": ("tts", "voice"),
        "FFMPEG_PATH": ("ffmpeg", "path"),
        "OUTPUT_DIR": ("output", "dir"),
    }
    for env_key, (section, field) in env_map.items():
        val = os.environ.get(env_key)
        if val:
            cfg.setdefault(section, {})[field] = val

    # helpers
    cfg.setdefault("llm", {}).setdefault("use_ai", True)
    if cfg["llm"].get("api_key_override") and not cfg["llm"].get("api_key"):
        cfg["llm"]["api_key"] = cfg["llm"]["api_key_override"]
    return cfg


CONFIG = load_config()
