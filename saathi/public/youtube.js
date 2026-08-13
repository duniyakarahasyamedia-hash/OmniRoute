const Tube = (() => {
  const SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
  ].join(" ");

  const INVIDIOUS = ["https://inv.nadeko.net", "https://invidious.nerdvpn.de", "https://yewtu.be"];

  function connected(settings) {
    return Boolean(settings.ytToken && Number(settings.ytExpires || 0) > Date.now() + 15_000);
  }

  function consumeHash() {
    const hash = new URLSearchParams(location.hash.replace(/^#/, ""));
    const token = hash.get("access_token");
    const expires = Number(hash.get("expires_in") || 0);
    if (!token) return null;
    history.replaceState({}, "", location.pathname + location.search);
    return { token, expires: Date.now() + expires * 1000 };
  }

  function connect(clientId) {
    if (!clientId) throw new Error("OAuth Client ID missing");
    const redirect = location.origin + location.pathname;
    const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    url.searchParams.set("client_id", clientId);
    url.searchParams.set("redirect_uri", redirect);
    url.searchParams.set("response_type", "token");
    url.searchParams.set("scope", SCOPES);
    url.searchParams.set("include_granted_scopes", "true");
    url.searchParams.set("prompt", "consent");
    location.href = url.toString();
  }

  async function api(path, settings, params = {}, init = {}) {
    const root = path.startsWith("http") ? path : `https://www.googleapis.com/youtube/v3/${path}`;
    const url = new URL(root);
    Object.entries(params).forEach(([k, v]) => {
      if (v != null && v !== "") url.searchParams.set(k, v);
    });
    const headers = { ...(init.headers || {}) };
    if (connected(settings)) headers.Authorization = `Bearer ${settings.ytToken}`;
    else if (settings.ytApiKey && !path.startsWith("http")) url.searchParams.set("key", settings.ytApiKey);
    else throw new Error("YouTube API key or login required");
    const res = await fetch(url, { ...init, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error?.message || `YouTube ${res.status}`);
    return data;
  }

  async function myChannel(settings) {
    const data = await api("channels", settings, { part: "snippet,statistics", mine: "true" });
    const item = data.items?.[0];
    if (!item) return null;
    return {
      id: item.id,
      title: item.snippet.title,
      thumb: item.snippet.thumbnails?.default?.url || "",
      subs: item.statistics?.subscriberCount || "0",
    };
  }

  function normalizeGoogle(items = []) {
    return items
      .map((it) => ({
        id: it.id?.videoId || it.id,
        title: it.snippet?.title || "",
        channel: it.snippet?.channelTitle || "",
        thumb: it.snippet?.thumbnails?.medium?.url || it.snippet?.thumbnails?.default?.url || "",
        published: it.snippet?.publishedAt || "",
      }))
      .filter((v) => v.id && v.title);
  }

  async function searchGoogle(query, settings, region = "IN") {
    const data = await api("search", settings, {
      part: "snippet",
      type: "video",
      maxResults: "8",
      q: query,
      order: "relevance",
      regionCode: region,
      relevanceLanguage: /india|hindi|hinglish/i.test(query) ? "hi" : "en",
    });
    return normalizeGoogle(data.items);
  }

  async function searchInvidious(query) {
    for (const host of INVIDIOUS) {
      try {
        const res = await fetch(`${host}/api/v1/search?q=${encodeURIComponent(query)}&type=video`, {
          signal: AbortSignal.timeout(6000),
        });
        if (!res.ok) continue;
        const data = await res.json();
        const list = (Array.isArray(data) ? data : [])
          .filter((v) => v.type === "video" || v.videoId)
          .slice(0, 8)
          .map((v) => ({
            id: v.videoId,
            title: v.title,
            channel: v.author || "",
            thumb: v.videoThumbnails?.[1]?.url || v.videoThumbnails?.[0]?.url || "",
            published: v.publishedText || "",
          }));
        if (list.length) return list;
      } catch {
        /* next */
      }
    }
    return [];
  }

  async function search(query, settings, region = "IN") {
    if (connected(settings) || settings.ytApiKey) {
      try {
        return await searchGoogle(query, settings, region);
      } catch {
        /* fall through */
      }
    }
    return searchInvidious(query);
  }

  async function uploadVideo(file, meta, settings, onProgress) {
    if (!connected(settings)) throw new Error("Connect YouTube first");
    const status = {
      privacyStatus: meta.publishAt ? "private" : meta.privacy || "private",
      selfDeclaredMadeForKids: false,
    };
    if (meta.publishAt) status.publishAt = meta.publishAt;
    const init = await fetch(
      "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${settings.ytToken}`,
          "Content-Type": "application/json; charset=UTF-8",
          "X-Upload-Content-Length": String(file.size),
          "X-Upload-Content-Type": file.type || "video/webm",
        },
        body: JSON.stringify({
          snippet: {
            title: String(meta.title || "Untitled").slice(0, 100),
            description: meta.description || "",
            tags: (meta.tags || []).slice(0, 15),
            categoryId: meta.categoryId || "27",
          },
          status,
        }),
      },
    );
    if (!init.ok) {
      const err = await init.json().catch(() => ({}));
      throw new Error(err.error?.message || `Upload init ${init.status}`);
    }
    const session = init.headers.get("Location");
    if (!session) throw new Error("No upload session");
    if (onProgress) onProgress(10);
    const put = await fetch(session, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${settings.ytToken}`,
        "Content-Type": file.type || "video/webm",
      },
      body: file,
    });
    const data = await put.json().catch(() => ({}));
    if (!put.ok) throw new Error(data.error?.message || `Upload ${put.status}`);
    if (onProgress) onProgress(90);
    return data;
  }

  async function setThumbnail(videoId, blob, settings) {
    const res = await fetch(
      `https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=${encodeURIComponent(videoId)}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${settings.ytToken}`,
          "Content-Type": blob.type || "image/jpeg",
        },
        body: blob,
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Thumbnail ${res.status}`);
    }
    return res.json();
  }

  async function ensurePlaylist(title, settings) {
    const list = await api("playlists", settings, { part: "snippet", mine: "true", maxResults: "25" });
    const hit = (list.items || []).find((p) => p.snippet?.title === title);
    if (hit) return hit.id;
    const created = await api(
      "playlists",
      settings,
      { part: "snippet,status" },
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          snippet: { title, description: "Saathi Studio start-here playlist" },
          status: { privacyStatus: "public" },
        }),
      },
    );
    return created.id;
  }

  async function addToPlaylist(playlistId, videoId, settings) {
    return api(
      "playlistItems",
      settings,
      { part: "snippet" },
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          snippet: { playlistId, resourceId: { kind: "youtube#video", videoId } },
        }),
      },
    );
  }

  async function uploadCaptions(videoId, srtText, language, settings) {
    const boundary = "saathi" + Date.now();
    const meta = JSON.stringify({
      snippet: { videoId, language: language || "en", name: "Saathi captions", isDraft: false },
    });
    const body =
      `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${meta}\r\n` +
      `--${boundary}\r\nContent-Type: text/plain\r\n\r\n${srtText}\r\n--${boundary}--`;
    const res = await fetch("https://www.googleapis.com/upload/youtube/v3/captions?part=snippet&uploadType=multipart", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${settings.ytToken}`,
        "Content-Type": `multipart/related; boundary=${boundary}`,
      },
      body,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error?.message || `Captions ${res.status}`);
    return data;
  }

  async function listComments(videoId, settings) {
    const data = await api("commentThreads", settings, {
      part: "snippet",
      videoId,
      maxResults: "8",
      textFormat: "plainText",
    });
    return (data.items || []).map((it) => ({
      id: it.id,
      parentId: it.snippet?.topLevelComment?.id,
      author: it.snippet?.topLevelComment?.snippet?.authorDisplayName,
      text: it.snippet?.topLevelComment?.snippet?.textDisplay,
    }));
  }

  async function replyComment(parentId, text, settings) {
    return api(
      "comments",
      settings,
      { part: "snippet" },
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snippet: { parentId, textOriginal: text } }),
      },
    );
  }

  async function analytics(settings) {
    const end = new Date();
    const start = new Date(Date.now() - 28 * 86400000);
    const fmt = (d) => d.toISOString().slice(0, 10);
    return api("https://youtubeanalytics.googleapis.com/v2/reports", settings, {
      ids: "channel==MINE",
      startDate: fmt(start),
      endDate: fmt(end),
      metrics: "views,estimatedMinutesWatched,subscribersGained,likes",
    });
  }

  return {
    connected,
    consumeHash,
    connect,
    myChannel,
    search,
    uploadVideo,
    setThumbnail,
    ensurePlaylist,
    addToPlaylist,
    uploadCaptions,
    listComments,
    replyComment,
    analytics,
  };
})();
