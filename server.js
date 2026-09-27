const express = require("express");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const app = express();

function loadEnv() {
  const envFile = path.join(__dirname, ".env");

  if (!fs.existsSync(envFile)) return;

  for (const line of fs.readFileSync(envFile, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) {
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
}

loadEnv();

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || "0.0.0.0";

function chooseRoot() {
  const configured = process.env.GALLERY_ROOT;

  if (configured) {
    const resolved = path.resolve(configured);

    if (fs.existsSync(resolved)) return resolved;

    // On Render/Linux, Android paths don't exist.
    if (
      resolved === "/sdcard" ||
      resolved === "/storage/emulated/0"
    ) {
      const fallback = path.join(__dirname, "gallery");
      fs.mkdirSync(fallback, { recursive: true });
      return fallback;
    }

    fs.mkdirSync(resolved, { recursive: true });
    return resolved;
  }

  const android =
    process.platform === "android" &&
    fs.existsSync("/storage/emulated/0");

  if (android) return "/storage/emulated/0";

  const fallback = path.join(__dirname, "gallery");
  fs.mkdirSync(fallback, { recursive: true });
  return fallback;
}

const ROOT = chooseRoot();
const HISTORY_FILE = path.join(__dirname, "history.json");
const HISTORY_PASSWORD =
  process.env.HISTORY_PASSWORD || "change-this-history-password";

const IMAGE_EXT = new Set([
  "jpg", "jpeg", "png", "gif", "webp",
  "bmp", "heic", "heif", "avif"
]);

const VIDEO_EXT = new Set([
  "mp4", "mkv", "webm", "mov",
  "avi", "m4v", "3gp"
]);

const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  ".cache",
  "cache"
]);

app.use(express.json({ limit: "2mb" }));

app.use((req, res, next) => {
  res.setHeader("Cache-Control", "no-store");
  next();
});

app.use(express.static(path.join(__dirname, "public")));

function safeResolve(relativePath = "") {
  const clean = String(relativePath)
    .replace(/\\/g, "/")
    .replace(/^\/+/, "");

  const full = path.resolve(ROOT, clean);
  const rootWithSep = ROOT.endsWith(path.sep)
    ? ROOT
    : ROOT + path.sep;

  if (full !== ROOT && !full.startsWith(rootWithSep)) {
    return null;
  }

  return full;
}

function relativeToRoot(full) {
  return path.relative(ROOT, full).split(path.sep).join("/");
}

function typeFor(name) {
  const ext = path.extname(name).slice(1).toLowerCase();

  if (IMAGE_EXT.has(ext)) return "image";
  if (VIDEO_EXT.has(ext)) return "video";
  return "file";
}

function isMedia(name) {
  return typeFor(name) !== "file";
}

function statSafe(file) {
  try {
    return fs.statSync(file);
  } catch {
    return null;
  }
}

function readHistory() {
  try {
    if (!fs.existsSync(HISTORY_FILE)) return {};
    const data = JSON.parse(
      fs.readFileSync(HISTORY_FILE, "utf8")
    );
    return data && typeof data === "object" ? data : {};
  } catch {
    return {};
  }
}

function writeHistory(data) {
  const tmp = HISTORY_FILE + ".tmp";
  fs.writeFileSync(
    tmp,
    JSON.stringify(data, null, 2),
    "utf8"
  );
  fs.renameSync(tmp, HISTORY_FILE);
}

function cleanDeviceId(value) {
  return String(value || "")
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .slice(0, 100);
}

function historyAuth(req, res, next) {
  const password =
    req.headers["x-history-password"] ||
    req.query.password ||
    req.body?.password;

  if (password !== HISTORY_PASSWORD) {
    return res.status(401).json({
      ok: false,
      error: "Invalid history password"
    });
  }

  next();
}

/* =========================
   HEALTH
========================= */

app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    name: "RAKIB GALLERY API",
    version: "3.0.0",
    root: ROOT,
    platform: process.platform,
    time: new Date().toISOString()
  });
});

/* =========================
   LIST
========================= */

app.get("/api/list", (req, res) => {
  const dir = safeResolve(req.query.path || "");

  if (!dir) {
    return res.status(400).json({
      ok: false,
      error: "Invalid path"
    });
  }

  const stat = statSafe(dir);

  if (!stat || !stat.isDirectory()) {
    return res.status(404).json({
      ok: false,
      error: "Folder not found"
    });
  }

  let entries = [];

  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    return res.status(500).json({
      ok: false,
      error: e.message
    });
  }

  const result = [];

  for (const entry of entries) {
    if (entry.name.startsWith(".") && entry.isDirectory()) continue;
    if (SKIP_DIRS.has(entry.name)) continue;

    const full = path.join(dir, entry.name);
    const stat = statSafe(full);

    if (!stat) continue;

    if (entry.isDirectory()) {
      result.push({
        name: entry.name,
        path: relativeToRoot(full),
        type: "folder",
        modified: stat.mtimeMs
      });
      continue;
    }

    if (!entry.isFile()) continue;

    result.push({
      name: entry.name,
      path: relativeToRoot(full),
      type: typeFor(entry.name),
      size: stat.size,
      modified: stat.mtimeMs
    });
  }

  result.sort((a, b) => {
    if (a.type === "folder" && b.type !== "folder") return -1;
    if (a.type !== "folder" && b.type === "folder") return 1;

    return a.name.localeCompare(b.name, undefined, {
      numeric: true,
      sensitivity: "base"
    });
  });

  res.json({
    ok: true,
    root: ROOT,
    path: req.query.path || "",
    items: result
  });
});

/* =========================
   SEARCH
========================= */

app.get("/api/search", (req, res) => {
  const query = String(req.query.q || "")
    .trim()
    .toLowerCase();

  if (!query) {
    return res.json({
      ok: true,
      items: []
    });
  }

  const results = [];
  const maxResults = 500;

  function walk(dir) {
    if (results.length >= maxResults) return;

    let entries;

    try {
      entries = fs.readdirSync(dir, {
        withFileTypes: true
      });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (results.length >= maxResults) return;

      if (
        entry.isDirectory() &&
        !SKIP_DIRS.has(entry.name) &&
        !entry.name.startsWith(".")
      ) {
        walk(path.join(dir, entry.name));
        continue;
      }

      if (!entry.isFile()) continue;

      if (
        !entry.name.toLowerCase().includes(query)
      ) {
        continue;
      }

      const full = path.join(dir, entry.name);
      const stat = statSafe(full);

      if (!stat) continue;

      results.push({
        name: entry.name,
        path: relativeToRoot(full),
        type: typeFor(entry.name),
        size: stat.size,
        modified: stat.mtimeMs
      });
    }
  }

  walk(ROOT);

  res.json({
    ok: true,
    items: results
  });
});

/* =========================
   FILE
========================= */

app.get("/api/file", (req, res) => {
  const file = safeResolve(req.query.path || "");

  if (!file) {
    return res.status(400).send("Invalid path");
  }

  const stat = statSafe(file);

  if (!stat || !stat.isFile()) {
    return res.status(404).send("File not found");
  }

  res.sendFile(file);
});

/* =========================
   DOWNLOAD
========================= */

app.get("/api/download", (req, res) => {
  const file = safeResolve(req.query.path || "");

  if (!file) {
    return res.status(400).send("Invalid path");
  }

  const stat = statSafe(file);

  if (!stat || !stat.isFile()) {
    return res.status(404).send("File not found");
  }

  res.download(file, path.basename(file));
});

/* =========================
   HISTORY RECORD
========================= */

app.post("/api/history", (req, res) => {
  const deviceId = cleanDeviceId(req.body?.deviceId);

  if (!deviceId) {
    return res.status(400).json({
      ok: false,
      error: "deviceId required"
    });
  }

  const filePath = String(req.body?.path || "");
  const action = String(req.body?.action || "view");

  if (!filePath) {
    return res.status(400).json({
      ok: false,
      error: "path required"
    });
  }

  const data = readHistory();

  if (!Array.isArray(data[deviceId])) {
    data[deviceId] = [];
  }

  data[deviceId].unshift({
    id: crypto.randomUUID(),
    path: filePath,
    name: path.basename(filePath),
    action,
    time: Date.now()
  });

  data[deviceId] = data[deviceId].slice(0, 300);

  writeHistory(data);

  res.json({
    ok: true
  });
});

/* =========================
   HISTORY READ
========================= */

app.get("/api/history", historyAuth, (req, res) => {
  const deviceId = cleanDeviceId(req.query.deviceId);

  if (!deviceId) {
    return res.status(400).json({
      ok: false,
      error: "deviceId required"
    });
  }

  const data = readHistory();

  res.json({
    ok: true,
    deviceId,
    items: Array.isArray(data[deviceId])
      ? data[deviceId]
      : []
  });
});

/* =========================
   HISTORY DEVICES
========================= */

app.get("/api/history/devices", historyAuth, (req, res) => {
  const data = readHistory();

  const devices = Object.keys(data).map(id => ({
    id,
    count: Array.isArray(data[id])
      ? data[id].length
      : 0
  }));

  res.json({
    ok: true,
    devices
  });
});

/* =========================
   HISTORY CLEAR
========================= */

app.delete("/api/history", historyAuth, (req, res) => {
  const deviceId = cleanDeviceId(req.query.deviceId);

  if (!deviceId) {
    return res.status(400).json({
      ok: false,
      error: "deviceId required"
    });
  }

  const data = readHistory();

  delete data[deviceId];

  writeHistory(data);

  res.json({
    ok: true
  });
});

/* =========================
   404 API
========================= */

app.use("/api", (req, res) => {
  res.status(404).json({
    ok: false,
    error: "API endpoint not found"
  });
});

app.listen(PORT, HOST, () => {
  console.log("");
  console.log("==========================================");
  console.log("       RAKIB GALLERY API v3.0");
  console.log("==========================================");
  console.log("Local :", `http://127.0.0.1:${PORT}`);
  console.log("Host  :", HOST);
  console.log("Root  :", ROOT);
  console.log("Platform:", process.platform);
  console.log("==========================================");
  console.log("");
});
