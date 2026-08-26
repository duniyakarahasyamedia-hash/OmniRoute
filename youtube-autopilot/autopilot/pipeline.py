"""Pipeline orchestration — story → images → voice → music → render → meta → manifest."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config, seo
from .images import gen_all_scene_images, gen_thumbnail_source
from .story import derive_short, generate_story, save_story
from .voice import synth_all


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_run_id(topic: str, mode: str) -> str:
    slug = seo.slugify(topic)[:24] or "story"
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{slug}_{mode}"


def make_dirs(run_id: str) -> dict[str, Path]:
    r = config.run_dir(run_id)
    dirs = {
        "id": run_id,
        "root": r,
        "story": r / "story",
        "images": r / "images",
        "voice": r / "voice",
        "music": r / "music",
        "clips": r / "clips",
        "thumb": r / "thumbnail",
        "full": r / "full",
        "short": r / "short",
        "meta": r / "meta",
    }
    for d in dirs.values():
        if isinstance(d, Path):
            d.mkdir(parents=True, exist_ok=True)
    return dirs


def load_manifest(run_id: str) -> dict[str, Any]:
    p = config.run_dir(run_id) / "manifest.json"
    if not p.exists():
        raise FileNotFoundError(f"Run nahi mila: {run_id} ({p})")
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, Any]) -> None:
    p = config.run_dir(manifest["id"]) / "manifest.json"
    p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _update(manifest: dict, stage: str, status: str, **extra: Any) -> None:
    manifest.setdefault("stages", {})[stage] = {"status": status, "at": _now(), **extra}
    manifest["updated"] = _now()
    save_manifest(manifest)


def create_run(cfg: dict, topic: str = "", mode: str = "both",
               story_file: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Naya run banao: story + images + voice + music + render + meta.

    mode: 'full' | 'short' | 'both'  (both = full video + usi story se Short)
    """
    run_id = run_id or new_run_id(topic or story_file or "story", mode)
    dirs = make_dirs(run_id)
    manifest = {
        "id": run_id,
        "created": _now(),
        "updated": _now(),
        "mode": mode,
        "topic": topic,
        "status": "working",          # working → ready → approved → uploaded | rejected
        "stages": {},
        "meta": None,
        "videos": {},
    }
    save_manifest(manifest)

    # 1) Story
    story = generate_story(cfg, "full" if mode != "short" else "short", topic, story_file)
    if story_file:
        shutil.copyfile(story_file, dirs["story"] / "story_source.json")
    save_story(story, dirs)
    manifest["story"] = {"title": story.get("title"), "series": story.get("series"),
                         "part": story.get("part"), "scenes": len(story["scenes"])}
    _update(manifest, "story", "done")

    # 2) Images
    if not _skip(cfg, "images"):
        try:
            gen_all_scene_images(cfg, story, dirs)
            gen_thumbnail_source(cfg, story, dirs)
            _update(manifest, "images", "done")
        except Exception as e:  # noqa: BLE001
            _update(manifest, "images", "error", error=str(e))
            raise
    else:
        _update(manifest, "images", "skipped")

    # 3) Voiceover
    if not _skip(cfg, "voice"):
        try:
            voice_files = synth_all(cfg, story, dirs)
            manifest["voice"] = [{"scene": s, "file": p.name, "dur": round(d, 2)}
                                 for s, p, d in voice_files]
            _update(manifest, "voice", "done")
        except Exception as e:  # noqa: BLE001
            _update(manifest, "voice", "error", error=str(e))
            raise
    else:
        _update(manifest, "voice", "skipped")
        voice_files = _load_voice_from_disk(story, dirs)

    # 4) Render
    from .render import render_full

    try:
        if mode in ("full", "both"):
            final = render_full(cfg, story, dirs, voice_files, "full")
            manifest["videos"]["full"] = str(final)
        if mode in ("short", "both"):
            short_story = derive_short(story)
            (dirs["story"] / "short_story.json").write_text(
                json.dumps(short_story, ensure_ascii=False, indent=2), encoding="utf-8")
            # full story ke voice files reuse karo (TTS cost bachao)
            short_ids = {int(s["id"]) for s in short_story["scenes"]}
            short_voice = [vf for vf in voice_files if vf[0] in short_ids]
            if len(short_voice) != len(short_story["scenes"]):
                short_voice = synth_all(cfg, short_story, dirs)
            final_s = render_full(cfg, short_story, dirs, short_voice, "short")
            manifest["videos"]["short"] = str(final_s)
        _update(manifest, "render", "done")
    except Exception as e:  # noqa: BLE001
        _update(manifest, "render", "error", error=str(e))
        raise

    # 5) Thumbnail
    from .thumbnail import make_thumbnail

    try:
        thumb = make_thumbnail(cfg, story, dirs)
        manifest["videos"]["thumbnail"] = str(thumb)
        _update(manifest, "thumbnail", "done")
    except Exception as e:  # noqa: BLE001
        _update(manifest, "thumbnail", "error", error=str(e))

    # 6) SEO meta
    meta = seo.build_meta(cfg, story, "full" if mode != "short" else "short")
    (dirs["meta"] / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    manifest["meta"] = meta
    manifest["status"] = "ready"
    _update(manifest, "seo", "done")

    sizes = {}
    for k, p in manifest["videos"].items():
        pp = Path(p)
        sizes[k] = f"{pp.stat().st_size / 1e6:.1f} MB" if pp.exists() else "—"
    manifest["sizes"] = sizes
    save_manifest(manifest)
    return manifest


def _skip(cfg: dict, stage: str) -> bool:
    return bool(cfg.get("pipeline", {}).get(f"skip_{stage}", False))


def _load_voice_from_disk(story: dict, dirs: dict) -> list[tuple[int, Path, float]]:
    from .voice import probe_duration

    out = []
    for s in story["scenes"]:
        p = dirs["voice"] / f"scene_{int(s['id']):02d}.mp3"
        if not p.exists():
            raise FileNotFoundError(f"Voice nahi mili: {p}")
        out.append((int(s["id"]), p, probe_duration(p)))
    return out


def upload_run(cfg: dict, run_id: str, privacy: str | None = None) -> dict[str, Any]:
    """Approved run ko YouTube pe upload karo. Returns upload result."""
    from . import upload

    manifest = load_manifest(run_id)
    if manifest["status"] == "uploaded":
        return {"skipped": True, "reason": "already uploaded", "manifest": manifest}
    if manifest["status"] != "approved":
        raise RuntimeError("Pehle dashboard se approve karein (status 'approved' chahiye)")

    upload.valid_channel_handle(cfg)
    meta = manifest["meta"]
    results = {}
    for key in ("full", "short"):
        vp = manifest["videos"].get(key)
        if vp and Path(vp).exists():
            if key == "short":
                m = dict(meta)
                m["title"] = meta["title"].replace("Part", "Shorts").replace("| Hindi Horror Story", "#shorts | Hindi Horror Story")[:100]
                m["tags"] = meta["tags"] + ["shorts", "youtube shorts hindi"]
            else:
                m = meta
            vid = upload.upload_video(cfg, m, Path(vp), Path(manifest["videos"]["thumbnail"]),
                                      privacy=privacy)
            results[key] = upload.video_url(vid)
    manifest["results"] = results
    manifest["status"] = "uploaded"
    _update(manifest, "upload", "done", results=results)
    return results


def list_runs() -> list[dict[str, Any]]:
    out = []
    for p in sorted(config.RUNS_DIR.glob("*/manifest.json"), reverse=True):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out
