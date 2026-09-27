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

const DATA_ROOT = path.resolve(
  process.env.DATA_ROOT || path.join(__dirname, "data")
);

const DEVICES_ROOT = path.join(DATA_ROOT, "devices");
const DEVICES_FILE = path.join(DATA_ROOT, "devices.json");
const HISTORY_FILE = path.join(DATA_ROOT, "history.json");

const HISTORY_PASSWORD =
  process.env.HISTORY_PASSWORD ||
  "change-this-history-password";

fs.mkdirSync(DEVICES_ROOT, { recursive: true });

const IMAGE_EXT = new Set([
  "jpg",
  "jpeg",
  "png",
  "gif",
  "webp",
  "bmp",
  "heic",
  "heif",
  "avif"
]);

const VIDEO_EXT = new Set([
  "mp4",
  "mkv",
  "webm",
  "mov",
  "avi",
  "m4v",
  "3gp"
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

/* =================================================
   JSON HELPERS
================================================= */

function readJson(file, fallback) {
  try {
    if (!fs.existsSync(file)) return fallback;

    const data = JSON.parse(
      fs.readFileSync(file, "utf8")
    );

    return data;
  } catch {
    return fallback;
  }
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), {
    recursive: true
  });

  const tmp = file + ".tmp";

  fs.writeFileSync(
    tmp,
    JSON.stringify(data, null, 2),
    "utf8"
  );

  fs.renameSync(tmp, file);
}

/* =================================================
   DEVICE
================================================= */

function cleanDeviceName(name) {
  return String(name || "My Phone")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "")
    .trim()
    .slice(0, 80) || "My Phone";
}

function cleanDeviceId(id) {
  return String(id || "")
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .slice(0, 80);
}

function getCookie(req, name) {
  const header = String(req.headers.cookie || "");

  const parts = header.split(";");

  for (const part of parts) {
    const index = part.indexOf("=");

    if (index === -1) continue;

    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();

    if (key === name) {
      return decodeURIComponent(value);
    }
  }

  return "";
}

function getToken(req) {
  return String(
    req.headers["x-device-token"] ||
    req.query.token ||
    getCookie(req, "rakib_device_token") ||
    ""
  ).trim();
}

function getDevices() {
  return readJson(DEVICES_FILE, {});
}

function saveDevices(data) {
  writeJson(DEVICES_FILE, data);
}

function getDevice(req) {
  const token = getToken(req);

  if (!token) return null;

  const devices = getDevices();

  for (const [id, device] of Object.entries(devices)) {
    if (device.token === token) {
      return {
        id,
        ...device
      };
    }
  }

  return null;
}

function requireDevice(req, res, next) {
  let device = getDevice(req);

  /*
   * Automatic device registration.
   *
   * No token/copy-paste is required for normal browser users.
   * A device token is stored in an HttpOnly cookie.
   */
  if (!device) {
    const devices = getDevices();

    const id =
      "phone_" +
      crypto.randomBytes(8).toString("hex");

    const token =
      crypto.randomBytes(32).toString("hex");

    const shortName =
      "Phone " +
      id.slice(-4).toUpperCase();

    devices[id] = {
      name: shortName,
      token,
      createdAt: Date.now()
    };

    saveDevices(devices);

    const root = deviceRoot(id);

    fs.mkdirSync(root, {
      recursive: true
    });

    device = {
      id,
      name: shortName,
      token
    };

    res.cookieDeviceToken = token;
  }

  if (res.cookieDeviceToken) {
    res.setHeader(
      "Set-Cookie",
      "rakib_device_token=" +
      encodeURIComponent(res.cookieDeviceToken) +
      "; Path=/; HttpOnly; SameSite=Lax"
    );
  }

  req.device = device;
  next();
}

function deviceRoot(deviceId) {
  const clean = cleanDeviceId(deviceId);

  if (!clean) return null;

  return path.join(DEVICES_ROOT, clean);
}

/* =================================================
   PATH SAFETY
================================================= */

function safeResolve(root, relativePath = "") {
  const clean = String(relativePath)
    .replace(/\\/g, "/")
    .replace(/^\/+/, "");

  const full = path.resolve(root, clean);

  const rootWithSep =
    root.endsWith(path.sep)
      ? root
      : root + path.sep;

  if (
    full !== root &&
    !full.startsWith(rootWithSep)
  ) {
    return null;
  }

  return full;
}

function relativeToRoot(root, full) {
  return path
    .relative(root, full)
    .split(path.sep)
    .join("/");
}

/* =================================================
   FILE HELPERS
================================================= */

function typeFor(name) {
  const ext = path
    .extname(name)
    .slice(1)
    .toLowerCase();

  if (IMAGE_EXT.has(ext)) return "image";
  if (VIDEO_EXT.has(ext)) return "video";

  return "file";
}

function statSafe(file) {
  try {
    return fs.statSync(file);
  } catch {
    return null;
  }
}

/* =================================================
   HEALTH
================================================= */

app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    name: "RAKIB GALLERY API",
    version: "4.0.0",
    dataRoot: DATA_ROOT,
    time: new Date().toISOString()
  });
});

/* =================================================
   REGISTER DEVICE
================================================= */

app.post("/api/device/register", (req, res) => {
  const name = cleanDeviceName(req.body?.name);

  const devices = getDevices();

  const id =
    "phone_" +
    crypto.randomBytes(8).toString("hex");

  const token =
    crypto.randomBytes(32).toString("hex");

  devices[id] = {
    name,
    token,
    createdAt: Date.now()
  };

  saveDevices(devices);

  const root = deviceRoot(id);

  fs.mkdirSync(root, {
    recursive: true
  });

  res.setHeader(
    "Set-Cookie",
    "rakib_device_token=" +
    encodeURIComponent(token) +
    "; Path=/; HttpOnly; SameSite=Lax"
  );

  res.json({
    ok: true,
    device: {
      id,
      name,
      token
    }
  });
});

/* =================================================
   DEVICE PAIRING
================================================= */

function makePairCode() {
  return String(
    Math.floor(100000 + Math.random() * 900000)
  );
}

if (!global.__DEVICE_PAIR_CODES__) {
  global.__DEVICE_PAIR_CODES__ = {};
}

/*
 * Browser device generates a short-lived pairing code.
 * The Android sync client can claim this code once.
 */
app.post(
  "/api/device/pair/start",
  requireDevice,
  (req, res) => {
    const code = makePairCode();

    global.__DEVICE_PAIR_CODES__[code] = {
      deviceId: req.device.id,
      expiresAt: Date.now() + 5 * 60 * 1000
    };

    res.json({
      ok: true,
      code,
      expiresIn: 300,
      device: {
        id: req.device.id,
        name: req.device.name
      }
    });
  }
);

/*
 * Android sync client claims the code.
 * Code is single-use and expires after 5 minutes.
 */
app.post(
  "/api/device/pair/claim",
  (req, res) => {
    const code = String(
      req.body?.code || ""
    ).trim();

    if (!/^\d{6}$/.test(code)) {
      return res.status(400).json({
        ok: false,
        error: "Invalid pairing code"
      });
    }

    const pairs =
      global.__DEVICE_PAIR_CODES__ || {};

    const pair = pairs[code];

    if (!pair) {
      return res.status(404).json({
        ok: false,
        error: "Pairing code not found"
      });
    }

    if (Date.now() > pair.expiresAt) {
      delete pairs[code];

      return res.status(410).json({
        ok: false,
        error: "Pairing code expired"
      });
    }

    const devices = getDevices();
    const device = devices[pair.deviceId];

    delete pairs[code];

    if (!device) {
      return res.status(404).json({
        ok: false,
        error: "Device not found"
      });
    }

    res.json({
      ok: true,
      device: {
        id: pair.deviceId,
        name: device.name
      },
      token: device.token
    });
  }
);

/* =================================================
   DEVICE INFO
================================================= */

app.get(
  "/api/device/me",
  requireDevice,
  (req, res) => {
    res.json({
      ok: true,
      device: {
        id: req.device.id,
        name: req.device.name
      }
    });
  }
);

/* =================================================
   LIST
================================================= */

app.get(
  "/api/list",
  requireDevice,
  (req, res) => {
    const root = deviceRoot(req.device.id);

    const dir = safeResolve(
      root,
      req.query.path || ""
    );

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

    let entries;

    try {
      entries = fs.readdirSync(dir, {
        withFileTypes: true
      });
    } catch (e) {
      return res.status(500).json({
        ok: false,
        error: e.message
      });
    }

    const result = [];

    for (const entry of entries) {
      if (
        entry.isDirectory() &&
        (
          entry.name.startsWith(".") ||
          SKIP_DIRS.has(entry.name)
        )
      ) {
        continue;
      }

      const full = path.join(
        dir,
        entry.name
      );

      const stat = statSafe(full);

      if (!stat) continue;

      if (entry.isDirectory()) {
        result.push({
          name: entry.name,
          path: relativeToRoot(root, full),
          type: "folder",
          modified: stat.mtimeMs
        });

        continue;
      }

      if (!entry.isFile()) continue;

      result.push({
        name: entry.name,
        path: relativeToRoot(root, full),
        type: typeFor(entry.name),
        size: stat.size,
        modified: stat.mtimeMs
      });
    }

    result.sort((a, b) => {
      if (
        a.type === "folder" &&
        b.type !== "folder"
      ) return -1;

      if (
        a.type !== "folder" &&
        b.type === "folder"
      ) return 1;

      return a.name.localeCompare(
        b.name,
        undefined,
        {
          numeric: true,
          sensitivity: "base"
        }
      );
    });

    res.json({
      ok: true,
      device: {
        id: req.device.id,
        name: req.device.name
      },
      path: req.query.path || "",
      items: result
    });
  }
);

/* =================================================
   SEARCH
================================================= */

app.get(
  "/api/search",
  requireDevice,
  (req, res) => {
    const root = deviceRoot(req.device.id);

    const query = String(
      req.query.q || ""
    )
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
      if (results.length >= maxResults) {
        return;
      }

      let entries;

      try {
        entries = fs.readdirSync(dir, {
          withFileTypes: true
        });
      } catch {
        return;
      }

      for (const entry of entries) {
        if (results.length >= maxResults) {
          return;
        }

        const full = path.join(
          dir,
          entry.name
        );

        if (
          entry.isDirectory() &&
          !SKIP_DIRS.has(entry.name) &&
          !entry.name.startsWith(".")
        ) {
          walk(full);
          continue;
        }

        if (!entry.isFile()) continue;

        if (
          !entry.name
            .toLowerCase()
            .includes(query)
        ) {
          continue;
        }

        const stat = statSafe(full);

        if (!stat) continue;

        results.push({
          name: entry.name,
          path: relativeToRoot(root, full),
          type: typeFor(entry.name),
          size: stat.size,
          modified: stat.mtimeMs
        });
      }
    }

    walk(root);

    res.json({
      ok: true,
      items: results
    });
  }
);

/* =================================================
   FILE
================================================= */

app.get(
  "/api/file",
  requireDevice,
  (req, res) => {
    const root = deviceRoot(
      req.device.id
    );

    const file = safeResolve(
      root,
      req.query.path || ""
    );

    if (!file) {
      return res.status(400).send(
        "Invalid path"
      );
    }

    const stat = statSafe(file);

    if (!stat || !stat.isFile()) {
      return res.status(404).send(
        "File not found"
      );
    }

    res.sendFile(file);
  }
);

/* =================================================
   DOWNLOAD
================================================= */

app.get(
  "/api/download",
  requireDevice,
  (req, res) => {
    const root = deviceRoot(
      req.device.id
    );

    const file = safeResolve(
      root,
      req.query.path || ""
    );

    if (!file) {
      return res.status(400).send(
        "Invalid path"
      );
    }

    const stat = statSafe(file);

    if (!stat || !stat.isFile()) {
      return res.status(404).send(
        "File not found"
      );
    }

    res.download(
      file,
      path.basename(file)
    );
  }
);

/* =================================================
   RAW SYNC UPLOAD
================================================= */

app.put(
  "/api/sync/file",
  requireDevice,
  (req, res) => {
    let relativePath = String(
      req.headers["x-file-path"] || ""
    );

    /*
     * sync.py sends the Android path URL-encoded
     * so Bengali/Unicode filenames are safe in HTTP headers.
     */
    try {
      relativePath = decodeURIComponent(relativePath);
    } catch {
      return res.status(400).json({
        ok: false,
        error: "Invalid encoded file path"
      });
    }

    if (!relativePath) {
      return res.status(400).json({
        ok: false,
        error: "x-file-path required"
      });
    }

    const root = deviceRoot(
      req.device.id
    );

    const file = safeResolve(
      root,
      relativePath
    );

    if (!file || file === root) {
      return res.status(400).json({
        ok: false,
        error: "Invalid file path"
      });
    }

    fs.mkdirSync(
      path.dirname(file),
      {
        recursive: true
      }
    );

    const temp =
      file + ".uploading";

    const stream =
      fs.createWriteStream(temp);

    let failed = false;

    req.on("data", chunk => {
      if (!failed) {
        stream.write(chunk);
      }
    });

    req.on("end", () => {
      if (failed) return;

      stream.end(() => {
        try {
          fs.renameSync(
            temp,
            file
          );

          res.json({
            ok: true,
            path: relativePath
          });
        } catch (e) {
          res.status(500).json({
            ok: false,
            error: e.message
          });
        }
      });
    });

    req.on("error", err => {
      failed = true;

      try {
        stream.destroy();
        if (fs.existsSync(temp)) {
          fs.unlinkSync(temp);
        }
      } catch {}

      if (!res.headersSent) {
        res.status(500).json({
          ok: false,
          error: err.message
        });
      }
    });
  }
);

/* =================================================
   SYNC DELETE
================================================= */

app.delete(
  "/api/sync/file",
  requireDevice,
  (req, res) => {
    const relativePath = String(
      req.query.path || ""
    );

    const root = deviceRoot(
      req.device.id
    );

    const file = safeResolve(
      root,
      relativePath
    );

    if (!file || file === root) {
      return res.status(400).json({
        ok: false,
        error: "Invalid path"
      });
    }

    try {
      if (fs.existsSync(file)) {
        fs.unlinkSync(file);
      }

      res.json({
        ok: true
      });
    } catch (e) {
      res.status(500).json({
        ok: false,
        error: e.message
      });
    }
  }
);

/* =================================================
   HISTORY
================================================= */

function readHistory() {
  return readJson(
    HISTORY_FILE,
    {}
  );
}

function saveHistory(data) {
  writeJson(
    HISTORY_FILE,
    data
  );
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

app.post(
  "/api/history",
  requireDevice,
  (req, res) => {
    const filePath = String(
      req.body?.path || ""
    );

    const action = String(
      req.body?.action || "view"
    );

    if (!filePath) {
      return res.status(400).json({
        ok: false,
        error: "path required"
      });
    }

    const data = readHistory();

    const key = req.device.id;

    if (!Array.isArray(data[key])) {
      data[key] = [];
    }

    data[key].unshift({
      id: crypto.randomUUID(),
      deviceId: req.device.id,
      deviceName: req.device.name,
      path: filePath,
      name: path.basename(filePath),
      action,
      time: Date.now()
    });

    data[key] =
      data[key].slice(0, 500);

    saveHistory(data);

    res.json({
      ok: true
    });
  }
);

app.get(
  "/api/history",
  requireDevice,
  historyAuth,
  (req, res) => {
    const data = readHistory();

    res.json({
      ok: true,
      device: {
        id: req.device.id,
        name: req.device.name
      },
      items: Array.isArray(
        data[req.device.id]
      )
        ? data[req.device.id]
        : []
    });
  }
);

app.delete(
  "/api/history",
  requireDevice,
  historyAuth,
  (req, res) => {
    const data = readHistory();

    delete data[req.device.id];

    saveHistory(data);

    res.json({
      ok: true
    });
  }
);

/* =================================================
   404
================================================= */

app.use("/api", (req, res) => {
  res.status(404).json({
    ok: false,
    error: "API endpoint not found"
  });
});

app.listen(PORT, HOST, () => {
  console.log("");
  console.log("==========================================");
  console.log("       RAKIB GALLERY API v4.0");
  console.log("==========================================");
  console.log("Local:", `http://127.0.0.1:${PORT}`);
  console.log("Host :", HOST);
  console.log("Data :", DATA_ROOT);
  console.log("==========================================");
});
