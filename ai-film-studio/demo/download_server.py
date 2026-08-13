#!/usr/bin/env python3
"""Serve the demo video with a clean download page (works through the live preview)."""
import os
import socketserver
from http.server import BaseHTTPRequestHandler

BASE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE, "AI_Film_Studio_Demo.mp4")
SIZE = os.path.getsize(FILE)

PAGE = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Film Studio — Demo Download</title>
<style>
  body { font-family: system-ui, sans-serif; background:#0f1220; color:#fff;
         display:flex; flex-direction:column; align-items:center; justify-content:center;
         min-height:100vh; margin:0; text-align:center; padding:24px; }
  .card { background:#1a1e33; border:1px solid #2c3355; border-radius:16px;
          padding:32px 40px; max-width:560px; }
  h1 { font-size:22px; margin:0 0 6px; }
  p { color:#aab; margin:8px 0 20px; }
  a.btn { display:inline-block; background:#ff5c5c; color:#fff; text-decoration:none;
          font-weight:600; padding:14px 28px; border-radius:10px; font-size:17px; }
  a.btn:hover { background:#ff4040; }
  .meta { font-size:13px; color:#889; margin-top:18px; }
</style>
</head>
<body>
  <div class="card">
    <h1>🎬 AI Film Studio — Demo Video</h1>
    <p>32-second Hindi short film (voiceover + subtitles + music)</p>
    <a class="btn" href="/download">⬇️ Download MP4</a>
    <div class="meta">AI_Film_Studio_Demo.mp4 · 10.4 MB · 1920×1080 · 30fps</div>
  </div>
</body>
</html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/download":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header(
                "Content-Disposition", 'attachment; filename="AI_Film_Studio_Demo.mp4"'
            )
            self.send_header("Content-Length", str(SIZE))
            self.end_headers()
            with open(FILE, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("0.0.0.0", 8099), H) as httpd:
    print("Serving demo download page on http://0.0.0.0:8099")
    httpd.serve_forever()
