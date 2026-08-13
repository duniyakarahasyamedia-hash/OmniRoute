#!/usr/bin/env python3
"""Tiny webhook server so n8n (or anything) can trigger the pipeline via HTTP.

Usage:
  python scripts/webhook_server.py --port 8899

Endpoints:
  POST /make            → run one short (body: {"topic": "..."} optional)
  GET  /health          → ok

Then import n8n/workflow_omniroute_shorts.json, set the URL to
http://localhost:8899/make  (or your LAN IP), and let the Cron node
schedule daily shorts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter logs
        print(f"[webhook] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health"):
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/make"):
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                body = {}
        topic = (body.get("topic") or "").strip() or None
        no_upload = bool(body.get("no_upload", False))
        print(f"[webhook] starting short (topic={topic}, no_upload={no_upload})", flush=True)
        try:
            cmd = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/make_short.py")]
            if no_upload:
                cmd.append("--no-upload")
            if topic:
                cmd += ["--topic", topic]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 20)
            ok = proc.returncode == 0
            self._json(200 if ok else 500, {
                "ok": ok,
                "stdout": (proc.stdout or "")[-2000:],
                "stderr": (proc.stderr or "")[-1000:],
            })
        except subprocess.TimeoutExpired:
            self._json(500, {"ok": False, "error": "pipeline timeout"})

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8899)
    args = ap.parse_args()
    print(f"webhook server on http://{args.host}:{args.port}  (POST /make, GET /health)")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
