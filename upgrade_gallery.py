from pathlib import Path

ROOT = Path(".")
PUBLIC = ROOT / "public"
PUBLIC.mkdir(exist_ok=True)

# =========================================================
# SERVER PATCH — HISTORY API
# =========================================================

server = ROOT / "server.js"
s = server.read_text(encoding="utf-8")

if "const HISTORY_FILE" not in s:
    marker = 'const PASSWORD = process.env.GALLERY_PASSWORD || "change-this-password";'

    insert = r'''

const HISTORY_FILE = path.join(__dirname, "history.json");
const MAX_HISTORY = 500;

function readHistory() {
  try {
    if (!fs.existsSync(HISTORY_FILE)) return [];

    const data = JSON.parse(
      fs.readFileSync(HISTORY_FILE, "utf8")
    );

    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function writeHistory(history) {
  try {
    fs.writeFileSync(
      HISTORY_FILE,
      JSON.stringify(history.slice(0, MAX_HISTORY), null, 2),
      "utf8"
    );
  } catch (e) {
    console.warn("History write error:", e.message);
  }
}

function addHistory(entry) {
  const history = readHistory();

  const item = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2),
    ...entry,
    time: Date.now()
  };

  history.unshift(item);

  writeHistory(history);

  return item;
}
'''

    if marker not in s:
        raise SystemExit("❌ Could not find PASSWORD line")

    s = s.replace(marker, marker + insert, 1)


# Add history routes
if 'app.get("/api/history", auth' not in s:

    history_routes = r'''

// =========================================================
// HISTORY API
// =========================================================

app.get("/api/history", auth, (req, res) => {
  const history = readHistory();

  res.json({
    status: true,
    total: history.length,
    items: history
  });
});

app.post("/api/history", auth, (req, res) => {
  try {
    const pathValue = String(req.body?.path || "");
    const action = String(req.body?.action || "view");

    if (!pathValue) {
      return res.status(400).json({
        status: false,
        error: "Path is required"
      });
    }

    if (!["view", "download"].includes(action)) {
      return res.status(400).json({
        status: false,
        error: "Invalid history action"
      });
    }

    const file = safeResolve(pathValue);
    const stat = statSafe(file);

    if (!stat || !stat.isFile()) {
      return res.status(404).json({
        status: false,
        error: "File not found"
      });
    }

    const type = typeFor(path.basename(file), false);

    if (type !== "image" && type !== "video") {
      return res.status(403).json({
        status: false,
        error: "Only media files are supported"
      });
    }

    const item = addHistory({
      action,
      name: path.basename(file),
      path: relativeToRoot(file),
      type,
      size: stat.size,
      modified: stat.mtimeMs
    });

    res.json({
      status: true,
      item
    });

  } catch (e) {
    res.status(e.status || 500).json({
      status: false,
      error: e.message
    });
  }
});

app.delete("/api/history", auth, (req, res) => {
  writeHistory([]);

  res.json({
    status: true,
    message: "History cleared"
  });
});

'''

    # Put routes before the file routes.
    marker = 'app.get("/api/file", auth, (req, res) => {'

    if marker not in s:
        raise SystemExit("❌ Could not find /api/file")

    s = s.replace(marker, history_routes + marker, 1)


server.write_text(s, encoding="utf-8")


# =========================================================
# NEW INDEX.HTML
# =========================================================

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1,viewport-fit=cover">

<meta name="theme-color" content="#09090b">

<title>Rakib Gallery</title>

<link rel="stylesheet" href="/style.css?v=20260927-ui3">
</head>

<body>

<div class="app-shell">

  <!-- HEADER -->

  <header class="topbar">

    <div class="brand">

      <div class="brand-icon">
        RG
      </div>

      <div class="brand-text">
        <strong>Rakib Gallery</strong>
        <span id="currentPath">/</span>
      </div>

    </div>

    <button id="logoutBtn" class="icon-btn">
      ⇥
    </button>

  </header>


  <!-- LOGIN -->

  <section id="login" class="login-screen">

    <div class="login-card">

      <div class="login-logo">
        RG
      </div>

      <h1>Private Gallery</h1>

      <p>
        Your personal photos and videos
      </p>

      <div class="password-box">

        <input
          id="password"
          type="password"
          placeholder="Gallery password"
          autocomplete="current-password"
        >

        <button id="loginBtn">
          Open Gallery
        </button>

      </div>

      <div id="loginError" class="error"></div>

    </div>

  </section>


  <!-- GALLERY -->

  <main id="gallery" hidden>

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

      <button id="backBtn" class="tool-btn">
        ←
      </button>

      <div class="search-box">

        <span>⌕</span>

        <input
          id="search"
          placeholder="Search photos & videos"
          autocomplete="off"
        >

      </div>

      <button id="homeBtn" class="tool-btn">
        ⌂
      </button>

    </div>


    <div id="grid" class="grid"></div>


    <!-- HISTORY -->

    <section id="historyPanel" class="history-panel" hidden>

      <div class="section-heading">

        <div>
          <span class="eyebrow">RECENT ACTIVITY</span>
          <h2>History</h2>
        </div>

        <button id="clearHistory" class="danger-btn">
          Clear
        </button>

      </div>

      <div id="historyList" class="history-list"></div>

    </section>

  </main>


  <!-- BOTTOM NAV -->

  <nav id="bottomNav" class="bottom-nav" hidden>

    <button class="nav-item active" data-page="galleryPage">

      <span>⌂</span>
      <small>Gallery</small>

    </button>

    <button class="nav-item" data-page="historyPage">

      <span>◷</span>
      <small>History</small>

    </button>

  </nav>


  <!-- VIEWER -->

  <div id="viewer" class="viewer" hidden>

    <button
      id="closeViewer"
      class="viewer-close"
      aria-label="Close"
    >
      ×
    </button>

    <div
      id="viewerContent"
      class="viewer-content"
    ></div>

    <div class="viewer-bottom">

      <div id="viewerName" class="viewer-name"></div>

      <a
        id="downloadBtn"
        class="download-btn"
      >
        ↓ Download
      </a>

    </div>

  </div>


</div>


<script src="/app.js?v=20260927-ui3"></script>

</body>
</html>
'''

(ROOT / "public/index.html").write_text(html, encoding="utf-8")


# =========================================================
# NEW APP.JS
# =========================================================

app = r'''let password = "";
let currentPath = "";

const $ = id => document.getElementById(id);

const login = $("login");
const gallery = $("gallery");
const grid = $("grid");
const statusEl = $("status");

const viewer = $("viewer");
const viewerContent = $("viewerContent");
const downloadBtn = $("downloadBtn");
const viewerName = $("viewerName");

const historyPanel = $("historyPanel");
const historyList = $("historyList");
const bottomNav = $("bottomNav");

function api(url) {
  const join = url.includes("?") ? "&" : "?";
  return `${url}${join}password=${encodeURIComponent(password)}`;
}

function formatSize(bytes) {
  if (bytes == null) return "";

  const units = ["B", "KB", "MB", "GB", "TB"];

  let n = bytes;
  let i = 0;

  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }

  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function formatDate(time) {
  const d = new Date(time);

  return d.toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function fileUrl(item) {
  return api(
    `/api/file?path=${encodeURIComponent(item.path)}`
  );
}

function escapeHtml(s) {
  return String(s).replace(
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


/* ==========================================
   HISTORY
========================================== */

async function history(action, item) {

  try {

    await fetch(api("/api/history"), {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        action,
        path: item.path
      })
    });

  } catch {}
}


async function loadHistory() {

  historyList.innerHTML =
    `<div class="loading">Loading history…</div>`;

  try {

    const r = await fetch(api("/api/history"));

    const data = await r.json();

    if (!data.status) {
      throw new Error(data.error || "Failed");
    }

    if (!data.items.length) {

      historyList.innerHTML = `
        <div class="empty-history">
          <div>◷</div>
          <strong>No history yet</strong>
          <span>Open a photo or video to see it here.</span>
        </div>
      `;

      return;
    }

    historyList.innerHTML = data.items.map(item => {

      const url = fileUrl(item);

      return `
        <div
          class="history-item"
          data-path="${escapeHtml(item.path)}"
        >

          <div class="history-thumb">

            ${
              item.type === "image"
              ? `<img src="${url}" loading="lazy">`
              : `<div class="video-history">▶</div>`
            }

          </div>

          <div class="history-info">

            <strong>
              ${escapeHtml(item.name)}
            </strong>

            <span>
              ${item.action === "download"
                ? "Downloaded"
                : "Viewed"}
              · ${formatDate(item.time)}
            </span>

          </div>

          <div class="history-arrow">
            ›
          </div>

        </div>
      `;

    }).join("");


    historyList
      .querySelectorAll(".history-item")
      .forEach(el => {

        el.onclick = () => {

          const path = el.dataset.path;

          const item = data.items.find(
            x => x.path === path
          );

          if (item) {
            openViewer(item);
          }

        };

      });

  } catch (e) {

    historyList.innerHTML =
      `<div class="error">${escapeHtml(e.message)}</div>`;

  }
}


/* ==========================================
   FOLDER
========================================== */

async function loadFolder(p = "") {

  showGalleryPage();

  statusEl.textContent = "Loading…";

  try {

    const r = await fetch(
      api(`/api/list?path=${encodeURIComponent(p)}`)
    );

    const data = await r.json();

    if (!data.status) {
      throw new Error(data.error || "Failed");
    }

    currentPath = p;

    $("currentPath").textContent =
      "/" + p;

    $("backBtn").disabled = !p;

    statusEl.textContent =
      `${data.total} item${data.total === 1 ? "" : "s"}`;

    render(data.items);

  } catch (e) {

    statusEl.textContent = e.message;

  }
}


/* ==========================================
   RENDER
========================================== */

function render(items) {

  grid.innerHTML = "";

  if (!items.length) {

    grid.innerHTML = `
      <div class="empty-gallery">
        <div>⌁</div>
        <strong>Nothing here</strong>
        <span>No photos, videos or folders found.</span>
      </div>
    `;

    return;
  }


  for (const item of items) {

    const card =
      document.createElement("article");

    card.className = "media-card";


    if (item.type === "folder") {

      card.innerHTML = `
        <div class="folder-preview">
          <div class="folder-icon">▱</div>
        </div>

        <div class="card-name">
          ${escapeHtml(item.name)}
        </div>

        <div class="card-meta">
          Folder
        </div>
      `;

      card.onclick =
        () => loadFolder(item.path);

    } else {

      const url = fileUrl(item);

      card.innerHTML = `

        <div class="media-preview">

          ${
            item.type === "image"

            ? `<img
                 src="${url}"
                 loading="lazy"
                 alt=""
               >`

            : `<video
                 src="${url}"
                 preload="metadata"
               ></video>
               <div class="play-icon">▶</div>`
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
        () => openViewer(item);
    }


    grid.appendChild(card);

  }
}


/* ==========================================
   VIEWER
========================================== */

function openViewer(item) {

  viewerContent.innerHTML = "";

  const url = fileUrl(item);


  if (item.type === "image") {

    const img =
      document.createElement("img");

    img.src = url;
    img.alt = item.name;

    viewerContent.appendChild(img);

  } else {

    const video =
      document.createElement("video");

    video.src = url;
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;

    viewerContent.appendChild(video);
  }


  viewerName.textContent = item.name;

  downloadBtn.href =
    api(
      `/api/download?path=${encodeURIComponent(item.path)}`
    );

  downloadBtn.download = item.name;

  viewer.hidden = false;

  document.body.classList.add("viewer-open");

  history("view", item);
}


function closeViewer() {

  const video =
    viewerContent.querySelector("video");

  if (video) {
    video.pause();
    video.removeAttribute("src");
  }

  viewerContent.innerHTML = "";

  viewer.hidden = true;

  document.body.classList.remove("viewer-open");
}


/* ==========================================
   DOWNLOAD
========================================== */

downloadBtn.addEventListener("click", () => {

  const pathValue =
    new URL(downloadBtn.href).searchParams.get("path");

  if (pathValue) {

    history("download", {
      path: decodeURIComponent(pathValue),
      name: viewerName.textContent,
      type:
        viewerContent.querySelector("video")
          ? "video"
          : "image"
    });

  }

});


/* ==========================================
   CONTROLS
========================================== */

$("closeViewer").onclick =
  closeViewer;

viewer.onclick = e => {

  if (e.target === viewer) {
    closeViewer();
  }

};

document.addEventListener("keydown", e => {

  if (e.key === "Escape" && !viewer.hidden) {
    closeViewer();
  }

});


$("loginBtn").onclick =
  async () => {

    password =
      $("password").value;

    $("loginError").textContent = "";

    try {

      const r = await fetch(
        api("/api/list?path=")
      );

      const data =
        await r.json();

      if (!r.ok || !data.status) {
        throw new Error(
          data.error || "Invalid password"
        );
      }

      login.hidden = true;
      gallery.hidden = false;
      bottomNav.hidden = false;

      sessionStorage.setItem(
        "galleryPassword",
        password
      );

      loadFolder("");

    } catch (e) {

      $("loginError").textContent =
        e.message;

    }

  };


$("password").addEventListener(
  "keydown",
  e => {

    if (e.key === "Enter") {
      $("loginBtn").click();
    }

  }
);


$("backBtn").onclick = () => {

  if (!currentPath) return;

  const parent =
    currentPath
      .split("/")
      .slice(0, -1)
      .join("/");

  loadFolder(parent);

};


$("homeBtn").onclick =
  () => loadFolder("");


$("logoutBtn").onclick = () => {

  sessionStorage.removeItem(
    "galleryPassword"
  );

  password = "";

  gallery.hidden = true;
  bottomNav.hidden = true;

  login.hidden = false;

  $("password").value = "";

};


$("clearHistory").onclick =
  async () => {

    if (!confirm(
      "Clear all gallery history?"
    )) return;

    await fetch(
      api("/api/history"),
      {
        method: "DELETE"
      }
    );

    loadHistory();

  };


/* ==========================================
   SEARCH
========================================== */

let searchTimer;

$("search").addEventListener(
  "input",
  () => {

    clearTimeout(searchTimer);

    const q =
      $("search").value.trim();

    searchTimer =
      setTimeout(async () => {

        if (!q) {
          return loadFolder(currentPath);
        }

        statusEl.textContent =
          "Searching…";

        try {

          const r =
            await fetch(
              api(
                `/api/search?q=${encodeURIComponent(q)}`
              )
            );

          const data =
            await r.json();

          if (!data.status) {
            throw new Error(data.error);
          }

          statusEl.textContent =
            `${data.total} result${data.total === 1 ? "" : "s"}`;

          render(data.items);

        } catch (e) {

          statusEl.textContent =
            e.message;

        }

      }, 300);

  }
);


/* ==========================================
   NAVIGATION
========================================== */

function showGalleryPage() {

  historyPanel.hidden = true;
  grid.hidden = false;

  document
    .querySelectorAll(".nav-item")
    .forEach(x => x.classList.remove("active"));

  document
    .querySelector('[data-page="galleryPage"]')
    ?.classList.add("active");
}


function showHistoryPage() {

  grid.hidden = true;
  historyPanel.hidden = false;

  document
    .querySelectorAll(".nav-item")
    .forEach(x => x.classList.remove("active"));

  document
    .querySelector('[data-page="historyPage"]')
    ?.classList.add("active");

  loadHistory();
}


document
  .querySelectorAll(".nav-item")
  .forEach(btn => {

    btn.onclick = () => {

      if (
        btn.dataset.page ===
        "historyPage"
      ) {

        showHistoryPage();

      } else {

        loadFolder(currentPath);

      }

    };

  });


/* ==========================================
   AUTO LOGIN
========================================== */

const saved =
  sessionStorage.getItem(
    "galleryPassword"
  );

if (saved) {

  password = saved;

  fetch(api("/api/list?path="))
    .then(r => r.json())
    .then(data => {

      if (data.status) {

        login.hidden = true;
        gallery.hidden = false;
        bottomNav.hidden = false;

        loadFolder("");

      } else {

        sessionStorage.removeItem(
          "galleryPassword"
        );

        password = "";

      }

    })
    .catch(() => {});

}
'''

(ROOT / "public/app.js").write_text(app, encoding="utf-8")


# =========================================================
# NEW STYLE.CSS
# =========================================================

css = r'''
:root {
  --bg: #07070a;
  --surface: #111116;
  --surface2: #18181f;
  --border: rgba(255,255,255,.08);
  --text: #f5f5f7;
  --muted: #92929d;
  --accent: #ffffff;
  --danger: #ff5f6d;
}

* {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}

html,
body {
  margin: 0;
  min-height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family:
    Inter,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

body {
  padding-bottom: 90px;
}

button,
input {
  font: inherit;
}

button {
  border: 0;
}

.app-shell {
  width: 100%;
  max-width: 1100px;
  margin: auto;
}


/* HEADER */

.topbar {
  height: 74px;

  display: flex;
  align-items: center;
  justify-content: space-between;

  padding: 12px 18px;

  position: sticky;
  top: 0;

  z-index: 50;

  background: rgba(7,7,10,.82);

  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);

  border-bottom: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon,
.login-logo {
  width: 44px;
  height: 44px;

  border-radius: 14px;

  display: flex;
  align-items: center;
  justify-content: center;

  font-weight: 900;

  background:
    linear-gradient(
      145deg,
      #fff,
      #85858e
    );

  color: #050505;

  box-shadow:
    0 8px 30px rgba(255,255,255,.08);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-text strong {
  font-size: 16px;
}

.brand-text span {
  color: var(--muted);
  font-size: 11px;
  margin-top: 2px;

  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-btn,
.tool-btn {
  width: 42px;
  height: 42px;

  border-radius: 13px;

  background: var(--surface2);
  color: var(--text);

  border: 1px solid var(--border);

  cursor: pointer;
}


/* LOGIN */

.login-screen {
  min-height: calc(100vh - 74px);

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 25px;
}

.login-card {
  width: 100%;
  max-width: 420px;

  padding: 38px 28px;

  border: 1px solid var(--border);

  border-radius: 28px;

  background:
    radial-gradient(
      circle at top right,
      rgba(255,255,255,.08),
      transparent 45%
    ),
    var(--surface);

  text-align: center;

  box-shadow:
    0 30px 100px rgba(0,0,0,.5);
}

.login-logo {
  margin: 0 auto 22px;
  width: 64px;
  height: 64px;
  border-radius: 20px;
  font-size: 20px;
}

.login-card h1 {
  margin: 0;
  font-size: 28px;
}

.login-card p {
  color: var(--muted);
  margin: 10px 0 28px;
}

.password-box {
  display: grid;
  gap: 10px;
}

.password-box input {
  width: 100%;

  padding: 15px 16px;

  border-radius: 14px;

  border: 1px solid var(--border);

  outline: none;

  background: #0b0b0f;

  color: white;
}

.password-box button {
  padding: 15px;

  border-radius: 14px;

  background: white;
  color: black;

  font-weight: 800;

  cursor: pointer;
}

.error {
  color: var(--danger);
  margin-top: 12px;
  font-size: 13px;
}


/* HERO */

.hero {
  margin: 22px 18px;

  min-height: 145px;

  padding: 25px;

  border-radius: 25px;

  position: relative;
  overflow: hidden;

  background:
    radial-gradient(
      circle at 90% 10%,
      rgba(255,255,255,.13),
      transparent 35%
    ),
    linear-gradient(
      145deg,
      #17171d,
      #0c0c10
    );

  border: 1px solid var(--border);
}

.eyebrow {
  color: var(--muted);

  font-size: 10px;
  letter-spacing: 2px;

  font-weight: 800;
}

.hero h1 {
  margin: 7px 0 5px;

  font-size: 30px;
}

.hero p {
  color: var(--muted);
  margin: 0;
  font-size: 13px;
}

.hero-orb {
  position: absolute;

  right: 28px;
  bottom: -15px;

  font-size: 90px;

  opacity: .08;

  transform: rotate(15deg);
}


/* TOOLBAR */

.toolbar {
  display: flex;
  gap: 8px;

  padding: 0 18px 18px;
}

.search-box {
  flex: 1;

  display: flex;
  align-items: center;

  gap: 8px;

  padding: 0 14px;

  height: 42px;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: 13px;
}

.search-box span {
  color: var(--muted);
  font-size: 22px;
}

.search-box input {
  width: 100%;

  border: 0;
  outline: 0;

  background: transparent;

  color: white;
}

.tool-btn:disabled {
  opacity: .3;
}


/* GRID */

.grid {
  display: grid;

  grid-template-columns:
    repeat(2, minmax(0,1fr));

  gap: 12px;

  padding: 0 14px 30px;
}

.media-card {
  min-width: 0;

  overflow: hidden;

  border-radius: 18px;

  background: var(--surface);

  border: 1px solid var(--border);

  cursor: pointer;

  transition:
    transform .18s ease,
    border-color .18s ease;
}

.media-card:active {
  transform: scale(.97);
}

.media-preview,
.folder-preview {
  aspect-ratio: 1 / 1;

  position: relative;

  overflow: hidden;

  background: #0c0c10;
}

.media-preview img,
.media-preview video {
  width: 100%;
  height: 100%;

  object-fit: cover;

  display: block;
}

.play-icon {
  position: absolute;

  left: 50%;
  top: 50%;

  transform: translate(-50%,-50%);

  width: 46px;
  height: 46px;

  border-radius: 50%;

  display: flex;
  align-items: center;
  justify-content: center;

  background: rgba(0,0,0,.6);

  backdrop-filter: blur(10px);

  color: white;
}

.folder-preview {
  display: flex;
  align-items: center;
  justify-content: center;
}

.folder-icon {
  font-size: 72px;
  opacity: .75;
}

.card-name {
  padding: 10px 11px 2px;

  font-size: 13px;
  font-weight: 650;

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  padding: 2px 11px 12px;

  font-size: 10px;

  color: var(--muted);
}


/* EMPTY */

.empty-gallery,
.empty-history {
  grid-column: 1 / -1;

  min-height: 260px;

  display: flex;
  flex-direction: column;

  align-items: center;
  justify-content: center;

  text-align: center;

  color: var(--muted);
}

.empty-gallery div,
.empty-history div {
  font-size: 55px;
  opacity: .25;
}

.empty-gallery strong,
.empty-history strong {
  color: var(--text);
  margin-top: 10px;
}

.empty-gallery span,
.empty-history span {
  font-size: 12px;
  margin-top: 5px;
}


/* HISTORY */

.history-panel {
  padding: 0 16px 35px;
}

.section-heading {
  display: flex;

  justify-content: space-between;
  align-items: center;

  margin: 5px 2px 18px;
}

.section-heading h2 {
  margin: 5px 0 0;
  font-size: 25px;
}

.danger-btn {
  background: rgba(255,95,109,.1);

  color: var(--danger);

  border: 1px solid rgba(255,95,109,.2);

  padding: 9px 13px;

  border-radius: 11px;

  cursor: pointer;
}

.history-list {
  display: grid;
  gap: 9px;
}

.history-item {
  display: flex;
  align-items: center;

  gap: 12px;

  padding: 9px;

  background: var(--surface);

  border: 1px solid var(--border);

  border-radius: 16px;

  cursor: pointer;
}

.history-thumb {
  width: 58px;
  height: 58px;

  flex: 0 0 58px;

  border-radius: 12px;

  overflow: hidden;

  background: #09090c;
}

.history-thumb img {
  width: 100%;
  height: 100%;

  object-fit: cover;
}

.video-history {
  height: 100%;

  display: flex;
  align-items: center;
  justify-content: center;

  font-size: 20px;
}

.history-info {
  min-width: 0;

  flex: 1;

  display: flex;
  flex-direction: column;
  gap: 5px;
}

.history-info strong {
  font-size: 13px;

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-info span {
  color: var(--muted);
  font-size: 10px;
}

.history-arrow {
  color: var(--muted);
  font-size: 24px;
}


/* BOTTOM NAV */

.bottom-nav {
  position: fixed;

  left: 50%;
  bottom: 12px;

  transform: translateX(-50%);

  z-index: 100;

  width: min(420px, calc(100% - 24px));

  height: 64px;

  display: flex;

  padding: 6px;

  border-radius: 20px;

  background: rgba(20,20,25,.9);

  border: 1px solid var(--border);

  backdrop-filter: blur(20px);

  box-shadow:
    0 20px 60px rgba(0,0,0,.5);
}

.nav-item {
  flex: 1;

  display: flex;
  flex-direction: column;

  align-items: center;
  justify-content: center;

  gap: 2px;

  border-radius: 15px;

  background: transparent;

  color: var(--muted);

  cursor: pointer;
}

.nav-item span {
  font-size: 19px;
}

.nav-item small {
  font-size: 9px;
}

.nav-item.active {
  background: white;
  color: black;
}


/* VIEWER */

.viewer {
  position: fixed;

  inset: 0;

  z-index: 999999;

  display: flex;

  align-items: center;
  justify-content: center;

  background: rgba(0,0,0,.97);

  padding: 75px 12px 100px;

  touch-action: manipulation;
}

.viewer[hidden] {
  display: none !important;
}

.viewer-content {
  width: 100%;
  height: 100%;

  display: flex;

  align-items: center;
  justify-content: center;
}

.viewer-content img,
.viewer-content video {
  max-width: 100%;
  max-height: 100%;

  object-fit: contain;

  border-radius: 8px;
}

.viewer-close {
  position: fixed;

  top: 18px;
  right: 16px;

  width: 50px;
  height: 50px;

  z-index: 1000001;

  border-radius: 50%;

  background: rgba(255,255,255,.14);

  color: white;

  font-size: 30px;

  cursor: pointer;
}

.viewer-bottom {
  position: fixed;

  left: 0;
  right: 0;
  bottom: 0;

  z-index: 1000001;

  padding:
    12px
    16px
    max(18px, env(safe-area-inset-bottom));

  display: flex;

  align-items: center;

  gap: 12px;

  background:
    linear-gradient(
      transparent,
      rgba(0,0,0,.9)
    );
}

.viewer-name {
  flex: 1;

  min-width: 0;

  color: white;

  font-size: 12px;

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.download-btn {
  display: inline-flex;

  align-items: center;
  justify-content: center;

  min-width: 110px;
  height: 44px;

  padding: 0 16px;

  border-radius: 13px;

  background: white;

  color: black;

  text-decoration: none;

  font-weight: 800;

  font-size: 13px;
}


/* DESKTOP */

@media (min-width: 700px) {

  .grid {
    grid-template-columns:
      repeat(4, minmax(0,1fr));
  }

  .hero {
    margin-left: 18px;
    margin-right: 18px;
  }

}


/* LOADING */

.loading {
  padding: 30px;
  text-align: center;
  color: var(--muted);
}
'''

(ROOT / "public/style.css").write_text(css, encoding="utf-8")


# =========================================================
# INITIAL HISTORY FILE
# =========================================================

history = ROOT / "history.json"

if not history.exists():
    history.write_text("[]\n", encoding="utf-8")


print()
print("==========================================")
print("   RAKIB GALLERY UI UPGRADED")
print("==========================================")
print("✅ Modern mobile gallery UI")
print("✅ Bottom navigation")
print("✅ Gallery / History tabs")
print("✅ Persistent history")
print("✅ Viewed history")
print("✅ Download history")
print("✅ History thumbnails")
print("✅ Clear history")
print("✅ Modern fullscreen viewer")
print("✅ Search")
print("✅ Folder navigation")
print("✅ Mobile + desktop layout")
print()
print("Run:")
print("  node --check server.js")
print("  npm start")
