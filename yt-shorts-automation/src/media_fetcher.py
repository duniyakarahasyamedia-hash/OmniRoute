"""Stock footage fetch — Pexels / Pixabay, with generated-gradient fallback."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

log = logging.getLogger("omnishorts.media")

STOPWORDS_HI = {
    "क्या", "है", "हैं", "और", "का", "की", "के", "में", "से", "को", "पर",
    "यह", "वह", "कि", "जो", "भी", "हो", "था", "थी", "थे", "नहीं", "क्यों",
    "कैसे", "कहाँ", "कब", "किस", "किसी", "अपने", "अपनी", "सबसे", "एक",
    "इस", "उस", "तो", "ही", "बहुत", "करता", "करते", "करती", "जाता", "जाती",
    "रहा", "रही", "रहे", "गया", "गई", "गए", "आज", "दुनिया", "दुनिया का",
}


def hindi_to_english_keywords(text: str, cfg: dict) -> str:
    """Map Hindi text to English search terms using the config keyword_map."""
    kw_map = cfg.get("keyword_map", {})
    hits = []
    for hi_word, en in kw_map.items():
        if hi_word in text:
            hits.append(en)
    if hits:
        return " ".join(hits)
    # fallback: crude keyword strip
    tokens = [t for t in re.split(r"[\s,।.?]+", text) if t and t not in STOPWORDS_HI]
    return " ".join(tokens[:4]) or "mystery dark"


def fetch_background(search: str, out_path: Path, cfg: dict) -> Path | None:
    """Download one portrait background video. Returns path or None."""
    source = cfg.get("source", "pexels")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if source == "pexels" and cfg.get("pexels_api_key"):
            return _fetch_pexels(search, out_path, cfg["pexels_api_key"])
        if source == "pixabay" and cfg.get("pixabay_api_key"):
            return _fetch_pixabay(search, out_path, cfg["pixabay_api_key"])
        if source == "pixabay" and cfg.get("pexels_api_key"):
            return _fetch_pexels(search, out_path, cfg["pexels_api_key"])
        if source == "pexels" and cfg.get("pixabay_api_key"):
            return _fetch_pixabay(search, out_path, cfg["pixabay_api_key"])
    except Exception as exc:  # noqa: BLE001
        log.warning("media fetch failed for '%s': %s", search, exc)
    return None


def _pick_pexels_video(data: dict) -> str | None:
    best = None
    for video in data.get("videos", []):
        h = video.get("height", 0)
        if h < 1080:
            continue
        for f in video.get("video_files", []):
            if f.get("quality") == "hd" and f.get("height", 0) >= 1080:
                return f["link"]
            if best is None and f.get("link"):
                best = f["link"]
    return best


def _fetch_pexels(query: str, out_path: Path, key: str) -> Path | None:
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "per_page": 6, "orientation": "portrait"},
        headers={"Authorization": key},
        timeout=30,
    )
    resp.raise_for_status()
    url = _pick_pexels_video(resp.json())
    if not url:
        return None
    dl = requests.get(url, timeout=60, stream=True)
    dl.raise_for_status()
    out_path.write_bytes(dl.content)
    log.info("  [media] pexels: %s", url.split("/")[-1][:40])
    return out_path


def _fetch_pixabay(query: str, out_path: Path, key: str) -> Path | None:
    resp = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": key, "q": query, "video_type": "film", "per_page": 10},
        timeout=30,
    )
    resp.raise_for_status()
    best = None
    for hit in resp.json().get("hits", []):
        vids = hit.get("videos", {})
        large = vids.get("large") or vids.get("medium")
        if large and int(large.get("height", 0)) >= 1080:
            best = large["url"]
            break
        if best is None and large:
            best = large["url"]
    if not best:
        return None
    dl = requests.get(best, timeout=60, stream=True)
    dl.raise_for_status()
    out_path.write_bytes(dl.content)
    log.info("  [media] pixabay ok")
    return out_path
