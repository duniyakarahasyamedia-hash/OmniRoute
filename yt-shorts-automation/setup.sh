#!/usr/bin/env bash
# OmniRoute YouTube Shorts Automation — one-shot setup
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/4] Python venv"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> [2/4] Hindi font (Noto Sans Devanagari) — already bundled in assets/fonts/"
if [ ! -f assets/fonts/NotoSansDevanagari.ttf ]; then
  echo "    font missing — downloading…"
  mkdir -p assets/fonts
  curl -sL -o /tmp/nsd_font.json \
    "https://api.github.com/repos/google/fonts/contents/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf"
  python3 - <<'PY'
import base64, json
d = json.load(open('/tmp/nsd_font.json'))
open('assets/fonts/NotoSansDevanagari.ttf', 'wb').write(base64.b64decode(d['content']))
PY
fi

echo "==> [3/4] Ambient background music"
if [ ! -f assets/music/ambient.mp3 ]; then
  .venv/bin/python scripts/generate_ambient_music.py
fi

echo "==> [4/4] .env"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    .env created — add your API keys when ready"
fi

echo ""
echo "✅ Setup complete. Try:"
echo "   .venv/bin/python scripts/make_short.py --tts silent --no-upload   # offline test"
echo "   .venv/bin/python scripts/make_short.py                            # real run"
