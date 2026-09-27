
/*
 * Device identity is now handled automatically
 * by the server using an HttpOnly cookie.
 */

async function ensureDevice() {
  try {
    const res = await fetch("/api/device/me", {
      credentials: "same-origin"
    });

    if (res.ok) {
      const data = await res.json();

      window.DEVICE_NAME =
        data.device.name;

      return true;
    }

    /*
     * A protected API request automatically creates
     * a new device cookie on the server.
     */
    const init = await fetch("/api/list", {
      credentials: "same-origin"
    });

    if (!init.ok) {
      throw new Error(
        "Unable to create device"
      );
    }

    const data = await init.json();

    if (data.device) {
      window.DEVICE_NAME =
        data.device.name;
    }

    return true;

  } catch (error) {
    console.error(error);
    throw error;
  }
}

async function deviceFetch(url, options = {}) {
  options.credentials = "same-origin";

  return fetch(url, options);
}

const $ = id => document.getElementById(id);

const content = $("content");
const breadcrumb = $("breadcrumb");
const backBtn = $("backBtn");
const refreshBtn = $("refreshBtn");
const search = $("search");

const viewer = $("viewer");
const viewerBody = $("viewerBody");
const viewerName = $("viewerName");
const downloadBtn = $("downloadBtn");
const closeViewer = $("closeViewer");

const historyBtn = $("historyBtn");
const historyModal = $("historyModal");
const closeHistory = $("closeHistory");
const historyLogin = $("historyLogin");
const historyPassword = $("historyPassword");
const historyLoginBtn = $("historyLoginBtn");
const historyError = $("historyError");
const historyContent = $("historyContent");
const historyList = $("historyList");
const clearHistory = $("clearHistory");

let currentPath = "";
let pathStack = [];
let historyUnlocked = false;
let historyPass = "";

function api(url, params = {}) {
  const u = new URL(url, location.origin);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      u.searchParams.set(key, value);
    }
  });

  return u.toString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatSize(bytes) {
  if (!bytes) return "0 B";

  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let n = bytes;

  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }

  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function formatDate(ms) {
  if (!ms) return "";

  return new Date(ms).toLocaleString();
}

function fileUrl(path) {
  return api("/api/file", { path });
}

function downloadUrl(path) {
  return api("/api/download", { path });
}

async function recordHistory(path, action) {
  try {
    await deviceFetch("/api/history", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        path,
        action
      })
    });
  } catch {}
}

async function loadFolder(folder = "") {
  currentPath = folder;

  content.innerHTML =
    `<div class="loading">Loading...</div>`;

  try {
    const res = await deviceFetch(
      api("/api/list", { path: folder })
    );

    const data = await res.json();

    if (!data.ok) {
      throw new Error(data.error || "Unable to load");
    }

    render(data.items);
    updateBreadcrumb();
  } catch (e) {
    content.innerHTML = `
      <div class="error-box">
        <div>⚠️</div>
        <b>Unable to load folder</b>
        <small>${escapeHtml(e.message)}</small>
      </div>
    `;
  }
}

function render(items) {
  if (!items.length) {
    content.innerHTML = `
      <div class="empty">
        <div class="empty-icon">📂</div>
        <b>This folder is empty</b>
        <small>No files or folders found</small>
      </div>
    `;
    return;
  }

  const folders = items.filter(x => x.type === "folder");
  const files = items.filter(x => x.type !== "folder");

  let html = "";

  if (folders.length) {
    html += `<section>
      <div class="section-title">Folders <span>${folders.length}</span></div>
      <div class="folder-grid">`;

    for (const item of folders) {
      html += `
        <button class="folder-card"
          data-folder="${escapeHtml(item.path)}">
          <div class="folder-icon">📂</div>
          <div class="folder-name">${escapeHtml(item.name)}</div>
          <div class="folder-arrow">›</div>
        </button>
      `;
    }

    html += `</div></section>`;
  }

  if (files.length) {
    html += `
      <section>
        <div class="section-title">
          Files <span>${files.length}</span>
        </div>

        <div class="file-list">
    `;

    for (const item of files) {
      const thumb =
        item.type === "image"
          ? `<img src="${fileUrl(item.path)}" loading="lazy">`
          : item.type === "video"
            ? `<div class="video-thumb">▶</div>`
            : `<div class="file-thumb">📄</div>`;

      html += `
        <button class="file-card"
          data-path="${escapeHtml(item.path)}"
          data-type="${item.type}">

          <div class="thumb">
            ${thumb}
          </div>

          <div class="file-info">
            <div class="file-name">
              ${escapeHtml(item.name)}
            </div>

            <div class="file-meta">
              ${formatSize(item.size)}
              ${item.modified ? " • " + formatDate(item.modified) : ""}
            </div>
          </div>

          <div class="file-arrow">›</div>
        </button>
      `;
    }

    html += `
        </div>
      </section>
    `;
  }

  content.innerHTML = html;

  document.querySelectorAll(".folder-card")
    .forEach(card => {
      card.addEventListener("click", () => {
        pathStack.push(currentPath);
        loadFolder(card.dataset.folder);
      });
    });

  document.querySelectorAll(".file-card")
    .forEach(card => {
      card.addEventListener("click", () => {
        openViewer(
          card.dataset.path,
          card.dataset.type
        );
      });
    });
}

function updateBreadcrumb() {
  const parts = currentPath
    ? currentPath.split("/").filter(Boolean)
    : [];

  let html = `
    <button class="crumb" data-path="">📂 Home</button>
  `;

  let built = "";

  parts.forEach((part, index) => {
    built += (built ? "/" : "") + part;

    html += `
      <span class="crumb-sep">›</span>
      <button class="crumb" data-path="${escapeHtml(built)}">
        ${escapeHtml(part)}
      </button>
    `;
  });

  breadcrumb.innerHTML = html;

  breadcrumb.querySelectorAll(".crumb")
    .forEach(btn => {
      btn.addEventListener("click", () => {
        pathStack = [];
        loadFolder(btn.dataset.path);
      });
    });

  backBtn.disabled = !currentPath && pathStack.length === 0;
}

function goBack() {
  if (pathStack.length) {
    const previous = pathStack.pop();
    loadFolder(previous);
    return;
  }

  if (currentPath) {
    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();

    loadFolder(parts.join("/"));
  }
}

function openViewer(path, type) {
  viewerName.textContent = path.split("/").pop();
  downloadBtn.href = downloadUrl(path);

  if (type === "image") {
    viewerBody.innerHTML = `
      <img
        class="preview-image"
        src="${fileUrl(path)}"
        alt=""
      >
    `;
  } else if (type === "video") {
    viewerBody.innerHTML = `
      <video
        class="preview-video"
        src="${fileUrl(path)}"
        controls
        autoplay
      ></video>
    `;
  } else {
    viewerBody.innerHTML = `
      <div class="file-preview">
        <div>📄</div>
        <b>${escapeHtml(path.split("/").pop())}</b>
        <a href="${downloadUrl(path)}">Download file</a>
      </div>
    `;
  }

  viewer.classList.remove("hidden");
  document.body.classList.add("viewer-open");

  recordHistory(path, "view");
}

function closePreview() {
  viewer.classList.add("hidden");
  document.body.classList.remove("viewer-open");
  viewerBody.innerHTML = "";
}

closeViewer.addEventListener("click", closePreview);

viewer.addEventListener("click", e => {
  if (e.target === viewer) closePreview();
});

downloadBtn.addEventListener("click", () => {
  const url = new URL(downloadBtn.href);
  recordHistory(
    url.searchParams.get("path") || "",
    "download"
  );
});

backBtn.addEventListener("click", goBack);

refreshBtn.addEventListener("click", () => {
  loadFolder(currentPath);
});

search.addEventListener("keydown", e => {
  if (e.key !== "Enter") return;

  const q = search.value.trim();

  if (!q) {
    loadFolder(currentPath);
    return;
  }

  performSearch(q);
});

async function performSearch(q) {
  content.innerHTML =
    `<div class="loading">Searching...</div>`;

  try {
    const res = await deviceFetch(
      api("/api/search", { q })
    );

    const data = await res.json();

    if (!data.ok) throw new Error(data.error);

    renderSearch(data.items);
  } catch (e) {
    content.innerHTML = `
      <div class="error-box">
        ⚠️ ${escapeHtml(e.message)}
      </div>
    `;
  }
}

function renderSearch(items) {
  if (!items.length) {
    content.innerHTML = `
      <div class="empty">
        <div class="empty-icon">🔎</div>
        <b>No results</b>
      </div>
    `;
    return;
  }

  const html = `
    <section>
      <div class="section-title">
        Search Results <span>${items.length}</span>
      </div>

      <div class="file-list">
        ${items.map(item => `
          <button class="file-card"
            data-path="${escapeHtml(item.path)}"
            data-type="${item.type}">

            <div class="thumb">
              ${
                item.type === "image"
                ? `<img src="${fileUrl(item.path)}">`
                : item.type === "video"
                  ? `<div class="video-thumb">▶</div>`
                  : `<div class="file-thumb">📄</div>`
              }
            </div>

            <div class="file-info">
              <div class="file-name">
                ${escapeHtml(item.name)}
              </div>

              <div class="file-meta">
                📁 ${escapeHtml(item.path)}
              </div>
            </div>

            <div class="file-arrow">›</div>
          </button>
        `).join("")}
      </div>
    </section>
  `;

  content.innerHTML = html;

  document.querySelectorAll(".file-card")
    .forEach(card => {
      card.addEventListener("click", () => {
        openViewer(
          card.dataset.path,
          card.dataset.type
        );
      });
    });
}

/* =========================
   HISTORY
========================= */

historyBtn.addEventListener("click", () => {
  historyModal.classList.remove("hidden");

  if (historyUnlocked) {
    loadHistory();
  }
});

closeHistory.addEventListener("click", () => {
  historyModal.classList.add("hidden");
});

historyModal.addEventListener("click", e => {
  if (e.target === historyModal) {
    historyModal.classList.add("hidden");
  }
});

historyLoginBtn.addEventListener("click", async () => {
  const pass = historyPassword.value;

  if (!pass) return;

  historyError.textContent = "Checking...";

  try {
    const res = await deviceFetch(
      api("/api/history", {
        password: pass
      })
    );

    if (!res.ok) {
      historyError.textContent =
        "❌ Wrong history password";
      return;
    }

    historyPass = pass;
    historyUnlocked = true;

    historyLogin.classList.add("hidden");
    historyContent.classList.remove("hidden");

    loadHistory();
  } catch {
    historyError.textContent =
      "❌ Connection error";
  }
});

async function loadHistory() {
  historyList.innerHTML =
    `<div class="loading">Loading history...</div>`;

  try {
    const res = await deviceFetch(
      api("/api/history", {
        password: historyPass
      })
    );

    const data = await res.json();

    if (!data.ok) throw new Error(data.error);

    if (!data.items.length) {
      historyList.innerHTML = `
        <div class="empty">
          <div class="empty-icon">🕘</div>
          <b>No history yet</b>
        </div>
      `;
      return;
    }

    historyList.innerHTML = data.items.map(item => `
      <button class="history-item"
        data-path="${escapeHtml(item.path)}">

        <div class="history-icon">
          ${item.action === "download" ? "⬇️" : "👁️"}
        </div>

        <div class="history-info">
          <b>${escapeHtml(item.name)}</b>
          <small>${escapeHtml(item.path)}</small>
          <small>${formatDate(item.time)}</small>
        </div>

        <span>›</span>
      </button>
    `).join("");

    document.querySelectorAll(".history-item")
      .forEach(item => {
        item.addEventListener("click", () => {
          const p = item.dataset.path;
          const ext = p.split(".").pop().toLowerCase();

          const type =
            ["jpg","jpeg","png","gif","webp","bmp","heic","heif","avif"].includes(ext)
              ? "image"
              : ["mp4","mkv","webm","mov","avi","m4v","3gp"].includes(ext)
                ? "video"
                : "file";

          historyModal.classList.add("hidden");
          openViewer(p, type);
        });
      });

  } catch (e) {
    historyList.innerHTML = `
      <div class="error-box">
        ${escapeHtml(e.message)}
      </div>
    `;
  }
}

clearHistory.addEventListener("click", async () => {
  if (!confirm("Clear this device's history?")) return;

  await deviceFetch(
    api("/api/history"),
    {
      method: "DELETE",
      headers: {
        "x-history-password": historyPass
      }
    }
  );

  loadHistory();
});

ensureDevice()
  .then(() => loadFolder(""))
  .catch(err => {
    content.innerHTML = `
      <div class="error-box">
        ⚠️ ${escapeHtml(err.message)}
      </div>
    `;
  });


/* =================================================
   PAIR SYNC
================================================= */

const pairSyncBtn = $("pairSyncBtn");
const pairSyncModal = $("pairSyncModal");
const closePairSync = $("closePairSync");

const pairLoading = $("pairLoading");
const pairCode = $("pairCode");
const pairTimer = $("pairTimer");
const pairInstructions = $("pairInstructions");
const pairCommand = $("pairCommand");
const pairError = $("pairError");

let pairTimerInterval = null;


function closePairModal() {

  if (pairTimerInterval) {
    clearInterval(pairTimerInterval);
    pairTimerInterval = null;
  }

  pairSyncModal.classList.add("hidden");
}


function showPairModal() {

  pairSyncModal.classList.remove("hidden");

  pairLoading.classList.remove("hidden");
  pairCode.classList.add("hidden");
  pairInstructions.classList.add("hidden");

  pairError.textContent = "";
  pairTimer.textContent = "";
}


async function startPairing() {

  showPairModal();

  try {

    const res = await deviceFetch(
      "/api/device/pair/start",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        }
      }
    );

    const data = await res.json();

    if (!res.ok || !data.ok) {
      throw new Error(
        data.error ||
        "Unable to generate pairing code"
      );
    }

    pairLoading.classList.add("hidden");

    pairCode.textContent = data.code;

    pairCode.classList.remove("hidden");

    pairInstructions.classList.remove(
      "hidden"
    );

    pairCommand.textContent =
      `python sync.py --pair ${data.code}`;

    let remaining = data.expiresIn || 300;

    updatePairTimer(remaining);

    if (pairTimerInterval) {
      clearInterval(pairTimerInterval);
    }

    pairTimerInterval = setInterval(() => {

      remaining--;

      updatePairTimer(remaining);

      if (remaining <= 0) {

        clearInterval(
          pairTimerInterval
        );

        pairTimerInterval = null;

        pairTimer.textContent =
          "⏱️ Pairing code expired.";

      }

    }, 1000);

  } catch (error) {

    pairLoading.classList.add("hidden");

    pairError.textContent =
      "❌ " + error.message;
  }
}


function updatePairTimer(seconds) {

  const min =
    Math.floor(seconds / 60);

  const sec =
    String(seconds % 60)
      .padStart(2, "0");

  pairTimer.textContent =
    `Expires in ${min}:${sec}`;
}


if (pairSyncBtn) {

  pairSyncBtn.addEventListener(
    "click",
    startPairing
  );

}


if (closePairSync) {

  closePairSync.addEventListener(
    "click",
    closePairModal
  );

}


if (pairSyncModal) {

  pairSyncModal.addEventListener(
    "click",
    event => {

      if (
        event.target ===
        pairSyncModal
      ) {
        closePairModal();
      }

    }
  );

}
