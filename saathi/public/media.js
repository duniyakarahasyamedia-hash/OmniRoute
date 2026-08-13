const MediaKit = (() => {
  function wrap(ctx, text, x, y, max, size) {
    ctx.font = `800 ${size}px Sora, Be Vietnam Pro, sans-serif`;
    const words = String(text).split(/\s+/);
    let line = "";
    let yy = y;
    for (const w of words) {
      const test = line ? `${line} ${w}` : w;
      if (ctx.measureText(test).width > max && line) {
        ctx.fillText(line, x, yy);
        line = w;
        yy += size + 8;
      } else line = test;
    }
    if (line) ctx.fillText(line, x, yy);
    return yy;
  }

  function lineSeconds(text) {
    return Math.min(12, Math.max(2.4, 1.6 + String(text).split(/\s+/).length * 0.42));
  }

  function paintThumb({ text, topic, channel, variant = 0, w = 1280, h = 720 }) {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    const palettes = [
      ["#0b0b0d", "#ff2d2d", "#f5c16c"],
      ["#12080a", "#ff7a18", "#fff4d6"],
      ["#070b14", "#3ee0b0", "#f5c16c"],
    ];
    const [bg, accent, gold] = palettes[variant % palettes.length];
    const g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, bg);
    g.addColorStop(1, "#16161c");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = accent;
    ctx.fillRect(0, 0, w, 16);
    ctx.fillStyle = gold;
    ctx.font = `700 ${Math.round(w * 0.022)}px Be Vietnam Pro, sans-serif`;
    ctx.fillText((channel || "SAATHI").toUpperCase().slice(0, 28), 56, Math.round(h * 0.12));
    ctx.fillStyle = "#fff";
    wrap(ctx, text || "ONE RULE", 56, Math.round(h * 0.34), w * 0.78, Math.round(w * 0.07));
    ctx.fillStyle = "rgba(255,255,255,0.72)";
    ctx.font = `600 ${Math.round(w * 0.022)}px Be Vietnam Pro, sans-serif`;
    wrap(ctx, topic || "", 56, Math.round(h * 0.72), w * 0.8, Math.round(w * 0.022));
    return canvas.toDataURL("image/jpeg", 0.86);
  }

  function studioThumbs(project) {
    const topic = project.selectedTopic?.topic || project.title || "New video";
    const text = project.pack?.thumbnail?.text || "ONE RULE";
    const channel = project.channel?.name || "Saathi";
    return [0, 1, 2].map((variant) => ({
      id: `canvas-${variant}`,
      kind: "studio",
      src: paintThumb({ text, topic, channel, variant }),
    }));
  }

  function aiThumbUrls(project) {
    const topic = project.selectedTopic?.topic || project.title || "youtube thumbnail";
    const text = project.pack?.thumbnail?.text || "ONE RULE";
    const visual = project.pack?.thumbnail?.visual || "dark cinematic youtube thumbnail";
    const prompt = `cinematic youtube thumbnail, no logos, no celebrity face, high contrast, giant text ${text}, ${topic}, ${visual}, 16:9`;
    const seed = encodeURIComponent(topic).slice(0, 24);
    return [1, 2].map((n) => ({
      id: `ai-${n}`,
      kind: "ai",
      src: `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=1280&height=720&nologo=true&seed=${seed}${n}`,
    }));
  }

  function voiceUrl(text, voice = "nova") {
    return `https://text.pollinations.ai/${encodeURIComponent(String(text).slice(0, 220))}?model=openai-audio&voice=${voice}`;
  }

  async function fetchAudio(text, voice) {
    const res = await fetch(voiceUrl(text, voice));
    if (!res.ok) throw new Error("voice fetch failed");
    const blob = await res.blob();
    if (!blob.type.startsWith("audio") && blob.size < 1000) throw new Error("not audio");
    return { blob, url: URL.createObjectURL(blob) };
  }

  function speakLine(text) {
    return new Promise((resolve) => {
      if (!window.speechSynthesis) return resolve();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.02;
      const hi = speechSynthesis.getVoices().find((v) => /hi-IN|Hindi/i.test(`${v.lang} ${v.name}`));
      if (hi) u.voice = hi;
      u.onend = resolve;
      u.onerror = resolve;
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    });
  }

  async function buildVoiceovers(project) {
    const lines = (project.script?.lines || []).filter((l) => l.who === "VO");
    const out = [];
    for (const line of lines) {
      try {
        const audio = await fetchAudio(line.text);
        out.push({ t: line.t, text: line.text, url: audio.url, blob: audio.blob, ok: true });
      } catch {
        out.push({ t: line.t, text: line.text, url: "", blob: null, ok: false });
      }
    }
    return out;
  }

  function loadImage(src) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  }

  function fmtSrt(sec) {
    const ms = Math.max(0, Math.round(sec * 1000));
    const h = String(Math.floor(ms / 3600000)).padStart(2, "0");
    const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, "0");
    const s = String(Math.floor((ms % 60000) / 1000)).padStart(2, "0");
    const z = String(ms % 1000).padStart(3, "0");
    return `${h}:${m}:${s},${z}`;
  }

  function makeSrt(project) {
    const lines = (project.script?.lines || []).filter((l) => l.who === "VO");
    let t = 0;
    return lines
      .map((l, i) => {
        const dur = lineSeconds(l.text);
        const start = t;
        t += dur + 0.2;
        return `${i + 1}\n${fmtSrt(start)} --> ${fmtSrt(start + dur)}\n${l.text}\n`;
      })
      .join("\n");
  }

  async function makeMusic(seconds) {
    const sr = 44100;
    const ctx = new OfflineAudioContext(2, Math.max(sr, Math.floor(sr * seconds)), sr);
    const master = ctx.createGain();
    master.gain.value = 0.05;
    master.connect(ctx.destination);
    const notes = [220, 261.63, 329.63, 392, 329.63, 261.63];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const filter = ctx.createBiquadFilter();
      const g = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.value = freq;
      filter.type = "lowpass";
      filter.frequency.value = 520;
      g.gain.setValueAtTime(0.0001, 0);
      g.gain.exponentialRampToValueAtTime(0.18, 0.4 + i * 0.08);
      g.gain.exponentialRampToValueAtTime(0.0001, seconds - 0.2);
      osc.connect(filter);
      filter.connect(g);
      g.connect(master);
      osc.start(0);
      osc.stop(seconds);
    });
    const pulse = ctx.createOscillator();
    const pg = ctx.createGain();
    pulse.type = "sine";
    pulse.frequency.value = 55;
    pg.gain.value = 0.04;
    pulse.connect(pg);
    pg.connect(master);
    pulse.start(0);
    pulse.stop(seconds);
    return ctx.startRendering();
  }

  function drawSlide(ctx, { w, h, bg, still, project, line, t }) {
    ctx.fillStyle = "#070708";
    ctx.fillRect(0, 0, w, h);
    const img = still || bg;
    if (img) {
      const zoom = 1.04 + Math.sin(t / 900) * 0.03;
      const iw = w * zoom;
      const ih = h * zoom;
      ctx.drawImage(img, (w - iw) / 2, (h - ih) / 2, iw, ih);
    }
    ctx.fillStyle = "rgba(0,0,0,0.58)";
    ctx.fillRect(0, h * 0.52, w, h * 0.48);
    ctx.fillStyle = "#f5c16c";
    ctx.font = "700 22px Be Vietnam Pro, sans-serif";
    ctx.fillText(project.channel?.name || "Saathi Studio", 48, h * 0.6);
    ctx.fillStyle = "#fff";
    wrap(ctx, line.text || "", 48, h * 0.68, w - 96, w > 800 ? 34 : 42);
  }

  async function recordCanvas(canvas, audioStream, durationMs, drawFrame, onTick) {
    const vStream = canvas.captureStream(30);
    const tracks = [...vStream.getVideoTracks()];
    if (audioStream) tracks.push(...audioStream.getAudioTracks());
    const stream = new MediaStream(tracks);
    const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
      ? "video/webm;codecs=vp9,opus"
      : MediaRecorder.isTypeSupported("video/webm;codecs=vp8,opus")
        ? "video/webm;codecs=vp8,opus"
        : "video/webm";
    const rec = new MediaRecorder(stream, { mimeType: mime });
    const chunks = [];
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    const done = new Promise((resolve) => {
      rec.onstop = () => resolve(new Blob(chunks, { type: "video/webm" }));
    });
    rec.start(250);
    const start = performance.now();
    while (performance.now() - start < durationMs) {
      const elapsed = performance.now() - start;
      drawFrame(elapsed);
      if (onTick) onTick(Math.min(99, Math.round((elapsed / durationMs) * 100)));
      await new Promise((r) => requestAnimationFrame(r));
    }
    rec.stop();
    return done;
  }

  async function decodeBlob(ctx, blob) {
    const buf = await blob.arrayBuffer();
    return ctx.decodeAudioData(buf.slice(0));
  }

  async function renderEpisode(project, { vertical = false, lines, onTick } = {}) {
    const w = vertical ? 1080 : 1280;
    const h = vertical ? 1920 : 720;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    const slides = (lines || (project.script?.lines || []).filter((l) => l.who === "VO")).map((l) => ({
      ...l,
      dur: lineSeconds(l.text) * 1000,
    }));
    if (!slides.length) slides.push({ text: project.title || "Saathi Studio", dur: 4000 });
    const totalMs = slides.reduce((n, s) => n + s.dur + 180, 800);
    const thumb = project.media?.thumbs?.find((t) => t.id === project.media.selectedThumb) || project.media?.thumbs?.[0];
    const stock = (project.media?.thumbs || []).filter((t) => t.kind === "stock" || t.kind === "ai");
    const bg = thumb?.src ? await loadImage(thumb.src) : null;
    const stills = [];
    for (const s of stock.slice(0, 4)) stills.push(await loadImage(s.src));

    const audioCtx = new AudioContext();
    const dest = audioCtx.createMediaStreamDestination();
    const music = await makeMusic(totalMs / 1000 + 1);
    const musicSrc = audioCtx.createBufferSource();
    const musicGain = audioCtx.createGain();
    musicSrc.buffer = music;
    musicSrc.loop = true;
    musicGain.gain.value = 0.7;
    musicSrc.connect(musicGain);
    musicGain.connect(dest);
    musicSrc.start();

    let cursor = audioCtx.currentTime + 0.15;
    const voices = project.media?.voices || [];
    for (let i = 0; i < slides.length; i++) {
      const v = voices.find((x) => x.text === slides[i].text && x.blob);
      if (!v?.blob) continue;
      try {
        const buf = await decodeBlob(audioCtx, v.blob);
        const src = audioCtx.createBufferSource();
        const g = audioCtx.createGain();
        src.buffer = buf;
        src.connect(g);
        g.connect(dest);
        g.gain.value = 1;
        src.start(cursor);
        cursor += buf.duration + 0.18;
      } catch {
        cursor += slides[i].dur / 1000;
      }
    }

    let acc = 0;
    const timeline = slides.map((s) => {
      const row = { ...s, from: acc, to: acc + s.dur };
      acc += s.dur + 180;
      return row;
    });

    const blob = await recordCanvas(
      canvas,
      dest.stream,
      totalMs,
      (elapsed) => {
        const slide = timeline.find((s) => elapsed >= s.from && elapsed < s.to) || timeline[timeline.length - 1];
        const still = stills[timeline.indexOf(slide) % Math.max(1, stills.length)] || null;
        drawSlide(ctx, { w, h, bg, still, project, line: slide, t: elapsed });
      },
      onTick,
    );
    audioCtx.close().catch(() => {});
    const name = `${project.upload?.filename || "saathi"}-${vertical ? "short" : "episode"}.webm`;
    return { blob, url: URL.createObjectURL(blob), name, durationMs: totalMs };
  }

  async function renderPreview(project, onTick) {
    return renderEpisode(project, { onTick });
  }

  async function renderShorts(project, onTick) {
    const vos = (project.script?.lines || []).filter((l) => l.who === "VO");
    const packs = [
      vos.slice(0, 2),
      vos.slice(2, 4),
      vos.slice(Math.max(0, vos.length - 2)),
    ].map((set) => (set.length ? set : vos.slice(0, 1)));
    const out = [];
    for (let i = 0; i < packs.length; i++) {
      if (onTick) onTick(Math.round(((i + 1) / packs.length) * 90));
      const clip = await renderEpisode(project, { vertical: true, lines: packs[i] });
      out.push({ ...clip, name: `${project.upload?.filename || "saathi"}-short-${i + 1}.webm` });
    }
    return out;
  }

  async function dataUrlToBlob(src) {
    const res = await fetch(src);
    return res.blob();
  }

  return {
    paintThumb,
    studioThumbs,
    aiThumbUrls,
    voiceUrl,
    fetchAudio,
    speakLine,
    buildVoiceovers,
    renderPreview,
    renderEpisode,
    renderShorts,
    makeSrt,
    makeMusic,
    dataUrlToBlob,
  };
})();
