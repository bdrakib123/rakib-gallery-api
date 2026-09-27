from pathlib import Path
import json
import re

ROOT = Path(".")
SERVER = ROOT / "server.js"
APP = ROOT / "public/app.js"
HTML = ROOT / "public/index.html"
CSS = ROOT / "public/style.css"

# =========================================================
# SERVER
# =========================================================

s = SERVER.read_text(encoding="utf-8")

# Remove old history constants/functions if present
s = re.sub(
    r'\nconst HISTORY_FILE = .*?\nconst MAX_HISTORY = 500;\n.*?function addHistory\(entry\) \{.*?\n\}\n',
    '\n',
    s,
    flags=re.S
)

# Insert new history configuration after PASSWORD
password_line = 'const PASSWORD = process.env.GALLERY_PASSWORD || "change-this-password";'

history_config = r'''

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
'''

if password_line not in s:
    raise SystemExit(
        "❌ Could not find PASSWORD configuration"
    )

# Avoid duplicate insertion
if "const HISTORY_PASSWORD" not in s:
    s = s.replace(
        password_line,
        password_line + history_config,
        1
    )


# =========================================================
# REMOVE OLD HISTORY ROUTES
# =========================================================

start = s.find(
    '// =========================================================\n// HISTORY API'
)

if start != -1:

    end = s.find(
        'app.get("/api/file"',
        start
    )

    if end != -1:
        s = s[:start] + s[end:]


# =========================================================
# NEW HISTORY ROUTES
# =========================================================

history_routes = r'''
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

'''

marker = 'app.get("/api/file", auth, (req, res) => {'

if marker not in s:
    raise SystemExit(
        "❌ Could not find /api/file route"
    )

s = s.replace(
    marker,
    history_routes + marker,
    1
)

# =========================================================
# REMOVE GALLERY AUTH FROM NORMAL GALLERY ROUTES
# =========================================================

s = s.replace(
    'app.get("/api/list", auth, (req, res) => {',
    'app.get("/api/list", (req, res) => {'
)

s = s.replace(
    'app.get("/api/search", auth, (req, res) => {',
    'app.get("/api/search", (req, res) => {'
)

s = s.replace(
    'app.get("/api/file", auth, (req, res) => {',
    'app.get("/api/file", (req, res) => {'
)

s = s.replace(
    'app.get("/api/download", auth, (req, res) => {',
    'app.get("/api/download", (req, res) => {'
)

# =========================================================
# .ENV DEFAULTS
# =========================================================

env = ROOT / ".env"

if env.exists():
    env_text = env.read_text(
        encoding="utf-8"
    )
else:
    env_text = ""

lines = env_text.splitlines()

found_history = False

for i, line in enumerate(lines):

    if line.startswith(
        "HISTORY_PASSWORD="
    ):
        found_history = True

        # Do not overwrite user's existing password
        break

if not found_history:

    lines.append(
        "HISTORY_PASSWORD=change-this-history-password"
    )

    env.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print(
        "✅ HISTORY_PASSWORD added to .env"
    )

else:
    print(
        "ℹ️ Existing HISTORY_PASSWORD preserved"
    )


SERVER.write_text(
    s,
    encoding="utf-8"
)

# =========================================================
# APP.JS
# =========================================================

app = r'''// =========================================================
// RAKIB GALLERY
// Public Gallery + Private Device History
// =========================================================

let currentPath = "";

const $ = id =>
  document.getElementById(id);

const gallery =
  $("gallery");

const grid =
  $("grid");

const statusEl =
  $("status");

const viewer =
  $("viewer");

const viewerContent =
  $("viewerContent");

const downloadBtn =
  $("downloadBtn");

const viewerName =
  $("viewerName");

const historyPanel =
  $("historyPanel");

const historyList =
  $("historyList");

const bottomNav =
  $("bottomNav");


// =========================================================
// DEVICE ID
// =========================================================

let deviceId =
  localStorage.getItem(
    "rakibGalleryDeviceId"
  );

if (!deviceId) {

  deviceId =
    "device_" +
    crypto.randomUUID()
      .replace(/-/g, "");

  localStorage.setItem(
    "rakibGalleryDeviceId",
    deviceId
  );

}


// =========================================================
// API
// =========================================================

function api(url) {
  return url;
}


// =========================================================
// HELPERS
// =========================================================

function formatSize(bytes) {

  if (bytes == null)
    return "";

  const units =
    ["B","KB","MB","GB","TB"];

  let n = bytes;
  let i = 0;

  while (
    n >= 1024 &&
    i < units.length - 1
  ) {

    n /= 1024;
    i++;

  }

  return (
    n.toFixed(i ? 1 : 0) +
    " " +
    units[i]
  );

}


function formatDate(time) {

  return new Date(time)
    .toLocaleString([], {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });

}


function fileUrl(item) {

  return (
    "/api/file?path=" +
    encodeURIComponent(
      item.path
    )
  );

}


function escapeHtml(s) {

  return String(s)
    .replace(
      /[&<>"']/g,
      c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[c])
    );

}


// =========================================================
// HISTORY WRITE
// =========================================================

async function recordHistory(
  action,
  item
) {

  try {

    await fetch(
      "/api/history",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body:
          JSON.stringify({
            deviceId,

            action,

            path:
              item.path,

            userAgent:
              navigator.userAgent
          })
      }
    );

  } catch {}

}


// =========================================================
// FOLDER
// =========================================================

async function loadFolder(
  p = ""
) {

  showGallery();

  statusEl.textContent =
    "Loading…";

  try {

    const r =
      await fetch(
        "/api/list?path=" +
        encodeURIComponent(p)
      );

    const data =
      await r.json();

    if (!data.status) {
      throw new Error(
        data.error ||
        "Failed"
      );
    }

    currentPath = p;

    $("currentPath")
      .textContent =
      "/" + p;

    $("backBtn")
      .disabled = !p;

    statusEl.textContent =
      data.total +
      " item" +
      (
        data.total === 1
          ? ""
          : "s"
      );

    render(
      data.items
    );

  } catch (e) {

    statusEl.textContent =
      e.message;

  }

}


// =========================================================
// RENDER
// =========================================================

function render(items) {

  grid.innerHTML = "";

  if (!items.length) {

    grid.innerHTML = `
      <div class="empty-gallery">
        <div>⌁</div>
        <strong>Nothing here</strong>
        <span>
          No photos, videos or folders found.
        </span>
      </div>
    `;

    return;

  }


  for (
    const item of items
  ) {

    const card =
      document.createElement(
        "article"
      );

    card.className =
      "media-card";


    if (
      item.type ===
      "folder"
    ) {

      card.innerHTML = `
        <div class="folder-preview">
          <div class="folder-icon">
            ▱
          </div>
        </div>

        <div class="card-name">
          ${escapeHtml(item.name)}
        </div>

        <div class="card-meta">
          Folder
        </div>
      `;

      card.onclick =
        () =>
          loadFolder(
            item.path
          );

    } else {

      const url =
        fileUrl(item);

      card.innerHTML = `

        <div class="media-preview">

          ${
            item.type === "image"

              ? `
                <img
                  src="${url}"
                  loading="lazy"
                  alt=""
                >
              `

              : `
                <video
                  src="${url}"
                  preload="metadata"
                ></video>

                <div class="play-icon">
                  ▶
                </div>
              `
          }

        </div>

        <div class="card-name">
          ${escapeHtml(item.name)}
        </div>

        <div class="card-meta">
          ${formatSize(item.size)}
        </div>
      `;

      card.onclick =
        () =>
          openViewer(item);

    }

    grid.appendChild(card);

  }

}


// =========================================================
// VIEWER
// =========================================================

function openViewer(item) {

  viewerContent.innerHTML = "";

  const url =
    fileUrl(item);


  if (
    item.type ===
    "image"
  ) {

    const img =
      document.createElement(
        "img"
      );

    img.src = url;

    img.alt =
      item.name;

    viewerContent
      .appendChild(img);

  } else {

    const video =
      document.createElement(
        "video"
      );

    video.src = url;

    video.controls =
      true;

    video.autoplay =
      true;

    video.playsInline =
      true;

    viewerContent
      .appendChild(video);

  }


  viewerName.textContent =
    item.name;

  downloadBtn.href =
    "/api/download?path=" +
    encodeURIComponent(
      item.path
    );

  downloadBtn.download =
    item.name;

  viewer.hidden =
    false;

  document.body
    .classList
    .add("viewer-open");

  recordHistory(
    "view",
    item
  );

}


function closeViewer() {

  const video =
    viewerContent
      .querySelector(
        "video"
      );

  if (video) {

    video.pause();

    video.removeAttribute(
      "src"
    );

  }

  viewerContent.innerHTML =
    "";

  viewer.hidden =
    true;

  document.body
    .classList
    .remove(
      "viewer-open"
    );

}


$("closeViewer")
  .onclick =
    closeViewer;


viewer.onclick =
  e => {

    if (
      e.target ===
      viewer
    ) {

      closeViewer();

    }

  };


document.addEventListener(
  "keydown",
  e => {

    if (
      e.key === "Escape" &&
      !viewer.hidden
    ) {

      closeViewer();

    }

  }
);


// =========================================================
// DOWNLOAD HISTORY
// =========================================================

downloadBtn.onclick =
  () => {

    recordHistory(
      "download",
      {
        path:
          new URL(
            downloadBtn.href,
            location.href
          )
          .searchParams
          .get("path"),

        name:
          viewerName
            .textContent,

        type:
          viewerContent
            .querySelector(
              "video"
            )
            ? "video"
            : "image"
      }
    );

  };


// =========================================================
// HISTORY PASSWORD
// =========================================================

let historyPassword =
  sessionStorage.getItem(
    "rakibHistoryPassword"
  ) || "";


function historyApi(
  url
) {

  const join =
    url.includes("?")
      ? "&"
      : "?";

  return (
    url +
    join +
    "historyPassword=" +
    encodeURIComponent(
      historyPassword
    )
  );

}


async function askHistoryPassword() {

  if (historyPassword) {

    const test =
      await fetch(
        historyApi(
          "/api/history?deviceId=" +
          encodeURIComponent(
            deviceId
          )
        )
      );

    if (test.ok) {
      return true;
    }

  }


  const pass =
    prompt(
      "Enter History Password"
    );

  if (!pass)
    return false;

  historyPassword =
    pass;

  const r =
    await fetch(
      historyApi(
        "/api/history?deviceId=" +
        encodeURIComponent(
          deviceId
        )
      )
    );

  if (!r.ok) {

    historyPassword =
      "";

    alert(
      "Wrong history password."
    );

    return false;

  }

  sessionStorage.setItem(
    "rakibHistoryPassword",
    historyPassword
  );

  return true;

}


// =========================================================
// HISTORY PAGE
// =========================================================

async function showHistory() {

  const ok =
    await askHistoryPassword();

  if (!ok)
    return;

  grid.hidden =
    true;

  historyPanel.hidden =
    false;

  document
    .querySelectorAll(
      ".nav-item"
    )
    .forEach(
      x =>
        x.classList
          .remove("active")
    );

  document
    .querySelector(
      '[data-page="historyPage"]'
    )
    ?.classList
    .add("active");

  await loadHistory();

}


async function loadHistory() {

  historyList.innerHTML = `
    <div class="history-loading">
      Loading your private history…
    </div>
  `;


  try {

    const r =
      await fetch(
        historyApi(
          "/api/history?deviceId=" +
          encodeURIComponent(
            deviceId
          )
        )
      );

    const data =
      await r.json();

    if (!r.ok || !data.status) {

      historyPassword = "";

      sessionStorage.removeItem(
        "rakibHistoryPassword"
      );

      historyList.innerHTML =
        `<div class="error">
          ${escapeHtml(
            data.error ||
            "Unable to load history"
          )}
        </div>`;

      return;

    }


    if (
      !data.items.length
    ) {

      historyList.innerHTML = `
        <div class="history-empty">
          <div class="history-empty-icon">
            ◷
          </div>

          <strong>
            No activity yet
          </strong>

          <span>
            Photos and downloads
            from this device
            will appear here.
          </span>
        </div>
      `;

      return;

    }


    historyList.innerHTML =
      data.items
        .map(
          item => {

            const url =
              fileUrl(item);

            return `
              <article
                class="history-card"
                data-path="${escapeHtml(
                  item.path
                )}"
              >

                <div
                  class="history-card-thumb"
                >

                  ${
                    item.type ===
                    "image"

                    ? `
                      <img
                        src="${url}"
                        loading="lazy"
                      >
                    `

                    : `
                      <div
                        class="history-video"
                      >
                        ▶
                      </div>
                    `
                  }

                </div>

                <div
                  class="history-card-main"
                >

                  <strong>
                    ${escapeHtml(
                      item.name
                    )}
                  </strong>

                  <span>
                    ${
                      item.action ===
                      "download"
                        ? "↓ Downloaded"
                        : "◉ Viewed"
                    }
                  </span>

                  <small>
                    ${formatDate(
                      item.time
                    )}
                  </small>

                </div>

                <div
                  class="history-card-arrow"
                >
                  ›
                </div>

              </article>
            `;

          }
        )
        .join("");


    historyList
      .querySelectorAll(
        ".history-card"
      )
      .forEach(
        el => {

          el.onclick =
            () => {

              const item =
                data.items.find(
                  x =>
                    x.path ===
                    el.dataset.path
                );

              if (item) {

                showGallery();

                openViewer(
                  item
                );

              }

            };

        }
      );


  } catch (e) {

    historyList.innerHTML =
      `<div class="error">
        ${escapeHtml(
          e.message
        )}
      </div>`;

  }

}


// =========================================================
// CLEAR HISTORY
// =========================================================

$("clearHistory")
  .onclick =
  async () => {

    if (
      !confirm(
        "Clear history for this device?"
      )
    ) return;

    await fetch(
      historyApi(
        "/api/history?deviceId=" +
        encodeURIComponent(
          deviceId
        )
      ),
      {
        method:
          "DELETE"
      }
    );

    loadHistory();

  };


// =========================================================
// NAVIGATION
// =========================================================

function showGallery() {

  historyPanel.hidden =
    true;

  grid.hidden =
    false;

  document
    .querySelectorAll(
      ".nav-item"
    )
    .forEach(
      x =>
        x.classList
          .remove("active")
    );

  document
    .querySelector(
      '[data-page="galleryPage"]'
    )
    ?.classList
    .add("active");

}


document
  .querySelectorAll(
    ".nav-item"
  )
  .forEach(
    btn => {

      btn.onclick =
        () => {

          if (
            btn.dataset.page ===
            "historyPage"
          ) {

            showHistory();

          } else {

            loadFolder(
              currentPath
            );

          }

        };

    }
  );


// =========================================================
// SEARCH
// =========================================================

let searchTimer;

$("search")
  .addEventListener(
    "input",
    () => {

      clearTimeout(
        searchTimer
      );

      const q =
        $("search")
          .value
          .trim();

      searchTimer =
        setTimeout(
          async () => {

            if (!q) {

              loadFolder(
                currentPath
              );

              return;

            }

            statusEl.textContent =
              "Searching…";

            try {

              const r =
                await fetch(
                  "/api/search?q=" +
                  encodeURIComponent(
                    q
                  )
                );

              const data =
                await r.json();

              if (!data.status) {
                throw new Error(
                  data.error
                );
              }

              statusEl.textContent =
                data.total +
                " result" +
                (
                  data.total === 1
                    ? ""
                    : "s"
                );

              render(
                data.items
              );

            } catch (e) {

              statusEl.textContent =
                e.message;

            }

          },
          300
        );

    }
  );


// =========================================================
// BACK / HOME
// =========================================================

$("backBtn")
  .onclick =
  () => {

    if (!currentPath)
      return;

    const parent =
      currentPath
        .split("/")
        .slice(0, -1)
        .join("/");

    loadFolder(
      parent
    );

  };


$("homeBtn")
  .onclick =
    () =>
      loadFolder("");


loadFolder("");
'''

APP.write_text(
    app,
    encoding="utf-8"
)


# =========================================================
# INDEX HTML — remove login, add history UI
# =========================================================

html = r'''<!doctype html>
<html lang="en">

<head>

<meta charset="utf-8">

<meta
  name="viewport"
  content="width=device-width,initial-scale=1,viewport-fit=cover"
>

<meta
  name="theme-color"
  content="#07070a"
>

<title>Rakib Gallery</title>

<link
  rel="stylesheet"
  href="/style.css?v=20260927-device-history"
>

</head>

<body>

<div class="app-shell">

<header class="topbar">

  <div class="brand">

    <div class="brand-icon">
      RG
    </div>

    <div class="brand-text">

      <strong>
        Rakib Gallery
      </strong>

      <span id="currentPath">
        /
      </span>

    </div>

  </div>

</header>


<main id="gallery">

<section class="hero">

  <div>

    <span class="eyebrow">
      YOUR LIBRARY
    </span>

    <h1>
      My Gallery
    </h1>

    <p id="status">
      Loading…
    </p>

  </div>

  <div class="hero-orb">
    ✦
  </div>

</section>


<div class="toolbar">

  <button
    id="backBtn"
    class="tool-btn"
  >
    ←
  </button>

  <div class="search-box">

    <span>
      ⌕
    </span>

    <input
      id="search"
      placeholder="Search photos & videos"
      autocomplete="off"
    >

  </div>

  <button
    id="homeBtn"
    class="tool-btn"
  >
    ⌂
  </button>

</div>


<div
  id="grid"
  class="grid"
></div>


<section
  id="historyPanel"
  class="history-panel"
  hidden
>

  <div class="history-header">

    <div>

      <span class="eyebrow">
        PRIVATE ACTIVITY
      </span>

      <h2>
        My History
      </h2>

      <p>
        Only this device
      </p>

    </div>

    <button
      id="clearHistory"
      class="danger-btn"
    >
      Clear
    </button>

  </div>


  <div
    id="historyList"
    class="history-list"
  ></div>

</section>

</main>


<nav
  id="bottomNav"
  class="bottom-nav"
>

  <button
    class="nav-item active"
    data-page="galleryPage"
  >

    <span>
      ▦
    </span>

    <small>
      Gallery
    </small>

  </button>


  <button
    class="nav-item"
    data-page="historyPage"
  >

    <span>
      ◷
    </span>

    <small>
      History
    </small>

  </button>

</nav>


<div
  id="viewer"
  class="viewer"
  hidden
>

  <button
    id="closeViewer"
    class="viewer-close"
  >
    ×
  </button>


  <div
    id="viewerContent"
    class="viewer-content"
  ></div>


  <div class="viewer-bottom">

    <div
      id="viewerName"
      class="viewer-name"
    ></div>

    <a
      id="downloadBtn"
      class="download-btn"
    >
      ↓ Download
    </a>

  </div>

</div>


</div>


<script
  src="/app.js?v=20260927-device-history"
></script>

</body>
</html>
'''

HTML.write_text(
    html,
    encoding="utf-8"
)


# =========================================================
# HISTORY UI CSS PATCH
# =========================================================

c = CSS.read_text(
    encoding="utf-8"
)

# Remove previous history-specific block approximately
# only if our new marker exists.
if "DEVICE HISTORY UI" in c:
    c = c.split(
        "/* DEVICE HISTORY UI */"
    )[0]


new_css = r'''

/* =========================================================
   DEVICE HISTORY UI
   ========================================================= */

.history-panel {
  padding: 8px 16px 35px;
}

.history-header {
  margin: 10px 2px 24px;

  padding: 22px;

  border-radius: 24px;

  background:
    radial-gradient(
      circle at 100% 0%,
      rgba(255,255,255,.10),
      transparent 40%
    ),
    linear-gradient(
      145deg,
      #17171d,
      #0d0d11
    );

  border: 1px solid var(--border);

  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.history-header h2 {
  margin: 7px 0 3px;

  font-size: 28px;
}

.history-header p {
  margin: 0;

  color: var(--muted);

  font-size: 11px;
}

.danger-btn {
  background:
    rgba(255,95,109,.10);

  color:
    #ff6975;

  border:
    1px solid
    rgba(255,95,109,.20);

  padding:
    9px 13px;

  border-radius:
    12px;

  cursor:
    pointer;
}

.history-list {
  display:
    grid;

  gap:
    10px;
}

.history-card {
  display:
    flex;

  align-items:
    center;

  gap:
    13px;

  padding:
    10px;

  border-radius:
    19px;

  background:
    linear-gradient(
      145deg,
      #15151b,
      #0e0e12
    );

  border:
    1px solid
    rgba(255,255,255,.07);

  box-shadow:
    0 10px 35px
    rgba(0,0,0,.20);

  cursor:
    pointer;

  transition:
    transform .15s ease,
    border-color .15s ease;
}

.history-card:active {
  transform:
    scale(.975);
}

.history-card-thumb {
  width:
    64px;

  height:
    64px;

  flex:
    0 0 64px;

  overflow:
    hidden;

  border-radius:
    15px;

  background:
    #08080b;
}

.history-card-thumb img {
  width:
    100%;

  height:
    100%;

  object-fit:
    cover;

  display:
    block;
}

.history-video {
  width:
    100%;

  height:
    100%;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  font-size:
    22px;

  background:
    linear-gradient(
      145deg,
      #24242b,
      #101014
    );
}

.history-card-main {
  min-width:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    4px;
}

.history-card-main strong {
  font-size:
    13px;

  white-space:
    nowrap;

  overflow:
    hidden;

  text-overflow:
    ellipsis;
}

.history-card-main span {
  font-size:
    11px;

  color:
    #d1d1d7;
}

.history-card-main small {
  font-size:
    10px;

  color:
    var(--muted);
}

.history-card-arrow {
  width:
    28px;

  height:
    28px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    50%;

  background:
    rgba(255,255,255,.06);

  color:
    var(--muted);

  font-size:
    19px;
}

.history-empty {
  min-height:
    330px;

  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  justify-content:
    center;

  text-align:
    center;

  color:
    var(--muted);
}

.history-empty-icon {
  width:
    76px;

  height:
    76px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    24px;

  background:
    rgba(255,255,255,.05);

  border:
    1px solid
    var(--border);

  font-size:
    35px;

  margin-bottom:
    16px;
}

.history-empty strong {
  color:
    white;

  font-size:
    16px;
}

.history-empty span {
  max-width:
    260px;

  margin-top:
    7px;

  font-size:
    11px;

  line-height:
    1.5;
}

.history-loading {
  padding:
    50px 10px;

  text-align:
    center;

  color:
    var(--muted);
}


/* MOBILE */

@media (max-width: 500px) {

  .history-header {
    padding:
      20px;
  }

  .history-card {
    padding:
      9px;
  }

  .history-card-thumb {
    width:
      60px;

    height:
      60px;

    flex-basis:
      60px;
  }

}
'''

c += new_css

CSS.write_text(
    c,
    encoding="utf-8"
)


# =========================================================
# HISTORY FILE
# =========================================================

history = ROOT / "history.json"

if not history.exists():

    history.write_text(
        json.dumps(
            {"devices": {}},
            indent=2
        ),
        encoding="utf-8"
    )

else:

    try:

        old = json.loads(
            history.read_text(
                encoding="utf-8"
            )
        )

        # Do not destroy existing data.
        if (
            isinstance(old, list)
        ):

            backup = (
                ROOT /
                "history.old.json"
            )

            backup.write_text(
                json.dumps(
                    old,
                    indent=2
                ),
                encoding="utf-8"
            )

            history.write_text(
                json.dumps(
                    {"devices": {}},
                    indent=2
                ),
                encoding="utf-8"
            )

            print(
                "⚠️ Old history format backed up to history.old.json"
            )

    except Exception:
        pass


print()
print("==========================================")
print("   DEVICE HISTORY PATCH COMPLETE")
print("==========================================")
print("✅ Gallery is now public")
print("✅ Gallery password removed")
print("✅ History has separate password")
print("✅ Per-device history")
print("✅ Device ID stored in localStorage")
print("✅ Separate history cards")
print("✅ View history")
print("✅ Download history")
print("✅ Clear current-device history")
print("✅ Device history API")
print()
print("Next:")
print("  cat .env")
print("  node --check server.js")
print("  npm start")
