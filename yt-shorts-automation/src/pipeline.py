"""End-to-end pipeline: topic → script → voice → media → video → metadata → upload."""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .composer import compose
from .config import CONFIG
from .llm import LLMClient
from .media_fetcher import fetch_background, hindi_to_english_keywords
from .metadata import MetadataBuilder
from .script_writer import ScriptWriter
from .tts import make_tts
from .uploader import YouTubeUploader
from .utils import probe_duration, probe_streams
from .visuals import (build_captions_ass, captions_from_audio, make_gradient,
                      make_thumbnail)

log = logging.getLogger("omnishorts.pipeline")

COVER_DUR = 2.6
VOICE_START = 1.0
TAIL = 0.9


class PipelineError(Exception):
    pass


def run_short(cfg: dict = None, topic: str | None = None, do_upload: bool = True,
              privacy: str | None = None, keep_clips: bool = False,
              tts_override: str | None = None) -> dict:
    cfg = cfg or CONFIG
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_root = Path(cfg["output"]["dir"]) / f"short_{run_id}"
    workdir = out_root / "work"
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    log.info("=== OmniRoute Shorts pipeline: run %s ===", run_id)

    # 1 ---------- topic + script
    llm = LLMClient(cfg.get("llm", {})) if cfg.get("llm", {}).get("use_ai", True) else None
    writer = ScriptWriter(cfg, llm)
    topic = writer.pick_topic(topic)
    script = writer.write_script(topic)
    items = ScriptWriter.all_speech(script)
    writer.to_json_file(script, out_root / "script.json")
    log.info("[1/7] script ready: %d speech parts, topic='%s'", len(items), topic)

    # 2 ---------- voiceover
    tts_cfg = dict(cfg.get("tts", {}))
    if tts_override:
        tts_cfg["backend"] = tts_override
    tts = make_tts(tts_cfg, workdir)
    lines = tts.synthesize_lines(items)
    if not lines:
        raise PipelineError("TTS produced no audio")
    pause = float(tts_cfg.get("pause_between_lines", 0.35))
    voice_end = VOICE_START + sum(l.duration for l in lines) + pause * (len(lines) - 1)
    if voice_end > float(cfg["video"].get("max_duration", 60)):
        log.warning("  voice %0.1fs exceeds %ss target — trimming last non-CTA line",
                    voice_end, cfg["video"]["max_duration"])
        # drop last line (keep hook + cta) and re-render quickly
        for i in range(len(items) - 2, 0, -1):
            if items[i]["kind"] == "line" and voice_end > cfg["video"]["max_duration"]:
                del items[i]
                del lines[i]
                voice_end = VOICE_START + sum(l.duration for l in lines) + pause * (len(lines) - 1)
        script["lines"] = [it["text"] for it in items if it["kind"] == "line"]

    # 3 ---------- backgrounds (one per line)
    segments = [{"src": None, "dur": COVER_DUR, "kind": "cover"}]  # gradient cover
    media_cfg = cfg.get("media", {})
    for i, (item, la) in enumerate(zip(items, lines)):
        bg_path = None
        if media_cfg.get("source") != "none":
            query = hindi_to_english_keywords(item["text"], media_cfg)
            if query:
                bg_path = fetch_background(query, workdir / f"bg_{i:02d}.mp4", media_cfg)
        if bg_path is None and media_cfg.get("fallback_gradients", True):
            img = workdir / f"bg_{i:02d}.png"
            make_gradient(img, seed=i + run_id.__hash__() % 1000)
            bg_path = img
        seg_dur = max(la.duration + 0.35, 3.0)
        segments.append({"src": bg_path, "dur": seg_dur, "kind": item["kind"]})
    log.info("[2/7] %d video segments (+cover)", len(segments) - 1)

    # 4 ---------- captions (karaoke ASS) + cover card events + watermark
    captions = captions_from_audio(items, lines, pause, hook_hold=1.2,
                                   start_offset=VOICE_START)
    channel_name = cfg.get("channel", {}).get("name", "दुनिया का रहस्य")
    subs_ass = build_captions_ass(captions, workdir / "captions.ass",
                                  cover_duration=COVER_DUR, cover_hook=script["hook"],
                                  watermark_text=channel_name)
    log.info("[3/7] captions + cover card built (%d events)", len(captions))

    # 5 ---------- compose
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    music_path = None
    raw_music = cfg.get("video", {}).get("music_path") or ""
    if raw_music:
        candidate = Path(raw_music)
        music_path = candidate if candidate.is_absolute() else assets_dir / raw_music
        if not music_path.exists():
            log.warning("  music file not found: %s (continuing without music)", music_path)
            music_path = None
    v_cfg = cfg.get("video", {})
    compose(segments, lines, subs_ass, music_path,
            float(v_cfg.get("music_volume", 0.12)), workdir, out_root / "short.mp4",
            keep_clips=keep_clips, pause=pause, voice_start=VOICE_START)
    final = out_root / "short.mp4"
    log.info("[4/7] video composed")

    # 6 ---------- thumbnail + metadata
    make_thumbnail(script["hook"], topic, out_root / "thumbnail.jpg")
    meta_builder = MetadataBuilder(cfg)
    meta = meta_builder.build(script)
    meta_builder.to_json_file(meta, out_root / "metadata.json")
    log.info("[5/7] thumbnail + metadata ready")

    # 7 ---------- upload
    result = None
    if do_upload:
        up = YouTubeUploader(cfg, Path(__file__).resolve().parent.parent)
        priv = privacy or cfg.get("channel", {}).get("default_privacy", "private")
        try:
            result = up.upload(final, meta, privacy=priv,
                               made_for_kids=cfg.get("channel", {}).get("made_for_kids", False))
            log.info("[6/7] uploaded: %s", result["url"])
        except RuntimeError as exc:
            log.warning("  upload skipped: %s", exc)
            result = up.save_draft(final, meta, {"run_id": run_id})
    else:
        log.info("[6/7] upload skipped (--no-upload)")
        result = {"skipped": True}

    # 8 ---------- report
    info = probe_streams(final)
    report = {
        "run_id": run_id,
        "topic": topic,
        "script": script,
        "video": str(final),
        "thumbnail": str(out_root / "thumbnail.jpg"),
        "metadata": meta,
        "duration_s": probe_duration(final),
        "streams": info,
        "upload": result,
        "elapsed_s": round(time.time() - t0, 1),
    }
    if cfg["output"].get("run_report", True):
        (out_root / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("[7/7] done in %.1fs → %s (%.1fs)", time.time() - t0, final,
             probe_duration(final))
    return report


def cli_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
