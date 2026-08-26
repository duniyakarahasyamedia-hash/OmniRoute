"""Image generation — horror scene images (multiple providers)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import config


def _staged(cfg: dict, run_dirs: dict, name: str) -> Path:
    """Sandbox provider: staged assets folder se copy karo."""
    stage = config.staging_dir(run_dirs["id"]) / "images"
    src = stage / name
    if not src.exists():
        raise FileNotFoundError(
            f"Staged image nahi mili: {src}\n"
            f"Ise yahan daalein ya 'images.provider' ko openai/replicate karein."
        )
    dst = run_dirs["images"] / name
    shutil.copyfile(src, dst)
    return dst


def _openai(cfg: dict, prompt: str, out_path: Path, size: str) -> Path:
    from openai import OpenAI

    client = OpenAI()
    icfg = cfg.get("images", {})
    model = icfg.get("model", "gpt-image-1")
    resp = client.images.generate(model=model, prompt=prompt, size=size, n=1)
    data = resp.data[0]
    if getattr(data, "b64_json", None):
        import base64

        out_path.write_bytes(base64.b64decode(data.b64_json))
    elif getattr(data, "url", None):
        import requests

        r = requests.get(data.url, timeout=120)
        r.raise_for_status()
        out_path.write_bytes(r.content)
    else:
        raise RuntimeError("OpenAI image response samajh nahi aayi")
    return out_path


def _replicate(cfg: dict, prompt: str, out_path: Path) -> Path:
    import replicate

    icfg = cfg.get("images", {})
    model = icfg.get("model", "black-forest-labs/flux-dev")
    out = replicate.run(model, input={"prompt": prompt, "aspect_ratio": "16:9"})
    if isinstance(out, list):
        out = out[0]
    import requests

    r = requests.get(str(out), timeout=120)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path


def gen_image(cfg: dict, prompt: str, run_dirs: dict, name: str) -> Path:
    """Har scene ki image banao. Returns image path."""
    out_path = run_dirs["images"] / name
    icfg = cfg.get("images", {})
    provider = icfg.get("provider", "openai")
    full_prompt = f"{icfg.get('style_prefix', '')}. {prompt}"

    if provider == "sandbox":
        return _staged(cfg, run_dirs, name)
    if provider == "openai":
        return _openai(cfg, full_prompt, out_path, icfg.get("size", "1536x1024"))
    if provider == "replicate":
        return _replicate(cfg, full_prompt, out_path)
    raise ValueError(f"Unknown images provider: {provider}")


def gen_all_scene_images(cfg: dict, story: dict[str, Any], run_dirs: dict) -> list[Path]:
    paths = []
    for s in story["scenes"]:
        name = f"scene_{int(s['id']):02d}.png"
        p = gen_image(cfg, s["image_prompt"], run_dirs, name)
        paths.append(p)
    return paths


def gen_thumbnail_source(cfg: dict, story: dict[str, Any], run_dirs: dict) -> Path:
    prompt = story.get("thumbnail_prompt") or story["scenes"][0]["image_prompt"]
    return gen_image(cfg, prompt, run_dirs, "thumb_src.png")
