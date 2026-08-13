const YT = (() => {
  const STAGES = [
    { id: "setup", label: "Channel Setup", hint: "Niche, audience, voice" },
    { id: "research", label: "Market Research", hint: "Trends, gaps, competitors" },
    { id: "topics", label: "Topic Lab", hint: "10 scored ideas" },
    { id: "deep", label: "Deep Research", hint: "Facts, stakes, angle" },
    { id: "script", label: "Script Room", hint: "Hook to end screen" },
    { id: "package", label: "Packaging", hint: "Title, thumb, SEO" },
    { id: "production", label: "Production Kit", hint: "Shots, VO, B-roll" },
    { id: "upload", label: "Upload Pack", hint: "Ready to publish" },
  ];

  const DEFAULT_CHANNEL = {
    name: "Rupee Radar",
    niche: "Personal Finance",
    subNiche: "India money systems for salaried people",
    country: "India",
    language: "Hinglish",
    audience: "Salaried 22-35 who feel behind on money",
    ageRange: "22-35",
    contentStyle: "Faceless documentary + on-screen proof",
    videoLength: "10-13 min",
    uploadFrequency: "3 videos / week",
    competitors: "Labour Law Advisor, Shankar IAS-style explainers, CA Rachana, Groww / Zerodha education",
    monetizationGoal: "YPP + finance affiliates + digital product",
    brandVoice: "Calm, sharp, no guru energy. Talk like a smart older cousin.",
    visualStyle: "Dark studio, red/gold type, receipts, charts, India street B-roll",
  };

  const NICHES = {
    "personal finance": {
      label: "Personal Finance",
      demand: 9,
      money: 9,
      formats: ["myth vs math", "one system", "salary teardown", "rule that saves tax", "story + ledger"],
      evergreen: [
        "emergency fund that actually fits an Indian salary",
        "EPF vs PPF vs NPS in one decision tree",
        "first 1 lakh invested without a guru",
        "credit card that does not become debt",
        "tax-saving that is not just 80C panic",
      ],
      trending: [
        "new tax regime vs old for 2026 salary slips",
        "why SIPs feel fake when rent eats 40%",
        "gold ETF vs jewellery after family pressure",
        "side income that does not kill the day job",
        "UPI credit and the silent debt loop",
      ],
      gaps: [
        "city-wise cost of living vs take-home",
        "what to do in the 48 hours after a job loss",
        "parents' LIC policies vs actually useful cover",
      ],
      problems: [
        "salary looks big on paper, vanishes by the 10th",
        "family money decisions without a fight",
        "fear of investing because of one bad IPO story",
      ],
    },
    tech: {
      label: "Tech Explainers",
      demand: 8,
      money: 8,
      formats: ["one tool teardown", "build with me", "scam autopsy", "career map"],
      evergreen: ["how the internet actually bills you", "privacy settings that matter", "laptop buying without regret"],
      trending: ["AI agents replacing intern work", "cheap Android vs work phone", "why every app wants your contacts"],
      gaps: ["tools for Indian freelancers that take INR", "college project to portfolio in 14 days"],
      problems: ["too many tools, no system", "fear of being left behind by AI"],
    },
    health: {
      label: "Health & Habits",
      demand: 8,
      money: 7,
      formats: ["one habit", "lab report decode", "kitchen science"],
      evergreen: ["sleep before supplements", "desk-job back pain", "protein on a veg Indian plate"],
      trending: ["creatine confusion", "glucose spikes after chai-nashta", "walking 8k in a hot city"],
      gaps: ["shift-worker health", "PCOS-friendly tiffin ideas without guru claims"],
      problems: ["no time, no gym, no honesty"],
    },
    career: {
      label: "Career & Skills",
      demand: 8,
      money: 8,
      formats: ["offer teardown", "skill stack", "week in the life"],
      evergreen: ["resume that survives ATS", "switch career without a degree reset"],
      trending: ["AI-proof skills in India", "service company to product jump", "LinkedIn that is not cringe"],
      gaps: ["tier-2 city remote playbook", "first 90 days after a layoff"],
      problems: ["stuck after 3 years", "interview anxiety"],
    },
    ai: {
      label: "AI Tools",
      demand: 9,
      money: 8,
      formats: ["workflow", "one job replaced", "honest limit test"],
      evergreen: ["prompt system that does not waste hours", "local vs cloud models"],
      trending: ["YouTube automation that is not spam", "AI for CA / legal / clinic ops", "agents vs chatbots"],
      gaps: ["Hindi workflow stack", "what still needs a human editor"],
      problems: ["tools everywhere, output still mid"],
    },
    history: {
      label: "History / Documentary",
      demand: 7,
      money: 6,
      formats: ["one object", "48 hours that changed a city", "letter from the archive"],
      evergreen: ["how a trade route made a city rich", "a law that still controls daily life"],
      trending: ["partition objects", "vanished professions", "maps that lie"],
      gaps: ["city micro-histories outside Delhi/Mumbai"],
      problems: ["school history felt dead"],
    },
  };

  function uid() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  }

  function hash(s) {
    let h = 2166136261;
    for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
    return h >>> 0;
  }

  function pick(arr, seed) {
    return arr[hash(seed) % arr.length];
  }

  function clamp(n, a = 1, b = 10) {
    return Math.max(a, Math.min(b, Math.round(n)));
  }

  function nicheKey(channel) {
    const blob = `${channel.niche} ${channel.subNiche}`.toLowerCase();
    if (/money|finance|rupee|tax|sip|invest/.test(blob)) return "personal finance";
    if (/\bai\b|agent|automat/.test(blob)) return "ai";
    if (/tech|gadget|phone|software|coding/.test(blob)) return "tech";
    if (/health|fit|diet|sleep/.test(blob)) return "health";
    if (/career|job|resume|skill/.test(blob)) return "career";
    if (/history|docu|war|ancient/.test(blob)) return "history";
    return "personal finance";
  }

  function packFor(channel) {
    return NICHES[nicheKey(channel)] || NICHES["personal finance"];
  }

  function scoreTopic(topic, channel, i) {
    const pack = packFor(channel);
    const viral = clamp(7 + ((hash(topic + "v") % 5) - 1) + (i < 3 ? 1 : 0));
    const search = clamp(pack.demand + ((hash(topic + "s") % 3) - 1));
    const competition = clamp(4 + (hash(topic + "c") % 5));
    const evergreen = clamp(6 + (hash(topic + "e") % 4));
    const money = clamp(pack.money + ((hash(topic + "m") % 3) - 1));
    const difficulty = clamp(3 + (hash(topic + "d") % 5));
    const total = clamp(
      viral * 0.22 + search * 0.18 + (11 - competition) * 0.14 + evergreen * 0.16 + money * 0.2 + (11 - difficulty) * 0.1,
    );
    return { viral, search, competition, evergreen, money, difficulty, total };
  }

  function uniqueAngle(topic, channel, i) {
    const angles = [
      `India-specific math, not US advice copy-pasted`,
      `One ugly real number in the first 20 seconds`,
      `Contrarian: the popular tip is the trap`,
      `City-split: metro vs tier-2 reality`,
      `A 7-day experiment, not a lecture`,
      `What YouTube gurus skip because it is boring and true`,
      `A receipt / screenshot as the hero prop`,
      `Two characters: 2019 you vs 2026 you`,
    ];
    return `${pick(angles, topic + i)} · ${channel.country} · ${channel.language}`;
  }

  function hookFor(topic, channel) {
    const hooks = [
      `If you earn in ${channel.country} and still feel broke by the 10th, this is not a motivation problem.`,
      `Stop scrolling. The next 11 minutes will save you from a mistake most ${channel.audience} already made.`,
      `Nobody making content on this tells you the ugly version. I will.`,
      `${topic}? The thumbnail is lying. The real story is smaller, sharper, and more useful.`,
      `I wish someone showed me this before I wasted 3 years doing the popular thing.`,
    ];
    return pick(hooks, topic + channel.name);
  }

  function generateTopics(channel, liveTitles = []) {
    const pack = packFor(channel);
    const liveSeeds = liveTitles
      .slice(0, 5)
      .map((t) => `What they missed in “${String(t).replace(/^Angle on:\s*/i, "")}”`);
    const seeds = [...liveSeeds, ...pack.trending, ...pack.evergreen, ...pack.gaps, ...pack.problems];
    const ideas = [];
    const used = new Set();
    for (let i = 0; i < seeds.length && ideas.length < 10; i++) {
      const base = seeds[i];
      if (used.has(base)) continue;
      used.add(base);
      const topic = titleCase(base);
      const scores = scoreTopic(topic, channel, i);
      ideas.push({
        id: uid(),
        topic,
        angle: uniqueAngle(topic, channel, i),
        hook: hookFor(topic, channel),
        audience: channel.audience,
        length: channel.videoLength,
        whyClick: `Curiosity + a concrete promise for ${channel.audience}.`,
        whyWatch: `New number, new rule, or a decision tree every 90 seconds.`,
        scores,
      });
    }
    while (ideas.length < 10) {
      const topic = `${pack.label} playbook #${ideas.length + 1} for ${channel.country}`;
      ideas.push({
        id: uid(),
        topic,
        angle: uniqueAngle(topic, channel, ideas.length),
        hook: hookFor(topic, channel),
        audience: channel.audience,
        length: channel.videoLength,
        whyClick: "Clear outcome in the title.",
        whyWatch: "Checklist they can screenshot.",
        scores: scoreTopic(topic, channel, ideas.length),
      });
    }
    return ideas.sort((a, b) => b.scores.total - a.scores.total);
  }

  function titleCase(s) {
    return s.replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function researchMarket(channel) {
    const pack = packFor(channel);
    return {
      trending: pack.trending,
      evergreen: pack.evergreen,
      demand: pack.demand,
      problems: pack.problems,
      competitors: channel.competitors
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      competitorPatterns: [
        "Long titles with a number and a fear word",
        "Red/yellow face or rupee prop on thumbnail",
        "First 30s is story, then list",
        "Weak middle: too much theory, too few receipts",
      ],
      gaps: pack.gaps,
      formats: pack.formats,
      live: [],
      recommendation:
        `Lead with ${pack.trending[0]}. Evergreen backbone: ${pack.evergreen[0]}. Gap nobody owns cleanly: ${pack.gaps[0]}.`,
    };
  }

  function mergeLive(research, videos) {
    const next = { ...(research || {}), live: videos || [] };
    const titles = (videos || []).map((v) => v.title).filter(Boolean);
    if (titles.length) {
      next.trending = [...titles.slice(0, 5), ...(research?.trending || [])].slice(0, 8);
      next.recommendation = `Live YouTube is talking about “${titles[0]}”. Unique angle: do the version they skipped. ${research?.recommendation || ""}`;
    }
    return next;
  }

  function deepResearch(topic, channel) {
    const pack = packFor(channel);
    return {
      facts: [
        `${channel.country} viewers punish vague advice — they stay for numbers, rules, and screenshots.`,
        `Search demand around “${topic.toLowerCase()}” sits next to ${pack.evergreen[0]}.`,
        `Audience pain: ${pack.problems[0]}.`,
        `Monetization path: ${channel.monetizationGoal}. Stay educational, no guaranteed returns.`,
        `Language: ${channel.language}. Keep jargon, then translate it in one line.`,
      ],
      stakes: `If they ignore this, they repeat the same expensive default for another year.`,
      sources: [
        "Official / primary rules and public docs (tax, labour, product TOS)",
        "2 competitor videos — steal structure, never script",
        "One lived example from the target city/salary band",
        "One contrarian data point that breaks the guru version",
      ],
      objections: [
        "I don't earn enough to start",
        "I will do this next month",
        "My family will not agree",
        "This is only for metro people",
      ],
      proof: ["on-screen calculator", "before/after ledger", "policy screenshot", "city cost table"],
    };
  }

  function writeScript(topic, channel, research) {
    const hook = hookFor(topic, channel);
    const mins = parseInt(channel.videoLength, 10) || 11;
    const lang = /hindi|hinglish/i.test(channel.language) ? "hinglish" : "en";
    const lines = [];
    const add = (t, who, text) => lines.push({ t, who, text });
    const fact = research?.facts?.[0] || `${channel.audience} stay for numbers, not slogans.`;
    const obj = research?.objections?.[0] || "I will start next month";
    const live = research?.wiki?.[0]?.extract || "";

    if (lang === "hinglish") {
      add("0:00", "VO", hook);
      add("0:20", "VO", `Main ${channel.name} hoon. Aaj sirf ${topic}. Promise: ek rule, ek number, ek 7-din ka experiment.`);
      add("0:45", "VO", `Pehle popular lie. Log kehte hain knowledge kam hai. Asli problem system ki kami hai.`);
      add("1:10", "B-ROLL", "Full-screen ugly number. Hold 3 seconds.");
      add("1:20", "VO", `Yeh number isliye chubhta hai kyunki ${channel.audience} isi loop mein phanse hain.`);
      add("1:50", "VO", `Ignore list: guru screenshots, overnight hacks, aur koi bhi line jisme guaranteed return ho.`);
      add("2:20", "VO", `Measure list: ek weekly number, ek leak, ek automatic transfer. Bas teen.`);
      add("2:50", "VO", fact);
      if (live) add("3:20", "VO", `Context jo log skip karte hain: ${live.slice(0, 240)}`);
      add("4:00", "VO", `Common objection: “${obj}.” Answer: start itna chhota rakho ke ego bore ho jaye.`);
      add("4:30", "VO", `Metro vs tier-2: rent ratio alag hai, rule same hai. Pehle ratio, phir product.`);
      add("5:05", "VO", `Ab system. Step 1 — naam do. Step 2 — date do. Step 3 — default banao taaki willpower na chahiye.`);
      add("5:40", "B-ROLL", "Three cards: NAME / DATE / DEFAULT.");
      add("5:50", "VO", `7-day experiment. Day 1 measure. Day 2 ek leak kaato. Day 3 ek transfer automate.`);
      add("6:25", "VO", `Day 4 kisi insaan ko dikhao, app ko nahi. Day 5 wahi number dubara. Day 6 friction hatao. Day 7 rule likh ke fridge pe chipkao.`);
      add("7:05", "VO", `Mid-video pause. Agar tumne ab tak koi number nahi likha, video band karke likho. Phir wapas aana.`);
      add("7:35", "VO", `Do galti jo har ${channel.country} viewer karta hai: copy-paste US advice, aur family pressure ko plan samajh lena.`);
      add("8:10", "VO", `Proof ka format: screenshot, calculator, ek before/after line. Story optional hai, math nahi.`);
      add("8:40", "VO", `Monetization note: yeh education hai, guarantee nahi. ${channel.monetizationGoal}.`);
      add("9:10", "VO", `Recap teen lafz mein: measure, cut, automate. ${topic.toLowerCase()} ko mood mat banao, rule banao.`);
      add("9:40", "VO", `Agar yeh useful laga, next video isi rule ko tumhare city ke numbers pe chalayenge.`);
      add("10:10", "VO", `Subscribe if you want the system. Skip if you want a guru. Comment: city + ek number.`);
      add("10:35", "B-ROLL", "End screen: previous video + Start here playlist.");
    } else {
      add("0:00", "VO", hook);
      add("0:20", "VO", `I'm ${channel.name}. Today: ${topic}. One rule, one number, one 7-day experiment.`);
      add("0:45", "VO", `The popular lie is that you lack knowledge. You lack a system.`);
      add("1:10", "B-ROLL", "Hold the ugly number.");
      add("1:20", "VO", `This number hurts because ${channel.audience} already live inside it.`);
      add("1:50", "VO", `Ignore list: guru screenshots, overnight hacks, any guaranteed return.`);
      add("2:20", "VO", `Measure three things only: a weekly number, one leak, one automatic transfer.`);
      add("2:50", "VO", fact);
      if (live) add("3:20", "VO", `Context most videos skip: ${live.slice(0, 240)}`);
      add("4:00", "VO", `Objection: “${obj}.” Start smaller than your ego wants.`);
      add("4:30", "VO", `Metro or tier-2: the rent ratio changes. The rule does not.`);
      add("5:05", "VO", `Name it. Date it. Default it so willpower is optional.`);
      add("5:50", "VO", `7 days: measure, cut, automate, show a human, remeasure, remove friction, write the rule.`);
      add("7:05", "VO", `If you have not written a number yet, pause. Write. Come back.`);
      add("7:35", "VO", `Two ${channel.country} mistakes: imported advice, and treating family pressure as a plan.`);
      add("8:10", "VO", `Proof is a screenshot and a calculator, not a speech.`);
      add("8:40", "VO", `Education, not a guarantee. ${channel.monetizationGoal}.`);
      add("9:10", "VO", `Recap: measure, cut, automate. Turn ${topic.toLowerCase()} into a rule.`);
      add("10:10", "VO", `Subscribe for the system. Comment your city and one number.`);
    }

    const spoken = lines.filter((l) => l.who === "VO").map((l) => l.text).join(" ");
    return {
      hook,
      lengthTarget: `${mins} min`,
      wordCount: spoken.split(/\s+/).length,
      chapters: [
        { t: "0:00", title: "The ugly open" },
        { t: "0:45", title: "The lie" },
        { t: "1:10", title: "The number" },
        { t: "2:20", title: "What to measure" },
        { t: "5:05", title: "The system" },
        { t: "5:50", title: "7-day experiment" },
        { t: "7:35", title: "Local mistakes" },
        { t: "9:10", title: "Recap + CTA" },
      ],
      lines,
      cta: "Comment your city + one number. Next video runs this rule on real local math.",
    };
  }

  function packageVideo(topic, channel, script) {
    const titles = [
      `${topic} (The Version Nobody Posts)`,
      `I Fixed ${topic} With One Ugly Rule`,
      `${topic} in ${channel.country}: Do This, Skip That`,
      `Stop Doing ${topic} The Guru Way`,
      `${topic}? Watch This Before You Lose Another Year`,
    ].map((t) => t.slice(0, 70));

    const thumbTexts = ["STOP THIS", "UGLY TRUTH", "ONE RULE", "DO THIS", "NOT A GURU"];
    return {
      titles,
      thumbnail: {
        text: pick(thumbTexts, topic),
        visual: `${channel.visualStyle}. One face-or-prop, giant 3-word text, high contrast, left third empty for mobile crop.`,
        colors: "Near-black base, YouTube red accent, gold highlight on the number.",
        avoid: "Clutter, tiny text, fake shocked face spam, copyrighted logos.",
      },
      description: [
        `${script.hook}`,
        ``,
        `In this video:`,
        ...script.chapters.map((c) => `${c.t} ${c.title}`),
        ``,
        `This is educational commentary for ${channel.audience} in ${channel.country}. Not financial, medical, or legal advice.`,
        ``,
        `Channel: ${channel.name} · ${channel.subNiche}`,
        ``,
        `#${slug(channel.niche)} #${slug(channel.country)} #youtube`,
      ].join("\n"),
      tags: uniqueTags(topic, channel),
      hashtags: [`#${slug(channel.niche)}`, `#${slug(topic).split("-").slice(0, 2).join("")}`, `#${slug(channel.country)}`],
      pinned: `What number should I break down next — comment your city + situation.`,
      endScreen: "Suggested: previous system video + subscribe + playlist “Start here”.",
    };
  }

  function uniqueTags(topic, channel) {
    const bits = `${topic} ${channel.niche} ${channel.subNiche} ${channel.country} ${channel.language} youtube ${channel.audience}`
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2);
    return [...new Set(bits)].slice(0, 18);
  }

  function slug(s) {
    return String(s)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
  }

  function productionKit(topic, channel, script) {
    return {
      voice: `${channel.brandVoice} Record dry, 10–15cm from mic, then light compression. No royalty music under speech.`,
      shots: [
        "Hook cold-open with the number full-screen",
        "Talking-head or faceless VO over B-roll",
        "Screen recording of calculator / sheet",
        "Street / desk B-roll matching the city",
        "Chapter cards every 90–120s",
        "End-screen 20s",
      ],
      broll: [
        "Hands counting cash / UPI animation",
        "City traffic at dusk",
        "Notebook with one rule written large",
        "Calendar / 7-day boxes",
      ],
      assets: ["lower thirds", "chapter cards", "one data slide", "end screen", "thumbnail PSD/Canva"],
      checklist: [
        "Original VO — no cloned celebrity voice",
        "No copyrighted music or movie clips",
        "Claims are educational, not guaranteed outcomes",
        "Affiliate / sponsor disclosure if used",
        "Captions burned or uploaded (language: " + channel.language + ")",
        "Loudness around -14 LUFS",
        "First 15s watched back on a phone",
      ],
      editPace: "Cut every 2–4s in the open. Slow down only on the number.",
      runtime: script.lengthTarget,
    };
  }

  function uploadPack(topic, channel, script, pack) {
    return {
      filename: `${slug(channel.name)}-${slug(topic).slice(0, 48)}`,
      schedule: `${channel.uploadFrequency} · first 48h reply to every comment`,
      playlist: `${channel.niche} · Start here`,
      cards: ["previous video at 40%", "playlist at 70%"],
      communityPost: `New video is live. The rule is in the first minute. Tell me if it matches your city.`,
      shortsCutdowns: [
        "Hook only (22s)",
        "The number (28s)",
        "7-day experiment (35s)",
      ],
      compliance: [
        "Original commentary — not a competitor recitation",
        "No medical/financial promises",
        "Fair-use clips only if transformative and short",
        "Made for kids: OFF",
        "Paid promotion box if any affiliate is mentioned",
      ],
      firstHour: [
        "Pin the comment",
        "Share to Community + one relevant Discord/Reddit if allowed",
        "Check mobile thumbnail at 2 sizes",
      ],
    };
  }

  function emptyProject(channel) {
    return {
      id: uid(),
      createdAt: Date.now(),
      stage: "setup",
      title: "Untitled video",
      channel: { ...channel },
      research: null,
      topics: [],
      selectedTopic: null,
      deep: null,
      script: null,
      pack: null,
      production: null,
      upload: null,
      media: { thumbs: [], selectedThumb: null, voices: [], previewUrl: "", previewName: "", ytVideoId: "", liveVideos: [] },
    };
  }

  function runStage(project, stage) {
    const channel = project.channel;
    const next = { ...project, stage };
    if (stage === "research") next.research = researchMarket(channel);
    if (stage === "topics") {
      const liveTitles = (next.research?.live || []).map((v) => v.title);
      next.topics = generateTopics(channel, liveTitles);
    }
    if (stage === "deep") {
      if (!next.selectedTopic && next.topics[0]) next.selectedTopic = next.topics[0];
      const topic = next.selectedTopic?.topic || channel.subNiche;
      next.title = topic;
      next.deep = deepResearch(topic, channel);
    }
    if (stage === "script") {
      const topic = next.selectedTopic?.topic || next.title;
      next.script = writeScript(topic, channel, next.deep || deepResearch(topic, channel));
    }
    if (stage === "package") {
      const topic = next.selectedTopic?.topic || next.title;
      next.pack = packageVideo(topic, channel, next.script || writeScript(topic, channel, next.deep || deepResearch(topic, channel)));
    }
    if (stage === "production") {
      const topic = next.selectedTopic?.topic || next.title;
      next.production = productionKit(topic, channel, next.script || writeScript(topic, channel, next.deep || deepResearch(topic, channel)));
    }
    if (stage === "upload") {
      const topic = next.selectedTopic?.topic || next.title;
      if (!next.script) next.script = writeScript(topic, channel, next.deep || deepResearch(topic, channel));
      if (!next.pack) next.pack = packageVideo(topic, channel, next.script);
      next.upload = uploadPack(topic, channel, next.script, next.pack);
    }
    return next;
  }

  function produceAll(channel, topicText) {
    let project = emptyProject(channel);
    project = runStage(project, "research");
    project = runStage(project, "topics");
    if (topicText) {
      const match = project.topics.find((t) => t.topic.toLowerCase().includes(topicText.toLowerCase()));
      project.selectedTopic = match || {
        id: uid(),
        topic: titleCase(topicText),
        angle: uniqueAngle(topicText, channel, 0),
        hook: hookFor(topicText, channel),
        audience: channel.audience,
        length: channel.videoLength,
        whyClick: "Custom brief from the operator.",
        whyWatch: "Because we designed the retention map.",
        scores: scoreTopic(topicText, channel, 0),
      };
    } else {
      project.selectedTopic = project.topics[0];
    }
    project = runStage(project, "deep");
    project = runStage(project, "script");
    project = runStage(project, "package");
    project = runStage(project, "production");
    project = runStage(project, "upload");
    project.stage = "upload";
    return project;
  }

  function masterPrompt(channel, project) {
    return [
      "You are a PROFESSIONAL YOUTUBE AUTOMATION MASTER AGENT.",
      "Operate an end-to-end YouTube content production system.",
      "PRIMARY OBJECTIVE: high-quality, original, engaging, monetization-friendly videos with minimum human intervention.",
      "Never copy competitors. Find a UNIQUE ANGLE.",
      "Stay educational. No guaranteed money/health claims. No copyrighted music or cloned celebrity voices.",
      `Channel: ${JSON.stringify(channel, null, 2)}`,
      project?.selectedTopic ? `Selected topic: ${project.selectedTopic.topic}` : "No topic selected yet.",
      "If information is missing, ask only essential questions. If told to decide, make professional assumptions.",
    ].join("\n");
  }

  return {
    STAGES,
    DEFAULT_CHANNEL,
    NICHES,
    uid,
    packFor,
    generateTopics,
    researchMarket,
    deepResearch,
    writeScript,
    packageVideo,
    productionKit,
    uploadPack,
    emptyProject,
    mergeLive,
    runStage,
    produceAll,
    masterPrompt,
    hookFor,
  };
})();
