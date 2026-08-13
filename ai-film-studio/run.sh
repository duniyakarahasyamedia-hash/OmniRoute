#!/usr/bin/env bash
# AI Film Studio launcher (Linux/macOS)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
else
  PY=python3
fi
exec "$PY" "$DIR/run_film.py" "$@"
