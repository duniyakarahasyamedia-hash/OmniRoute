# Saathi Studio — YouTube Automation Master Agent

End-to-end YouTube desk: research → topics → script → packaging → thumbnails → voiceover → preview render → YouTube publish.

```bash
cd saathi
node server.js
```

## Pipeline

1. Channel setup
2. Market research + live YouTube search
3. Topic lab (10 scored ideas, live titles mixed in)
4. Deep research
5. Script room
6. Packaging + generated thumbnails
7. Production kit + voiceover + preview video
8. Upload pack + YouTube publish (private)

## Connections

- **Local engine** — always on, no key
- **Pollinations** — free text / image / audio from the browser
- **Groq / Gemini / OpenAI / Claude / OpenRouter** — optional rewrite models
- **YouTube Data API key** — live search
- **Google OAuth Client ID** — upload video + thumbnail

Redirect URI must be this exact page URL. Publish defaults to **private**.

Click **Connect remaining** to wire live search, thumbs, VO, and preview in one pass.
