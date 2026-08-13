const $ = (s) => document.querySelector(s);

const STORE = {
  studio: "saathi.studio.v2",
  settings: "saathi.settings.v2",
};

const DEFAULT_SETTINGS = {
  provider: "auto",
  apiKey: "",
  model: "openai",
  ytApiKey: "",
  ytClientId: "",
  ytToken: "",
  ytExpires: 0,
  ytChannelTitle: "",
  ytChannelId: "",
};

function currentModelMeta() {
  const id = state.settings.model;
  const provider = state.settings.provider;
  if (provider === "local" || id === "saathi-studio") return findModel("saathi-studio");
  return modelsFor(provider).find((m) => m.id === id) || findModel(id);
}

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

function slimMedia(media) {
  if (!media) {
    return {
      thumbs: [],
      selectedThumb: null,
      voices: [],
      previewUrl: "",
      previewName: "",
      ytVideoId: "",
      liveVideos: [],
      shorts: [],
      srt: "",
      wiki: [],
      comments: [],
      analytics: null,
      playlistId: "",
    };
  }
  return {
    thumbs: (media.thumbs || []).filter((t) => t.src && !String(t.src).startsWith("blob:")),
    selectedThumb: media.selectedThumb || null,
    voices: [],
    previewUrl: "",
    previewName: media.previewName || "",
    ytVideoId: media.ytVideoId || "",
    liveVideos: media.liveVideos || [],
    shorts: [],
    srt: media.srt || "",
    wiki: media.wiki || [],
    comments: media.comments || [],
    analytics: media.analytics || null,
    playlistId: media.playlistId || "",
  };
}

function persist() {
  const projects = state.projects.map((p) => ({ ...p, media: slimMedia(p.media) }));
  localStorage.setItem(STORE.studio, JSON.stringify({ projects }));
  localStorage.setItem("saathi.channel.v2", JSON.stringify(state.channel));
  localStorage.setItem(STORE.settings, JSON.stringify(state.settings));
  fetch("/api/studio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel: state.channel, projects }),
  }).catch(() => {});
}

function ensureMedia(p) {
  if (!p.media) p.media = slimMedia(null);
  return p.media;
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

function renderYtCard() {
  const on = Tube.connected(state.settings);
  const el = $("#ytStatus");
  if (!el) return;
  el.textContent = on
    ? `Connected · ${state.settings.ytChannelTitle || "YouTube"}`
    : state.settings.ytApiKey
      ? "API key saved · search only"
      : "Not connected";
  if ($("#ytApiKey") && document.activeElement !== $("#ytApiKey")) $("#ytApiKey").value = state.settings.ytApiKey || "";
  if ($("#ytClientId") && document.activeElement !== $("#ytClientId")) $("#ytClientId").value = state.settings.ytClientId || "";
}

function renderRail() {
  renderYtCard();
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
  const live = p.research?.live || p.media?.liveVideos || [];
  return `<div class="row"><h2 style="margin:0 0 10px">Market research</h2>
      <button data-act="live-search">Live YouTube search</button>
      <button class="btn-red" data-act="goto" data-stage="topics">Generate 10 topics</button></div>
    ${
      live.length
        ? `<div class="card" style="margin-bottom:10px"><h3>Live YouTube</h3>${live
            .map(
              (v) => `<div class="live-vid">${v.thumb ? `<img src="${escapeHtml(v.thumb)}" alt="">` : "<div></div>"}<div><b>${escapeHtml(v.title)}</b><small>${escapeHtml(v.channel)}</small></div></div>`,
            )
            .join("")}</div>`
        : `<div class="card" style="margin-bottom:10px"><span>Connect YouTube or hit Live search — public Invidious is used if no key.</span></div>`
    }
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
  const wiki = p.media?.wiki || [];
  return `<div class="row"><h2 style="margin:0 0 10px">Deep research</h2>
      <button data-act="wiki-facts">Pull live facts</button>
      <button class="btn-red" data-act="goto" data-stage="script">Write script</button></div>
    ${
      wiki.length
        ? `<div class="card" style="margin-bottom:10px"><h3>Wikipedia</h3>${wiki
            .map((w) => `<p><b>${escapeHtml(w.title)}</b> — ${escapeHtml(w.extract.slice(0, 280))}</p>`)
            .join("")}</div>`
        : ""
    }
    <div class="grid-2">
      <div class="card"><h3>Facts</h3><div class="pre">${d.facts.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
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
  const thumbs = p.media?.thumbs || [];
  return `<div class="row"><h2 style="margin:0 0 10px">Packaging</h2>
      <button data-act="gen-thumbs">Generate thumbnails</button>
      <button class="btn-red" data-act="goto" data-stage="production">Production kit</button></div>
    <div class="card" style="margin-bottom:10px"><h3>Thumbnail options</h3>
      ${
        thumbs.length
          ? `<div class="thumbs">${thumbs
              .map(
                (t) => `<button class="thumb-pick ${p.media.selectedThumb === t.id ? "on" : ""}" data-act="pick-thumb" data-tid="${escapeHtml(t.id)}"><img src="${escapeHtml(t.src)}" alt="${escapeHtml(t.kind)}"></button>`,
              )
              .join("")}</div>`
          : `<p>Generate studio + AI thumbnails, then pick one.</p>`
      }
      <p><b>${escapeHtml(pack.thumbnail.text)}</b> · ${escapeHtml(pack.thumbnail.visual)}</p>
    </div>
    <div class="grid-2">
      <div class="card"><h3>Titles</h3><div class="pre">${pack.titles.map((t, i) => `${i + 1}. ${t}`).join("\n")}</div></div>
      <div class="card"><h3>Thumbnail brief</h3>
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
      <button class="btn-red" data-act="make-complete">Make complete episode</button>
      <button data-act="yt-publish">Publish private</button>
      <button data-act="yt-schedule">Schedule</button>
      <button data-act="yt-playlist">Add to playlist</button>
      <button data-act="yt-captions">Upload captions</button>
      <button data-act="yt-comments">Fetch + reply comments</button>
      <button data-act="yt-analytics">Analytics</button>
      <button data-act="copy-community">Copy community post</button>
      <button data-act="download-zip">Download ZIP</button></div>
    <label>Schedule (optional)</label>
    <input id="publishAt" type="datetime-local" />
    ${
      p.media?.ytVideoId
        ? `<div class="card" style="margin:10px 0"><h3>Published</h3><a href="https://youtu.be/${escapeHtml(p.media.ytVideoId)}" target="_blank" rel="noreferrer">https://youtu.be/${escapeHtml(p.media.ytVideoId)}</a></div>`
        : `<div class="card" style="margin:10px 0"><span>${Tube.connected(state.settings) ? "YouTube connected. Make complete episode, then publish." : "No login needed for the full local episode + ZIP. YouTube login is only for posting."}</span></div>`
    }
    ${p.media?.previewUrl ? `<video class="preview" controls src="${escapeHtml(p.media.previewUrl)}"></video>` : ""}
    ${p.media?.analytics ? `<div class="card" style="margin-top:10px"><h3>28-day analytics</h3><pre class="pre">${escapeHtml(JSON.stringify(p.media.analytics, null, 2))}</pre></div>` : ""}
    ${
      (p.media?.comments || []).length
        ? `<div class="card" style="margin-top:10px"><h3>Comments</h3>${p.media.comments
            .map((c) => `<p><b>${escapeHtml(c.author || "")}</b> — ${escapeHtml(c.text || "")}</p>`)
            .join("")}</div>`
        : ""
    }
    <div class="grid-2">
      <div class="card"><h3>File / playlist</h3>
        <p><b>${escapeHtml(u.filename)}</b></p>
        <p>${escapeHtml(u.playlist)}</p>
        <p>${escapeHtml(u.schedule)}</p>
      </div>
      <div class="card"><h3>First hour</h3><div class="pre">${u.firstHour.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Shorts</h3><div class="pre">${u.shortsCutdowns.map((x) => "• " + escapeHtml(x)).join("\n")}</div></div>
      <div class="card"><h3>Compliance</h3><div class="pre">${u.compliance.map((x) => "☐ " + escapeHtml(x)).join("\n")}</div></div>
    </div>
    <div class="card" style="margin-top:10px"><h3>Community post</h3><p>${escapeHtml(u.communityPost)}</p></div>`;
}

function fillModelSelect() {
  const provider = $("#settingsProvider").value;
  const list = provider === "local" ? modelsFor("local") : modelsFor(provider);
  const select = $("#settingsModel");
  const current = state.settings.model;
  select.innerHTML = list
    .map((m) => `<option value="${escapeHtml(m.id)}" ${m.id === current ? "selected" : ""}>${escapeHtml(m.name)} — ${escapeHtml(m.use)}</option>`)
    .join("");
  if (!list.some((m) => m.id === select.value) && list[0]) select.value = list[0].id;
  const pack = MODEL_CATALOG[provider === "auto" ? "pollinations" : provider] || MODEL_CATALOG.pollinations;
  $("#modelHint").textContent = pack.hint || "";
}

function renderCatalog() {
  const active = `${state.settings.provider}:${state.settings.model}`;
  $("#modelCatalog").innerHTML = Object.entries(MODEL_CATALOG)
    .map(([provider, pack]) => {
      const chips = pack.models
        .map((m) => {
          const on = state.settings.provider === provider && state.settings.model === m.id;
          return `<div class="model-chip ${on ? "on" : ""}" data-pick-provider="${provider}" data-pick-model="${escapeHtml(m.id)}">
            <div><b>${escapeHtml(m.name)}</b><small>${escapeHtml(m.use)}</small></div>
            <span class="badge ${m.tier}">${m.tier.replace("-", " ")}</span>
          </div>`;
        })
        .join("");
      return `<div class="model-group"><h4>${escapeHtml(pack.label)} · ${pack.key ? "key" : "no key"}</h4>${chips}</div>`;
    })
    .join("");
  const meta = currentModelMeta();
  $("#activeModel").textContent = `${meta.providerLabel || "Local"} · ${meta.name}`;
}

function renderAll() {
  renderSteps();
  renderProjects();
  renderRail();
  renderWorkspace();
  renderCatalog();
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

function queryForSearch(p) {
  const ch = p?.channel || state.channel;
  return `${ch.niche} ${ch.country} ${ch.language} ${p?.selectedTopic?.topic || ch.subNiche || ""}`.trim();
}

async function liveSearch(p = project()) {
  if (!p) return [];
  setStatus("thinking", "Searching YouTube…");
  const videos = await Tube.search(queryForSearch(p), state.settings, /india/i.test(state.channel.country) ? "IN" : "US");
  ensureMedia(p);
  p.media.liveVideos = videos;
  if (p.research) p.research = YT.mergeLive(p.research, videos);
  applyProject(p);
  setStatus("", videos.length ? `${videos.length} live videos found` : "No live hits — using local research");
  return videos;
}

async function genThumbs(p = project()) {
  if (!p?.pack) goto("package");
  p = project();
  ensureMedia(p);
  setStatus("thinking", "Painting thumbnails…");
  const studio = MediaKit.studioThumbs(p);
  const ai = MediaKit.aiThumbUrls(p);
  const stock = await Facts.stockStills(`${state.channel.country} ${state.channel.niche} street`).catch(() => []);
  p.media.thumbs = [...studio, ...ai, ...stock];
  p.media.selectedThumb = studio[0].id;
  applyProject(p);
  setStatus("", "Thumbnails + stock B-roll ready");
}

async function genVoice(p = project()) {
  if (!p?.script) goto("script");
  p = project();
  ensureMedia(p);
  setStatus("thinking", "Generating voiceover…");
  p.media.voices = await MediaKit.buildVoiceovers(p, 6);
  applyProject(p);
  const ok = p.media.voices.filter((v) => v.ok).length;
  setStatus("", ok ? `${ok} VO lines ready` : "Cloud VO blocked — use Speak for browser voice");
}

async function renderPreview(p = project()) {
  if (!p?.script) {
    goto("script");
    p = project();
  }
  ensureMedia(p);
  if (!p.media.thumbs?.length) await genThumbs(p);
  p = project();
  setStatus("thinking", "Rendering preview video…");
  const out = await MediaKit.renderPreview(p, (n) => setStatus("thinking", `Rendering ${n}%`));
  p.media.previewUrl = out.url;
  p.media.previewBlob = out.blob;
  p.media.previewName = out.name;
  applyProject(p);
  setStatus("", "Preview video ready");
  return out;
}

async function publishYouTube() {
  let p = project();
  if (!p) return;
  if (!Tube.connected(state.settings)) {
    setStatus("", "Connect YouTube first");
    return;
  }
  if (!p.media?.previewBlob) await renderPreview(p);
  p = project();
  setStatus("thinking", "Uploading to YouTube…");
  const publishAt = $("#publishAt")?.value ? new Date($("#publishAt").value).toISOString() : "";
  const meta = {
    title: p.pack?.titles?.[0] || p.title,
    description: p.pack?.description || "",
    tags: p.pack?.tags || [],
    privacy: "private",
    publishAt,
  };
  const video = await Tube.uploadVideo(p.media.previewBlob, meta, state.settings);
  p.media.ytVideoId = video.id;
  const thumb = (p.media.thumbs || []).find((t) => t.id === p.media.selectedThumb) || p.media.thumbs?.[0];
  if (thumb?.src) {
    try {
      const blob = await MediaKit.dataUrlToBlob(thumb.src);
      await Tube.setThumbnail(video.id, blob, state.settings);
    } catch {
      /* optional */
    }
  }
  applyProject(p);
  setStatus("", publishAt ? `Scheduled · ${video.id}` : `Published privately · ${video.id}`);
  return video;
}

async function pullWiki() {
  let p = project();
  if (!p) return;
  setStatus("thinking", "Pulling Wikipedia facts…");
  const wiki = await Facts.liveFacts(p.selectedTopic?.topic || p.title, p.channel.niche);
  ensureMedia(p);
  p.media.wiki = wiki;
  if (p.deep && wiki[0]) p.deep.wiki = wiki;
  applyProject(p);
  setStatus("", wiki.length ? `${wiki.length} live facts` : "No wiki hits");
}

async function makeSrt() {
  const p = project();
  if (!p?.script) goto("script");
  const cur = project();
  ensureMedia(cur);
  cur.media.srt = MediaKit.makeSrt(cur);
  applyProject(cur);
  setStatus("", "SRT ready");
}

async function renderShorts() {
  let p = project();
  if (!p?.script) goto("script");
  p = project();
  ensureMedia(p);
  if (!p.media.thumbs?.length) await genThumbs(p);
  p = project();
  setStatus("thinking", "Rendering Shorts…");
  p.media.shorts = await MediaKit.renderShorts(p, (n) => setStatus("thinking", `Shorts ${n}%`));
  applyProject(p);
  setStatus("", "3 Shorts ready");
}

async function downloadZip() {
  const p = project();
  if (!p) return;
  const files = [{ name: `${p.upload?.filename || "episode"}.md`, blob: new Blob([exportMarkdown()], { type: "text/markdown" }) }];
  if (p.media?.srt) files.push({ name: `${p.upload?.filename || "episode"}.srt`, blob: new Blob([p.media.srt], { type: "text/plain" }) });
  if (p.media?.previewBlob) files.push({ name: p.media.previewName || "episode.webm", blob: p.media.previewBlob });
  for (const s of p.media?.shorts || []) if (s.blob) files.push({ name: s.name, blob: s.blob });
  const zip = await Zip.build(files);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(zip);
  a.download = `${p.upload?.filename || "saathi-episode"}.zip`;
  a.click();
}

async function makeCompleteEpisode() {
  saveChannelFromForm();
  setStatus("thinking", "Building the complete episode…");
  let p = project();
  if (!p?.upload) p = autopilot();
  await liveSearch(p);
  await pullWiki();
  p = project();
  if (p.deep) {
    p.deep.wiki = p.media.wiki || [];
    p.script = YT.writeScript(p.selectedTopic?.topic || p.title, p.channel, p.deep);
    applyProject(p);
  }
  p = project();
  if (p.research?.live?.length) {
    p.topics = YT.generateTopics(p.channel, p.research.live.map((v) => v.title));
    p.selectedTopic = p.selectedTopic || p.topics[0];
    applyProject(p);
  }
  await genThumbs(project());
  await genVoice(project());
  await makeSrt();
  await renderPreview(project());
  await renderShorts();
  goto("upload");
  setStatus("", "Complete episode ready — ZIP or publish. YouTube login only if you want it live.");
}

async function connectRemaining() {
  return makeCompleteEpisode();
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

async function postJson(url, headers, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`http ${res.status}`);
  return res.json();
}

async function callOpenAI(url, key, model, messages) {
  const data = await postJson(url, key ? { Authorization: `Bearer ${key}` } : {}, { model, messages, temperature: 0.6 });
  const text = data.choices?.[0]?.message?.content;
  if (!text) throw new Error("empty");
  return text.trim();
}

async function callAnthropic(key, model, messages) {
  const system = messages.find((m) => m.role === "system")?.content || "";
  const data = await postJson(
    "https://api.anthropic.com/v1/messages",
    { "x-api-key": key, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" },
    {
      model,
      max_tokens: 1800,
      system,
      messages: messages.filter((m) => m.role !== "system"),
    },
  );
  const text = data.content?.map((c) => c.text).filter(Boolean).join("\n");
  if (!text) throw new Error("empty");
  return text.trim();
}

async function callGemini(key, model, messages) {
  const system = messages.find((m) => m.role === "system")?.content || "";
  const contents = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.content }] }));
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(key)}`;
  const data = await postJson(url, {}, { systemInstruction: { parts: [{ text: system }] }, contents });
  const text = data.candidates?.[0]?.content?.parts?.map((p) => p.text).join("");
  if (!text) throw new Error("empty");
  return text.trim();
}

async function callModel(userText) {
  const s = state.settings;
  if (s.provider === "local" || s.model === "saathi-studio") return null;
  const messages = [
    { role: "system", content: YT.masterPrompt(state.channel, project()) },
    { role: "user", content: userText },
  ];
  const meta = currentModelMeta();
  const attempts = [];

  const push = (fn) => attempts.push(fn);
  if (s.provider === "anthropic" && s.apiKey) push(() => callAnthropic(s.apiKey, s.model, messages));
  if (s.provider === "gemini" && s.apiKey) push(() => callGemini(s.apiKey, s.model, messages));
  if (s.provider === "groq" && s.apiKey) push(() => callOpenAI(MODEL_CATALOG.groq.url, s.apiKey, s.model, messages));
  if (s.provider === "openai" && s.apiKey) push(() => callOpenAI(MODEL_CATALOG.openai.url, s.apiKey, s.model, messages));
  if (s.provider === "openrouter" && s.apiKey) push(() => callOpenAI(MODEL_CATALOG.openrouter.url, s.apiKey, s.model, messages));
  if (s.provider === "pollinations") push(() => callOpenAI(MODEL_CATALOG.pollinations.url, "", s.model || "openai", messages));

  if (s.provider === "auto") {
    if (s.apiKey) {
      push(() => callOpenAI(MODEL_CATALOG.groq.url, s.apiKey, s.model.includes("/") || s.model.startsWith("llama") || s.model.includes("gemma") || s.model.includes("qwen") || s.model.includes("deepseek") || s.model.includes("kimi") || s.model.includes("gpt-oss") ? s.model : "llama-3.1-8b-instant", messages));
      push(() => callGemini(s.apiKey, /gemini/.test(s.model) ? s.model : "gemini-2.0-flash", messages));
      push(() => callOpenAI(MODEL_CATALOG.openrouter.url, s.apiKey, s.model, messages));
    }
    push(() => callOpenAI(MODEL_CATALOG.pollinations.url, "", meta?.provider === "pollinations" ? s.model : "openai", messages));
  }

  for (const attempt of attempts) {
    try {
      const text = await attempt();
      if (text) return text;
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
    return "Upload pack ready. Connect YouTube to publish the preview as Private.";
  }
  if (/thumb|thumbnail/.test(lower)) {
    genThumbs();
    return "Generating studio + AI thumbnails.";
  }
  if (/voice|voiceover|tts/.test(lower)) {
    genVoice();
    return "Generating voiceover lines.";
  }
  if (/render|preview video|video bana/.test(lower)) {
    renderPreview();
    return "Rendering preview cut.";
  }
  if (/connect|live search|youtube/.test(lower)) {
    connectRemaining();
    return "Connecting remaining pieces: live search, thumbs, VO, preview.";
  }
  if (/model|llm|gpt|claude|gemini|groq|kaun sa model/.test(lower)) {
    const list = allModels()
      .map((m) => `• ${m.providerLabel}: ${m.name} (${m.tier}) — ${m.use}`)
      .join("\n");
    return `Yeh models add hain. Right rail se pick karo.\n\n${list}\n\nLocal Engine hamesha on hai. Pollinations free hai. Groq/Gemini ke liye free key. OpenAI/Claude paid.`;
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

  const oauth = Tube.consumeHash();
  if (oauth) {
    state.settings.ytToken = oauth.token;
    state.settings.ytExpires = oauth.expires;
    persist();
    Tube.myChannel(state.settings)
      .then((ch) => {
        if (!ch) return;
        state.settings.ytChannelTitle = ch.title;
        state.settings.ytChannelId = ch.id;
        persist();
        renderYtCard();
        setStatus("", `YouTube connected · ${ch.title}`);
      })
      .catch(() => setStatus("", "YouTube token saved"));
  }

  $("#settingsProvider").value = state.settings.provider || "auto";
  $("#settingsKey").value = state.settings.apiKey || "";
  fillModelSelect();
  if (state.settings.model) $("#settingsModel").value = state.settings.model;
  if ($("#ytApiKey")) $("#ytApiKey").value = state.settings.ytApiKey || "";
  if ($("#ytClientId")) $("#ytClientId").value = state.settings.ytClientId || "";

  renderAll();

  $("#settingsProvider").addEventListener("change", () => {
    state.settings.provider = $("#settingsProvider").value;
    fillModelSelect();
    state.settings.model = $("#settingsModel").value;
    persist();
    renderCatalog();
  });
  $("#settingsModel").addEventListener("change", () => {
    state.settings.model = $("#settingsModel").value;
    persist();
    renderCatalog();
  });
  $("#modelCatalog").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-pick-model]");
    if (!chip) return;
    state.settings.provider = chip.dataset.pickProvider;
    state.settings.model = chip.dataset.pickModel;
    $("#settingsProvider").value = state.settings.provider;
    fillModelSelect();
    $("#settingsModel").value = state.settings.model;
    persist();
    renderCatalog();
    setStatus("", `${findModel(state.settings.model).name} selected`);
  });

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
  $("#makeComplete")?.addEventListener("click", () => {
    makeCompleteEpisode().catch((err) => setStatus("", err.message));
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
    if (act === "live-search") liveSearch();
    if (act === "gen-thumbs") genThumbs();
    if (act === "pick-thumb") {
      const p = ensureProject();
      ensureMedia(p);
      p.media.selectedThumb = btn.dataset.tid;
      applyProject(p);
    }
    if (act === "gen-voice") genVoice();
    if (act === "speak-line") {
      const line = project()?.media?.voices?.[Number(btn.dataset.idx)];
      if (line?.text) MediaKit.speakLine(line.text);
    }
    if (act === "render-preview") renderPreview().catch((err) => setStatus("", err.message));
    if (act === "render-shorts") renderShorts().catch((err) => setStatus("", err.message));
    if (act === "make-srt") makeSrt();
    if (act === "wiki-facts") pullWiki();
    if (act === "make-complete") makeCompleteEpisode().catch((err) => setStatus("", err.message));
    if (act === "download-zip") downloadZip().catch((err) => setStatus("", err.message));
    if (act === "copy-community") {
      const text = project()?.upload?.communityPost || "";
      navigator.clipboard.writeText(text);
      if (state.settings.ytChannelId) {
        window.open(`https://studio.youtube.com/channel/${state.settings.ytChannelId}/posts`, "_blank", "noopener");
      }
      setStatus("", "Community post copied");
    }
    if (act === "yt-publish" || act === "yt-schedule") {
      publishYouTube().catch((err) => setStatus("", err.message));
    }
    if (act === "yt-playlist") {
      const p = project();
      if (!p?.media?.ytVideoId) return setStatus("", "Publish first");
      Tube.ensurePlaylist(p.upload?.playlist || "Start here", state.settings)
        .then((id) => {
          p.media.playlistId = id;
          return Tube.addToPlaylist(id, p.media.ytVideoId, state.settings);
        })
        .then(() => {
          applyProject(p);
          setStatus("", "Added to playlist");
        })
        .catch((err) => setStatus("", err.message));
    }
    if (act === "yt-captions") {
      const p = project();
      if (!p?.media?.ytVideoId || !p.media.srt) return setStatus("", "Need video + SRT");
      const lang = /hindi|hinglish/i.test(p.channel.language) ? "hi" : "en";
      Tube.uploadCaptions(p.media.ytVideoId, p.media.srt, lang, state.settings)
        .then(() => setStatus("", "Captions uploaded"))
        .catch((err) => setStatus("", err.message));
    }
    if (act === "yt-comments") {
      const p = project();
      if (!p?.media?.ytVideoId) return setStatus("", "Publish first");
      Tube.listComments(p.media.ytVideoId, state.settings)
        .then(async (comments) => {
          p.media.comments = comments;
          const reply = p.pack?.pinned || "Thanks — drop your city + one number.";
          for (const c of comments.slice(0, 3)) {
            if (c.parentId) {
              try {
                await Tube.replyComment(c.parentId, reply, state.settings);
              } catch {
                /* skip */
              }
            }
          }
          applyProject(p);
          setStatus("", `Replied to ${Math.min(3, comments.length)} comments`);
        })
        .catch((err) => setStatus("", err.message));
    }
    if (act === "yt-analytics") {
      Tube.analytics(state.settings)
        .then((data) => {
          const p = project();
          ensureMedia(p);
          p.media.analytics = data.rows || data;
          applyProject(p);
          setStatus("", "Analytics loaded");
        })
        .catch((err) => setStatus("", err.message));
    }
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
