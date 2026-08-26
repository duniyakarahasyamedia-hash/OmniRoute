# 🎬 YouTube Autopilot — Make-Joke-Horror Style AI Video Pipeline

Aapke channel ke liye **full automation AI agent** — MAKE JOKE HORROR (@makejokehorror)
jaisi Hindi animated horror videos, **100% automatically**:

```
Story (AI) → Horror Images (AI) → Hindi Voiceover → Subtitles → Horror Music
→ Full Video (16:9) + Short (9:16) → Thumbnail → SEO Title/Desc/Tags
→ Review Dashboard → YouTube Upload (aapki approval ke baad)
```

---

## ⚡ 30-second demo dekhna ho to

Demo pipeline pehle se chala hua hai (`runs/` folder me). Dashboard kholo:

```bash
cd youtube-autopilot
DASHBOARD_TOKEN=your-password ./.venv/bin/python -m autopilot dashboard
# → http://localhost:8765/?token=your-password
```

Demo me **sandbox** providers use hue hain (pehle se bani images/voice) taaki bina kisi
API key ke poori pipeline dikhe. Real production ke liye neeche dekho.

---

## 🚀 Real videos banana (production)

### Step 1 — API keys lagao

```bash
cd youtube-autopilot
cp .env.example .env
# .env edit karo:
#   OPENAI_API_KEY=sk-...          (story + images ke liye)
#   ELEVENLABS_API_KEY=...         (premium Hindi horror voice ke liye)
#   ELEVENLABS voice id config.yaml me voice.voice_id me daalo
```

> 💡 Koi API key nahi? Is repo ke **OmniRoute gateway** se bhi story bana sakte ho —
> config.yaml me `story.provider: omniroute` + `OPENAI_BASE_URL` set karo.

### Step 2 — Story ke saath video banao

```bash
./.venv/bin/python -m autopilot make --topic "भुतिया गुड़िया"          # full + short
./.venv/bin/python -m autopilot make --mode short --topic "siren head" # sirf short
./.venv/bin/python -m autopilot make --story demo/story_demo.json      # apni story se
```

### Step 3 — Review karo

```bash
./.venv/bin/python -m autopilot dashboard
# Browser me kholo → video dekho → ✅ Approve (upload ho jayegi) ya ❌ Reject
```

### Step 4 — YouTube connect karo (sirf ek baar)

```bash
./.venv/bin/python -m autopilot auth
```

Iske liye chahiye:
1. [Google Cloud Console](https://console.cloud.google.com) → naya project
2. **YouTube Data API v3** enable karo
3. **OAuth Client ID** (Desktop app type) banao → JSON download karo
4. Us JSON ko `youtube-autopilot/client_secret.json` naam se rakho
5. `python -m autopilot auth` → browser me login → ho gaya ✅

Upload **private** hota hai default (config.yaml me `default_privacy`) — aap YouTube
Studio me jaake public karoge jab quality pasand aaye. Ya `--privacy public` bhi kar
sakte ho.

### Step 5 — Daily auto-pilot (roz nayi video)

```bash
./.venv/bin/python -m autopilot daily --interval 24   # har 24h me nayi story+video
```

Har video review dashboard pe aayegi — aap bas approve karte jaao. 🎉

---

## 🧩 Pipeline kaise kaam karti hai

| Stage | Kaam | Providers |
|---|---|---|
| **story** | LLM se Hindi horror script (MJH style, scenes + narration + image prompts) | openai / omniroute / file |
| **images** | Har scene ki 3D cartoon horror image + thumbnail source | openai (gpt-image-1) / replicate / sandbox |
| **voice** | Hindi dramatic narration | elevenlabs (best) / openai tts / sandbox |
| **music** | Procedural horror BGM — drone + heartbeat + tension (100% copyright-free) | built-in (numpy) |
| **render** | Zoom/pan effects, Devanagari subtitles, music mix | ffmpeg (bundled) |
| **meta** | MJH-style Hindi SEO title, description, 24+ tags | built-in |
| **upload** | YouTube Data API v3 — private/unlisted/public + custom thumbnail | google api |

Output har baar `runs/<run_id>/` me milta hai:
```
full/full.mp4          ← 1920×1080 (16:9) full video
short/short.mp4        ← 1080×1920 (9:16) YouTube Shorts
thumbnail/thumbnail.png← custom thumbnail (Hindi title ke saath)
meta/meta.json         ← title, description, tags
story/story.json       ← poori script
manifest.json          ← run ka status (ready → approved → uploaded)
```

---

## ⚙️ Config (`config.yaml`)

- `channel.*` — channel naam, privacy, category
- `story.*` — model, scenes count, target length, characters (apne characters likho!)
- `images.*` — provider/model/style prefix
- `voice.*` — provider, voice id, speed
- `music.*` — BGM on/off, volume
- `video.*` — resolution, fps, quality (CRF)
- `subtitles.*` — font size/color
- `dashboard.*` — port + token

**Sandbox mode** (bina keys ke full test):
```bash
export AP_STORY__PROVIDER=file AP_IMAGES__PROVIDER=sandbox AP_VOICE__PROVIDER=sandbox
./.venv/bin/python scripts/stage_and_run_demo.py
```

---

## 📌 Notes

- Demo me voice **AI-auditioned Hindi narrator** se banayi gayi hai (premium pipeline
  me ElevenLabs se aap apni channel voice choose kar sakte ho).
- Demo story `demo/story_demo.json` — original story, MJH jaisi structure (hook →
  tension → cliffhanger).
- Saari visuals AI-generated hain — copyright-safe.
- Music procedurally generated hai — 100% copyright-free (Content ID strike ka koi dar nahi).
- Har run ka status `manifest.json` me track hota hai.

## 🔒 Privacy

`.env`, `client_secret.json`, `runs/` — sab `.gitignore` me hain. API keys kabhi
commit nahi hoti.
