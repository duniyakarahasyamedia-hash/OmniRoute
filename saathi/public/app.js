const $ = (s) => document.querySelector(s);

const STORE = {
  studio: "saathi.studio.v2",
  settings: "saathi.settings.v2",
};

const DEFAULT_SETTINGS = { provider: "auto", apiKey: "", model: "openai" };

let state = {
  settings: loadJson(STORE.settings, DEFAULT_SETTINGS),
  channel: loadJson("saathi.channel.v2", { ...YT.DEFAULT_CHANNEL }),
  projects: loadStudio(),
  activeId: null,
  messages: [],
  busy: false,
};

function loadJson(key, fallback) {
  try {
    return { ...fallback, ...JSON.parse(localStorage.getItem(key) || "null") };
  } catch {
    return fallback;
  }
}

function loadStudio() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE.studio) || "null");
    if (Array.isArray(raw)) return raw;
    if (raw && Array.isArray(raw.projects)) return raw.projects;
  } catch {}
  return [];
}

function persist() {
  localStorage.setItem(STORE.studio, JSON.stringify({ projects: state.projects }));
  localStorage.setItem("saathi.channel.v2", JSON.stringify(state.channel));
  localStorage.setItem(STORE.settings, JSON.stringify(state.settings));
  fetch("/api/studio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel: state.channel, projects: state.projects }),
  }).catch(() => {});
}

function project() {
  return state.projects.find((p) => p.id === state.activeId);
}

function ensureProject() {
  if (project()) return project();
  const p = YT.emptyProject(state.channel);
  state.projects.unshift(p);
  state.activeId = p.id;
  persist();
  return p;
}

function setStatus(kind, text) {
  const el = $("#status");
  el.className = `status ${kind || ""}`;
  el.innerHTML = `<i></i>${text}`;
}

function escapeHtml(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function stageIndex(id) {
  return YT.STAGES.findIndex((s) => s.id === id);
}

function renderSteps() {
  const p = project();
  const current = p?.stage || "setup";
  $("#steps").innerHTML = YT.STAGES.map((s, i) => {
    const done = p && stageIndex(current) > i;
    const active = current === s.id;
    return `<div class="step ${active ? "active" : ""} ${done ? "done" : ""}" data-stage="${s.id}">
      <div class="dot"></div>
      <div><strong>${s.label}</strong><span>${s.hint}</span></div>
    </div>`;
  }).join("");
}

function renderProjects() {
  if (!state.projects.length) {
    $("#projects").innerHTML = `<div class="item"><span>No videos yet. Hit Decide for me.</span></div>`;
    return;
  }
  $("#projects").innerHTML = state.projects
    .map(
      (p) => `<div class="item ${p.id === state.activeId ? "active" : ""}" data-id="${p.id}">
        <strong>${escapeHtml(p.title)}</strong>
        <small>${escapeHtml(p.stage)} · ${new Date(p.createdAt).toLocaleDateString()}</small>
      </div>`,
    )
    .join("");
}

function renderRail() {
  const c = state.channel;
  $("#channelCard").innerHTML = `
    <h3>${escapeHtml(c.name)}</h3>
    <div class="kv"><span>Niche</span><b>${escapeHtml(c.niche)}</b></div>
    <div class="kv"><span>Market</span><b>${escapeHtml(c.country)} · ${escapeHtml(c.language)}</b></div>
    <div class="kv"><span>Length</span><b>${escapeHtml(c.videoLength)}</b></div>
    <div class="kv"><span>Cadence</span><b>${escapeHtml(c.uploadFrequency)}</b></div>
    <div class="kv"><span>Voice</span><b>${escapeHtml(c.brandVoice)}</b></div>`;

  const p = project();
  const t = p?.selectedTopic;
  if (!t) {
    $("#videoCard").innerHTML = `<span>No topic locked. Run Topic Lab or Decide for me.</span>`;
    return;
  }
  const s = t.scores;
  $("#videoCard").innerHTML = `
    <h3>${escapeHtml(t.topic)}</h3>
    <p class="pre">${escapeHtml(t.angle)}</p>
    <div class="meters">
      ${meter("Viral", s.viral)}${meter("Search", s.search)}${meter("Evergreen", s.evergreen)}
      ${meter("Money", s.money)}${meter("Easy", 11 - s.difficulty)}${meter("Total", s.total)}
    </div>`;
}

function meter(label, n) {
  return `<div class="meter"><span>${label}</span><div class="bar"><span style="width:${n * 10}%"></span></div><b>${n}</b></div>`;
}

function renderWorkspace() {
  const p = project();
  const stage = p?.stage || "setup";
  const map = {
    setup: viewSetup,
    research: viewResearch,
    topics: viewTopics,
    deep: viewDeep,
    script: viewScript,
    package: viewPackage,
    production: viewProduction,
    upload: viewUpload,
  };
  $("#workspace").innerHTML = (map[stage] || viewSetup)(p);
  if (state.messages.length) {
    $("#workspace").innerHTML += `<div class="messages">${state.messages
      .map((m) => `<div class="msg ${m.role}"><b>${m.role === "user" ? "You" : "Master Agent"}</b>\n${escapeHtml(m.content)}</div>`)
      .join("")}</div>`;
  }
}

function viewSetup() {
  const c = state.channel;
  const fields = [
    ["name", "Channel name"],
    ["niche", "Niche"],
    ["subNiche", "Sub-niche"],
    ["country", "Target country"],
    ["language", "Language"],
    ["audience", "Audience"],
    ["ageRange", "Age range"],
    ["contentStyle", "Content style"],
    ["videoLength", "Video length"],
    ["uploadFrequency", "Upload frequency"],
    ["competitors", "Competitor channels"],
    ["monetizationGoal", "Monetization goal"],
    ["brandVoice", "Brand voice"],
    ["visualStyle", "Visual style"],
  ];
  return `<section class="hero">
      <img src="./avatar.png" alt="" />
      <h2>YouTube production, on rails.</h2>
      <p>I run the full desk: research, 10 scored topics, unique angle, script, titles, thumbnail brief, SEO, shot list, and an upload pack. Fill this once — or let me decide.</p>
      <div class="row" style="justify-content:center">
        <button class="btn-red" data-act="autopilot">Decide everything</button>
        <button data-act="save-channel">Save channel</button>
        <button data-act="goto" data-stage="research">Start research</button>
      </div>
    </section>
    <div class="grid-2">
      ${fields
        .map(
          ([k, label]) => `<div><label>${label}</label>${
            k === "competitors" || k === "brandVoice" || k === "visualStyle"
              ? `<textarea data-field="${k}">${escapeHtml(c[k] || "")}</textarea>`
              : `<input data-field="${k}" value="${escapeHtml(c[k] || "")}" />`
          }</div>`,
        )
        .join("")}
    </div>`;
}

function viewResearch(p) {
  const r = p?.research;
  if (!r) {
    return `<div class="card"><p>No research yet.</p><button class="btn-red" data-act="goto" data-stage="research">Run market research</button></div>`;
  }
  return `<div class="row"><h2 style="margin:0 0 10px">Market research</h2>
      <button class="btn-red" data-act="goto" data-stage="topics">Generate 10 topics</button></div>
    <div class="grid-2">
      <div class="card"><h3>Trending</h3><div class="pre">${r.trending.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Evergreen</h3><div class="pre">${r.evergreen.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Audience problems</h3><div class="pre">${r.problems.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Content gaps</h3><div class="pre">${r.gaps.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Competitor tells</h3><div class="pre">${r.competitorPatterns.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Winning formats</h3><div class="pre">${r.formats.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
    </div>
    <div class="card" style="margin-top:10px"><h3>Call</h3><p>${escapeHtml(r.recommendation)}</p></div>`;
}

function viewTopics(p) {
  const topics = p?.topics || [];
  return `<div class="row"><h2 style="margin:0 0 10px">Topic lab</h2>
      <button class="btn-red" data-act="lock-best">Lock #1 and write video</button></div>
    <div class="grid-2">
      ${topics
        .map(
          (t, i) => `<div class="card pick ${p.selectedTopic?.id === t.id ? "selected" : ""}" data-act="pick-topic" data-tid="${t.id}">
            <h3>#${i + 1} · ${escapeHtml(t.topic)}</h3>
            <p><b>Angle:</b> ${escapeHtml(t.angle)}</p>
            <p><b>Hook:</b> ${escapeHtml(t.hook)}</p>
            <div class="kv"><span>Viral ${t.scores.viral}</span><span>Search ${t.scores.search}</span><span>Money ${t.scores.money}</span><span>Total ${t.scores.total}</span></div>
            <small>${escapeHtml(t.whyClick)} ${escapeHtml(t.whyWatch)}</small>
          </div>`,
        )
        .join("")}
    </div>`;
}

function viewDeep(p) {
  const d = p?.deep;
  if (!d) return `<div class="card"><button class="btn-red" data-act="goto" data-stage="deep">Run deep research</button></div>`;
  return `<div class="row"><h2 style="margin:0 0 10px">Deep research</h2>
      <button class="btn-red" data-act="goto" data-stage="script">Write script</button></div>
    <div class="grid-2">
      <div class="card"><h3>Facts</h3><div class="pre">${d.facts.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>Stakes</h3><p>${escapeHtml(d.stakes)}</p></div>
      <div class="card"><h3>Sources to pull</h3><div class="pre">${d.sources.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>Objections</h3><div class="pre">${d.objections.map((x) => "• " + x).join("\n")}</div></div>
    </div>`;
}

function viewScript(p) {
  const s = p?.script;
  if (!s) return `<div class="card"><button class="btn-red" data-act="goto" data-stage="script">Write script</button></div>`;
  return `<div class="row"><h2 style="margin:0 0 10px">Script room</h2>
      <span class="item"><small>${s.wordCount} words · ${escapeHtml(s.lengthTarget)}</small></span>
      <button class="btn-red" data-act="goto" data-stage="package">Package titles + SEO</button></div>
    <div class="card"><h3>Hook</h3><p>${escapeHtml(s.hook)}</p></div>
    <div class="card" style="margin-top:10px">
      ${s.lines
        .map(
          (l) => `<div class="script-line"><b>${escapeHtml(l.t)}</b><span>${escapeHtml(l.who)}</span><div>${escapeHtml(l.text)}</div></div>`,
        )
        .join("")}
    </div>
    <div class="card" style="margin-top:10px"><h3>Chapters</h3><div class="pre">${s.chapters.map((c) => `${c.t} ${c.title}`).join("\n")}</div></div>`;
}

function viewPackage(p) {
  const pack = p?.pack;
  if (!pack) return `<div class="card"><button class="btn-red" data-act="goto" data-stage="package">Build package</button></div>`;
  return `<div class="row"><h2 style="margin:0 0 10px">Packaging</h2>
      <button class="btn-red" data-act="goto" data-stage="production">Production kit</button></div>
    <div class="grid-2">
      <div class="card"><h3>Titles</h3><div class="pre">${pack.titles.map((t, i) => `${i + 1}. ${t}`).join("\n")}</div></div>
      <div class="card"><h3>Thumbnail</h3>
        <p><b>${escapeHtml(pack.thumbnail.text)}</b></p>
        <p>${escapeHtml(pack.thumbnail.visual)}</p>
        <p>${escapeHtml(pack.thumbnail.colors)}</p>
        <small>${escapeHtml(pack.thumbnail.avoid)}</small>
      </div>
    </div>
    <div class="card" style="margin-top:10px"><h3>Description</h3><div class="pre">${escapeHtml(pack.description)}</div></div>
    <div class="card" style="margin-top:10px"><h3>Tags</h3><p>${escapeHtml(pack.tags.join(", "))}</p></div>`;
}

function viewProduction(p) {
  const k = p?.production;
  if (!k) return `<div class="card"><button class="btn-red" data-act="goto" data-stage="production">Build kit</button></div>`;
  return `<div class="row"><h2 style="margin:0 0 10px">Production kit</h2>
      <button class="btn-red" data-act="goto" data-stage="upload">Upload pack</button></div>
    <div class="grid-2">
      <div class="card"><h3>Shots</h3><div class="pre">${k.shots.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>B-roll</h3><div class="pre">${k.broll.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>Voice</h3><p>${escapeHtml(k.voice)}</p><p>${escapeHtml(k.editPace)}</p></div>
      <div class="card"><h3>Compliance checklist</h3><div class="pre">${k.checklist.map((x) => "☐ " + x).join("\n")}</div></div>
    </div>`;
}

function viewUpload(p) {
  const u = p?.upload;
  if (!u) return `<div class="card"><button class="btn-red" data-act="goto" data-stage="upload">Build upload pack</button></div>`;
  return `<div class="row"><h2 style="margin:0 0 10px">Upload pack</h2>
      <button class="btn-red" data-act="export">Download full pack</button></div>
    <div class="grid-2">
      <div class="card"><h3>File / playlist</h3>
        <p><b>${escapeHtml(u.filename)}</b></p>
        <p>${escapeHtml(u.playlist)}</p>
        <p>${escapeHtml(u.schedule)}</p>
      </div>
      <div class="card"><h3>First hour</h3><div class="pre">${u.firstHour.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>Shorts cutdowns</h3><div class="pre">${u.shortsCutdowns.map((x) => "• " + x).join("\n")}</div></div>
      <div class="card"><h3>Compliance</h3><div class="pre">${u.compliance.map((x) => "☐ " + x).join("\n")}</div></div>
    </div>
    <div class="card" style="margin-top:10px"><h3>Community post</h3><p>${escapeHtml(u.communityPost)}</p></div>`;
}

function renderAll() {
  renderSteps();
  renderProjects();
  renderRail();
  renderWorkspace();
}

function saveChannelFromForm() {
  document.querySelectorAll("[data-field]").forEach((el) => {
    state.channel[el.dataset.field] = el.value.trim();
  });
  persist();
}

function applyProject(next) {
  const i = state.projects.findIndex((p) => p.id === next.id);
  if (i >= 0) state.projects[i] = next;
  else state.projects.unshift(next);
  state.activeId = next.id;
  persist();
  renderAll();
}

function goto(stage) {
  let p = ensureProject();
  p.channel = { ...state.channel };
  if (stage === "setup") {
    p.stage = "setup";
    applyProject(p);
    return;
  }
  const order = YT.STAGES.map((s) => s.id);
  const target = order.indexOf(stage);
  for (let i = 1; i <= target; i++) {
    p = YT.runStage(p, order[i]);
  }
  applyProject(p);
  setStatus("", `${YT.STAGES[target].label} ready`);
}

function autopilot(topicText) {
  setStatus("thinking", "Producing full video system…");
  const p = YT.produceAll(state.channel, topicText);
  applyProject(p);
  setStatus("", "Full pack ready");
  return p;
}

function exportMarkdown() {
  const p = project();
  if (!p) return "";
  const t = p.selectedTopic?.topic || p.title;
  const bits = [
    `# ${t}`,
    ``,
    `Channel: ${p.channel.name} · ${p.channel.niche} · ${p.channel.country}`,
    ``,
    p.selectedTopic ? `## Angle\n${p.selectedTopic.angle}\n\n## Hook\n${p.selectedTopic.hook}` : "",
    p.research ? `## Research\n${p.research.recommendation}` : "",
    p.script ? `## Script\n${p.script.lines.map((l) => `[${l.t}] (${l.who}) ${l.text}`).join("\n")}` : "",
    p.pack ? `## Titles\n${p.pack.titles.map((x, i) => `${i + 1}. ${x}`).join("\n")}\n\n## Description\n${p.pack.description}` : "",
    p.production ? `## Shots\n${p.production.shots.map((x) => `- ${x}`).join("\n")}` : "",
    p.upload ? `## Upload\nFile: ${p.upload.filename}\n${p.upload.communityPost}` : "",
  ];
  return bits.filter(Boolean).join("\n\n");
}

function downloadPack() {
  const md = exportMarkdown();
  if (!md) return;
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${(project()?.upload?.filename || "youtube-pack")}.md`;
  a.click();
}

async function callModel(userText) {
  const s = state.settings;
  const messages = [
    { role: "system", content: YT.masterPrompt(state.channel, project()) },
    { role: "user", content: userText },
  ];
  const attempts = [];
  if (s.apiKey && (s.provider === "groq" || s.provider === "auto")) {
    attempts.push({
      url: "https://api.groq.com/openai/v1/chat/completions",
      headers: { Authorization: `Bearer ${s.apiKey}` },
      body: { model: s.model || "llama-3.1-8b-instant", messages, temperature: 0.6 },
    });
  }
  if (s.apiKey && s.provider === "openai") {
    attempts.push({
      url: "https://api.openai.com/v1/chat/completions",
      headers: { Authorization: `Bearer ${s.apiKey}` },
      body: { model: s.model || "gpt-4o-mini", messages },
    });
  }
  if (s.apiKey && s.provider === "openrouter") {
    attempts.push({
      url: "https://openrouter.ai/api/v1/chat/completions",
      headers: { Authorization: `Bearer ${s.apiKey}` },
      body: { model: s.model || "openai/gpt-4o-mini", messages },
    });
  }
  if (s.provider === "auto" || s.provider === "pollinations") {
    attempts.push({
      url: "https://text.pollinations.ai/openai",
      headers: {},
      body: { model: s.model || "openai", messages },
    });
  }
  for (const attempt of attempts) {
    try {
      const res = await fetch(attempt.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...attempt.headers },
        body: JSON.stringify(attempt.body),
      });
      if (!res.ok) continue;
      const data = await res.json();
      const text = data.choices?.[0]?.message?.content;
      if (text) return text.trim();
    } catch {}
  }
  return null;
}

function localDirect(text) {
  const lower = text.toLowerCase();
  if (/decide|auto|poora|pura|sab (bana|kar)|full pack|start/.test(lower)) {
    const topic = text.replace(/decide for me|decide everything|autopilot|poora bana|full pack|start/gi, "").trim();
    const p = autopilot(topic.length > 8 ? topic : "");
    return `Full production pack ready for “${p.title}”. Pipeline is at Upload Pack. Export whenever you want.`;
  }
  if (/research|market|trend/.test(lower)) {
    goto("research");
    return "Market research is on the board — trends, gaps, competitor tells, and the call.";
  }
  if (/topic|ideas|10 /.test(lower)) {
    goto("topics");
    return "10 scored topics are in the lab. Click one or lock #1.";
  }
  if (/script|write/.test(lower)) {
    goto("script");
    return "Script room is loaded: hook, timed VO, chapters, CTA.";
  }
  if (/title|thumb|seo|packag/.test(lower)) {
    goto("package");
    return "Packaging ready: 5 titles, thumbnail brief, description, tags.";
  }
  if (/shot|b-?roll|produc/.test(lower)) {
    goto("production");
    return "Production kit ready: shots, B-roll, voice notes, compliance.";
  }
  if (/upload|publish/.test(lower)) {
    goto("upload");
    return "Upload pack ready: filename, playlist, shorts cutdowns, first-hour list.";
  }
  if (/channel|setup|niche/.test(lower) && /save|set|change|naam|name/.test(lower) === false) {
    goto("setup");
    return "Channel desk is open. Fill the essentials or tell me to decide.";
  }
  const nicheHit = Object.entries({
    finance: ["Personal Finance", "India money systems for salaried people"],
    money: ["Personal Finance", "India money systems for salaried people"],
    ai: ["AI Tools", "YouTube + work automation without spam"],
    tech: ["Tech Explainers", "Tools and systems for Indian operators"],
    health: ["Health & Habits", "Desk-job health without guru claims"],
    career: ["Career & Skills", "Offers, switches, and skill stacks"],
    history: ["History / Documentary", "City-scale stories, objects, maps"],
  }).find(([k]) => lower.includes(k));
  if (nicheHit) {
    state.channel.niche = nicheHit[1][0];
    state.channel.subNiche = nicheHit[1][1];
    persist();
    const p = autopilot();
    return `${nicheHit[1][0]} lock ho gaya. Full pack: “${p.title}”.`;
  }
  return null;
}

async function send(raw) {
  const text = raw.trim();
  if (!text || state.busy) return;
  state.messages.push({ role: "user", content: text });
  $("#input").value = "";
  state.busy = true;
  setStatus("thinking", "Agent working…");
  renderWorkspace();
  try {
    let answer = localDirect(text);
    if (!answer) {
      const model = await callModel(text);
      answer =
        model ||
        "Samajh gaya. Niche / topic clearly bolo, ya “decide for me” likho — main poora video system nikaal dunga.";
    }
    state.messages.push({ role: "agent", content: answer });
    setStatus("", "Ready to produce");
  } finally {
    state.busy = false;
    renderAll();
  }
}

function bind() {
  if (!state.projects.length) {
    const p = YT.emptyProject(state.channel);
    state.projects = [p];
    state.activeId = p.id;
  } else {
    state.activeId = state.projects[0].id;
  }

  $("#settingsProvider").value = state.settings.provider || "auto";
  $("#settingsKey").value = state.settings.apiKey || "";
  $("#settingsModel").value = state.settings.model || "";

  renderAll();

  $("#steps").addEventListener("click", (e) => {
    const step = e.target.closest("[data-stage]");
    if (step) goto(step.dataset.stage);
  });
  $("#projects").addEventListener("click", (e) => {
    const item = e.target.closest("[data-id]");
    if (!item) return;
    state.activeId = item.dataset.id;
    renderAll();
  });
  $("#newVideo").addEventListener("click", () => {
    const p = YT.emptyProject(state.channel);
    state.projects.unshift(p);
    state.activeId = p.id;
    persist();
    renderAll();
  });
  $("#autoPilot").addEventListener("click", () => {
    saveChannelFromForm();
    autopilot();
  });
  $("#exportMd").addEventListener("click", downloadPack);
  $("#copyPack").addEventListener("click", async () => {
    const md = exportMarkdown();
    if (!md) return;
    await navigator.clipboard.writeText(md);
    setStatus("", "Pack copied");
  });
  $("#saveSettings").addEventListener("click", () => {
    state.settings.provider = $("#settingsProvider").value;
    state.settings.apiKey = $("#settingsKey").value.trim();
    state.settings.model = $("#settingsModel").value.trim();
    persist();
    setStatus("", "Model settings saved");
  });
  $("#workspace").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn) return;
    const act = btn.dataset.act;
    if (act === "save-channel") {
      saveChannelFromForm();
      setStatus("", "Channel saved");
      renderRail();
    }
    if (act === "autopilot") {
      saveChannelFromForm();
      autopilot();
    }
    if (act === "goto") goto(btn.dataset.stage);
    if (act === "lock-best") {
      const p = ensureProject();
      if (p.topics[0]) p.selectedTopic = p.topics[0];
      applyProject(p);
      goto("upload");
    }
    if (act === "pick-topic") {
      const p = ensureProject();
      p.selectedTopic = p.topics.find((t) => t.id === btn.dataset.tid);
      applyProject(p);
      goto("deep");
    }
    if (act === "export") downloadPack();
  });
  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    send($("#input").value);
  });
  $("#input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send($("#input").value);
    }
  });
}

window.addEventListener("DOMContentLoaded", bind);
