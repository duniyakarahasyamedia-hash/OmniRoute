"""Voiceover — Hindi narration TTS (elevenlabs | openai | edge | sandbox)."""
from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import config

_DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def probe_duration(path: str | Path) -> float:
    """ffmpeg se audio/video duration nikaalo (seconds)."""
    cmd = [config.ffmpeg_bin(), "-hide_banner", "-i", str(path), "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    m = _DUR_RE.search(proc.stderr)
    if not m:
        raise RuntimeError(f"Duration nahi mili: {path}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def _staged_voice(cfg: dict, run_dirs: dict, name: str) -> Path:
    stage = config.staging_dir(run_dirs["id"]) / "voice"
    src = stage / name
    if not src.exists():
        raise FileNotFoundError(
            f"Staged voice nahi mili: {src}\n"
            f"Ise yahan daalein ya 'voice.provider' ko elevenlabs/openai/edge karein."
        )
    dst = run_dirs["voice"] / name
    shutil.copyfile(src, dst)
    return dst


def _elevenlabs(cfg: dict, text: str, out_path: Path) -> Path:
    import os

    from elevenlabs.client import ElevenLabs

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY .env me set karein")
    client = ElevenLabs(api_key=key)
    vcfg = cfg.get("voice", {})
    audio = client.generate(
        text=text,
        voice=vcfg.get("voice_id", ""),
        model=vcfg.get("model", "eleven_multilingual_v2"),
    )
    data = b"".join(audio) if not isinstance(audio, bytes) else audio
    out_path.write_bytes(data)
    return out_path


def _openai_tts(cfg: dict, text: str, out_path: Path) -> Path:
    from openai import OpenAI

    client = OpenAI()
    vcfg = cfg.get("voice", {})
    resp = client.audio.speech.create(
        model="tts-1", voice=vcfg.get("openai_voice", "onyx"),
        input=text, speed=float(vcfg.get("speed", 1.0)),
    )
    out_path.write_bytes(resp.content)
    return out_path


def _edge_tts(cfg: dict, text: str, out_path: Path) -> Path:
    import edge_tts

    vcfg = cfg.get("voice", {})

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, vcfg.get("voice_name", "hi-IN-MadhurNeural"))
        await communicate.save(str(out_path))

    asyncio.run(_run())
    return out_path


def synth_scene(cfg: dict, text: str, run_dirs: dict, scene_id: int) -> Path:
    """Ek scene ki Hindi narration banao. Returns mp3 path."""
    name = f"scene_{scene_id:02d}.mp3"
    out_path = run_dirs["voice"] / name
    vcfg = cfg.get("voice", {})
    provider = vcfg.get("provider", "elevenlabs")

    if provider == "sandbox":
        return _staged_voice(cfg, run_dirs, name)
    if provider == "elevenlabs":
        return _elevenlabs(cfg, text, out_path)
    if provider == "openai":
        return _openai_tts(cfg, text, out_path)
    if provider == "edge":
        return _edge_tts(cfg, text, out_path)
    raise ValueError(f"Unknown voice provider: {provider}")


def synth_all(cfg: dict, story: dict[str, Any], run_dirs: dict) -> list[tuple[int, Path, float]]:
    """Saare scenes ki voiceover. Returns [(scene_id, path, duration_sec)]."""
    out = []
    for s in story["scenes"]:
        p = synth_scene(cfg, s["narration_hi"], run_dirs, int(s["id"]))
        d = probe_duration(p)
        out.append((int(s["id"]), p, d))
    return out
