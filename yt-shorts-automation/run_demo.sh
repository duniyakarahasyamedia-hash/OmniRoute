#!/usr/bin/env bash
# Quick demo — builds a real Short with template script + silent TTS + gradient
# backgrounds (no network keys needed) so you can verify the pipeline end-to-end.
set -euo pipefail
cd "$(dirname "$0")"

.venv/bin/python scripts/make_short.py --tts silent --no-upload --topic "${1:-अंटार्कटिका में रेत के टीले क्यों हैं?}"
