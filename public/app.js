// RAKIB FINAL DEVICE HISTORY UI
// Gallery = public
// History = private password vault

// =========================================================
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
      <div class="file-empty">
        <div class="file-empty-icon">📂</div>
        <strong>This folder is empty</strong>
        <span>No files or folders found.</span>
      </div>
    `;

    return;
  }


  // Folders first
  const folders = items.filter(
    item => item.type === "folder"
  );

  const files = items.filter(
    item => item.type !== "folder"
  );


  // =======================================================
  // FOLDERS
  // =======================================================

  if (folders.length) {

    const folderTitle =
      document.createElement("div");

    folderTitle.className =
      "file-section-title";

    folderTitle.innerHTML = `
      <span>Folders</span>
      <small>${folders.length}</small>
    `;

    grid.appendChild(folderTitle);


    const folderGrid =
      document.createElement("div");

    folderGrid.className =
      "folder-grid";


    for (const item of folders) {

      const card =
        document.createElement("article");

      card.className =
        "folder-card";


      card.innerHTML = `
        <div class="folder-icon-wrap">
          <div class="folder-back"></div>
          <div class="folder-front">
            <span>📂</span>
          </div>
        </div>

        <div class="folder-info">

          <strong>
            ${escapeHtml(item.name)}
          </strong>

          <small>
            Folder
          </small>

        </div>

        <div class="folder-arrow">
          ›
        </div>
      `;


      card.onclick =
        () => loadFolder(item.path);


      folderGrid.appendChild(card);

    }


    grid.appendChild(folderGrid);

  }


  // =======================================================
  // FILES
  // =======================================================

  if (files.length) {

    const fileTitle =
      document.createElement("div");

    fileTitle.className =
      "file-section-title files-title";

    fileTitle.innerHTML = `
      <span>Files</span>
      <small>${files.length}</small>
    `;

    grid.appendChild(fileTitle);


    const fileList =
      document.createElement("div");

    fileList.className =
      "file-list";


    for (const item of files) {

      const card =
        document.createElement("article");

      card.className =
        "file-card";


      const url =
        fileUrl(item);


      let preview = "";


      if (item.type === "image") {

        preview = `
          <div class="file-thumb image-thumb">
            <img
              src="${url}"
              loading="lazy"
              alt=""
            >
          </div>
        `;

      } else if (item.type === "video") {

        preview = `
          <div class="file-thumb video-thumb">
            <video
              src="${url}"
              preload="metadata"
            ></video>

            <span class="video-play">
              ▶
            </span>
          </div>
        `;

      } else {

        preview = `
          <div class="file-thumb generic-file">
            📄
          </div>
        `;

      }


      card.innerHTML = `

        ${preview}

        <div class="file-info">

          <strong>
            ${escapeHtml(item.name)}
          </strong>

          <span>
            ${formatSize(item.size)}
            ${item.modified
              ? " • " + formatDate(item.modified)
              : ""}
          </span>

        </div>

        <div class="file-type">
          ${
            item.type === "image"
              ? "IMG"
              : item.type === "video"
                ? "VIDEO"
                : "FILE"
          }
        </div>

        <div class="file-arrow">
          ›
        </div>

      `;


      if (
        item.type === "image" ||
        item.type === "video"
      ) {

        card.onclick =
          () => openViewer(item);

      }


      fileList.appendChild(card);

    }


    grid.appendChild(fileList);

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
