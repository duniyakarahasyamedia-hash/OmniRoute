#!/usr/bin/env python3
"""One-time OAuth2 setup for YouTube upload.

Step 1 — Google Cloud Console:
  1. https://console.cloud.google.com/ → create project
  2. Enable "YouTube Data API v3"
  3. OAuth consent screen → External → add scope .../auth/youtube.upload
     (add yourself as test user)
  4. Credentials → Create credentials → OAuth client ID → Desktop app
  5. Download JSON → save as credentials/client_secrets.json

Step 2 — run:
  python scripts/oauth_youtube.py
  (browser opens / paste URL → token saved to credentials/token.json)

Step 3 — done. Pipeline can now upload automatically.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CONFIG  # noqa: E402


def main() -> int:
    yt = CONFIG.get("youtube", {})
    root = Path(__file__).resolve().parent.parent
    secrets = root / yt.get("client_secrets", "credentials/client_secrets.json")
    token = root / yt.get("token_file", "credentials/token.json")

    if not secrets.exists():
        print(f"❌ client_secrets.json not found at {secrets}")
        print("   See the header of this script for Google Cloud Console steps.")
        return 1

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), yt["scopes"])
    creds = flow.run_local_server(port=0, prompt="consent")
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    print(f"✅ OAuth token saved to {token}")
    print("   Ab pipeline YouTube upload ke liye ready hai!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
