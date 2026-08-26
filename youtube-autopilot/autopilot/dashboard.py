"""Review dashboard (Flask) — videos dekhna, approve/reject/upload karna.

Chalane ke liye:  python -m autopilot dashboard
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, send_file

from . import config, pipeline

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎬 YouTube Autopilot — Review Dashboard</title>
<style>
  body{font-family:system-ui,sans-serif;background:#0e0e12;color:#eee;margin:0;padding:24px}
  h1{color:#ffd700}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px}
  .card{background:#1a1a22;border:1px solid #2c2c3a;border-radius:12px;overflow:hidden}
  .card video{width:100%;max-height:220px;background:#000}
  .card .body{padding:14px}
  .badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;margin:2px}
  .b-working{background:#444} .b-ready{background:#1b5e20}.b-approved{background:#0d47a1}
  .b-uploaded{background:#4a148c}.b-rejected{background:#7f0000}.b-error{background:#b71c1c}
  .btn{display:inline-block;padding:8px 14px;border-radius:8px;border:0;cursor:pointer;font-weight:700;text-decoration:none;margin:4px 4px 0 0;color:#fff}
  .ok{background:#2e7d32}.no{background:#c62828}.up{background:#1565c0}.meta{background:#37474f;padding:8px;border-radius:8px;font-size:12px;white-space:pre-wrap;margin-top:8px;max-height:160px;overflow:auto}
  .t{color:#ffd700}
</style>
</head>
<body>
<h1>🎬 YouTube Autopilot — Review Dashboard</h1>
<p>Yahan har video ko approve/reject karein. Approve karne par YouTube pe upload ho jayegi
(privacy: config me set ki hui — default <b>private</b>, matlab sirf aap dekh sakte ho).</p>
<div class="grid">
{% for r in runs %}
  <div class="card">
    <div class="body">
      <b class="t">{{ r.story.series if r.story else r.id }}</b>
      <div>
        <span class="badge b-{{ r.status }}">{{ r.status }}</span>
        <span class="badge">{{ r.mode }}</span>
        <span class="badge">{{ r.created }}</span>
      </div>
      {% if r.videos.thumbnail %}<img src="/{{ r.id }}/thumb" width="100%">{% endif %}
      {% for k in ('full','short') %}
        {% if r.videos.get(k) %}
          <video controls preload="metadata" src="/{{ r.id }}/video/{{ k }}"></video>
        {% endif %}
      {% endfor %}
      {% if r.meta %}
      <div class="meta"><b>Title:</b> {{ r.meta.title }}
\n<b>Desc:</b> {{ r.meta.description[:220] }}...</div>
      {% endif %}
      {% if r.results %}
      <p>🔗 {% for k,v in r.results.items() %}<a href="{{ v }}" target="_blank">{{ k }}</a> {% endfor %}</p>
      {% endif %}
      <div>
        {% if r.status == 'ready' %}
          <form method="post" action="/{{ r.id }}/approve" style="display:inline"><button class="btn ok">✅ Approve & Upload</button></form>
          <form method="post" action="/{{ r.id }}/reject" style="display:inline"><button class="btn no">❌ Reject</button></form>
        {% elif r.status == 'approved' %}
          <span>Upload ho raha hai...</span>
        {% elif r.status == 'uploaded' %}
          <span>✅ Uploaded</span>
        {% endif %}
      </div>
    </div>
  </div>
{% else %}
  <p>Abhi koi video nahi hai. Pehle banao: <code>python -m autopilot make --topic "bhutia gudiya"</code></p>
{% endfor %}
</div>
</body></html>"""


def _auth_ok() -> bool:
    tok = os.environ.get("DASHBOARD_TOKEN") or "change-me"
    return request.args.get("token") == tok or request.headers.get("X-Token") == tok


def _check_auth():
    if not _auth_ok():
        return jsonify({"error": "unauthorized — dashboard start karte waqt DASHBOARD_TOKEN set karein"}), 401
    return None


@app.route("/")
def index():
    err = _check_auth()
    if err:
        return err
    runs = pipeline.list_runs()
    return render_template_string(PAGE, runs=runs)


@app.route("/api/runs")
def api_runs():
    err = _check_auth()
    if err:
        return err
    return jsonify(pipeline.list_runs())


@app.post("/<run_id>/approve")
def approve(run_id: str):
    err = _check_auth()
    if err:
        return err
    try:
        m = pipeline.load_manifest(run_id)
        m["status"] = "approved"
        pipeline.save_manifest(m)
        # upload background me na karke sync me karo (progress log ke liye)
        results = pipeline.upload_run(config.load_config(), run_id)
        return redirect(f"/?token={request.args.get('token', '')}")
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.post("/<run_id>/reject")
def reject(run_id: str):
    err = _check_auth()
    if err:
        return err
    m = pipeline.load_manifest(run_id)
    m["status"] = "rejected"
    pipeline.save_manifest(m)
    return redirect("/")


@app.get("/<run_id>/video/<kind>")
def video(run_id: str, kind: str):
    m = pipeline.load_manifest(run_id)
    p = Path(m["videos"].get(kind, ""))
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    return send_file(p, mimetype="video/mp4")


@app.get("/<run_id>/thumb")
def thumb(run_id: str):
    m = pipeline.load_manifest(run_id)
    p = Path(m["videos"].get("thumbnail", ""))
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    return send_file(p, mimetype="image/png")


def main(cfg: dict) -> None:
    port = int(cfg.get("dashboard", {}).get("port", 8765))
    print(f"🎬 Dashboard: http://localhost:{port}/?token={os.environ.get('DASHBOARD_TOKEN', 'change-me')}")
    app.run(host="0.0.0.0", port=port, debug=False)
