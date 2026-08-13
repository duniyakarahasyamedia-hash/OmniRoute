const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const STORE_KEYS = {
  chats: "saathi.chats.v1",
  memory: "saathi.memory.v1",
  settings: "saathi.settings.v1",
};

const DEFAULT_SETTINGS = {
  name: "Saathi",
  userName: "",
  provider: "auto",
  apiKey: "",
  baseUrl: "",
  model: "openai",
  voice: true,
};

const JOKES = [
  "Teacher: Late kyun aaye? Student: Sir, board pe likha tha School Ahead... so I went ahead.",
  "WiFi password itni strong kyun hoti hai? Kyunki pyaar ki tarah yeh bhi easily connect nahi hota.",
  "Bug: main nahi hoon. Developer: phir yeh crash kiska hai? Bug: production ka.",
  "Kal se gym. Aaj se motivaton. Kal se phir sochunga.",
  "Life ka syntax error: expectations zyada, exceptions kam.",
];

const SHAYARI = [
  "Raaste lambe hon, saath ho toh manzil bhi mehsoos hoti hai.",
  "Thak jaao, ruk jaao, lekin khud se waada mat todo.",
  "Andhera lamba ho sakta hai, subah phir bhi aati hai.",
  "Jo dil se poochho, jawab seedha milta hai.",
];

const QUICK = [
  "Kaise ho?",
  "Abhi time kya hai?",
  "Ek joke suna",
  "Yaad rakh: mujhe chai pasand hai",
  "2 * (18 + 7)",
  "Aaj ke kaam dikhao",
];

let state = {
  settings: loadSettings(),
  chats: loadChats(),
  activeId: null,
  memory: loadMemory(),
  busy: false,
};

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function loadSettings() {
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(STORE_KEYS.settings) || "{}") };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function saveSettings() {
  localStorage.setItem(STORE_KEYS.settings, JSON.stringify(state.settings));
}

function loadChats() {
  try {
    const chats = JSON.parse(localStorage.getItem(STORE_KEYS.chats) || "[]");
    return Array.isArray(chats) ? chats : [];
  } catch {
    return [];
  }
}

function saveChats() {
  localStorage.setItem(STORE_KEYS.chats, JSON.stringify(state.chats));
}

function loadMemory() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEYS.memory) || '{"facts":[],"notes":[],"tasks":[]}');
  } catch {
    return { facts: [], notes: [], tasks: [] };
  }
}

function saveMemory() {
  localStorage.setItem(STORE_KEYS.memory, JSON.stringify(state.memory));
  fetch("/api/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.memory),
  }).catch(() => {});
}

function activeChat() {
  return state.chats.find((c) => c.id === state.activeId);
}

function ensureChat() {
  if (activeChat()) return activeChat();
  const chat = { id: uid(), title: "Nayi baat-cheet", messages: [], createdAt: Date.now() };
  state.chats.unshift(chat);
  state.activeId = chat.id;
  saveChats();
  return chat;
}

function setStatus(kind, text) {
  const el = $("#status");
  el.className = `status ${kind}`;
  el.innerHTML = `<i></i>${text}`;
}

function speak(text) {
  if (!state.settings.voice || !window.speechSynthesis) return;
  const clean = text.replace(/[#*_`>-]/g, " ").slice(0, 280);
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = 1.02;
  const hi = speechSynthesis.getVoices().find((v) => /hi-IN|Hindi/i.test(`${v.lang} ${v.name}`));
  if (hi) u.voice = hi;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function renderSessions() {
  const box = $("#sessions");
  box.innerHTML = state.chats
    .map(
      (c) => `
      <div class="item ${c.id === state.activeId ? "active" : ""}" data-id="${c.id}">
        <strong>${escapeHtml(c.title)}</strong>
        <small>${new Date(c.createdAt).toLocaleString()}</small>
      </div>`,
    )
    .join("");
}

function renderMemory() {
  $("#facts").innerHTML = state.memory.facts
    .slice()
    .reverse()
    .map((f) => `<div class="item"><strong>${escapeHtml(f.text)}</strong><small>${escapeHtml(f.at || "")}</small></div>`)
    .join("") || `<div class="item"><span>Abhi koi memory nahi. Bolo “yaad rakh …”.</span></div>`;
  $("#tasks").innerHTML = state.memory.tasks
    .map(
      (t) => `
      <div class="item ${t.done ? "done" : ""}" data-task="${t.id}">
        <strong>${t.done ? "✓ " : ""}${escapeHtml(t.text)}</strong>
        <small>${t.done ? "ho gaya" : "pending"}</small>
      </div>`,
    )
    .join("") || `<div class="item"><span>Koi task nahi. Bolo “task add kar …”.</span></div>`;
}

function renderMessages() {
  const chat = activeChat();
  const empty = $("#hero");
  const list = $("#messages");
  if (!chat || chat.messages.length === 0) {
    empty.classList.remove("hidden");
    list.innerHTML = "";
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = chat.messages
    .map((m) => {
      if (m.role === "tool") {
        return `<div class="tool-card"><b>Tool · ${escapeHtml(m.name)}</b><div>${escapeHtml(m.content)}</div></div>`;
      }
      return `<div class="msg ${m.role}"><div class="who">${m.role === "user" ? "Tum" : state.settings.name}</div>${escapeHtml(m.content)}</div>`;
    })
    .join("");
  list.scrollTop = list.scrollHeight;
}

function escapeHtml(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function nowBits() {
  const d = new Date();
  return {
    time: d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    date: d.toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" }),
    iso: d.toISOString(),
  };
}

function safeCalc(expr) {
  const cleaned = expr.replace(/[^0-9+\-*/%^().\s]/g, "").replaceAll("^", "**");
  if (!cleaned.trim()) throw new Error("empty");
  const fn = new Function(`return (${cleaned})`);
  const value = fn();
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("invalid");
  return value;
}

function detectLang(text) {
  return /[\u0900-\u097F]/.test(text) || /\b(kya|hai|ho|kar|mujhe|tum|mera|nahi|yaad|kaam|suna|bhai|yaar)\b/i.test(text)
    ? "hi"
    : "en";
}

function remember(text) {
  const fact = { id: uid(), text, at: new Date().toLocaleString() };
  state.memory.facts.push(fact);
  saveMemory();
  renderMemory();
  return fact;
}

function addTask(text) {
  const task = { id: uid(), text, done: false };
  state.memory.tasks.push(task);
  saveMemory();
  renderMemory();
  return task;
}

function completeTask(q) {
  const needle = q.toLowerCase();
  const task = state.memory.tasks.find((t) => !t.done && t.text.toLowerCase().includes(needle)) || state.memory.tasks.find((t) => !t.done);
  if (!task) return null;
  task.done = true;
  saveMemory();
  renderMemory();
  return task;
}

function localAgent(input) {
  const text = input.trim();
  const lower = text.toLowerCase();
  const lang = detectLang(text);
  const you = state.settings.userName || (lang === "hi" ? "dost" : "friend");
  const tools = [];

  const reply = (content, extraTools = []) => ({ content, tools: [...tools, ...extraTools] });

  if (/^(hi|hello|hey|yo|namaste|namaskar|salaam|hii+|helo)\b/i.test(lower) || /kaise ho|kya haal|whats up/.test(lower)) {
    return reply(
      lang === "hi"
        ? `Namaste ${you}! Main ${state.settings.name} hoon — tumhara personal AI agent. Time, hisaab, yaadein, tasks, jokes, shayari… sab handle karta hoon. Bolo, kya kaam hai?`
        : `Hey ${you}! I'm ${state.settings.name}, your personal AI agent. I can remember things, do math, manage tasks, and talk in Hinglish. What should we do?`,
    );
  }

  if (/who are you|kaun ho|tum kaun|your name|naam kya/.test(lower)) {
    return reply(
      `Main ${state.settings.name} hoon — tumhara local-first AI agent. Browser se free models try karta hoon, aur bina key ke bhi tools + memory ke saath kaam karta hoon.`,
    );
  }

  if (/help|madad|kya kar sakte|commands|skills/.test(lower)) {
    return reply(
      [
        "Main yeh kar sakta hoon:",
        "• Time / date — “abhi time kya hai”",
        "• Calculator — “125 * 18”",
        "• Memory — “yaad rakh mera naam Aarav hai”",
        "• Tasks — “task add kar grocery laani hai”",
        "• Joke / shayari",
        "• Settings mein Groq/OpenAI/OpenRouter key daaloge toh full LLM mode",
      ].join("\n"),
    );
  }

  if (/time|baje|kitne baje|date|aaj (kaun|kya)|din kya/.test(lower)) {
    const n = nowBits();
    tools.push({ name: "clock", content: `${n.date} · ${n.time}` });
    return reply(lang === "hi" ? `Abhi ${n.time} hai, ${n.date}.` : `It's ${n.time} on ${n.date}.`, tools);
  }

  const calcMatch = text.match(/(-?\d[\d\s+\-*/%^().]+-?\d)/);
  if (calcMatch && /[\d]/.test(text) && /[+\-*/x×^%]/.test(text)) {
    try {
      const value = safeCalc(calcMatch[1].replaceAll("x", "*").replaceAll("×", "*"));
      tools.push({ name: "calculator", content: `${calcMatch[1].trim()} = ${value}` });
      return reply(lang === "hi" ? `Hisaab ho gaya: ${value}` : `That comes to ${value}.`, tools);
    } catch {
      /* fall through */
    }
  }

  const rememberMatch = text.match(/(?:yaad rakh|remember(?: that)?)[:\s]+(.+)/i);
  if (rememberMatch) {
    const fact = remember(rememberMatch[1].trim());
    tools.push({ name: "memory.write", content: fact.text });
    return reply(lang === "hi" ? `Pakka, yaad rakh liya: “${fact.text}”.` : `Got it. I’ll remember: “${fact.text}”.`, tools);
  }

  if (/kya yaad|what do you remember|meri memory|facts dikhao/.test(lower)) {
    tools.push({ name: "memory.read", content: `${state.memory.facts.length} facts` });
    if (!state.memory.facts.length) return reply("Abhi kuch yaad nahi. Bolo “yaad rakh …”.");
    return reply(state.memory.facts.map((f, i) => `${i + 1}. ${f.text}`).join("\n"), tools);
  }

  const taskAdd = text.match(/(?:task add(?: kar)?|add task|kaam add(?: kar)?|todo)[:\s]+(.+)/i);
  if (taskAdd) {
    const task = addTask(taskAdd[1].trim());
    tools.push({ name: "tasks.add", content: task.text });
    return reply(`Task add ho gaya: ${task.text}`, tools);
  }

  if (/task (done|complete|khatam|ho gaya)|mark done/.test(lower)) {
    const task = completeTask(text.replace(/task (done|complete|khatam|ho gaya)|mark done/gi, "").trim());
    if (!task) return reply("Koi pending task nahi mila.");
    tools.push({ name: "tasks.complete", content: task.text });
    return reply(`Done mark kar diya: ${task.text}`, tools);
  }

  if (/tasks? dikhao|list tasks|aaj ke kaam|todo list/.test(lower)) {
    tools.push({ name: "tasks.list", content: `${state.memory.tasks.length} items` });
    if (!state.memory.tasks.length) return reply("List khaali hai. Naya task bol ke add karo.");
    return reply(state.memory.tasks.map((t) => `${t.done ? "✓" : "•"} ${t.text}`).join("\n"), tools);
  }

  if (/joke|mazak|hasaa|funny/.test(lower)) {
    return reply(JOKES[Math.floor(Math.random() * JOKES.length)]);
  }

  if (/shayari|sher|gazal/.test(lower)) {
    return reply(SHAYARI[Math.floor(Math.random() * SHAYARI.length)]);
  }

  if (/mera naam|my name is|i am called/.test(lower)) {
    const name = text.replace(/.*(?:mera naam|my name is|i am called)\s*/i, "").replace(/[.?].*$/, "").trim();
    if (name) {
      state.settings.userName = name.replace(/\bhai\b/i, "").trim();
      saveSettings();
      remember(`User ka naam ${state.settings.userName} hai`);
      return reply(`Nice, ${state.settings.userName}. Ab main tumhe isi naam se bulaunga.`);
    }
  }

  if (state.memory.facts.length && /mujhe kya|about me|mere baare/.test(lower)) {
    return reply(`Jo tumne bataya hai:\n${state.memory.facts.map((f) => `• ${f.text}`).join("\n")}`);
  }

  return {
    content: "",
    tools,
    needsModel: true,
  };
}

function fallbackTalk(input) {
  const lang = detectLang(input);
  const facts = state.memory.facts.slice(-4).map((f) => f.text).join("; ");
  if (lang === "hi") {
    return [
      "Samajh gaya. Is sawaal ke liye cloud model ki zaroorat padti hai, lekin main yahin hoon.",
      facts ? `Jo yaad hai: ${facts}.` : "Koi API key nahi mili, isliye main local agent mode mein hoon.",
      "Settings mein Groq / OpenAI / OpenRouter key daal do — phir main deep answers bhi de paunga.",
      "Tab tak time, hisaab, memory, tasks, jokes mere paas ready hain.",
    ].join(" ");
  }
  return [
    "I get the question, but I need a model endpoint for a full answer.",
    "Add a Groq, OpenAI, or OpenRouter key in Settings and I will think much bigger.",
    "Meanwhile I can still handle time, math, memory, and tasks.",
  ].join(" ");
}

function systemPrompt() {
  const n = nowBits();
  const facts = state.memory.facts.map((f) => `- ${f.text}`).join("\n") || "- none yet";
  const tasks = state.memory.tasks.map((t) => `- [${t.done ? "x" : " "}] ${t.text}`).join("\n") || "- none";
  return [
    `You are ${state.settings.name}, a warm, sharp personal AI agent.`,
    "Talk naturally in the user's language. If they use Hinglish, reply in Hinglish.",
    "Be concise, useful, and a little charming. Never claim you are offline if you are answering.",
    `User name: ${state.settings.userName || "unknown"}.`,
    `Local time: ${n.date} ${n.time}.`,
    `Known memory:\n${facts}`,
    `Tasks:\n${tasks}`,
  ].join("\n");
}

async function callOpenAICompat({ url, headers, body }) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`http ${res.status}`);
  const data = await res.json();
  const text = data.choices?.[0]?.message?.content || data.output_text || data.text;
  if (!text) throw new Error("empty model");
  return String(text).trim();
}

async function callModel(messages) {
  const s = state.settings;
  const payloadMessages = [{ role: "system", content: systemPrompt() }, ...messages.map((m) => ({ role: m.role, content: m.content }))];

  const attempts = [];
  if (s.provider === "custom" && s.baseUrl) {
    attempts.push({
      url: s.baseUrl.replace(/\/$/, "") + "/chat/completions",
      headers: s.apiKey ? { Authorization: `Bearer ${s.apiKey}` } : {},
      body: { model: s.model || "openai", messages: payloadMessages },
    });
  }
  if ((s.provider === "groq" || s.provider === "auto") && s.apiKey && (s.provider === "groq" || s.baseUrl.includes("groq") || true)) {
    if (s.provider === "groq" || (s.provider === "auto" && s.apiKey && !s.baseUrl)) {
      attempts.push({
        url: "https://api.groq.com/openai/v1/chat/completions",
        headers: { Authorization: `Bearer ${s.apiKey}` },
        body: { model: s.model || "llama-3.1-8b-instant", messages: payloadMessages, temperature: 0.7 },
      });
    }
  }
  if ((s.provider === "openai" || s.provider === "auto") && s.apiKey && s.provider === "openai") {
    attempts.push({
      url: "https://api.openai.com/v1/chat/completions",
      headers: { Authorization: `Bearer ${s.apiKey}` },
      body: { model: s.model || "gpt-4o-mini", messages: payloadMessages },
    });
  }
  if ((s.provider === "openrouter" || (s.provider === "auto" && s.apiKey && s.provider === "openrouter")) && s.apiKey) {
    attempts.push({
      url: "https://openrouter.ai/api/v1/chat/completions",
      headers: { Authorization: `Bearer ${s.apiKey}` },
      body: { model: s.model || "openai/gpt-4o-mini", messages: payloadMessages },
    });
  }
  if (s.provider === "auto" || s.provider === "pollinations") {
    attempts.push({
      url: "https://text.pollinations.ai/openai",
      headers: {},
      body: { model: s.model || "openai", messages: payloadMessages },
    });
  }

  let lastErr = null;
  for (const attempt of attempts) {
    try {
      return await callOpenAICompat(attempt);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("no provider");
}

async function sendMessage(raw) {
  const text = raw.trim();
  if (!text || state.busy) return;
  const chat = ensureChat();
  if (chat.messages.length === 0) {
    chat.title = text.slice(0, 42);
  }
  chat.messages.push({ role: "user", content: text });
  saveChats();
  renderSessions();
  renderMessages();
  $("#input").value = "";
  autosize();

  state.busy = true;
  setStatus("thinking", "Soch raha hoon…");

  try {
    const local = localAgent(text);
    for (const tool of local.tools) {
      chat.messages.push({ role: "tool", name: tool.name, content: tool.content });
    }

    let answer = local.content;
    if (local.needsModel) {
      setStatus("tool", "Model se pooch raha hoon…");
      try {
        const history = chat.messages
          .filter((m) => m.role === "user" || m.role === "agent")
          .slice(-12)
          .map((m) => ({ role: m.role === "agent" ? "assistant" : "user", content: m.content }));
        answer = await callModel(history);
      } catch {
        answer = fallbackTalk(text);
      }
    }

    chat.messages.push({ role: "agent", content: answer });
    saveChats();
    renderMessages();
    speak(answer);
    setStatus("", "Online · ready");
  } catch (err) {
    chat.messages.push({ role: "agent", content: `Thoda atak gaya: ${err.message}` });
    renderMessages();
    setStatus("", "Online · ready");
  } finally {
    state.busy = false;
  }
}

function autosize() {
  const el = $("#input");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

function bind() {
  if (!state.chats.length) ensureChat();
  else state.activeId = state.chats[0].id;

  $("#agentName").textContent = state.settings.name;
  $("#settingsName").value = state.settings.name;
  $("#settingsUser").value = state.settings.userName;
  $("#settingsProvider").value = state.settings.provider;
  $("#settingsKey").value = state.settings.apiKey;
  $("#settingsModel").value = state.settings.model;
  $("#settingsVoice").checked = state.settings.voice;

  $("#quick").innerHTML = QUICK.map((q) => `<button class="quick" data-q="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("");

  renderSessions();
  renderMemory();
  renderMessages();
  setStatus("", "Online · ready");

  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage($("#input").value);
  });
  $("#input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage($("#input").value);
    }
  });
  $("#input").addEventListener("input", autosize);

  $("#quick").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-q]");
    if (btn) sendMessage(btn.dataset.q);
  });

  $("#sessions").addEventListener("click", (e) => {
    const item = e.target.closest("[data-id]");
    if (!item) return;
    state.activeId = item.dataset.id;
    renderSessions();
    renderMessages();
  });

  $("#newChat").addEventListener("click", () => {
    state.activeId = null;
    ensureChat();
    renderSessions();
    renderMessages();
  });

  $("#saveSettings").addEventListener("click", () => {
    state.settings.name = $("#settingsName").value.trim() || "Saathi";
    state.settings.userName = $("#settingsUser").value.trim();
    state.settings.provider = $("#settingsProvider").value;
    state.settings.apiKey = $("#settingsKey").value.trim();
    state.settings.model = $("#settingsModel").value.trim();
    state.settings.voice = $("#settingsVoice").checked;
    saveSettings();
    $("#agentName").textContent = state.settings.name;
    setStatus("", "Settings save ho gayi");
  });

  $("#mic").addEventListener("click", () => {
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Rec) {
      sendMessage("Voice input is browser pe available nahi.");
      return;
    }
    const rec = new Rec();
    rec.lang = "hi-IN";
    rec.onresult = (ev) => sendMessage(ev.results[0][0].transcript);
    rec.start();
    setStatus("tool", "Sun raha hoon…");
  });

  $("#tasks").addEventListener("click", (e) => {
    const item = e.target.closest("[data-task]");
    if (!item) return;
    const task = state.memory.tasks.find((t) => t.id === item.dataset.task);
    if (!task) return;
    task.done = !task.done;
    saveMemory();
    renderMemory();
  });
}

window.addEventListener("DOMContentLoaded", bind);
speechSynthesis?.getVoices();
