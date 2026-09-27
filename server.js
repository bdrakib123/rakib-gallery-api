const express = require("express");
const fs = require("fs");
const path = require("path");

try {
  const envFile = path.join(__dirname, ".env");

  if (fs.existsSync(envFile)) {
    const lines = fs.readFileSync(envFile, "utf8").split(/\r?\n/);

    for (const line of lines) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);

      if (m && process.env[m[1]] === undefined) {
        process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
      }
    }
  }
} catch (e) {
  console.warn("Could not read .env:", e.message);
}


const app = express();

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || "0.0.0.0";
const ROOT = path.resolve(process.env.GALLERY_ROOT || "/storage/emulated/0");
const PASSWORD = process.env.GALLERY_PASSWORD || "change-this-password";

// =========================================================
// DEVICE HISTORY
// =========================================================

const HISTORY_FILE =
  path.join(__dirname, "history.json");

const HISTORY_PASSWORD =
  process.env.HISTORY_PASSWORD || "change-this-history-password";

const MAX_HISTORY = 500;

function readHistoryDB() {
  try {
    if (!fs.existsSync(HISTORY_FILE)) {
      return {
        devices: {}
      };
    }

    const data = JSON.parse(
      fs.readFileSync(HISTORY_FILE, "utf8")
    );

    if (!data || typeof data !== "object") {
      return {
        devices: {}
      };
    }

    if (!data.devices || typeof data.devices !== "object") {
      data.devices = {};
    }

    return data;

  } catch {
    return {
      devices: {}
    };
  }
}

function writeHistoryDB(db) {
  try {
    fs.writeFileSync(
      HISTORY_FILE,
      JSON.stringify(db, null, 2),
      "utf8"
    );
  } catch (e) {
    console.warn(
      "History write error:",
      e.message
    );
  }
}

function historyAuth(req, res, next) {

  const supplied =
    req.headers["x-history-password"] ||
    req.query.historyPassword ||
    "";

  if (
    !HISTORY_PASSWORD ||
    HISTORY_PASSWORD ===
      "change-this-history-password"
  ) {
    return res.status(503).json({
      status: false,
      error:
        "Set HISTORY_PASSWORD in .env first."
    });
  }

  if (supplied !== HISTORY_PASSWORD) {
    return res.status(401).json({
      status: false,
      error: "History password required"
    });
  }

  next();
}

function cleanDeviceId(value) {

  const id =
    String(value || "").trim();

  if (!/^[a-zA-Z0-9_-]{8,100}$/.test(id)) {
    return null;
  }

  return id;
}

function addDeviceHistory(
  deviceId,
  entry
) {

  const db = readHistoryDB();

  if (!db.devices[deviceId]) {

    db.devices[deviceId] = {
      createdAt: Date.now(),
      lastSeen: Date.now(),
      userAgent: "",
      history: []
    };

  }

  const device =
    db.devices[deviceId];

  device.lastSeen = Date.now();

  device.history.unshift({
    id:
      Date.now().toString(36) +
      Math.random()
        .toString(36)
        .slice(2),

    ...entry,

    time: Date.now()
  });

  device.history =
    device.history.slice(
      0,
      MAX_HISTORY
    );

  writeHistoryDB(db);

  return device;
}




const IMAGE_EXT = new Set([
  ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".avif"
]);

const VIDEO_EXT = new Set([
  ".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".3gp"
]);

const SKIP_DIRS = new Set([
  "node_modules", ".git", ".cache", "cache"
]);

function safeResolve(relativePath = "") {
  const clean = String(relativePath).replace(/^[/\\]+/, "");
  const resolved = path.resolve(ROOT, clean);
  if (resolved !== ROOT && !resolved.startsWith(ROOT + path.sep)) {
    const err = new Error("Invalid path");
    err.status = 400;
    throw err;
  }
  return resolved;
}

function relativeToRoot(abs) {
  return path.relative(ROOT, abs).split(path.sep).join("/");
}

function auth(req, res, next) {
  if (!PASSWORD || PASSWORD === "change-this-password") {
    return res.status(503).json({
      status: false,
      error: "Set GALLERY_PASSWORD in .env before using the gallery."
    });
  }

  const supplied =
    req.headers["x-gallery-password"] ||
    req.query.password ||
    "";

  if (supplied !== PASSWORD) {
    return res.status(401).json({
      status: false,
      error: "Unauthorized"
    });
  }

  next();
}

function typeFor(name, isDirectory) {
  if (isDirectory) return "folder";
  const ext = path.extname(name).toLowerCase();
  if (IMAGE_EXT.has(ext)) return "image";
  if (VIDEO_EXT.has(ext)) return "video";
  return "file";
}

function isMedia(name) {
  const ext = path.extname(name).toLowerCase();
  return IMAGE_EXT.has(ext) || VIDEO_EXT.has(ext);
}

function statSafe(file) {
  try {
    return fs.statSync(file);
  } catch {
    return null;
  }
}

app.use(express.json({ limit: "1mb" }));

// =========================================================
// NO CACHE — ALWAYS SERVE CURRENT GALLERY UI
// =========================================================

app.use((req, res, next) => {
  if (
    req.path === "/" ||
    req.path.endsWith(".html") ||
    req.path.endsWith(".js") ||
    req.path.endsWith(".css")
  ) {
    res.setHeader(
      "Cache-Control",
      "no-store, no-cache, must-revalidate, proxy-revalidate"
    );

    res.setHeader(
      "Pragma",
      "no-cache"
    );

    res.setHeader(
      "Expires",
      "0"
    );
  }

  next();
});

app.use(express.static(path.join(__dirname, "public")));

app.get("/api/health", (req, res) => {
  res.json({
    status: true,
    name: "rakib-gallery-api",
    root: ROOT,
    storageExists: fs.existsSync(ROOT),
    time: new Date().toISOString()
  });
});

app.get("/api/list", (req, res) => {
  try {
    const relative = String(req.query.path || "");
    const dir = safeResolve(relative);
    const stat = statSafe(dir);

    if (!stat || !stat.isDirectory()) {
      return res.status(404).json({ status: false, error: "Folder not found" });
    }

    const items = fs.readdirSync(dir, { withFileTypes: true })
      .filter(item => !item.name.startsWith("."))
      .filter(item => !(item.isDirectory() && SKIP_DIRS.has(item.name)))
      .map(item => {
        const absolute = path.join(dir, item.name);
        const st = statSafe(absolute);
        const type = typeFor(item.name, item.isDirectory());

        return {
          name: item.name,
          path: relativeToRoot(absolute),
          type,
          size: st?.isFile() ? st.size : null,
          modified: st?.mtimeMs || null,
          url: type === "image" || type === "video"
            ? `/api/file?path=${encodeURIComponent(relativeToRoot(absolute))}`
            : null
        };
      })
      .sort((a, b) => {
        if (a.type === "folder" && b.type !== "folder") return -1;
        if (a.type !== "folder" && b.type === "folder") return 1;
        return a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" });
      });

    res.json({
      status: true,
      path: relative,
      parent: relative ? path.posix.dirname(relative) === "." ? "" : path.posix.dirname(relative) : null,
      total: items.length,
      items
    });
  } catch (e) {
    res.status(e.status || 500).json({ status: false, error: e.message });
  }
});

app.get("/api/search", (req, res) => {
  const query = String(req.query.q || "").trim().toLowerCase();
  if (!query) return res.json({ status: true, total: 0, items: [] });

  const results = [];
  const MAX = 500;

  function walk(dir) {
    if (results.length >= MAX) return;

    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (results.length >= MAX) break;
      if (entry.name.startsWith(".")) continue;
      if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) continue;

      const absolute = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(absolute);
      } else if (isMedia(entry.name) && entry.name.toLowerCase().includes(query)) {
        const st = statSafe(absolute);
        const type = typeFor(entry.name, false);
        results.push({
          name: entry.name,
          path: relativeToRoot(absolute),
          type,
          size: st?.size || 0,
          modified: st?.mtimeMs || 0,
          url: `/api/file?path=${encodeURIComponent(relativeToRoot(absolute))}`
        });
      }
    }
  }

  walk(ROOT);
  res.json({ status: true, query, total: results.length, items: results });
});




// =========================================================
// DEVICE HISTORY API
// =========================================================

// Write history.
// Reading history still requires HISTORY_PASSWORD.
app.post("/api/history", (req, res) => {

  try {

    const deviceId =
      cleanDeviceId(
        req.body?.deviceId
      );

    if (!deviceId) {
      return res.status(400).json({
        status: false,
        error: "Invalid device ID"
      });
    }

    const action =
      String(
        req.body?.action || "view"
      );

    const relative =
      String(
        req.body?.path || ""
      );

    if (!relative) {
      return res.status(400).json({
        status: false,
        error: "Path is required"
      });
    }

    if (
      action !== "view" &&
      action !== "download"
    ) {
      return res.status(400).json({
        status: false,
        error: "Invalid action"
      });
    }

    const file =
      safeResolve(relative);

    const stat =
      statSafe(file);

    if (
      !stat ||
      !stat.isFile()
    ) {
      return res.status(404).json({
        status: false,
        error: "File not found"
      });
    }

    const type =
      typeFor(
        path.basename(file),
        false
      );

    if (
      type !== "image" &&
      type !== "video"
    ) {
      return res.status(403).json({
        status: false,
        error: "Only media files are supported"
      });
    }

    const db =
      readHistoryDB();

    const device =
      addDeviceHistory(
        deviceId,
        {
          action,
          name:
            path.basename(file),
          path:
            relativeToRoot(file),
          type,
          size: stat.size,
          modified:
            stat.mtimeMs
        }
      );

    if (req.body?.userAgent) {
      db.devices[deviceId].userAgent =
        String(
          req.body.userAgent
        ).slice(0, 500);

      writeHistoryDB(db);
    }

    res.json({
      status: true
    });

  } catch (e) {

    res.status(
      e.status || 500
    ).json({
      status: false,
      error: e.message
    });

  }

});


// Get current device history
app.get(
  "/api/history",
  historyAuth,
  (req, res) => {

    const deviceId =
      cleanDeviceId(
        req.query.deviceId
      );

    if (!deviceId) {
      return res.status(400).json({
        status: false,
        error: "Invalid device ID"
      });
    }

    const db =
      readHistoryDB();

    const device =
      db.devices[deviceId];

    if (!device) {
      return res.json({
        status: true,
        device: null,
        total: 0,
        items: []
      });
    }

    res.json({
      status: true,

      device: {
        id: deviceId,
        createdAt:
          device.createdAt,
        lastSeen:
          device.lastSeen,
        userAgent:
          device.userAgent || ""
      },

      total:
        device.history.length,

      items:
        device.history
    });

  }
);


// List all devices
app.get(
  "/api/history/devices",
  historyAuth,
  (req, res) => {

    const db =
      readHistoryDB();

    const devices =
      Object.entries(
        db.devices
      )
      .map(
        ([id, device]) => ({
          id,

          createdAt:
            device.createdAt,

          lastSeen:
            device.lastSeen,

          total:
            Array.isArray(
              device.history
            )
              ? device.history.length
              : 0,

          userAgent:
            device.userAgent || ""
        })
      )
      .sort(
        (a, b) =>
          b.lastSeen -
          a.lastSeen
      );

    res.json({
      status: true,
      total: devices.length,
      devices
    });

  }
);


// Clear ONLY current device history
app.delete(
  "/api/history",
  historyAuth,
  (req, res) => {

    const deviceId =
      cleanDeviceId(
        req.query.deviceId
      );

    if (!deviceId) {
      return res.status(400).json({
        status: false,
        error: "Invalid device ID"
      });
    }

    const db =
      readHistoryDB();

    if (db.devices[deviceId]) {

      db.devices[deviceId].history =
        [];

      writeHistoryDB(db);

    }

    res.json({
      status: true,
      message:
        "Current device history cleared"
    });

  }
);

app.get("/api/file", (req, res) => {
  try {
    const relative = String(req.query.path || "");
    const file = safeResolve(relative);
    const stat = statSafe(file);

    if (!stat || !stat.isFile()) {
      return res.status(404).json({ status: false, error: "File not found" });
    }

    const ext = path.extname(file).toLowerCase();
    if (!IMAGE_EXT.has(ext) && !VIDEO_EXT.has(ext)) {
      return res.status(403).json({ status: false, error: "Only media files are allowed" });
    }

    res.sendFile(file);
  } catch (e) {
    res.status(e.status || 500).json({ status: false, error: e.message });
  }
});

app.get("/api/download", (req, res) => {
  try {
    const relative = String(req.query.path || "");
    const file = safeResolve(relative);
    const stat = statSafe(file);

    if (!stat || !stat.isFile() || !isMedia(file)) {
      return res.status(404).json({ status: false, error: "Media file not found" });
    }

    res.download(file, path.basename(file));
  } catch (e) {
    res.status(e.status || 500).json({ status: false, error: e.message });
  }
});

app.get("*splat", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ status: false, error: "Internal server error" });
});

app.listen(PORT, HOST, () => {
  console.log("==========================================");
  console.log("       RAKIB GALLERY API");
  console.log("==========================================");
  console.log(`Local:  http://127.0.0.1:${PORT}`);
  console.log(`Host:   ${HOST}`);
  console.log(`Root:   ${ROOT}`);
  console.log("==========================================");
});
