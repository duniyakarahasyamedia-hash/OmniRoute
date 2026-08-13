# 🎬 AI Film Studio — AI YouTube Automation (Short Movie / Film Making)

Hindi-first, fully-automated **short-film / faceless YouTube** pipeline — built on top of
the tools already present in this monorepo:

| Tool | Role |
| --- | --- |
| **MoneyPrinterTurbo** (`repos/MoneyPrinterTurbo`) | Script → voiceover → subtitles → BGM → final video + auto-publish |
| **Veo 3.1** (Google Gemini API) | AI cinematic scene clips (text-to-video) |
| **Wan2.1** (`repos/Wan2.1`) | Open-source alternative to Veo (runs on your own GPU, no per-video cost) |
| **Gemini** (free Flash tier) | Hindi script + shot-list generation |
| **Edge-TTS** (`hi-IN` voices) | Free Hindi voiceover |

```
idea ──▶ [Gemini Flash] ──▶ story + shot-list ──▶ [Veo 3.1 / Wan2.1] ──▶ scene clips
                                                          │
                          Hindi voiceover + SRT  (edge-tts, free)
                                                          │
                          [ffmpeg] final.mp4  ──or──▶ [MoneyPrinterTurbo] burned subtitles + BGM
                                                          │
                                          [YouTube Data API] auto-upload + Hindi captions
```

---

## 0. Pehle ye samajh lo (billing reality-check) 💸

Aapke paas **Google AI Studio Pro** hai. Important baat:

| Feature | Kaise milta hai | Kharcha |
| --- | --- | --- |
| Hindi **script + shot-list** (Gemini Flash) | Free API key | ₹0 |
| Hindi **voiceover** (Edge-TTS) | koi key nahi chahiye | ₹0 |
| **Veo 3.1** video via **Gemini app / Flow** | Pro subscription ke credits (~50 Veo Fast/month, 720p) | included in Pro |
| **Veo 3.1** video via **API** (is pipeline ke liye) | ⚠️ **paid Cloud billing chahiye** — subscription ki Veo credits API par nahi lagti | ~$0.15/sec (Fast) |
| **Wan2.1** video (open-source) | apna GPU (RTX 4090 / 8GB VRAM) | ₹0 per video |

> **Shortcut (sasta tareeka):** script + voiceover + stitch sab free hain. Sirf Veo clips
> ke liye either (a) Gemini app/Flow mein manually clips banao aur `shots/` folder mein daal
> do, ya (b) paid API billing lagao, ya (c) Wan2.1 apne GPU par chalao.

---

## ⚡ One-command + Batch + Auto-scheduler (full automation)

Sab kuch ek command se — `run_film.py` orchestrator:

```bash
cd ai-film-studio

# 1 film, cinematic (Veo)
python3 run_film.py --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है"

# faceless (₹0) + YouTube par private upload
python3 run_film.py --idea "भारत के 5 रहस्यमयी स्थान" --engine mpt --upload

# Wan2.1 (apna GPU)
python3 run_film.py --idea "..." --engine wan21 --ckpt-dir ../repos/Wan2.1/Wan2.1-T2V-1.3B

# BATCH: ideas.txt se back-to-back N videos (ek line = ek video)
python3 run_film.py --batch ideas.txt --engine mpt --upload
```

**Auto-scheduler** (roz 1 video khud banao + upload karo):

```bash
# 1) ideas daalo (queue.example.txt ko copy karo):
cp queue.example.txt queue.txt

# 2) cron se daily 7 AM:
crontab -e
0 7 * * * cd /home/user/OmniRoute/ai-film-studio && \
          /usr/bin/python3 scheduler.py --engine mpt --upload >> logs/scheduler.log 2>&1

# ya daemon ki tarah chalao (har 24h ek video):
python3 scheduler.py --engine mpt --upload --loop
```

- `queue.txt` → pending ideas; `done.txt` → processed ideas (re-run ke liye clear karo)
- har run ka full log `logs/runs.log` mein milta hai

> **`--engine` options:** `veo` (cinematic, paid API) · `mpt` (faceless, ₹0) · `wan21` (open-source GPU)

---

## 1. Setup (ek baar) — ek hi command

```bash
cd ai-film-studio
python3 setup.py          # venv + dependencies + config + MPT + ffmpeg sab ready

# phir aapki Gemini key daalo (setup.py yahi remind karega):
#   ai-film-studio/config.toml           -> gemini_api_key = "..."
#   repos/MoneyPrinterTurbo/config.toml  -> gemini_api_key = "..."

# ab run karo:
./run.sh --idea "आपकी कहानी" --engine mpt      # Linux/macOS
run.bat --idea "आपकी कहानी" --engine mpt       # Windows
```

> `setup.py` kya karta hai: Python 3.11 check → `.venv` banata hai → saari deps
> install (google-genai, edge-tts, YouTube API, ffmpeg fallback) → `config.toml`
> banata hai → MoneyPrinterTurbo ka config + `uv sync` → ffmpeg verify. Idempotent
> hai — dobara chalane par skip karta hai jo already ready hai.

### Manual setup (agar chaaho)

```bash
# 1) Python 3.11+ chahiye; ffmpeg ya to system par ho ya imageio-ffmpeg se aa jayega
python3 --version          # >= 3.11
ffmpeg -version            # (optional) Ubuntu: sudo apt install ffmpeg

# 2) Python deps (film-studio scripts ke liye)
python3 -m pip install "google-genai>=2.11" edge-tts imageio-ffmpeg

# 3) API key
#    https://aistudio.google.com/app/apikey  se key lo
cp ai-film-studio/config.example.toml ai-film-studio/config.toml
#    ab config.toml mein gemini_api_key = "..." paste karo
```

### MoneyPrinterTurbo bhi setup karo (subtitles + BGM + auto-publish ke liye)

```bash
cd repos/MoneyPrinterTurbo
# Ready-made config (Gemini + Hindi font) copy karo:
cp ../ai-film-studio/templates/moneyprinterturbo.config.toml config.toml
#   apni Gemini key usme daal do:
#   gemini_api_key = "..."        (line ~98)
#   gemini_model_name = ""        (registry default, ya "gemini-2.5-flash" for free)

python3 -m pip install uv        # agar uv nahi hai
uv sync --frozen                 # dependencies install (pehli baar time lagega)
```

---

## 2. Path A — Faceless video (fastest, ₹0, stock footage)

MoneyPrinterTurbo ka native flow: ek topic do, woh Hindi script + voiceover + stock
footage + subtitles + BGM ka full video bana deta hai.

```bash
cd repos/MoneyPrinterTurbo

# Pexels se free stock footage (pehle https://www.pexels.com/api/ se free key lo,
# config.toml mein pexels_api_keys = ["..."] daalo)
uv run python cli.py \
  --video-subject "एक रहस्यमयी गांव की सच्ची कहानी" \
  --video-language hi-IN \
  --voice-name hi-IN-SwaraNeural-Female \
  --video-aspect 9:16 \
  --font-name Hind-Bold.ttf \
  --subtitle-enabled

# WebUI bhi chala sakte ho:
uv run python main.py     # http://127.0.0.1:8080/docs  (API) 
sh webui.sh               # Streamlit UI
```

Hindi voice options (Edge-TTS, free):
- `hi-IN-SwaraNeural-Female` (female)
- `hi-IN-MadhurNeural-Male` (male)

---

## 3. Path B — AI Cinematic short-film (Veo 3.1)

Story se poori film: shot-list → Veo clips → Hindi voiceover → final video → YouTube.

```bash
cd ai-film-studio

# (a) sirf script + shot-list (FREE — koi Veo call nahi):
python3 scripts/veo_film_pipeline.py \
  --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है" \
  --num-scenes 6 --aspect 9:16 \
  --skip-video

# (b) full run (Veo API — paid billing chahiye):
python3 scripts/veo_film_pipeline.py \
  --idea "एक अकेला लड़का रेगिस्तान में एक पुराना दरवाज़ा खोजता है" \
  --num-scenes 6 --aspect 9:16
```

Outputs (`storage/film-xxxxxxxx/`):

```
story.json        full shot-list + YouTube metadata
script.txt        Hindi narration
shots/            scene_01.mp4 ... (Veo clips)
audio/            scene audio + voiceover.m4a
subtitles.srt     Hindi captions (YouTube-ready)
final.mp4         assembled film (clips + voiceover)
mpt_commands.sh   re-render via MoneyPrinterTurbo (burned subs + BGM)
```

> Veo clips ko **Gemini app/Flow** se manually banake `shots/` mein daal do, phir
> `--skip-video` ke bina bhi narration+assembly chala sakte ho:
> ```bash
> python3 scripts/veo_film_pipeline.py --idea "..." --skip-video
> # ab shots/ folder mein apni clips daal do, phir:
> # (narration + assembly sirf)
> ```
> *(agar `--skip-video` se shots empty hain, to assembly skip hoti hai — clips daalne ke baad
> script dobara `--no-narration` ke saath nahi; narration wapas banani ho to bina skip chalayen.)*

---

## 4. Path C — Wan2.1 (open-source, apna GPU)

```bash
# Wan2.1 setup (GPU chahiye):
cd repos/Wan2.1 && python -m pip install -r requirements.txt
#   checkpoints download karo (README.md ka "Model Download" section)

cd ai-film-studio
python3 scripts/veo_film_pipeline.py --idea "..." --skip-video --no-narration
python3 scripts/wan21_film_pipeline.py \
  --story storage/film-xxxxxxxx/story.json \
  --task t2v-1.3B \
  --ckpt-dir ../repos/Wan2.1/Wan2.1-T2V-1.3B \
  --aspect 9:16
```

---

## 5. YouTube auto-upload (free, direct Data API)

`upload-post.com` (MoneyPrinterTurbo ki built-in posting) **paid third-party** hai.
Iske bajaye direct **YouTube Data API v3** use karo — free, full control.

```bash
cd ai-film-studio
python3 -m pip install google-api-python-client google-auth google-auth-oauthlib

# ek baar: YouTube Data API enable karo + OAuth Desktop client banao
#   https://console.cloud.google.com/apis/library/youtube.googleapis.com
#   client JSON ko yahan save karo: ai-film-studio/client_secrets.json

python3 scripts/upload_youtube.py storage/film-xxxxxxxx/final.mp4 \
  --metadata storage/film-xxxxxxxx/story.json \
  --captions storage/film-xxxxxxxx/subtitles.srt \
  --privacy private        # public/unlisted/private
```

---

## 6. Niche / channel tips (Hindi faceless)

- **Niche ideas:** horror kahaniyan, pauranik kathayein (Ramayan/Mahabharat retelling),
  motivational, crime mystery, sci-fi micro-films, "10 facts" cinematic.
- **9:16** for Shorts/Reels, **16:9** for long-form.
- Pehle **unlisted/private** upload karke quality check karo, phir schedule/public.
- Titles + tags Hindi mein rakho (metadata.json mein already aata hai).
- Har video ka idea alag rakho — YouTube repetitive AI content ko demote karta hai.
- Veo/API content: Google ke usage policy + YouTube ki AI-generated content disclosure
  (`isAIContent` / "Altered content" flag) ko follow karo.

---

## Files

```
ai-film-studio/
├── config.example.toml                 # apni keys ka template (config.toml = gitignored)
├── setup.py                            # ONE-COMMAND setup (venv + deps + config + MPT)
├── requirements.txt                    # python dependencies
├── run.sh / run.bat                    # launchers (Linux/macOS / Windows)
├── run_film.py                         # ONE-COMMAND orchestrator (single/batch/upload)
├── scheduler.py                        # daily auto-runner (cron/daemon)
├── queue.example.txt                   # ideas list ka template (queue.txt = gitignored)
├── templates/moneyprinterturbo.config.toml   # MPT config (Gemini + Hindi font) ready-made
└── scripts/
    ├── veo_film_pipeline.py            # story -> shot-list -> Veo clips -> final.mp4
    ├── wan21_film_pipeline.py          # same, but open-source Wan2.1 clips
    └── upload_youtube.py               # YouTube Data API upload + Hindi captions
```
