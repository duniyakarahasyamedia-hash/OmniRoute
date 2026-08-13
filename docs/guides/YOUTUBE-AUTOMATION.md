---
title: "YouTube AI Automation with OmniRoute"
version: 3.8.50
lastUpdated: 2026-08-13
---

# YouTube AI Automation Guide

> **TL;DR**: Connect your Google account once (Antigravity OAuth or a free Gemini API key), then run the bundled `yt-auto` kit to generate full video scripts, SEO metadata, thumbnails, voiceovers and Shorts — all through one OmniRoute endpoint.

The ready-to-use kit lives in [`examples/youtube-automation/`](../../examples/youtube-automation/README.md). It is a zero-dependency Node CLI that only talks to the OpenAI-compatible OmniRoute API (`/v1/chat/completions`, `/v1/images/generations`, `/v1/audio/speech`).

## 1. Connect Google (one connection)

### Option A — Google AI Pro / Google One AI subscription

Use the **Antigravity** provider. It logs in with your Google account via OAuth and exposes the models included in your plan (Gemini 3.x Pro/Flash, Claude Sonnet/Opus variants) on OmniRoute's single endpoint.

1. Dashboard → **Providers** → **Add Provider** → **Antigravity** (or **agy** for the live model catalog).
2. **Login with Google** → sign in with your Google AI Pro account.
3. Done. OmniRoute auto-discovers the Cloud Code `projectId` (see [ANTIGRAVITY-ONBOARDING.md](ANTIGRAVITY-ONBOARDING.md)).

OAuth client credentials are embedded public PKCE values ([Google documents these as non-secret](https://developers.google.com/identity/protocols/oauth2/native-app)), so no extra setup is required. Quota notes and troubleshooting: [ANTIGRAVITY-ONBOARDING.md](ANTIGRAVITY-ONBOARDING.md).

### Option B — Free Gemini API key

1. Create a free key at <https://aistudio.google.com/apikey> (1,500 req/day free tier).
2. Dashboard → **Providers** → **Add Provider** → **Gemini** → paste the key → **Connect**.

This also unlocks Gemini TTS (`gemini-3.1-flash-tts-preview`) for voiceovers.

## 2. Run the automation kit

```bash
cd examples/youtube-automation
cp .env.example .env         # set OMNIROUTE_KEY from Dashboard → Endpoints
node yt-auto.mjs test
node yt-auto.mjs full "your video topic"
```

`full` produces, inside `output/<slug>/`:

- `script.md` / `script.json` — word-for-word script: hook, intro, sections with b-roll notes, CTA, outro
- `metadata.md` / `metadata.json` — 5 titles, SEO description, 30 tags, hashtags, chapters, pinned comment
- `thumbnail.png` + `thumbnail.json` — generated thumbnail, CTR concept, text overlay
- `shorts.md` / `shorts.json` — 30–45 s Shorts cutdown with captions
- `voiceover.mp3` — AI narration via `/v1/audio/speech`

Languages: `--lang hinglish` (default), `--lang hi`, `--lang en`.

## 3. Recommended model routing

| Pipeline step   | Setting          | Suggested value                          |
| --------------- | ---------------- | ---------------------------------------- |
| Script writing  | `YT_MODEL`       | `antigravity/gemini-3.1-pro` (or `auto`) |
| Tags / metadata | `YT_FAST_MODEL`  | `auto` (falls back to free providers)    |
| Thumbnails      | `YT_IMAGE_MODEL` | `auto`                                   |
| Voiceover       | `YT_TTS_MODEL`   | `gemini/gemini-3.1-flash-tts-preview`    |

`auto` lets OmniRoute pick the best connected provider and fall back automatically when a quota is hit — so a batch of video generations never stops mid-run.

## 4. Scaling up

- **Batch ideas**: `node yt-auto.mjs ideas "your niche" --count 20`, then loop `full` over the titles you like.
- **Multiple channels**: keep one `.env` per folder; everything routes through the same gateway.
- **Cost control**: create a dedicated API key (Dashboard → **Endpoints**) with per-key budget limits before wiring the kit into cron/CI.
