import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, "public");
const DATA_DIR = path.join(__dirname, "data");
const MEMORY_FILE = path.join(DATA_DIR, "memory.json");
const HOST = "0.0.0.0";
const PORT = Number(process.env.PORT || 8787);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".ico": "image/x-icon",
  ".webp": "image/webp",
};

function ensureData() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(MEMORY_FILE)) {
    fs.writeFileSync(
      MEMORY_FILE,
      JSON.stringify(
        {
          facts: [],
          notes: [],
          tasks: [],
          updatedAt: new Date().toISOString(),
        },
        null,
        2,
      ),
    );
  }
}

function readMemory() {
  ensureData();
  return JSON.parse(fs.readFileSync(MEMORY_FILE, "utf8"));
}

function writeMemory(data) {
  ensureData();
  data.updatedAt = new Date().toISOString();
  fs.writeFileSync(MEMORY_FILE, JSON.stringify(data, null, 2));
  return data;
}

function send(res, status, body, headers = {}) {
  const payload = typeof body === "string" ? body : JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": typeof body === "string" ? "text/plain; charset=utf-8" : "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers,
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("invalid json"));
      }
    });
    req.on("error", reject);
  });
}

function serveStatic(req, res) {
  const url = new URL(req.url, "http://localhost");
  let filePath = path.normalize(url.pathname);
  if (filePath === "/") filePath = "/index.html";
  const abs = path.join(PUBLIC_DIR, filePath);
  if (!abs.startsWith(PUBLIC_DIR)) {
    send(res, 403, { error: "forbidden" });
    return;
  }
  fs.readFile(abs, (err, buf) => {
    if (err) {
      send(res, 404, { error: "not found" });
      return;
    }
    const ext = path.extname(abs).toLowerCase();
    res.writeHead(200, {
      "Content-Type": MIME[ext] || "application/octet-stream",
      "Cache-Control": ext === ".html" ? "no-store" : "public, max-age=3600",
    });
    res.end(buf);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (req.method === "GET" && url.pathname === "/api/health") {
    send(res, 200, { ok: true, agent: "saathi", time: new Date().toISOString() });
    return;
  }

  if (url.pathname === "/api/memory") {
    try {
      if (req.method === "GET") {
        send(res, 200, readMemory());
        return;
      }
      if (req.method === "POST") {
        const body = await readBody(req);
        const current = readMemory();
        const next = {
          facts: Array.isArray(body.facts) ? body.facts : current.facts,
          notes: Array.isArray(body.notes) ? body.notes : current.notes,
          tasks: Array.isArray(body.tasks) ? body.tasks : current.tasks,
        };
        send(res, 200, writeMemory(next));
        return;
      }
    } catch {
      send(res, 400, { error: "bad request" });
      return;
    }
  }

  if (req.method === "GET" || req.method === "HEAD") {
    serveStatic(req, res);
    return;
  }

  send(res, 404, { error: "not found" });
});

ensureData();
server.listen(PORT, HOST, () => {
  console.log(`Saathi agent live on http://${HOST}:${PORT}`);
});
