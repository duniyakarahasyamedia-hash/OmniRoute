"""YouTube upload via Data API v3 (OAuth2). Falls back to a draft JSON when
credentials are not configured yet."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("omnishorts.upload")


class YouTubeUploader:
    def __init__(self, cfg: dict, root: Path):
        self.cfg = cfg
        self.root = root
        yt = cfg.get("youtube", {})
        self.client_secrets = root / yt.get("client_secrets", "credentials/client_secrets.json")
        self.token_file = root / yt.get("token_file", "credentials/token.json")

    # ------------------------------------------------------- auth
    def _credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file),
                                                          self.cfg["youtube"]["scopes"])
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)
            return creds
        raise RuntimeError(
            "YouTube token missing/expired. Run: python scripts/oauth_youtube.py "
            "(needs credentials/client_secrets.json from Google Cloud Console)"
        )

    def _save_token(self, creds) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")

    def _service(self):
        from googleapiclient.discovery import build

        creds = self._credentials()
        return build("youtube", "v3", credentials=creds)

    # ------------------------------------------------------- upload
    def upload(self, video_path: Path, meta: dict, privacy: str = "private",
               made_for_kids: bool = False) -> dict:
        from googleapiclient.http import MediaFileUpload

        service = self._service()
        body = {
            "snippet": {
                "title": meta["title"],
                "description": meta["description"],
                "tags": meta["tags"],
                "categoryId": meta.get("categoryId", "24"),
                "defaultLanguage": "hi",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }
        media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
        req = service.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                log.info("  [upload] %d%%", int(status.progress() * 100))
        vid = resp.get("id")
        log.info("  [upload] DONE: https://youtu.be/%s (%s)", vid, privacy)
        return {"id": vid, "url": f"https://youtu.be/{vid}", "privacy": privacy}

    # ------------------------------------------------------- fallback
    def save_draft(self, video_path: Path, meta: dict, run_info: dict) -> dict:
        """No credentials → write a draft JSON for manual upload later."""
        draft = {
            "video_path": str(video_path),
            "metadata": meta,
            "privacy": self.cfg.get("channel", {}).get("default_privacy", "private"),
            "run_info": run_info,
            "note": "Auto-upload pending: add credentials/client_secrets.json and "
                    "run `python scripts/upload_pending.py` (or upload manually in YouTube Studio).",
        }
        path = self.root / "output" / "upload_pending.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("  [upload] no credentials → draft saved to %s", path)
        return draft


def upload_pending_file(cfg: dict, root: Path) -> None:
    """Upload whatever is in output/upload_pending.json (manual trigger)."""
    pending = root / "output" / "upload_pending.json"
    if not pending.exists():
        log.info("No pending uploads.")
        return
    draft = json.loads(pending.read_text(encoding="utf-8"))
    up = YouTubeUploader(cfg, root)
    result = up.upload(Path(draft["video_path"]), draft["metadata"], draft["privacy"])
    pending.unlink()
    print("Uploaded:", result["url"])
