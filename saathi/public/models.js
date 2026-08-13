const MODEL_CATALOG = {
  local: {
    label: "Built-in",
    key: false,
    hint: "No internet. Always works.",
    models: [
      { id: "saathi-studio", name: "Saathi Local Engine", use: "Full YouTube pipeline", tier: "free" },
    ],
  },
  pollinations: {
    label: "Pollinations",
    key: false,
    hint: "Free in the browser. No key.",
    url: "https://text.pollinations.ai/openai",
    models: [
      { id: "openai", name: "GPT (Pollinations)", use: "Scripts + titles", tier: "free" },
      { id: "openai-fast", name: "GPT Fast", use: "Quick rewrites", tier: "free" },
      { id: "openai-large", name: "GPT Large", use: "Long scripts", tier: "free" },
      { id: "deepseek", name: "DeepSeek", use: "Research + structure", tier: "free" },
      { id: "deepseek-reasoning", name: "DeepSeek R1", use: "Topic scoring", tier: "free" },
      { id: "mistral", name: "Mistral", use: "Clean Hinglish VO", tier: "free" },
      { id: "gemini", name: "Gemini", use: "Hooks + packaging", tier: "free" },
      { id: "claude", name: "Claude", use: "Premium scripts", tier: "free" },
      { id: "llama", name: "Llama", use: "Fast drafts", tier: "free" },
      { id: "qwen", name: "Qwen", use: "Lists + SEO tags", tier: "free" },
    ],
  },
  groq: {
    label: "Groq",
    key: true,
    hint: "Free key at console.groq.com",
    url: "https://api.groq.com/openai/v1/chat/completions",
    models: [
      { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B Instant", use: "Fastest drafts", tier: "free-key" },
      { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B", use: "Best Groq scripts", tier: "free-key" },
      { id: "meta-llama/llama-4-scout-17b-16e-instruct", name: "Llama 4 Scout", use: "Long context research", tier: "free-key" },
      { id: "meta-llama/llama-4-maverick-17b-128e-instruct", name: "Llama 4 Maverick", use: "Deep rewrites", tier: "free-key" },
      { id: "qwen/qwen3-32b", name: "Qwen 3 32B", use: "SEO + chapters", tier: "free-key" },
      { id: "deepseek-r1-distill-llama-70b", name: "DeepSeek R1 Distill", use: "Reasoning / angles", tier: "free-key" },
      { id: "gemma2-9b-it", name: "Gemma 2 9B", use: "Shorts hooks", tier: "free-key" },
      { id: "moonshotai/kimi-k2-instruct", name: "Kimi K2", use: "Long scripts", tier: "free-key" },
      { id: "openai/gpt-oss-120b", name: "GPT-OSS 120B", use: "Heavy packaging", tier: "free-key" },
    ],
  },
  openai: {
    label: "OpenAI",
    key: true,
    hint: "Paid key · platform.openai.com",
    url: "https://api.openai.com/v1/chat/completions",
    models: [
      { id: "gpt-4o-mini", name: "GPT-4o mini", use: "Cheap daily desk", tier: "paid" },
      { id: "gpt-4.1-mini", name: "GPT-4.1 mini", use: "Tight scripts", tier: "paid" },
      { id: "gpt-4o", name: "GPT-4o", use: "Premium packaging", tier: "paid" },
      { id: "gpt-4.1", name: "GPT-4.1", use: "Long-form VO", tier: "paid" },
      { id: "o4-mini", name: "o4-mini", use: "Topic strategy", tier: "paid" },
    ],
  },
  anthropic: {
    label: "Anthropic",
    key: true,
    hint: "Paid key · console.anthropic.com",
    style: "anthropic",
    url: "https://api.anthropic.com/v1/messages",
    models: [
      { id: "claude-haiku-4-5", name: "Claude Haiku 4.5", use: "Fast titles", tier: "paid" },
      { id: "claude-sonnet-4-5", name: "Claude Sonnet 4.5", use: "Best scripts", tier: "paid" },
      { id: "claude-opus-4", name: "Claude Opus 4", use: "Flagship videos", tier: "paid" },
    ],
  },
  gemini: {
    label: "Google Gemini",
    key: true,
    hint: "Free key · aistudio.google.com",
    style: "gemini",
    url: "https://generativelanguage.googleapis.com/v1beta/models",
    models: [
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", use: "Hooks + thumbs", tier: "free-key" },
      { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", use: "Daily production", tier: "free-key" },
      { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", use: "Deep research", tier: "paid" },
    ],
  },
  openrouter: {
    label: "OpenRouter",
    key: true,
    hint: "One key · many models, some free",
    url: "https://openrouter.ai/api/v1/chat/completions",
    models: [
      { id: "openrouter/auto", name: "OpenRouter Auto", use: "Let OR pick", tier: "free-key" },
      { id: "meta-llama/llama-3.3-70b-instruct:free", name: "Llama 3.3 70B Free", use: "Free scripts", tier: "free" },
      { id: "google/gemini-2.0-flash-exp:free", name: "Gemini Flash Free", use: "Free packaging", tier: "free" },
      { id: "qwen/qwen-2.5-72b-instruct:free", name: "Qwen 2.5 72B Free", use: "Free SEO", tier: "free" },
      { id: "deepseek/deepseek-chat-v3-0324:free", name: "DeepSeek V3 Free", use: "Free research", tier: "free" },
      { id: "moonshotai/kimi-k2", name: "Kimi K2", use: "Long context", tier: "paid" },
      { id: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4", use: "Premium VO", tier: "paid" },
      { id: "google/gemini-2.5-flash", name: "Gemini 2.5 Flash", use: "Fast desk", tier: "paid" },
      { id: "openai/gpt-4o-mini", name: "GPT-4o mini", use: "Reliable daily", tier: "paid" },
    ],
  },
};

function allModels() {
  return Object.entries(MODEL_CATALOG).flatMap(([provider, pack]) =>
    pack.models.map((m) => ({ ...m, provider, providerLabel: pack.label, needsKey: pack.key, style: pack.style || "openai", url: pack.url })),
  );
}

function findModel(id) {
  return allModels().find((m) => m.id === id) || allModels()[0];
}

function modelsFor(provider) {
  if (provider === "auto") return allModels().filter((m) => m.provider !== "local");
  return (MODEL_CATALOG[provider] || MODEL_CATALOG.pollinations).models.map((m) => ({
    ...m,
    provider,
    providerLabel: MODEL_CATALOG[provider]?.label || provider,
    needsKey: MODEL_CATALOG[provider]?.key,
    style: MODEL_CATALOG[provider]?.style || "openai",
    url: MODEL_CATALOG[provider]?.url,
  }));
}
