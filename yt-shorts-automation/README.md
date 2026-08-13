# 🎬 OmniRoute YouTube Shorts Automation — दुनिया का रहस्य

**Fully AI-powered YouTube Shorts pipeline (Hindi Mystery/Facts channel)**
Topic → Script → Voiceover → Video → Captions → Thumbnail → Title/Tags → **Auto-Upload** — sab kuch automatic.

Built for the **OmniRoute** monorepo: uses **OmniRoute** as the free AI gateway, runs standalone
(no keys required for a basic run), and optionally bridges into **MoneyPrinterTurbo** and **n8n**.

---

## ✨ Kya-kya milta hai

| Feature | Detail |
|---|---|
| 🤖 AI script | OmniRoute/OpenAI-compatible LLM se viral Hindi script (hook + 4-5 lines + CTA) — no key? Template mode (still works) |
| 🗣️ Voiceover | `edge-tts` free Hindi neural voices (Madhur/Swara/Aarav) + gTTS + OpenAI TTS fallbacks |
| 🎞️ Video | 1080x1920 vertical, Ken-Burns zoom, stock footage (Pexels/Pixabay) ya AI gradients (no key needed) |
| 💬 Captions | **Word-level karaoke captions** (har koi word highlight hota hai) — proper Devanagari shaping (libass + HarfBuzz) |
| 🎨 Cover card | 2.6s intro card — channel brand + hook + "सब्सक्राइब करें" |
| 🖼️ Thumbnail | 1280x720 AI thumbnail |
| 🏷️ Metadata | Viral title, description, hashtags, tags |
| 🚀 Upload | YouTube Data API v3 — private (review) ya public, auto |
| 🔁 Scheduling | `run_all.py` (loop), cron, ya n8n workflow (included) |
| 🔗 OmniRoute | LLM calls OmniRoute ke OpenAI-compatible endpoint se — free tiers use karo |
| 🔌 MPT bridge | MoneyPrinterTurbo rendering engine se bhi video banao (optional) |

---

## 📁 Structure

```
yt-shorts-automation/
├── config.yaml            # Channel/video/LLM/TTS/media/topics config (sab yahin)
├── .env.example           # API keys → .env me copy karo
├── setup.sh               # One-shot setup
├── run_demo.sh            # Offline demo (no keys needed)
├── requirements.txt
├── assets/
│   ├── fonts/             # Noto Sans Devanagari (bundled — proper Hindi rendering)
│   └── music/             # ambient.mp3 (generated) — apna track yahan daalo
├── src/                   # Pipeline modules (config, llm, script_writer, tts,
│                          #   media_fetcher, visuals, composer, metadata, uploader, pipeline)
├── scripts/
│   ├── make_short.py      # ⭐ ek Short banao (CLI)
│   ├── run_all.py         # Bulk / scheduled runs
│   ├── oauth_youtube.py   # YouTube OAuth setup (1 baar)
│   ├── upload_pending.py  # Pending drafts upload karo
│   ├── generate_ambient_music.py
│   └── webhook_server.py  # n8n trigger ke liye HTTP endpoint
├── moneyprinter/          # MoneyPrinterTurbo bridge (optional)
└── n8n/                   # n8n workflow JSON (scheduled trigger)
```

---

## 🚀 Quick Start (2 minute)

```bash
cd yt-shorts-automation
./setup.sh                      # venv + deps + font + music + .env

# Offline test (silent voice, gradient bg — koi key nahi chahiye):
./run_demo.sh

# Real test run (upload nahi, sirf video):
.venv/bin/python scripts/make_short.py --tts silent --no-upload

# Real run (edge-tts voice + auto-upload private draft):
.venv/bin/python scripts/make_short.py
```

Output: `output/short_YYYYMMDD_HHMMSS/short.mp4` + `thumbnail.jpg` + `metadata.json` + `run_report.json`.

---

## 🎯 Config — `config.yaml` me sab kuch

- **`channel`** — name, handle, category, default privacy (`private` = review ke baad publish)
- **`llm`** — `base_url: http://localhost:20128/v1` (OmniRoute), model, `use_ai: true/false`
- **`tts`** — backend (`edge`/`gtts`/`openai`/`silent`), voice, rate, pitch
- **`media`** — source (`pexels`/`pixabay`/`none`), keyword map (Hindi → English search)
- **`topics`** — topic bank + template facts (AI band ho to ye use hote hain)
- **`metadata`** — title/description templates, tags
- **`youtube`** — credentials paths

**.env me keys daalo:** (sab optional)

| Key | Kahan se milegi | Chahiye kya ke liye |
|---|---|---|
| `OMNIROUTE_BASE_URL` | OmniRoute local (default) | AI script/topic (optional — template mode bhi hai) |
| `PEXELS_API_KEY` | [pexels.com/api](https://www.pexels.com/api/) free | Stock footage |
| `PIXABAY_API_KEY` | [pixabay.com/api/docs](https://pixabay.com/api/docs/) free | Stock footage (fallback) |
| `YT_CLIENT_SECRETS` | Google Cloud Console | Auto-upload |

> Bina kisi key ke bhi pipeline chalega: template script + gradient backgrounds + silent voice.
> Real TTS (edge-tts) ke liye bhi **koi key nahi** chahiye — free Microsoft neural voices!

---

## 📺 YouTube Setup (auto-upload ke liye, 5 min)

1. [console.cloud.google.com](https://console.cloud.google.com/) → project banao
2. **Enable "YouTube Data API v3"**
3. **OAuth consent screen** → External → scope `.../auth/youtube.upload` → apne aap ko test user banao
4. **Credentials** → OAuth Client ID → **Desktop app** → JSON download
5. JSON ko save karo: `yt-shorts-automation/credentials/client_secrets.json`
6. Token banao:
   ```bash
   .venv/bin/python scripts/oauth_youtube.py
   ```
7. Done! Ab har run par video auto-upload hogi (`config.yaml` → `default_privacy: private` = draft review, `public` = direct publish)

> **⚠️ YouTube rules:** Faceless channels ke liye bhi original content policy apply hoti hai.
> Own voiceover + own script + licensed footage = safest. Monetization se pehle channel ko
> review pass karna hoga. Videos me apna watermark already aata hai.

---

## ⏰ Scheduling

**Option 1 — built-in loop:**
```bash
.venv/bin/python scripts/run_all.py --every 86400 --forever   # har din ek (24h)
.venv/bin/python scripts/run_all.py --count 5 --every 3600    # 5 videos, har ghante
```

**Option 2 — cron:**
```cron
0 10 * * * cd /path/to/yt-shorts-automation && .venv/bin/python scripts/make_short.py >> output/cron.log 2>&1
```

**Option 3 — n8n (visual):**
1. Webhook server chalao: `.venv/bin/python scripts/webhook_server.py --port 8899`
2. n8n me import karo: `n8n/workflow_omniroute_shorts.json`
3. URL apne machine ke IP pe set karo (e.g. `http://192.168.1.5:8899/make`)

---

## 🔗 OmniRoute Integration

Pipeline OmniRoute ke **OpenAI-compatible endpoint** se LLM calls karta hai:

```
POST http://localhost:20128/v1/chat/completions
```

- OmniRoute chalu hai → `config.yaml` me `llm.base_url` wahi rakh do (default already set hai)
- LLM down/off → pipeline **automatically template mode** me chali jati hai (kuch bhi crash nahi hota)
- MoneyPrinterTurbo ke andar bhi OmniRoute use kar sakte ho — see `moneyprinter/mpt_overrides.toml`
  (`llm_provider = "openai"`, `openai_base_url = "http://localhost:20128/v1"`)

---

## 🔌 MoneyPrinterTurbo Bridge (optional)

MPT ek alternate rendering engine hai (repos/MoneyPrinterTurbo). Uske saath:

```bash
cd repos/MoneyPrinterTurbo && cp config.example.toml config.toml
# mpt_overrides.toml ke values config.toml me merge karo (LLM→OmniRoute, 9:16, Hindi voice)
# MPT start karo (docker compose up / webui)
cd ../../yt-shorts-automation
.venv/bin/python moneyprinter/bridge_mpt.py --topic "अंटार्कटिका का रहस्य"
```

Bridge MPT ka `POST /api/v1/videos` endpoint use karta hai with our AI-generated script.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `LLM call failed (Connection refused)` | Normal — OmniRoute nahi chal raha to template mode use hota hai. OmniRoute start karo to AI scripts milein |
| edge-tts error | Network/firewall — `--tts gtts` try karo, ya `--tts silent` for testing |
| Captions me Hindi sahi nahi | Font bundled hai — `assets/fonts/NotoSansDevanagari.ttf` exist karna chahiye |
| `ffmpeg` not found | `imageio-ffmpeg` bundled hai; ya `FFMPEG_PATH=/usr/bin/ffmpeg` set karo |
| Upload fail: token expired | `python scripts/oauth_youtube.py` dobara chalao |
| Music nahi sunai de rahi | `assets/music/ambient.mp3` generate karo: `scripts/generate_ambient_music.py` |
| Video 60s se lamba | Script auto-trim hota hai (`max_duration` in config.yaml) |

---

## 💰 Cost

| Component | Cost |
|---|---|
| AI script (OmniRoute) | $0 — free tiers / local models |
| TTS (edge-tts) | $0 |
| Stock footage | $0 (Pexels/Pixabay free tiers) ya gradients |
| YouTube upload | $0 |
| Total | **$0** (sirf aapka time + keys setup) |

---

## 🧪 Pipeline Tested

End-to-end verified in this repo (silent mode): 1080x1920@30fps MP4, karaoke captions with
proper Devanagari shaping (HarfBuzz-verified), cover card, watermark, ambient music mix,
thumbnail, metadata — full run ~40s. Real TTS/upload aapki machine par credentials ke saath chalega.

Happy automating! 🚀
