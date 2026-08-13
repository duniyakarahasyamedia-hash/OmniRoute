const STILLS = ["./broll-1.png", "./broll-2.png", "./broll-3.png"];

function $(sel) {
  return document.querySelector(sel);
}

function lineSeconds(text) {
  return Math.min(7.5, Math.max(3.2, 2 + String(text).split(/\s+/).length * 0.38));
}

function buildEpisode() {
  const channel = { ...YT.DEFAULT_CHANNEL };
  return YT.produceAll(channel);
}

function startFilm(project) {
  const lines = (project.script?.lines || []).filter((l) => l.who === "VO");
  const bg = $("#cinemaBg");
  const lineEl = $("#cinemaLine");
  const clock = $("#cinemaClock");
  const channel = $("#cinemaChannel");
  const bar = $("#cinemaBar");
  if (!lines.length || !lineEl) return;

  channel.textContent = `${project.channel.name} · ${project.title}`;
  let i = 0;
  let started = performance.now();
  let hold = lineSeconds(lines[0].text) * 1000;

  const show = () => {
    const line = lines[i];
    lineEl.textContent = line.text;
    clock.textContent = line.t || `${i + 1}/${lines.length}`;
    bg.src = STILLS[i % STILLS.length];
    bg.classList.remove("kenburns");
    void bg.offsetWidth;
    bg.classList.add("kenburns");
    started = performance.now();
    hold = lineSeconds(line.text) * 1000;
    try {
      if (window.speechSynthesis) {
        const u = new SpeechSynthesisUtterance(line.text);
        u.rate = 1;
        const hi = speechSynthesis.getVoices().find((v) => /hi-IN|Hindi/i.test(`${v.lang} ${v.name}`));
        if (hi) u.voice = hi;
        speechSynthesis.cancel();
        speechSynthesis.speak(u);
      }
    } catch {
      /* visuals still run */
    }
  };

  const tick = (now) => {
    const p = Math.min(1, (now - started) / hold);
    if (bar) bar.style.width = `${((i + p) / lines.length) * 100}%`;
    if (p >= 1) {
      i = (i + 1) % lines.length;
      show();
    }
    requestAnimationFrame(tick);
  };

  show();
  requestAnimationFrame(tick);
}

function boot() {
  const project = buildEpisode();
  startFilm(project);
}

window.addEventListener("DOMContentLoaded", boot);
speechSynthesis?.getVoices();
