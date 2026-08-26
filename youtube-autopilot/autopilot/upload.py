"""YouTube upload — OAuth2 auth + video upload + thumbnail set."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from . import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = config.ROOT / "client_secret.json"


def _load_env(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def _save_env(path: Path, updates: dict[str, str]) -> None:
    env = _load_env(path)
    env.update(updates)
    lines = [f"{k}={v}" for k, v in env.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def oauth_authorize() -> None:
    """Pehli baar: browser me login karke refresh token save karo (.env me)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(
            f"{CLIENT_SECRET} nahi mila.\n"
            "Google Cloud Console → APIs & Services → Credentials → 'OAuth client' (Desktop app)\n"
            "banakar JSON download karke is repo folder me 'client_secret.json' naam se rakhein.\n"
            "YouTube Data API v3 bhi ENABLE karna na bhoolein!"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    if not creds.refresh_token:
        raise RuntimeError("Refresh token nahi mila — consent screen pe 'Allow' dabayein.")
    _save_env(config.ROOT / ".env", {"YOUTUBE_REFRESH_TOKEN": creds.refresh_token})
    print("✅ Auth ho gaya! Refresh token .env me save ho gaya.")


def _client():
    import google.auth.transport.requests
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not token:
        raise RuntimeError("YOUTUBE_REFRESH_TOKEN nahi hai — pehle `python -m autopilot auth` chalayein")
    creds = Credentials(
        token=None,
        refresh_token=token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_client_id(),
        client_secret=_client_secret(),
        scopes=SCOPES,
    )
    creds.refresh(google.auth.transport.requests.Request())
    return build("youtube", "v3", credentials=creds)


def _client_id() -> str:
    import json

    data = json.loads(CLIENT_SECRET.read_text())
    return data["installed"]["client_id"]


def _client_secret() -> str:
    import json

    data = json.loads(CLIENT_SECRET.read_text())
    return data["installed"]["client_secret"]


def upload_video(cfg: dict, meta: dict[str, Any], video_path: Path,
                 thumbnail: Path | None = None, privacy: str | None = None,
                 progress: bool = True) -> str:
    """Video upload karo. Returns video id."""
    from googleapiclient.http import MediaFileUpload

    youtube = _client()
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": meta["category_id"],
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy or cfg.get("channel", {}).get("default_privacy", "private"),
            "selfDeclaredMadeForKids": bool(cfg.get("channel", {}).get("made_for_kids", False)),
            "notifySubscribers": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=4 * 1024 * 1024,
                            resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    vid = None
    while True:
        status, resp = req.next_chunk()
        if resp:
            vid = resp["id"]
            if progress:
                print(f"✅ Upload complete: https://youtu.be/{vid}")
            break
        if status and progress:
            print(f"   uploading... {int(status.progress() * 100)}%")

    if thumbnail and thumbnail.exists():
        try:
            youtube.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail))).execute()
            if progress:
                print("✅ Custom thumbnail set ho gayi")
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Thumbnail set nahi hui: {e}")
    return vid


def video_url(vid: str) -> str:
    return f"https://youtu.be/{vid}"


def valid_channel_handle(cfg: dict) -> bool:
    """Optional sanity check — channel handle se match karo."""
    import json

    try:
        youtube = _client()
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if items:
            handle = items[0]["snippet"].get("customUrl", "")
            cfg_handle = cfg.get("channel", {}).get("handle", "").lstrip("@")
            print(f"Upload channel: {items[0]['snippet']['title']} ({handle})")
            if cfg_handle and handle.lstrip("@") != cfg_handle.lstrip("@"):
                print(f"⚠️ Dhyan dein: config me handle '{cfg_handle}' hai, channel '{handle}' hai")
        return bool(items)
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Channel check fail: {e}")
        return True
