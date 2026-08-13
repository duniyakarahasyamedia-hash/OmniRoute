#!/usr/bin/env python3
"""
Veo Film Pipeline — AI cinematic short-film generator (Hindi-first).

Story/idea  -->  [Gemini] shot-list + script  -->  [Veo 3.1] scene clips
            -->  [Edge-TTS] Hindi voiceover    -->  [ffmpeg] final assembly
            -->  (optional) YouTube upload via upload_youtube.py

The final `final.mp4` + `subtitles.srt` can also be re-processed through
MoneyPrinterTurbo (`mpt_commands.sh`) to add burned Hindi subtitles, BGM and
transitions.

Requirements:
    pip install "google-genai>=2.11" edge-tts

Env / config:
    GEMINI_API_KEY  (https://aistudio.google.com/app/apikey)
    or `gemini_api_key` inside ../config.toml

IMPORTANT (cost / billing):
    - Script + shot-list: works on the free Gemini Flash tier.
    - Veo 3.1 video generation: requires a PAID Gemini API (Cloud billing).
      The "Google AI Pro" consumer subscription gives Veo credits in the
      Gemini app/Flow UI only — it does NOT unlock the Veo API.
    - Run with --skip-video to build the whole shot-list + narration for free.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # ai-film-studio/
CONFIG_FILE = ROOT / "config.toml"

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_VEO_MODEL = "veo-3.1-generate-preview"
DEFAULT_VOICE = "hi-IN-SwaraNeural"  # female Hindi voice (edge-tts)
DEFAULT_ASPECT = "9:16"


# --------------------------------------------------------------------------- #
# config helpers
# --------------------------------------------------------------------------- #
def _read_config() -> dict:
    cfg: dict = {}
    if CONFIG_FILE.exists():
        try:
            import tomllib
        except ModuleNotFoundError:  # Python < 3.11 fallback
            tomllib = None
        if tomllib is not None:
            with CONFIG_FILE.open("rb") as fh:
                cfg = tomllib.load(fh)
    return cfg


def _api_key(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key
    env = os.environ.get("GEMINI_API_KEY", "").strip()
    if env:
        return env
    cfg = _read_config()
    return str(cfg.get("gemini_api_key", "")).strip()


# --------------------------------------------------------------------------- #
# Gemini: story -> shot-list
# --------------------------------------------------------------------------- #
_SHOTLIST_SYSTEM = """You are a professional Hindi short-film director and screenwriter.

Given an idea, produce a compact, cinematic short-film plan as STRICT JSON with this
exact shape (no extra keys, no markdown, no code fences):

{
  "title": "short punchy Hindi title",
  "logline": "one line story summary in Hindi",
  "style": "visual style keywords e.g. dark fantasy, cinematic, 35mm",
  "scenes": [
    {
      "scene": 1,
      "shot": "SHOT TYPE e.g. EXTREME CLOSE-UP",
      "veo_prompt": "detailed English visual prompt for a text-to-video model. Include camera movement, lighting, subject, mood, setting. 2-3 sentences. No dialogue text.",
      "narration_hi": "1-2 lines of Hindi voiceover narration for this scene"
    }
  ],
  "metadata": {
    "title": "YouTube title",
    "description": "YouTube description, 2-3 sentences in Hindi",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
  }
}

Rules:
- scenes: exactly {num_scenes} scenes.
- veo_prompt must be in English, highly visual, and must NOT contain the narration text.
- narration_hi must be natural spoken Hindi (Devanagari script), no English.
- Make scenes flow as a real story with a beginning, middle and end.
- style to apply: {style}"""


def _extract_json(text: str) -> dict:
    """Robustly pull the first JSON object out of a model response."""
    text = text.strip()
    # strip markdown code fences if present
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


def build_shotlist(
    idea: str, style: str, num_scenes: int, model: str, client
) -> dict:
    prompt = _SHOTLIST_SYSTEM.format(num_scenes=num_scenes, style=style or "cinematic")
    response = client.models.generate_content(
        model=model,
        contents=f"Idea: {idea}\n\n{prompt}",
    )
    data = _extract_json(response.text)
    scenes = data.get("scenes", [])
    if not scenes:
        raise ValueError("Model returned no scenes")
    for i, sc in enumerate(scenes, 1):
        sc["scene"] = i
    return data


# --------------------------------------------------------------------------- #
# Veo: generate one clip
# --------------------------------------------------------------------------- #
def generate_clip(
    client,
    prompt: str,
    model: str,
    aspect: str,
    duration: int,
    out_path: Path,
) -> Path:
    from google.genai import types

    config_kwargs: dict = {"aspect_ratio": aspect}
    if duration:
        config_kwargs["duration_seconds"] = duration
    # Older/newer SDKs may not accept every kwarg; degrade gracefully.
    try:
        config = types.GenerateVideosConfig(**config_kwargs)
    except TypeError:
        config = types.GenerateVideosConfig(aspect_ratio=aspect)

    operation = client.models.generate_videos(
        model=model, prompt=prompt, config=config
    )
    while not operation.done:
        print("      (waiting for Veo...)")
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        raise RuntimeError(f"Veo generation failed: {operation.error}")

    generated = operation.response.generated_videos[0]
    client.files.download(file=generated.video)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    generated.video.save(str(out_path))
    return out_path


# --------------------------------------------------------------------------- #
# narration (edge-tts) + assembly (ffmpeg)
# --------------------------------------------------------------------------- #
def _ffmpeg() -> str:
    """Resolve an ffmpeg binary: system PATH first, then imageio-ffmpeg's static build."""
    import shutil

    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _run(cmd: list[str]) -> None:
    if cmd and cmd[0] == "ffmpeg":
        cmd = [_ffmpeg()] + cmd[1:]
    print("   $ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr or "")
    if not m:
        raise RuntimeError(f"cannot read duration of {path}")
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def _edge_tts(text: str, voice: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await communicate.save(str(out_path))


def build_narration(scenes: list[dict], voice: str, audio_dir: Path) -> list[Path]:
    """Synthesise each scene's narration and return the audio files in order."""
    import asyncio

    audio_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    async def _all() -> None:
        for sc in scenes:
            text = sc.get("narration_hi", "").strip()
            out = audio_dir / f"scene_{sc['scene']:02d}.mp3"
            if not text:
                text = "..."  # never send empty string to edge-tts
            await _edge_tts(text, voice, out)
            paths.append(out)

    asyncio.run(_all())
    return paths


def _concat_audio(audio_paths: list[Path], out_path: Path) -> Path:
    """Concatenate scene mp3s into one voiceover file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_path.with_suffix(".txt")
    list_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in audio_paths), encoding="utf-8"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_path),
        ]
    )
    return out_path


def build_srt(scenes: list[dict], audio_paths: list[Path], out_path: Path) -> Path:
    """Build an SRT timed to the actual narration durations."""
    lines: list[str] = []
    cursor = 0.0
    for idx, (sc, ap) in enumerate(zip(scenes, audio_paths), 1):
        dur = _probe_duration(ap)
        text = sc.get("narration_hi", "").strip()
        lines.append(str(idx))
        lines.append(f"{_srt_time(cursor)} --> {_srt_time(cursor + dur)}")
        lines.append(text)
        lines.append("")
        cursor += dur
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _normalize_clip(clip: Path, aspect: str, dur: float, out_dir: Path, idx: int) -> Path:
    """Scale/pad a clip to the target aspect, trim to narration length, yuv420p."""
    out = out_dir / f"norm_{idx:02d}.mp4"
    w, h = (1080, 1920) if aspect == "9:16" else (1920, 1080)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip),
            "-t",
            f"{dur:.3f}",
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"fps=30,format=yuv420p",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(out),
        ]
    )
    return out


def assemble_final(
    clip_paths: list[Path],
    voiceover: Path,
    aspect: str,
    out_path: Path,
    work_dir: Path,
) -> Path:
    """Concatenate clips, mux the voiceover, write final.mp4."""
    work_dir.mkdir(parents=True, exist_ok=True)
    norm_dir = work_dir / "normalized"
    norm_dir.mkdir(exist_ok=True)

    # Trim each clip to its narration length so audio/video stay in sync.
    normalized: list[Path] = []
    audio_files = sorted(voiceover.parent.glob("scene_*.mp3"))
    for i, clip in enumerate(clip_paths, 1):
        dur = _probe_duration(audio_files[i - 1]) if i - 1 < len(audio_files) else 8.0
        normalized.append(_normalize_clip(clip, aspect, dur, norm_dir, i))

    list_file = work_dir / "concat.txt"
    list_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in normalized), encoding="utf-8"
    )
    video_only = work_dir / "video_only.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(video_only),
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_only),
            "-i",
            str(voiceover),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return out_path


# --------------------------------------------------------------------------- #
# MoneyPrinterTurbo bridge
# --------------------------------------------------------------------------- #
def write_mpt_commands(
    shotlist: dict, out_dir: Path, aspect: str, mpt_dir: Path, voice: str
) -> Path:
    clip_paths = sorted((out_dir / "shots").glob("scene_*.mp4"))
    materials = ",".join(str(p.resolve()) for p in clip_paths)
    title = shotlist.get("title") or shotlist.get("metadata", {}).get("title", "AI Short Film")
    script_file = out_dir / "script.txt"
    script_text = "\n".join(
        s.get("narration_hi", "") for s in shotlist.get("scenes", [])
    )
    script_file.write_text(script_text, encoding="utf-8")

    mpt = mpt_dir.resolve()
    gender = "Male" if "Male" in voice else "Female"
    font = "Hind-Bold.ttf"

    cmds = []
    cmds.append("#!/usr/bin/env bash")
    cmds.append("set -euo pipefail")
    cmds.append(f"cd {mpt}")
    cmds.append(
        "uv run python cli.py \\\n"
        f"  --video-subject '{title}' \\\n"
        f"  --video-script '{script_file.resolve()}' \\\n"
        "  --video-language hi-IN \\\n"
        f"  --voice-name {voice}-{gender} \\\n"
        "  --video-source local \\\n"
        f"  --video-materials '{materials}' \\\n"
        f"  --video-aspect {aspect} \\\n"
        f"  --font-name {font} \\\n"
        "  --subtitle-enabled \\\n"
        "  --bgm-type random"
    )
    cmds.append("")
    out = out_dir / "mpt_commands.sh"
    out.write_text("\n".join(cmds), encoding="utf-8")
    out.chmod(0o755)
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Veo AI cinematic short-film pipeline")
    p.add_argument("--idea", default="", help="story idea (English or Hindi)")
    p.add_argument("--story-file", default="", help="path to a text file with the idea")
    p.add_argument("--style", default="cinematic, dramatic lighting, film grain")
    p.add_argument("--num-scenes", type=int, default=6)
    p.add_argument("--aspect", default=DEFAULT_ASPECT, choices=["9:16", "16:9"])
    p.add_argument("--duration", type=int, default=8, help="per-scene Veo seconds (1-8)")
    p.add_argument("--voice", default=DEFAULT_VOICE, help="edge-tts voice id")
    p.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL)
    p.add_argument("--veo-model", default=DEFAULT_VEO_MODEL)
    p.add_argument("--api-key", default="", help="Gemini API key (or env GEMINI_API_KEY)")
    p.add_argument("--skip-video", action="store_true", help="shot-list only, no Veo calls")
    p.add_argument("--regenerate", action="store_true", help="force new story.json instead of reusing")
    p.add_argument("--no-narration", action="store_true", help="skip Hindi voiceover")
    p.add_argument("--no-assemble", action="store_true", help="skip final ffmpeg assembly")
    p.add_argument("--mpt-dir", default=str(ROOT.parent / "repos" / "MoneyPrinterTurbo"))
    p.add_argument("--out-dir", default="", help="output dir (default: storage/film-<id>)")
    args = p.parse_args(argv)

    idea = args.idea.strip()
    if not idea and args.story_file:
        idea = Path(args.story_file).read_text(encoding="utf-8").strip()

    out_dir = Path(args.out_dir) if args.out_dir else (
        ROOT / "storage" / f"film-{uuid.uuid4().hex[:8]}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- figure out what we actually need (Gemini key only when generating) ----
    story_path = out_dir / "story.json"
    shots_dir = out_dir / "shots"
    existing_clips = sorted(shots_dir.glob("scene_*.mp4"))

    need_story = (not story_path.exists()) or args.regenerate
    need_clips = (not existing_clips) and (not args.skip_video)

    client = None
    if need_story or need_clips:
        if not idea:
            print("ERROR: provide --idea or --story-file (needed to generate story/clips)")
            return 2
        key = _api_key(args)
        if not key:
            print("ERROR: Gemini API key missing. Set GEMINI_API_KEY or --api-key, "
                  "or put gemini_api_key in ai-film-studio/config.toml")
            return 2
        from google import genai

        client = genai.Client(api_key=key)

    # ---- story: reuse existing story.json so re-runs keep the same narration ----
    if need_story:
        print(f"[1/4] Building shot-list ({args.num_scenes} scenes) via {args.gemini_model} ...")
        shotlist = build_shotlist(idea, args.style, args.num_scenes, args.gemini_model, client)
        story_path.write_text(
            json.dumps(shotlist, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        shotlist = json.loads(story_path.read_text(encoding="utf-8"))
        print(f"[1/4] Reusing existing story.json ({len(shotlist.get('scenes', []))} scenes)")
    print(f"      title: {shotlist.get('title')!r}")

    scenes = shotlist["scenes"]

    # ---- clips: reuse any scene_*.mp4 already in shots/ (e.g. made in Gemini app) ----
    clip_paths: list[Path] = []
    if existing_clips:
        clip_paths = existing_clips
        print(f"[2/4] Found {len(existing_clips)} clips in {shots_dir} — using them.")
        for c in clip_paths:
            print(f"      {c.name}")
    elif args.skip_video:
        print("[2/4] --skip-video: no clips. (Put Veo clips in shots/ then re-run to assemble.)")
    else:
        print(f"[2/4] Generating {len(scenes)} clips via {args.veo_model} ...")
        for sc in scenes:
            out = shots_dir / f"scene_{sc['scene']:02d}.mp4"
            if out.exists():
                print(f"      scene {sc['scene']}: exists, skipping")
            else:
                print(f"      scene {sc['scene']}: {sc['shot']}")
                generate_clip(client, sc["veo_prompt"], args.veo_model,
                              args.aspect, args.duration, out)
            clip_paths.append(out)

    audio_paths: list[Path] = []
    if args.no_narration:
        print("[3/4] --no-narration: skipping Hindi voiceover.")
    else:
        audio_dir = out_dir / "audio"
        existing_voiceover = audio_dir / "voiceover.m4a"
        if existing_voiceover.exists() and not args.regenerate:
            audio_paths = sorted(audio_dir.glob("scene_*.mp3"))
            print(f"[3/4] Reusing existing voiceover ({len(audio_paths)} files).")
        else:
            print(f"[3/4] Hindi narration via edge-tts ({args.voice}) ...")
            audio_paths = build_narration(scenes, args.voice, audio_dir)
            voiceover = _concat_audio(audio_paths, audio_dir / "voiceover.m4a")
            build_srt(scenes, audio_paths, out_dir / "subtitles.srt")
            print(f"      voiceover: {voiceover}")

    if args.no_assemble or not clip_paths or not audio_paths:
        print("[4/4] --no-assemble (or missing clips/audio): skipping final assembly.")
    else:
        print("[4/4] Assembling final.mp4 ...")
        final = assemble_final(
            clip_paths,
            out_dir / "audio" / "voiceover.m4a",
            args.aspect,
            out_dir / "final.mp4",
            out_dir / "work",
        )
        print(f"      DONE: {final}")

    mpt_cmds = write_mpt_commands(shotlist, out_dir, args.aspect, Path(args.mpt_dir), args.voice)
    print(f"\nOutputs written to: {out_dir}")
    print(f"MPT re-render command: {mpt_cmds}")
    print(f"\nUpload:  python3 ai-film-studio/scripts/upload_youtube.py "
          f"{out_dir / 'final.mp4'} --metadata {out_dir / 'story.json'} "
          f"--captions {out_dir / 'subtitles.srt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
