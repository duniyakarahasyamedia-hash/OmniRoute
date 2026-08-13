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

  function paintThumb({ text, topic, channel, variant = 0 }) {
    const canvas = document.createElement("canvas");
    canvas.width = 1280;
    canvas.height = 720;
    const ctx = canvas.getContext("2d");
    const palettes = [
      ["#0b0b0d", "#ff2d2d", "#f5c16c"],
      ["#12080a", "#ff7a18", "#fff4d6"],
      ["#070b14", "#3ee0b0", "#f5c16c"],
    ];
    const [bg, accent, gold] = palettes[variant % palettes.length];
    const g = ctx.createLinearGradient(0, 0, 1280, 720);
    g.addColorStop(0, bg);
    g.addColorStop(1, "#16161c");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 1280, 720);
    ctx.fillStyle = accent;
    ctx.fillRect(variant === 1 ? 0 : 1180, 0, variant === 1 ? 1280 : 20, variant === 1 ? 18 : 720);
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    ctx.beginPath();
    ctx.arc(1080, 120, 260, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = gold;
    ctx.font = "700 28px Be Vietnam Pro, sans-serif";
    ctx.fillText((channel || "SAATHI").toUpperCase().slice(0, 28), 72, 90);
    ctx.fillStyle = "#fff";
    wrap(ctx, text || "ONE RULE", 72, 250, 900, 92);
    ctx.fillStyle = "rgba(255,255,255,0.72)";
    ctx.font = "600 28px Be Vietnam Pro, sans-serif";
    wrap(ctx, topic || "", 72, 520, 980, 28);
    ctx.fillStyle = accent;
    ctx.fillRect(72, 640, 180, 10);
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

  async function buildVoiceovers(project, limit = 6) {
    const lines = (project.script?.lines || []).filter((l) => l.who === "VO").slice(0, limit);
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

  async function renderPreview(project, onTick) {
    const canvas = document.createElement("canvas");
    canvas.width = 1280;
    canvas.height = 720;
    const ctx = canvas.getContext("2d");
    const thumb = project.media?.thumbs?.find((t) => t.id === project.media.selectedThumb) || project.media?.thumbs?.[0];
    const bg = thumb?.src ? await loadImage(thumb.src) : null;
    const lines = (project.script?.lines || []).filter((l) => l.who === "VO").slice(0, 5);
    const slides = lines.length ? lines : [{ text: project.selectedTopic?.topic || "Saathi Studio" }];
    const stream = canvas.captureStream(30);
    const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    const rec = new MediaRecorder(stream, { mimeType: mime });
    const chunks = [];
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    const done = new Promise((resolve) => {
      rec.onstop = () => resolve(new Blob(chunks, { type: mime }));
    });
    rec.start();
    for (let i = 0; i < slides.length; i++) {
      if (onTick) onTick(Math.round(((i + 1) / slides.length) * 90));
      const ms = Math.min(7000, 1800 + String(slides[i].text).length * 35);
      const start = performance.now();
      while (performance.now() - start < ms) {
        ctx.fillStyle = "#070708";
        ctx.fillRect(0, 0, 1280, 720);
        if (bg) ctx.drawImage(bg, 0, 0, 1280, 720);
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fillRect(0, 420, 1280, 300);
        ctx.fillStyle = "#f5c16c";
        ctx.font = "700 22px Be Vietnam Pro, sans-serif";
        ctx.fillText(project.channel?.name || "Saathi Studio", 64, 480);
        ctx.fillStyle = "#fff";
        wrap(ctx, slides[i].text, 64, 540, 1150, 36);
        await new Promise((r) => requestAnimationFrame(r));
      }
    }
    rec.stop();
    const blob = await done;
    if (onTick) onTick(100);
    return { blob, url: URL.createObjectURL(blob), name: `${project.upload?.filename || "saathi-preview"}.webm` };
  }

  async function dataUrlToBlob(src) {
    const res = await fetch(src);
    return res.blob();
  }

  return { paintThumb, studioThumbs, aiThumbUrls, voiceUrl, fetchAudio, speakLine, buildVoiceovers, renderPreview, dataUrlToBlob };
})();
