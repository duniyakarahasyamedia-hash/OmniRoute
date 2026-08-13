const Facts = (() => {
  async function wikiSearch(query) {
    const url = `https://en.wikipedia.org/w/api.php?action=opensearch&search=${encodeURIComponent(query)}&limit=4&namespace=0&format=json&origin=*`;
    const data = await fetch(url, { signal: AbortSignal.timeout(8000) }).then((r) => r.json());
    return data[1] || [];
  }

  async function wikiSummary(title) {
    const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`;
    const data = await fetch(url, { signal: AbortSignal.timeout(8000) }).then((r) => r.json());
    if (!data.extract) return null;
    return {
      title: data.title,
      extract: data.extract,
      url: data.content_urls?.desktop?.page || "",
    };
  }

  async function liveFacts(topic, niche) {
    const q = `${topic} ${niche || ""}`.trim();
    try {
      const titles = await wikiSearch(q);
      const out = [];
      for (const title of titles.slice(0, 3)) {
        const row = await wikiSummary(title);
        if (row) out.push(row);
      }
      return out;
    } catch {
      return [];
    }
  }

  async function stockStills(query) {
    const url =
      "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=" +
      encodeURIComponent(query) +
      "&gsrnamespace=6&gsrlimit=6&prop=imageinfo&iiprop=url|mime&iiurlwidth=1280&format=json&origin=*";
    try {
      const data = await fetch(url, { signal: AbortSignal.timeout(8000) }).then((r) => r.json());
      return Object.values(data.query?.pages || {})
        .map((p) => p.imageinfo?.[0])
        .filter((i) => i && /^image\//.test(i.mime || "") && i.thumburl)
        .map((i, n) => ({ id: `stock-${n}`, kind: "stock", src: i.thumburl || i.url }));
    } catch {
      return [];
    }
  }

  return { liveFacts, stockStills };
})();
