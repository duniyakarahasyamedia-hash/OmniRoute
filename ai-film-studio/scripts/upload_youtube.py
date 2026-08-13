#!/usr/bin/env python3
"""
Upload a finished short film to YouTube (free, direct YouTube Data API v3).

This avoids paid third-party "posting" services and gives you full control of
title / description / tags / privacy / Hindi captions.

One-time setup (do once, then it keeps reusing the saved token):

1. Enable "YouTube Data API v3":
   https://console.cloud.google.com/apis/library/youtube.googleapis.com
2. Create an OAuth consent screen (External, add yourself as a test user).
3. Create an OAuth client ID of type "Desktop app", download it as JSON.
4. Save it at ai-film-studio/client_secrets.json  (never commit it).

Usage:
    python3 upload_youtube.py final.mp4 --metadata story.json
    python3 upload_youtube.py final.mp4 --title "..." --description "..." \
        --tags "shortfilm,ai,hindi" --privacy unlisted --captions subtitles.srt

Requirements:
    pip install google-api-python-client google-auth google-auth-oauthlib
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRETS = ROOT / "client_secrets.json"
TOKEN_FILE = ROOT / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

DEFAULT_CATEGORY = "22"  # People & Blogs


def _get_credentials() -> object:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(
                    f"ERROR: {CLIENT_SECRETS} not found. "
                    "Create an OAuth Desktop client and save its JSON there."
                )
                sys.exit(2)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _load_metadata(metadata_path: Path) -> dict:
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    meta = data.get("metadata", data)
    scenes = data.get("scenes", [])
    return {
        "title": (meta.get("title") or data.get("title") or "AI Short Film").strip(),
        "description": (meta.get("description") or data.get("logline") or "").strip(),
        "tags": meta.get("tags") or ["ai", "shortfilm", "hindi"],
        "narration": "\n".join(s.get("narration_hi", "") for s in scenes),
    }


def upload_video(
    creds,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy: str,
) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": DEFAULT_CATEGORY,
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=8 * 1024 * 1024,
        resumable=True,
        mimetype="video/*",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    print("Uploading (resumable)...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}% uploaded")
    video_id = response["id"]
    print(f"Uploaded: https://youtu.be/{video_id}")
    return video_id


def upload_captions(creds, video_id: str, srt_path: Path, lang: str = "hi") -> None:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(str(srt_path), mimetype="application/octet-stream")
    request = youtube.captions().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "language": lang,
                "name": "Hindi (auto script)",
            }
        },
        media_body=media,
    )
    request.execute()
    print(f"Captions uploaded ({lang})")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Upload a video to YouTube")
    p.add_argument("video", help="path to the .mp4 to upload")
    p.add_argument("--metadata", default="", help="story.json with title/description/tags")
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--captions", default="", help="subtitles.srt to upload as Hindi captions")
    args = p.parse_args(argv)

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"ERROR: {video_path} not found")
        return 2

    title, description, tags = args.title, args.description, []
    if args.metadata:
        meta = _load_metadata(Path(args.metadata))
        title = title or meta["title"]
        description = description or meta["description"]
        tags = meta["tags"]
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if not title:
        title = video_path.stem

    creds = _get_credentials()
    video_id = upload_video(creds, video_path, title, description, tags, args.privacy)

    if args.captions and Path(args.captions).exists():
        upload_captions(creds, video_id, Path(args.captions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
