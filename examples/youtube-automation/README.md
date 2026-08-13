# 🎬 YouTube AI Automation Kit (yt-auto)

> **Ek endpoint, pura automation.** Script → SEO metadata → thumbnail → voiceover → Shorts — sab kuch OmniRoute ke through, free/advanced models ke saath.
> Zero dependencies (sirf Node 18+ chahiye).

English version below. 👇

---

## 🚀 5 minute setup

### Step 1 — OmniRoute chalao

```bash
npm install -g omniroute
omniroute
```

Dashboard khulega: `http://localhost:20128`

### Step 2 — Google connect karo (ek hi connection)

**Option A — Google AI Pro subscription (recommended, aapka case):**

1. Dashboard → **Providers** → **Add Provider** → **Antigravity** (ya **agy**)
2. **Login with Google** → apne Google AI Pro wale account se sign-in karo
3. Bas! Ab aapke paas **Gemini 3.1 Pro, Gemini 3.5 Flash, Claude Sonnet/Opus 4.6** — sab ek endpoint pe.

> OmniRoute projectId automatically discover kar leta hai — kuch bhi manually nahi karna.
> Detail guide: [docs/guides/ANTIGRAVITY-ONBOARDING.md](../../docs/guides/ANTIGRAVITY-ONBOARDING.md)

**Option B — Free Gemini API key (backup, $0):**

1. <https://aistudio.google.com/apikey> → free API key banao
2. Dashboard → **Providers** → **Add Provider** → **Gemini** → key paste karo → Connect
3. Ye aapko TTS voiceover + free-tier Gemini models deta hai (1,500 req/day free).

### Step 3 — API key copy karo

Dashboard → **Endpoints** → API key copy karo, phir is folder me `.env` banao:

```bash
cp .env.example .env
# .env me OMNIROUTE_KEY=apni_key paste karo
```

### Step 4 — Test & run

```bash
node yt-auto.mjs test                      # connection check
node yt-auto.mjs full "AI se paise kaise kamaye"   # 🚀 pura pipeline ek command me
```

Output milega `output/ai-se-paise-kaise-kamaye/` me:

| File                    | Kya hai                                             |
| ----------------------- | --------------------------------------------------- |
| `script.md` / `.json`   | Word-for-word script: hook → sections → CTA → outro |
| `metadata.md` / `.json` | 5 titles, description, 30 tags, hashtags, chapters  |
| `thumbnail.png`         | Generated thumbnail + concept + text overlay        |
| `shorts.md` / `.json`   | 30-45s Shorts script + captions                     |
| `voiceover.mp3`         | AI narration (Gemini TTS)                           |

---

## 🛠️ Saare commands

```bash
node yt-auto.mjs test                          # OmniRoute + models check
node yt-auto.mjs ideas "personal finance" --count 15
node yt-auto.mjs script "My topic" --lang hinglish   # hinglish | hi | en
node yt-auto.mjs meta "My topic"
node yt-auto.mjs thumb "My topic"
node yt-auto.mjs shorts "My topic"
node yt-auto.mjs tts output/my-topic/script.md
node yt-auto.mjs full "My topic"               # sab kuch ek saath
```

## ⚙️ Config (`.env` ya environment variables)

| Variable         | Default                               | Kya karta hai                              |
| ---------------- | ------------------------------------- | ------------------------------------------ |
| `OMNIROUTE_URL`  | `http://localhost:20128/v1`           | Gateway endpoint                           |
| `OMNIROUTE_KEY`  | —                                     | Dashboard → Endpoints se API key           |
| `YT_MODEL`       | `auto`                                | Script ke liye heavy model (smart routing) |
| `YT_FAST_MODEL`  | `auto`                                | Tags/metadata ke liye fast model           |
| `YT_TTS_MODEL`   | `gemini/gemini-3.1-flash-tts-preview` | Voiceover model                            |
| `YT_IMAGE_MODEL` | `auto`                                | Thumbnail generation model                 |
| `YT_LANG`        | `hinglish`                            | `hinglish` / `hi` / `en`                   |
| `YT_NICHE`       | `general`                             | Aapka channel niche                        |
| `YT_VOICE`       | `Kore`                                | TTS voice name                             |

`auto` = OmniRoute khud best connected provider choose karta hai, rate-limit pe automatic fallback ke saath. Specific model chahiye to provider prefix use karo: `antigravity/gemini-3.1-pro`, `agy/gemini-3.5-flash-high`, `gemini/gemini-2.5-flash`.

## 💡 Pro tips — free me maximum kaise

1. **Script likhne ke liye** Google AI Pro wala connection (`antigravity/gemini-3.1-pro`) — best quality.
2. **Tags/metadata** `auto` pe chhodo — free providers (Pollinations, OpenCode Free, etc.) use ho jaate hain.
3. **Voiceover** Gemini API key (Option B) se — free tier me TTS milta hai.
4. Quota khatam ho jaye to OmniRoute **automatically dusre provider pe fallback** karta hai — aapka pipeline nahi rukta.
5. Ek hi Google account ka quota Antigravity IDE, agy CLI aur OmniRoute me **shared** hota hai — heavy din me `YT_FAST_MODEL=auto` rakho.

## 🔧 Troubleshooting

- **`Cannot reach OmniRoute`** → `omniroute` chal raha hai? Port 20128 check karo.
- **`401/403`** → `OMNIROUTE_KEY` galat hai; Dashboard → Endpoints se dobara copy karo.
- **Thumbnail image nahi bani** → concept + `image_prompt` save ho jata hai — kisi bhi image AI me paste kar do.
- **TTS fail** → Gemini API key (Option B) connect hai na? `YT_TTS_MODEL` change karke try karo.

---

## English summary

**yt-auto** turns one topic into a complete YouTube package — word-for-word script (hook, sections, b-roll notes, CTA), SEO metadata (5 titles, description, 30 tags, hashtags, chapters, pinned comment), a generated thumbnail, a viral Shorts cutdown, and an AI voiceover — all through your single OmniRoute endpoint.

It speaks the OpenAI-compatible API (`/v1/chat/completions`, `/v1/images/generations`, `/v1/audio/speech`), so it also works against **any** OpenAI-compatible gateway: set `OMNIROUTE_URL` + `OMNIROUTE_KEY` and go.

Connect your **Google AI Pro** subscription once via Dashboard → Providers → **Antigravity/agy** (OAuth), optionally add a free **Gemini API key** for TTS, then run `node yt-auto.mjs full "your topic"`.
