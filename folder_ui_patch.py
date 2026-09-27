from pathlib import Path

css = Path("public/style.css")
app = Path("public/app.js")
html = Path("public/index.html")

# =========================================================
# APP.JS — folder/file manager style rendering
# =========================================================

s = app.read_text(encoding="utf-8")

start = s.find("function render(items) {")
end = s.find("\n\n// =========================================================\n// VIEWER", start)

if start == -1 or end == -1:
    raise SystemExit("❌ render() function not found")

new_render = r'''function render(items) {

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

}'''

s = s[:start] + new_render + s[end:]

app.write_text(s, encoding="utf-8")


# =========================================================
# CSS — File Manager / 📂 UI
# =========================================================

c = css.read_text(encoding="utf-8")

if "FOLDER FILE MANAGER UI" in c:
    c = c.split(
        "/* =========================================================\n"
        "   FOLDER FILE MANAGER UI"
    )[0]


folder_css = r'''

/* =========================================================
   FOLDER FILE MANAGER UI
   ========================================================= */

main#gallery {
  padding-bottom: 20px;
}


/* HERO */

.hero {
  margin: 16px;

  min-height: 125px;

  padding: 23px;

  border-radius: 24px;

  background:
    linear-gradient(
      145deg,
      #17191d,
      #0d0e11
    );

  border:
    1px solid
    rgba(255,255,255,.07);

  position: relative;

  overflow: hidden;
}

.hero h1 {
  font-size: 27px;

  letter-spacing:
    -.7px;
}

.hero-art {
  font-size:
    100px;

  opacity:
    .13;
}


/* TOOLBAR */

.toolbar {
  padding:
    0 16px 16px;
}


/* MAIN GRID */

.grid {
  display:
    block;

  padding:
    0 16px 35px;
}


/* SECTION TITLE */

.file-section-title {
  display:
    flex;

  align-items:
    center;

  gap:
    8px;

  margin:
    8px 3px 10px;

  color:
    #e8e8eb;

  font-size:
    13px;

  font-weight:
    800;
}

.file-section-title small {
  min-width:
    20px;

  height:
    20px;

  padding:
    0 6px;

  display:
    inline-flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    8px;

  background:
    rgba(255,255,255,.06);

  color:
    #777983;

  font-size:
    9px;
}

.files-title {
  margin-top:
    24px;
}


/* =========================================================
   FOLDERS
   ========================================================= */

.folder-grid {
  display:
    grid;

  grid-template-columns:
    repeat(2, minmax(0, 1fr));

  gap:
    10px;
}

.folder-card {
  min-width:
    0;

  min-height:
    104px;

  padding:
    13px;

  display:
    flex;

  align-items:
    center;

  gap:
    10px;

  position:
    relative;

  overflow:
    hidden;

  border-radius:
    18px;

  background:
    linear-gradient(
      145deg,
      #17181c,
      #101114
    );

  border:
    1px solid
    rgba(255,255,255,.07);

  cursor:
    pointer;

  transition:
    transform .15s ease;
}

.folder-card:active {
  transform:
    scale(.96);
}


/* FOLDER ICON */

.folder-icon-wrap {
  position:
    relative;

  width:
    54px;

  height:
    47px;

  flex:
    0 0 54px;
}

.folder-back {
  position:
    absolute;

  left:
    2px;

  top:
    5px;

  width:
    47px;

  height:
    35px;

  border-radius:
    7px;

  background:
    #c99832;

  transform:
    skewX(-4deg);
}

.folder-front {
  position:
    absolute;

  left:
    0;

  bottom:
    0;

  width:
    52px;

  height:
    37px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    7px;

  background:
    linear-gradient(
      145deg,
      #ffd96a,
      #dca83e
    );

  box-shadow:
    0 7px 15px
    rgba(0,0,0,.25);
}

.folder-front span {
  font-size:
    27px;

  line-height:
    1;
}


/* FOLDER INFO */

.folder-info {
  min-width:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    5px;
}

.folder-info strong {
  color:
    #f0f0f2;

  font-size:
    12px;

  white-space:
    nowrap;

  overflow:
    hidden;

  text-overflow:
    ellipsis;
}

.folder-info small {
  color:
    #74767e;

  font-size:
    9px;
}

.folder-arrow {
  color:
    #666871;

  font-size:
    20px;
}


/* =========================================================
   FILE LIST
   ========================================================= */

.file-list {
  display:
    grid;

  gap:
    8px;
}

.file-card {
  min-height:
    72px;

  padding:
    8px;

  display:
    flex;

  align-items:
    center;

  gap:
    11px;

  position:
    relative;

  border-radius:
    16px;

  background:
    #111216;

  border:
    1px solid
    rgba(255,255,255,.055);

  cursor:
    pointer;

  transition:
    transform .15s ease;
}

.file-card:active {
  transform:
    scale(.985);
}


/* FILE THUMB */

.file-thumb {
  width:
    56px;

  height:
    56px;

  flex:
    0 0 56px;

  overflow:
    hidden;

  border-radius:
    12px;

  background:
    #08090b;

  position:
    relative;
}

.image-thumb img,
.video-thumb video {
  width:
    100%;

  height:
    100%;

  object-fit:
    cover;

  display:
    block;
}

.video-play {
  position:
    absolute;

  left:
    50%;

  top:
    50%;

  transform:
    translate(-50%, -50%);

  width:
    27px;

  height:
    27px;

  border-radius:
    50%;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  background:
    rgba(0,0,0,.65);

  color:
    white;

  font-size:
    10px;
}

.generic-file {
  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  font-size:
    25px;
}


/* FILE INFO */

.file-info {
  min-width:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    5px;
}

.file-info strong {
  color:
    #ededf0;

  font-size:
    12px;

  white-space:
    nowrap;

  overflow:
    hidden;

  text-overflow:
    ellipsis;
}

.file-info span {
  color:
    #6e7078;

  font-size:
    9px;

  white-space:
    nowrap;

  overflow:
    hidden;

  text-overflow:
    ellipsis;
}


/* FILE TYPE */

.file-type {
  padding:
    5px 7px;

  border-radius:
    7px;

  background:
    rgba(255,255,255,.045);

  color:
    #74767e;

  font-size:
    7px;

  font-weight:
    900;

  letter-spacing:
    .5px;
}

.file-arrow {
  color:
    #55575f;

  font-size:
    19px;
}


/* EMPTY */

.file-empty {
  min-height:
    300px;

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
    #74767d;
}

.file-empty-icon {
  font-size:
    62px;

  margin-bottom:
    10px;

  filter:
    drop-shadow(
      0 8px 20px
      rgba(255,210,70,.12)
    );
}

.file-empty strong {
  color:
    #eeeeef;

  font-size:
    15px;
}

.file-empty span {
  margin-top:
    6px;

  font-size:
    10px;
}


/* DESKTOP */

@media (min-width: 700px) {

  .folder-grid {
    grid-template-columns:
      repeat(3, minmax(0, 1fr));
  }

  .file-list {
    max-width:
      850px;
  }

}


/* SMALL PHONES */

@media (max-width: 370px) {

  .folder-grid {
    grid-template-columns:
      1fr;
  }

}
'''

c += folder_css

css.write_text(c, encoding="utf-8")


# =========================================================
# CACHE BUST INDEX
# =========================================================

h = html.read_text(encoding="utf-8")

h = h.replace(
    "?v=final20260927",
    "?v=folder-ui-20260927"
)

h = h.replace(
    "?v=final20260927",
    "?v=folder-ui-20260927"
)

html.write_text(h, encoding="utf-8")


print("==========================================")
print("     📂 FOLDER GALLERY UI INSTALLED")
print("==========================================")
print("✅ Folder-first layout")
print("✅ 📂 folder cards")
print("✅ Folder navigation")
print("✅ File-manager style list")
print("✅ Image thumbnails")
print("✅ Video thumbnails")
print("✅ File type badges")
print("✅ Mobile friendly")
print("✅ Desktop friendly")
print("==========================================")
print()
print("Next:")
print("  node --check server.js")
print("  npm start")
