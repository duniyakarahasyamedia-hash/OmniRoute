#!/usr/bin/env python3
"""Upload videos from output/upload_pending.json (when credentials were added later)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CONFIG  # noqa: E402
from src.uploader import upload_pending_file  # noqa: E402


def main() -> int:
    upload_pending_file(CONFIG, Path(__file__).resolve().parent.parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
