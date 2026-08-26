"""SEO metadata — title, description, tags, filename (MJH-style Hindi SEO)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

BASE_TAGS = [
    "horror story", "horror stories in hindi", "animated horror story",
    "hindi horror story", "scary story hindi", "bhutiya kahani", "horror kahani",
    "gulli bulli horror", "3d animation horror", "horror video hindi",
    "animation cartoon hindi", "scary stories animated", "horror tales hindi",
    "make joke horror type video", "darr wali kahani", "horror cartoon hindi",
]

SERIES_TAGS = [
    "gulli bulli", "gulli bulli horror story", "gulli bulli cartoon",
    "gulli bulli aur bhoot", "kids horror story", "bacho ki horror kahani",
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:60] or "video"


def build_meta(cfg: dict, story: dict[str, Any], mode: str = "full") -> dict[str, Any]:
    series = story.get("series") or f"{cfg.get('story', {}).get('series_prefix', '')} {story.get('title', '')}".strip()
    part = int(story.get("part", 1))

    if mode == "short":
        title = f"{series} #shorts | {story.get('title', '')} | Hindi Horror Story"
    else:
        title = f"{series} Part {part} | Horror Story | Animated Hindi | Cartoon"

    hook = story.get("hook", "")
    desc = "\n".join([
        f"😱 {series} Part {part} — {story.get('title', '')}",
        "",
        f"{hook}",
        "",
        "🫣 Darr wali ye kahani dekhne ke baad aap raat ko akeli nahi so paoge!",
        "Agar video pasand aaye to LIKE karein, apne dosto ke saath SHARE karein aur",
        "nayi horror stories ke liye SUBSCRIBE karna na bhoolein! 🔔",
        "",
        "🎬 Is video me:",
    ] + [
        f"   {i + 1}. {s['narration_hi'][:80]}..." for i, s in enumerate(story["scenes"][:6])
    ] + [
        "",
        f"#HindiHorrorStory #HorrorStory #{slugify(series).replace('-', '')[:25]} #HorrorAnimation #ScaryStory",
        "",
        "© 2026 — Saari kahaniyan aur visuals AI se banayi gayi hain.",
    ])

    tags = list(BASE_TAGS) + list(SERIES_TAGS) + [series, story.get("title", "")]
    tags = [t for t in dict.fromkeys(tags) if len(t) <= 100][:450]

    return {
        "title": title[:100],
        "description": desc,
        "tags": tags,
        "category_id": str(cfg.get("channel", {}).get("category_id", "22")),
        "default_language": "hi",
        "filename": slugify(series),
    }
