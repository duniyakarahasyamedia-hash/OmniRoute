"""Story engine — LLM se Make-Joke-Horror style Hindi horror story generate karta hai.

Output JSON schema:
{
  "title": "भुतिया गुड़िया",                       # episode title
  "series": "गुल्ली बुल्ली और भुतिया गुड़िया",       # full series title
  "part": 1,
  "hook": "रात के बारह बजे...",                     # thumbnail/hook line
  "thumbnail_prompt": "english image prompt...",
  "outro": "देखते रहिए...",
  "scenes": [
    {"id": 1, "narration_hi": "...", "image_prompt": "english...", "action": "zoom_in"}
  ]
}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """Tum ek Hindi horror story writer ho jo YouTube channel 'MAKE JOKE HORROR' jaisi
videos ke liye scripts likhta hai. Us channel ki videos: 3D animated cartoon style horror
stories in Hindi, bachpan ke cartoon characters (jaise Gulli Bulli) ke saath, jisme ek
simple scary situation dheere-dheere nightmare ban jati hai. Har video ka ending cliffhanger
hoti hai ("Part 2 me dekhiye..."). Narration simple, dramatic aur darr wali Hindi me hoti hai.

Rules:
1. Saari narration PURE Hindi (Devanagari) me likho — bachche bhi samajh sakein.
2. Har scene me: narration_hi (dramatic Hindi), image_prompt (ENGLISH me — detailed,
   visual description for AI image generation), action (zoom_in / zoom_out / pan_left / pan_right).
3. Full video: {min_scenes}-{max_scenes} scenes, total narration ~{target_secs} seconds.
   Short video: sirf 4-6 chhote scenes, total ~60-75 seconds.
4. Scene 1 hook ho (turant attention pakde), beech me tension badhe, last scene cliffhanger.
5. Characters sirf inme se use karo: {characters}
6. Story ka villain koi horror element ho: bhootiya gudiya, jadugar, zombie, siren head,
   haunted doll, bhutiya hospital, purana ghar, granny wali game character etc.
7. Sirf VALID JSON return karo — koi extra text nahi, koi markdown nahi.
"""


def _default_story() -> dict[str, Any]:
    return {"title": "", "series": "", "part": 1, "hook": "", "thumbnail_prompt": "",
            "outro": "", "scenes": []}


def build_prompt(cfg: dict, mode: str, topic: str = "") -> str:
    scfg = cfg.get("story", {})
    chars = ", ".join(f"{c.get('name')} ({c.get('desc')})" for c in scfg.get("characters", []))
    if mode == "short":
        target_secs = 70
        nmin, nmax = 4, 6
    else:
        target_secs = int(scfg.get("target_full_minutes", 10)) * 60
        nmin, nmax = scfg.get("min_scenes", 8), scfg.get("max_scenes", 12)
    series = scfg.get("series_prefix", "").strip()
    user = (
        f"Ek nayi {mode} video ki story likho.\n"
        f"Series prefix: '{series}'\n"
        f"Topic idea (optional): {topic or 'koi bhi naya horror idea'}\n"
        f"Format: {mode} video, {nmin}-{nmax} scenes.\n"
        f"JSON return karo."
    )
    sys = SYSTEM_PROMPT.format(min_scenes=nmin, max_scenes=nmax, target_secs=target_secs,
                               characters=chars)
    return sys, user


def generate_story(cfg: dict, mode: str, topic: str = "", story_file: str | Path | None = None) -> dict[str, Any]:
    """Generate (ya file se load) karo. Returns story dict."""
    if story_file is not None or cfg.get("story", {}).get("provider") == "file":
        path = Path(story_file or "story.json")
        if not path.exists():
            raise FileNotFoundError(f"Story file nahi mili: {path}")
        story = json.loads(path.read_text(encoding="utf-8"))
        story["_source"] = str(path)
        _validate_story(story)
        return story

    provider = cfg.get("story", {}).get("provider", "openai")
    model = cfg.get("story", {}).get("model", "gpt-4o-mini")
    temp = float(cfg.get("story", {}).get("temperature", 0.9))

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        sys, user = build_prompt(cfg, mode, topic)
        resp = client.chat.completions.create(
            model=model,
            temperature=temp,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
        )
        story = json.loads(resp.choices[0].message.content)
    elif provider == "omniroute":
        # OmniRoute gateway = OpenAI-compatible endpoint (is repo ka apna gateway!)
        import os

        from openai import OpenAI

        base = os.environ.get("OPENAI_BASE_URL") or "http://localhost:3000/api/v1"
        client = OpenAI(base_url=base)
        sys, user = build_prompt(cfg, mode, topic)
        resp = client.chat.completions.create(
            model=model, temperature=temp,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
        )
        story = json.loads(resp.choices[0].message.content)
    else:
        raise ValueError(f"Unknown story provider: {provider}")

    _validate_story(story)
    return story


def _validate_story(story: dict[str, Any]) -> None:
    if not story.get("scenes"):
        raise ValueError("Story me koi scenes nahi hain")
    for i, s in enumerate(story["scenes"]):
        if not s.get("narration_hi", "").strip():
            raise ValueError(f"Scene {i + 1} me narration_hi khali hai")
        if not s.get("image_prompt", "").strip():
            s["image_prompt"] = s.get("narration_hi", "")
        s["id"] = int(s.get("id", i + 1))
        s.setdefault("action", "zoom_in")


def derive_short(story: dict[str, Any]) -> dict[str, Any]:
    """Full story se Short version derive karo (hook + pehle scenes + cliffhanger).

    Narration wahi rehti hai (audio reuse karne ke liye) — scenes kam kiye jaate hain
    taaki duration ~60-90s rahe.
    """
    scenes = story["scenes"]
    if len(scenes) <= 6:
        return story
    picked = [scenes[0]] + scenes[1:4] + [scenes[-1]]
    short = json.loads(json.dumps(story))
    short["scenes"] = picked
    return short


def save_story(story: dict, run_dirs: dict) -> Path:
    path = run_dirs["story"] / "story.json"
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
