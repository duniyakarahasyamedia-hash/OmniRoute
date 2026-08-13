#!/usr/bin/env python3
"""Serve the AI Film Studio demo video with an in-browser player (Range support)."""
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE, "AI_Film_Studio_Demo.mp4")
SIZE = os.path.getsize(FILE)

PAGE = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎬 AI Film Studio — Demo</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background:#070b14; color:#eaeaf5; min-height:100vh; display:flex;
         flex-direction:column; align-items:center; padding:24px 16px; }
  h1 { font-size:20px; margin:6px 0 2px; text-align:center; }
  .sub { color:#8b93b3; font-size:13px; margin:0 0 16px; text-align:center; }
  .wrap { width:100%; max-width:960px; background:#000; border-radius:14px;
          overflow:hidden; box-shadow:0 10px 40px rgba(0,0,0,.6); border:1px solid #1c2340; }
  video { width:100%; display:block; background:#000; }
  .bar { display:flex; gap:12px; margin-top:14px; flex-wrap:wrap; justify-content:center; }
  a.btn { background:#1c2340; color:#eaeaf5; border:1px solid #2c3355; padding:10px 18px;
          border-radius:9px; text-decoration:none; font-size:14px; }
  a.btn:hover { background:#252e52; }
  .note { color:#707a9c; font-size:12px; margin-top:14px; text-align:center; max-width:560px; line-height:1.5; }
</style>
</head>
<body>
  <h1>🎬 AI Film Studio — Cinematic Space Odyssey (Demo)</h1>
  <p class="sub">Hindi voiceover · subtitles · VFX · 36 sec · 1920×1080</p>
  <div class="wrap">
    <video controls preload="auto" playsinline>
      <source src="/video.mp4" type="video/mp4">
      Aapka browser video tag support nahi karta.
    </video>
  </div>
  <div class="bar">
    <a class="btn" href="/video.mp4" download="AI_Film_Studio_Demo.mp4">⬇️ Download</a>
  </div>
  <p class="note">Ye demo is sandbox mein banaya gaya (images + procedural motion + VFX).
  Asli full-motion clips ke liye Gemini app mein Veo 3.1 use karo — prompts
  VEO_PROMPTS.md mein hain.</p>
</body>
</html>"""


class H(BaseHTTPRequestHandler):
    def _send_bytes(self, code: int, ctype: str, data: bytes, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_file(self, start: int, end: int):
        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{SIZE}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(FILE, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(chunk)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send_bytes(200, "text/html; charset=utf-8", PAGE.encode())
            return
        if path == "/video.mp4":
            rng = self.headers.get("Range")
            if rng:
                m = re.match(r"bytes=(\d*)-(\d*)", rng)
                start = int(m.group(1)) if m and m.group(1) else 0
                end = int(m.group(2)) if m and m.group(2) else SIZE - 1
                end = min(end, SIZE - 1)
                start = min(start, end)
                self._send_file(start, end)
            else:
                self._send_file(0, SIZE - 1)
            return
        self._send_bytes(404, "text/plain", b"not found")

    def log_message(self, *args):
        pass


ThreadingHTTPServer.allow_reuse_address = True
print("Demo player on http://0.0.0.0:8100")
ThreadingHTTPServer(("0.0.0.0", 8100), H).serve_forever()
