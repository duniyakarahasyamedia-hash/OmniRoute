#!/usr/bin/env python3
"""
upload_film.py — DRAG-AND-DROP film assembler (no folders, no commands).

Apne Veo clips is web page par drag-drop karo, Hindi narration likho, aur
"Film Banao" dabao. Ye khud clips ko order karega, Hindi voiceover + subtitles
+ music add karega aur final.mp4 banayega.

Kaise chalayein (apne computer par):
    Windows:  .venv\\Scripts\\python upload_film.py
    Linux/Mac: .venv/bin/python upload_film.py
    (agar .venv nahi hai to pehle: python setup.py)

Phir browser mein kholo:  http://localhost:8900
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORAGE = ROOT / "storage"
FILM = STORAGE / "myfilm"
SHOTS = FILM / "shots"
PORT = 8900

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()

INDEX = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎬 AI Film Studio — Clip Uploader</title>
<style>
 *{box-sizing:border-box}
 body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
      background:#0b0f1c;color:#eaeaf5;min-height:100vh;padding:20px}
 .wrap{max-width:720px;margin:0 auto}
 h1{font-size:20px;margin:4px 0 2px}
 .sub{color:#8b93b3;font-size:13px;margin:0 0 18px}
 .card{background:#141a2e;border:1px solid #232b4d;border-radius:14px;padding:20px;margin-bottom:16px}
 .card h2{font-size:15px;margin:0 0 12px;color:#cdd3ee}
 #drop{border:2px dashed #38436f;border-radius:12px;padding:34px 16px;text-align:center;
       color:#8b93b3;cursor:pointer;transition:.15s;background:#10162a}
 #drop.hover{border-color:#5b7cff;background:#131b38;color:#cdd3ee}
 #drop b{color:#aab4e0}
 input,textarea,select{width:100%;background:#0e1322;border:1px solid #232b4d;color:#eaeaf5;
      border-radius:9px;padding:10px 12px;font-size:14px;font-family:inherit;margin-top:6px}
 textarea{min-height:110px;resize:vertical;line-height:1.6}
 label{font-size:12.5px;color:#8b93b3}
 .row{display:flex;gap:12px}
 .row>div{flex:1}
 ul{list-style:none;padding:0;margin:10px 0 0}
 li{display:flex;align-items:center;gap:10px;background:#0e1322;border:1px solid #232b4d;
    border-radius:9px;padding:8px 12px;margin-top:8px;font-size:13.5px}
 li .n{color:#5b7cff;font-weight:600;min-width:74px}
 li .nm{flex:1;word-break:break-all;color:#cdd3ee}
 li button{background:#2a1530;color:#ff9aa0;border:1px solid #5c2a36;border-radius:7px;
           padding:4px 10px;cursor:pointer;font-size:12px}
 .btn{display:inline-block;background:#3357e8;color:#fff;border:0;border-radius:10px;
      padding:13px 22px;font-size:15px;font-weight:600;cursor:pointer;width:100%}
 .btn:hover{background:#2c4bd4}
 .btn:disabled{background:#2a3150;cursor:not-allowed}
 .hint{color:#707a9c;font-size:12px;margin-top:8px;line-height:1.5}
 #log{background:#0a0e1a;border:1px solid #232b4d;border-radius:10px;padding:12px;
      font-family:ui-monospace,monospace;font-size:12px;white-space:pre-wrap;
      color:#8ee6a8;max-height:200px;overflow:auto;display:none}
 #result{display:none}
 #result video{width:100%;border-radius:10px;background:#000}
 a.dl{display:inline-block;margin-top:10px;background:#1f9d55;color:#fff;text-decoration:none;
      padding:11px 20px;border-radius:10px;font-weight:600}
</style>
</head>
<body>
<div class="wrap">
  <h1>🎬 AI Film Studio — Clip Uploader</h1>
  <p class="sub">Apne Veo clips yahan daalo → narration likho → film banao (kisi folder/command ki zaroorat nahi)</p>

  <div class="card">
    <h2>1️⃣ Apne clips daalo (kheench kar ya click karke)</h2>
    <div id="drop">📂 <b>Clips yahan drag-drop karo</b><br><span class="hint">(multiple .mp4 files — jis order mein daaloge, usi order mein film banegi)</span></div>
    <input type="file" id="file" multiple accept="video/*,.mp4" style="display:none">
    <ul id="list"></ul>
  </div>

  <div class="card">
    <h2>2️⃣ Har scene ki Hindi narration (optional)</h2>
    <textarea id="narr" placeholder="हर लाइन = एक scene की voiceover (जितने clips utni lines)&#10;उदाहरण:&#10;रेगिस्तान की सुनसान रात में...&#10;सालों से यह दरवाज़ा यहीं छिपा था..."></textarea>
    <div class="hint">Khaali chhodo to film bina voiceover ke banegi (sirf clips + music).</div>
  </div>

  <div class="card">
    <h2>3️⃣ Settings + Film Banao</h2>
    <div class="row">
      <div><label>Title</label><input id="title" placeholder="मेरी फिल्म"></div>
      <div><label>Aspect (clips ka ratio)</label>
        <select id="aspect"><option value="9:16">9:16 (Shorts/Reels)</option>
        <option value="16:9" selected>16:9 (YouTube)</option></select></div>
    </div>
    <br>
    <button class="btn" id="make" onclick="makeFilm()">🎬 Film Banao</button>
  </div>

  <div class="card" id="log"></div>

  <div class="card" id="result">
    <h2>✅ Aapki film taiyaar!</h2>
    <video controls src="/final.mp4"></video>
    <a class="dl" href="/final.mp4" download="final.mp4">⬇️ Download final.mp4</a>
  </div>
</div>

<script>
let clips = [];
const drop = document.getElementById('drop');
const fileInput = document.getElementById('file');
drop.onclick = () => fileInput.click();
fileInput.onchange = (e) => addFiles(e.target.files);
['dragover','dragenter'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add('hover');
}));
['dragleave','drop'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove('hover');
}));
drop.addEventListener('drop', e => addFiles(e.dataTransfer.files));

async function addFiles(files){
  for(const f of files){
    if(!/video|mp4/i.test(f.type) && !f.name.toLowerCase().endsWith('.mp4')) continue;
    clips.push(f);
  }
  render();
  for(let i=0;i<clips.length;i++){
    const fd = new FormData();
    fd.append('index', i);
    fd.append('file', clips[i]);
    await fetch('/upload', {method:'POST', body: fd});
  }
  refresh();
}
function render(){
  const ul = document.getElementById('list');
  ul.innerHTML = '';
  clips.forEach((f,i)=>{
    const li = document.createElement('li');
    li.innerHTML = `<span class="n">Scene ${String(i+1).padStart(2,'0')}</span>
      <span class="nm">${f.name}</span>
      <button onclick="del(${i})">✕</button>`;
    ul.appendChild(li);
  });
}
async function del(i){
  clips.splice(i,1);
  render();
  await fetch('/delete?index='+i, {method:'POST'});
  refresh();
}
async function refresh(){
  const r = await fetch('/list'); const d = await r.json();
  const ul = document.getElementById('list');
  // re-sync server list into clips (names only)
  d.clips.forEach((c,i)=>{ if(clips[i]) clips[i].name = c.name; });
}
function makeFilm(){
  const btn = document.getElementById('make');
  btn.disabled = true; btn.textContent = '⏳ Film ban rahi hai...';
  const log = document.getElementById('log');
  log.style.display = 'block'; log.textContent = 'Starting...';
  fetch('/make', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      title: document.getElementById('title').value || 'मेरी फिल्म',
      aspect: document.getElementById('aspect').value,
      narration: document.getElementById('narr').value.split('\\n').map(s=>s.trim()).filter(Boolean)
    })
  }).then(r=>r.json()).then(job => poll(job.id, btn, log));
}
function poll(id, btn, log){
  fetch('/status?id='+id).then(r=>r.json()).then(j=>{
    log.textContent = j.log || '...';
    if(j.done){
      btn.disabled = false; btn.textContent = '🎬 Film Banao';
      if(j.ok){ document.getElementById('result').style.display='block';
        document.getElementById('result').scrollIntoView({behavior:'smooth'}); }
      else { log.textContent += '\\n\\n❌ Kuch galat hua — upar error dekho.'; }
    } else {
      setTimeout(()=>poll(id, btn, log), 1500);
    }
  });
}
refresh();
</script>
</body>
</html>"""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _py() -> list[str]:
    """Return the python used to run this server (has our deps)."""
    return [sys.executable]


def _pipeline() -> Path:
    return ROOT / "scripts" / "veo_film_pipeline.py"


def _parse_multipart(data: bytes, boundary: bytes) -> list[dict]:
    parts = []
    for chunk in data.split(b"--" + boundary):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk in (b"--", b""):
            continue
        header_blob, _, content = chunk.partition(b"\r\n\r\n")
        cd = ""
        for line in header_blob.split(b"\r\n"):
            if line.lower().startswith(b"content-disposition:"):
                cd = line.split(b":", 1)[1].decode("latin1")
        name = re.search(r'name="([^"]*)"', cd)
        filename = re.search(r'filename="([^"]*)"', cd)
        parts.append({
            "name": name.group(1) if name else "",
            "filename": filename.group(1) if filename else "",
            "content": content,
        })
    return parts


def _renumber() -> None:
    clips = sorted(SHOTS.glob("scene_*.mp4"))
    # first normalize to temp names, then rename sequentially
    tmp = []
    for i, c in enumerate(clips, 1):
        t = SHOTS / f"__tmp_{i}.mp4"
        c.rename(t)
        tmp.append(t)
    for i, t in enumerate(tmp, 1):
        t.rename(SHOTS / f"scene_{i:02d}.mp4")


def _list_clips() -> list[str]:
    if not SHOTS.exists():
        return []
    return sorted(p.name for p in SHOTS.glob("scene_*.mp4"))


def _run_make(job_id: str, payload: dict) -> None:
    job = JOBS[job_id]
    log = []
    try:
        FILM.mkdir(parents=True, exist_ok=True)
        SHOTS.mkdir(parents=True, exist_ok=True)

        narration = payload.get("narration") or []
        title = payload.get("title", "मेरी फिल्म")
        aspect = payload.get("aspect", "16:9")

        # write story.json (narration lines -> scenes)
        scenes = []
        clips = _list_clips()
        for i, name in enumerate(clips, 1):
            nar = narration[i - 1] if i - 1 < len(narration) else f"दृश्य {i}"
            scenes.append({"scene": i, "shot": "SHOT", "veo_prompt": nar,
                           "narration_hi": nar})
        story = {"title": title, "logline": title, "style": "cinematic",
                 "scenes": scenes,
                 "metadata": {"title": title, "description": title,
                              "tags": ["ai", "shortfilm", "hindi"]}}
        (FILM / "story.json").write_text(
            json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
        log.append(f"story.json: {len(scenes)} scenes")

        cmd = _py() + [str(_pipeline()), "--out-dir", str(FILM),
                       "--skip-video", "--aspect", aspect]
        if not narration:
            cmd.append("--no-narration")
        log.append("$ " + " ".join(cmd))

        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.append(line)
            job["log"] = "\n".join(log[-80:])
        proc.wait()
        ok = proc.returncode == 0 and (FILM / "final.mp4").exists()
        job["done"], job["ok"] = True, ok
        log.append("✅ final.mp4 taiyaar!" if ok else "❌ assembly failed")
    except Exception as exc:
        log.append(f"❌ Error: {exc}")
        job["done"], job["ok"] = True, False
    job["log"] = "\n".join(log[-120:])


# --------------------------------------------------------------------------- #
class H(BaseHTTPRequestHandler):
    def _send(self, code: int, ctype: str, data: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj):
        self._send(200, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode())

    def _send_file(self, path: Path, ctype: str):
        if not path.exists():
            self._send(404, "text/plain", b"not found")
            return
        data = path.read_bytes()
        self._send(200, ctype, data)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", INDEX.encode())
        elif p == "/list":
            self._json({"clips": [{"name": n} for n in _list_clips()]})
        elif p == "/final.mp4":
            self._send_file(FILM / "final.mp4", "video/mp4")
        elif p == "/status":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            m = re.search(r"id=([^&]+)", qs)
            job = JOBS.get(m.group(1)) if m else None
            self._json(job if job else {"done": True, "ok": False, "log": "no job"})
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        p = self.path.split("?")[0]
        if p == "/upload":
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" in ctype:
                m = re.search(r"boundary=([^;]+)", ctype)
                boundary = m.group(1).encode() if m else b""
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                parts = _parse_multipart(body, boundary)
                filepart = next((x for x in parts if x["filename"]), None)
                indexpart = next((x for x in parts if x["name"] == "index"), None)
                if filepart:
                    SHOTS.mkdir(parents=True, exist_ok=True)
                    idx = int(indexpart["content"]) if indexpart else len(_list_clips())
                    # write all clips as __tmp_ based on index, then renumber
                    (SHOTS / f"__up_{idx}.mp4").write_bytes(filepart["content"])
                    # renumber from scratch using upload order
                    _renumber_from_uploads()
                self._json({"ok": True})
            else:
                self._send(400, "text/plain", b"expect multipart")
        elif p == "/delete":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            m = re.search(r"index=(\d+)", qs)
            if m:
                clips = _list_clips()
                idx = int(m.group(1))
                if 0 <= idx < len(clips):
                    (SHOTS / clips[idx]).unlink(missing_ok=True)
                    _renumber()
            self._json({"ok": True})
        elif p == "/make":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body or b"{}")
            except json.JSONDecodeError:
                payload = {}
            job_id = uuid.uuid4().hex[:12]
            JOBS[job_id] = {"id": job_id, "done": False, "ok": False, "log": ""}
            threading.Thread(target=_run_make, args=(job_id, payload), daemon=True).start()
            self._json({"id": job_id})
        else:
            self._send(404, "text/plain", b"not found")

    def log_message(self, *a):
        pass


def _renumber_from_uploads() -> None:
    """Rename __up_*.mp4 (ordered) into scene_XX.mp4."""
    ups = sorted(SHOTS.glob("__up_*.mp4"), key=lambda p: int(p.stem.split("_")[-1]))
    existing = sorted(SHOTS.glob("scene_*.mp4"))
    # move existing aside
    for i, c in enumerate(existing):
        c.rename(SHOTS / f"__old_{i}.mp4")
    # order: uploads by index then old
    ordered = ups + sorted(SHOTS.glob("__old_*.mp4"), key=lambda p: int(p.stem.split("_")[-1]))
    for i, t in enumerate(ordered, 1):
        t.rename(SHOTS / f"scene_{i:02d}.mp4")


def main() -> int:
    STORAGE.mkdir(exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print("=" * 58)
    print("  AI Film Studio — Clip Uploader")
    print(f"  Browser mein kholo:  http://localhost:{PORT}")
    print("=" * 58)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
