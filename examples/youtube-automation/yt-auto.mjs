#!/usr/bin/env node
/**
 * yt-auto — Full YouTube AI automation kit for OmniRoute.
 *
 * One endpoint (OmniRoute) → script, SEO metadata, thumbnail, voiceover, Shorts.
 * Zero dependencies (Node 18+). Configure via env vars or .env / config.json.
 *
 * Usage:
 *   node yt-auto.mjs test
 *   node yt-auto.mjs ideas "personal finance" --count 10
 *   node yt-auto.mjs script "topic" --lang hinglish
 *   node yt-auto.mjs meta "topic"
 *   node yt-auto.mjs thumb "topic"
 *   node yt-auto.mjs shorts "topic"
 *   node yt-auto.mjs tts output/<slug>/script.md --voice Kore
 *   node yt-auto.mjs full "topic"
 */

import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import process from "node:process";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const ROOT = dirname(new URL(import.meta.url).pathname);

/** Minimal .env loader (no deps). */
function loadDotEnv() {
  const out = {};
  for (const file of [join(ROOT, ".env"), join(process.cwd(), ".env")]) {
    if (!existsSync(file)) continue;
    for (const line of readFileSync(file, "utf8").split("\n")) {
      const m = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
      if (!m) continue;
      let v = m[2];
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        v = v.slice(1, -1);
      }
      if (!(m[1] in out)) out[m[1]] = v;
    }
  }
  return out;
}

function loadConfigJson() {
  const file = join(ROOT, "config.json");
  if (!existsSync(file)) return {};
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

const dotEnv = loadDotEnv();
const cfgJson = loadConfigJson();

function cfg(key, fallback) {
  return (
    process.env[key] ??
    dotEnv[key] ??
    cfgJson[key.replace(/^OMNIROUTE_/, "").toLowerCase()] ??
    fallback
  );
}

const CONFIG = {
  baseUrl: (cfg("OMNIROUTE_URL", "http://localhost:20128/v1") || "").replace(/\/+$/, ""),
  apiKey: cfg("OMNIROUTE_KEY", ""),
  model: cfg("YT_MODEL", "auto"), // heavy thinking: script writing
  fastModel: cfg("YT_FAST_MODEL", "auto"), // cheap: tags/metadata
  ttsModel: cfg("YT_TTS_MODEL", "gemini/gemini-3.1-flash-tts-preview"),
  imageModel: cfg("YT_IMAGE_MODEL", "auto"),
  voice: cfg("YT_VOICE", "Kore"),
  lang: cfg("YT_LANG", "hinglish"),
  niche: cfg("YT_NICHE", "general"),
  outDir: cfg("YT_OUT_DIR", join(process.cwd(), "output")),
};

// ---------------------------------------------------------------------------
// CLI helpers
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const command = args[0];

function flag(name, fallback = undefined) {
  const i = args.indexOf(`--${name}`);
  if (i === -1) return fallback;
  return args[i + 1] ?? fallback;
}

const topic = args.slice(1).find((a) => !a.startsWith("--")) || "";

function log(step, msg) {
  console.log(`\x1b[36m[yt-auto]\x1b[0m ${step ? `\x1b[1m${step}\x1b[0m — ` : ""}${msg}`);
}

function warn(msg) {
  console.warn(`\x1b[33m[warn]\x1b[0m ${msg}`);
}

function fail(msg) {
  console.error(`\x1b[31m[error]\x1b[0m ${msg}`);
  process.exit(1);
}

function slugify(text) {
  return (
    text
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "video"
  );
}

function outDirFor(slug) {
  const dir = join(CONFIG.outDir, slug);
  mkdirSync(dir, { recursive: true });
  return dir;
}

function save(dir, name, content) {
  const file = join(dir, name);
  writeFileSync(file, content);
  log("saved", file);
  return file;
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------

async function api(path, body) {
  const headers = { "Content-Type": "application/json" };
  if (CONFIG.apiKey) headers.Authorization = `Bearer ${CONFIG.apiKey}`;
  const res = await fetch(`${CONFIG.baseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} on ${path}: ${text.slice(0, 500)}`);
  }
  return res;
}

/** Chat completion → text. */
async function chat(prompt, { model = CONFIG.model, json = false, temperature = 0.8 } = {}) {
  const res = await api("/chat/completions", {
    model,
    temperature,
    messages: [{ role: "user", content: prompt }],
    ...(json ? { response_format: { type: "json_object" } } : {}),
  });
  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content ?? "";
  if (!text) throw new Error(`Empty completion from model "${model}"`);
  return text;
}

/** Chat completion → parsed JSON object. */
async function chatJson(prompt, opts = {}) {
  const text = await chat(prompt, { ...opts, json: true });
  // Strip accidental code fences, then grab the outermost { ... }.
  const cleaned = text.replace(/```(?:json)?/gi, "").trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end === -1)
    throw new Error(`Model did not return JSON:\n${cleaned.slice(0, 300)}`);
  return JSON.parse(cleaned.slice(start, end + 1));
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

const LANG_INSTRUCTIONS = {
  hinglish:
    "Write in HINGLISH: natural Hindi written in Roman/Latin script mixed with common English words — the way Indian YouTubers speak on camera (e.g. 'Aaj hum baat karenge...'). Keep technical terms in English.",
  hi: "Write in Hindi using Devanagari script (शुद्ध हिंदी), conversational YouTube tone.",
  en: "Write in clear, conversational English.",
};

function langLine(lang) {
  return LANG_INSTRUCTIONS[lang] || LANG_INSTRUCTIONS.hinglish;
}

function scriptPrompt(t, lang, niche) {
  return `You are a top YouTube scriptwriter with 10+ years of experience making viral videos.
${langLine(lang)}
Niche: ${niche}.

Video topic: "${t}"

Return ONLY a JSON object with this exact shape:
{
  "hook": "15-20 second opening hook that creates curiosity and stakes (spoken, no stage directions)",
  "intro": "channel intro + what the viewer will learn + why watch till end (20-30 sec)",
  "sections": [
    { "title": "section title", "content": "full spoken script for this section", "broll": "what to show on screen / b-roll ideas" }
  ],
  "cta": "subscribe/like/comment CTA woven naturally into the ending",
  "outro": "final lines + end-screen suggestion",
  "estimated_duration": "e.g. 8-10 min",
  "spoken_script_full": "the complete word-for-word narration: hook + intro + all sections + cta + outro, joined into one flowing script"
}
Make it 5-8 sections. Write for RETENTION: open loops, pattern interrupts, concrete examples, no fluff. The spoken script must be ready to record as-is.`;
}

function metaPrompt(t, lang) {
  return `You are a YouTube SEO expert. Topic: "${t}". Language audience: ${lang}.

Return ONLY a JSON object:
{
  "titles": ["5 click-worthy titles under 60 chars, curiosity-driven, no clickbait lies"],
  "description": "SEO description: strong first 2 lines, keyword-rich paragraph, timestamp placeholder section, 3-5 hashtags at the end",
  "tags": ["30 SEO tags: mix of exact topic, long-tail phrases and broad niche terms"],
  "hashtags": ["10 hashtags mixing trending + niche"],
  "chapters": [{ "time": "00:00", "title": "Intro" }],
  "pinned_comment": "an engaging pinned comment that drives replies",
  "best_upload_advice": "2-3 practical tips: best practices for thumbnail, first 48h push, community tab"
}
Chapters should follow a standard 8-10 minute video structure (Intro, main points, conclusion). Times are placeholders starting 00:00.`;
}

function thumbPrompt(t) {
  return `You are a YouTube thumbnail designer. Topic: "${t}".

Return ONLY a JSON object:
{
  "concept": "one-line thumbnail concept optimized for CTR (emotion + contrast + curiosity)",
  "text_overlay": "max 3-4 punchy words to put on the thumbnail",
  "image_prompt": "a detailed text-to-image prompt for the thumbnail background: bold high-contrast scene, expressive human emotion, vibrant colors, clean composition with empty space for text, photorealistic or 3D render, 16:9",
  "alt_versions": ["2 short alternative concepts"]
}`;
}

function shortsPrompt(t, lang) {
  return `You are a viral YouTube Shorts writer. Topic: "${t}".
${langLine(lang)}

Return ONLY a JSON object:
{
  "title": "punchy Shorts title under 55 chars",
  "script": "30-45 second word-for-word spoken script. First 2 seconds = scroll-stopping hook. Fast pacing, one single powerful idea, end with a loop-friendly last line.",
  "description": "2-line description + 5 hashtags (#shorts mandatory)",
  "captions": ["5-8 on-screen caption phrases timed to the script beats"]
}`;
}

function ideasPrompt(niche, count, lang) {
  return `You are a YouTube growth strategist. Niche: "${niche}". Audience language: ${lang}.

Return ONLY a JSON object:
{
  "ideas": [
    {
      "title": "video title (high CTR)",
      "angle": "one-line unique angle / why this works now",
      "format": "tutorial | listicle | story | challenge | reaction | explainer"
    }
  ]
}
Give exactly ${count} ideas. Prioritize proven formats with a fresh twist, searchable topics, and binge potential.`;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

function requireTopic() {
  if (!topic) fail('Missing topic. Example: node yt-auto.mjs script "My topic"');
}

async function cmdTest() {
  log("test", `Checking ${CONFIG.baseUrl} ...`);
  const headers = CONFIG.apiKey ? { Authorization: `Bearer ${CONFIG.apiKey}` } : {};
  const res = await fetch(`${CONFIG.baseUrl}/models`, { headers });
  if (!res.ok)
    fail(
      `Endpoint not reachable (HTTP ${res.status}). Is OmniRoute running? Start it, then copy your API key from Dashboard → Endpoints into OMNIROUTE_KEY.`
    );
  const data = await res.json();
  const models = data?.data ?? [];
  log("test", `Connected! ${models.length} models available.`);
  const wanted = [CONFIG.model, CONFIG.fastModel];
  if (wanted.includes("auto"))
    log("test", 'Using "auto" smart routing — OmniRoute picks the best connected provider.');
  const sample = models
    .slice(0, 8)
    .map((m) => m.id)
    .join(", ");
  if (sample) console.log(`   sample models: ${sample}${models.length > 8 ? " …" : ""}`);
}

async function cmdIdeas() {
  const niche = topic || CONFIG.niche;
  const count = Number(flag("count", 10));
  log("ideas", `Generating ${count} video ideas for niche "${niche}" ...`);
  const data = await chatJson(ideasPrompt(niche, count, CONFIG.lang), { model: CONFIG.fastModel });
  const dir = outDirFor(`ideas-${slugify(niche)}`);
  save(dir, "ideas.json", JSON.stringify(data, null, 2));
  const md = `# Video Ideas — ${niche}\n\n${(data.ideas || [])
    .map((i, n) => `${n + 1}. **${i.title}**\n   - Angle: ${i.angle}\n   - Format: ${i.format}`)
    .join("\n")}\n`;
  save(dir, "ideas.md", md);
}

async function cmdScript() {
  requireTopic();
  const lang = flag("lang", CONFIG.lang);
  log("script", `Writing full script for "${topic}" (${lang}) with model "${CONFIG.model}" ...`);
  const data = await chatJson(scriptPrompt(topic, lang, flag("niche", CONFIG.niche)));
  const dir = outDirFor(slugify(topic));
  save(dir, "script.json", JSON.stringify(data, null, 2));
  const md = [
    `# ${topic}`,
    "",
    `> Estimated duration: ${data.estimated_duration || "n/a"} · Language: ${lang}`,
    "",
    "## 🪝 Hook",
    "",
    data.hook || "",
    "",
    "## Intro",
    "",
    data.intro || "",
    "",
    ...(data.sections || []).flatMap((s, i) => [
      `## ${i + 1}. ${s.title}`,
      "",
      s.content || "",
      "",
      `> 🎬 B-roll: ${s.broll || "—"}`,
      "",
    ]),
    "## CTA",
    "",
    data.cta || "",
    "",
    "## Outro",
    "",
    data.outro || "",
    "",
    "---",
    "",
    "## 🎙️ Full spoken script (ready to record)",
    "",
    data.spoken_script_full || "",
    "",
  ].join("\n");
  save(dir, "script.md", md);
  return dir;
}

async function cmdMeta() {
  requireTopic();
  log("meta", `Generating SEO metadata for "${topic}" ...`);
  const data = await chatJson(metaPrompt(topic, flag("lang", CONFIG.lang)), {
    model: CONFIG.fastModel,
  });
  const dir = outDirFor(slugify(topic));
  save(dir, "metadata.json", JSON.stringify(data, null, 2));
  const md = [
    `# SEO Metadata — ${topic}`,
    "",
    "## Title options",
    ...(data.titles || []).map((t) => `- ${t}`),
    "",
    "## Description",
    "",
    data.description || "",
    "",
    "## Chapters",
    ...(data.chapters || []).map((c) => `- ${c.time} ${c.title}`),
    "",
    "## Tags",
    "",
    (data.tags || []).join(", "),
    "",
    "## Hashtags",
    "",
    (data.hashtags || []).join(" "),
    "",
    "## Pinned comment",
    "",
    data.pinned_comment || "",
    "",
    "## Upload advice",
    "",
    data.best_upload_advice || "",
    "",
  ].join("\n");
  save(dir, "metadata.md", md);
  return dir;
}

async function cmdThumb() {
  requireTopic();
  log("thumb", `Designing thumbnail concept for "${topic}" ...`);
  const data = await chatJson(thumbPrompt(topic), { model: CONFIG.fastModel });
  const dir = outDirFor(slugify(topic));
  save(dir, "thumbnail.json", JSON.stringify(data, null, 2));
  if (data.image_prompt) {
    log("thumb", "Generating thumbnail image via /v1/images/generations ...");
    try {
      const res = await api("/images/generations", {
        model: CONFIG.imageModel === "auto" ? undefined : CONFIG.imageModel,
        prompt: data.image_prompt,
        n: 1,
        size: "1792x1024",
      });
      const img = await res.json();
      const item = img?.data?.[0];
      if (item?.b64_json) {
        writeFileSync(join(dir, "thumbnail.png"), Buffer.from(item.b64_json, "base64"));
        log("saved", join(dir, "thumbnail.png"));
      } else if (item?.url) {
        const buf = Buffer.from(await (await fetch(item.url)).arrayBuffer());
        writeFileSync(join(dir, "thumbnail.png"), buf);
        log("saved", join(dir, "thumbnail.png"));
      } else {
        warn("Image endpoint returned no image — concept + prompt are still saved.");
      }
    } catch (err) {
      warn(`Image generation skipped (${err.message}). Prompt saved — paste it into any image AI.`);
    }
  }
  return dir;
}

async function cmdShorts() {
  requireTopic();
  log("shorts", `Writing Shorts script for "${topic}" ...`);
  const data = await chatJson(shortsPrompt(topic, flag("lang", CONFIG.lang)), {
    model: CONFIG.fastModel,
  });
  const dir = outDirFor(`${slugify(topic)}-shorts`);
  save(dir, "shorts.json", JSON.stringify(data, null, 2));
  const md = [
    `# SHORTS — ${topic}`,
    "",
    `**Title:** ${data.title || ""}`,
    "",
    "## Script (30-45s)",
    "",
    data.script || "",
    "",
    "## On-screen captions",
    ...(data.captions || []).map((c) => `- ${c}`),
    "",
    "## Description",
    "",
    data.description || "",
    "",
  ].join("\n");
  save(dir, "shorts.md", md);
  return dir;
}

async function cmdTts() {
  const target = topic;
  if (!target) fail("Pass a text file or raw text: node yt-auto.mjs tts output/my-video/script.md");
  let text;
  let outFile;
  if (existsSync(target)) {
    text = readFileSync(target, "utf8");
    outFile = `${basename(target).replace(/\.[^.]+$/, "")}-voiceover.mp3`;
  } else {
    text = target;
    outFile = "voiceover.mp3";
  }
  // Keep only the narration section if it's our full script markdown.
  const spoken = text.split("## 🎙️ Full spoken script")[1];
  if (spoken) text = spoken.replace(/^[^\n]*\n/, "");
  text = text
    .replace(/[#>*`|-]/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  if (!text) fail("No narration text found.");

  const dir = existsSync(target) ? dirname(target) : outDirFor("tts");
  log(
    "tts",
    `Synthesizing ${Math.round(text.length / 1000)}k chars with "${CONFIG.ttsModel}" (voice: ${CONFIG.voice}) ...`
  );
  const res = await api("/audio/speech", {
    model: CONFIG.ttsModel,
    input: text.slice(0, 4096 * 3),
    voice: flag("voice", CONFIG.voice),
  });
  writeFileSync(join(dir, outFile), Buffer.from(await res.arrayBuffer()));
  log("saved", join(dir, outFile));
}

async function cmdFull() {
  requireTopic();
  const t0 = Date.now();
  log("full", `🚀 Full pipeline for "${topic}"`);
  const dir = await cmdScript();
  await cmdMeta();
  await cmdThumb();
  await cmdShorts();
  // Voiceover last — it needs the script file.
  try {
    await cmdTtsRaw(join(dir, "script.md"));
  } catch (err) {
    warn(
      `Voiceover skipped (${err.message}). Run "node yt-auto.mjs tts ${join(dir, "script.md")}" later.`
    );
  }
  log("full", `✅ Done in ${Math.round((Date.now() - t0) / 1000)}s → ${dir}`);
}

/** TTS from an internal path (used by cmdFull). */
async function cmdTtsRaw(path) {
  const saved = process.argv;
  process.argv = ["node", "yt-auto.mjs", "tts", path];
  const origTopic = topic;
  try {
    // Re-implement minimal: read + synthesize.
    let text = readFileSync(path, "utf8");
    const spoken = text.split("## 🎙️ Full spoken script")[1];
    if (spoken) text = spoken.replace(/^[^\n]*\n/, "");
    text = text
      .replace(/[#>*`|-]/g, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
    if (!text) throw new Error("empty narration");
    log("tts", `Synthesizing voiceover with "${CONFIG.ttsModel}" ...`);
    const res = await api("/audio/speech", {
      model: CONFIG.ttsModel,
      input: text.slice(0, 4096 * 3),
      voice: CONFIG.voice,
    });
    writeFileSync(join(dirname(path), "voiceover.mp3"), Buffer.from(await res.arrayBuffer()));
    log("saved", join(dirname(path), "voiceover.mp3"));
  } finally {
    process.argv = saved;
    void origTopic;
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const COMMANDS = {
  test: cmdTest,
  ideas: cmdIdeas,
  script: cmdScript,
  meta: cmdMeta,
  thumb: cmdThumb,
  shorts: cmdShorts,
  tts: cmdTts,
  full: cmdFull,
};

if (!command || command === "help" || command === "--help" || command === "-h") {
  console.log(`yt-auto — YouTube AI automation through OmniRoute

Commands:
  test                          Check OmniRoute connection & models
  ideas "<niche>" --count 10    Generate video ideas
  script "<topic>" [--lang x]   Full video script (hook→outro, word-for-word)
  meta "<topic>"                Titles, description, tags, hashtags, chapters
  thumb "<topic>"               Thumbnail concept + generated image
  shorts "<topic>"              Viral Shorts script + captions
  tts <script.md|"text">        Voiceover narration (mp3)
  full "<topic>"                Everything above, one command

Config (env vars or .env / config.json in this folder):
  OMNIROUTE_URL   default http://localhost:20128/v1
  OMNIROUTE_KEY   API key from OmniRoute Dashboard → Endpoints
  YT_MODEL        script model   (default: auto)
  YT_FAST_MODEL   metadata model (default: auto)
  YT_TTS_MODEL    (default: gemini/gemini-3.1-flash-tts-preview)
  YT_IMAGE_MODEL  thumbnail model (default: auto)
  YT_LANG         hinglish | hi | en (default: hinglish)
  YT_NICHE        your channel niche
  YT_VOICE        TTS voice name (default: Kore)`);
  process.exit(command ? 0 : 1);
}

const run = COMMANDS[command];
if (!run) fail(`Unknown command "${command}". Run without arguments for help.`);

run().catch((err) => {
  const msg = err?.message || String(err);
  if (/ECONNREFUSED|fetch failed/i.test(msg)) {
    fail(
      `Cannot reach OmniRoute at ${CONFIG.baseUrl} — start it first (npm i -g omniroute && omniroute), or set OMNIROUTE_URL.`
    );
  }
  if (/401|403/i.test(msg) && CONFIG.baseUrl.includes("20128")) {
    fail(
      `Auth rejected — copy your API key from OmniRoute Dashboard → Endpoints and set OMNIROUTE_KEY.\n(${msg})`
    );
  }
  fail(msg);
});
