from pathlib import Path

server = Path("server.js")
app = Path("public/app.js")

# =========================
# PATCH SERVER.JS
# =========================

s = server.read_text(encoding="utf-8")

marker = 'app.get("/api/file", auth, (req, res) => {'

if 'app.get("/api/download", auth' not in s:
    endpoint = r'''app.get("/api/download", auth, (req, res) => {
  try {
    const relative = String(req.query.path || "");
    const file = safeResolve(relative);
    const stat = statSafe(file);

    if (!stat || !stat.isFile()) {
      return res.status(404).json({
        status: false,
        error: "File not found"
      });
    }

    const ext = path.extname(file).toLowerCase();

    if (!IMAGE_EXT.has(ext) && !VIDEO_EXT.has(ext)) {
      return res.status(403).json({
        status: false,
        error: "Only media files are allowed"
      });
    }

    res.download(file, path.basename(file));
  } catch (e) {
    res.status(e.status || 500).json({
      status: false,
      error: e.message
    });
  }
});

'''

    if marker not in s:
        raise SystemExit("❌ Could not find /api/file route")

    s = s.replace(marker, endpoint + marker, 1)
    server.write_text(s, encoding="utf-8")
    print("✅ /api/download endpoint added")
else:
    print("ℹ️ /api/download already exists")


# =========================
# PATCH APP.JS
# =========================

a = app.read_text(encoding="utf-8")

old_viewer = '''function openViewer(item) {
  const url = fileUrl(item);
  viewerContent.innerHTML = item.type === "image"
    ? `<img src="${url}" alt="">`
    : `<video src="${url}" controls autoplay playsinline></video>`;
  downloadBtn.href = api(`/api/download?path=${encodeURIComponent(item.path)}`);
  viewer.hidden = false;
}'''

new_viewer = '''function openViewer(item) {
  const url = fileUrl(item);

  viewerContent.innerHTML = item.type === "image"
    ? `<img src="${url}" alt="">`
    : `<video src="${url}" controls autoplay playsinline></video>`;

  downloadBtn.href =
    api(`/api/download?path=${encodeURIComponent(item.path)}`);

  downloadBtn.download = item.name;
  downloadBtn.target = "_self";

  viewer.hidden = false;
  document.body.classList.add("viewer-open");
}'''

if old_viewer in a:
    a = a.replace(old_viewer, new_viewer, 1)
    print("✅ Viewer updated")
else:
    print("⚠️ Viewer function pattern not found")


old_close = '''$("closeViewer").onclick = () => {
  viewer.hidden = true;
  viewerContent.innerHTML = "";
};

viewer.onclick = e => {
  if (e.target === viewer) $("closeViewer").click();
};'''

new_close = '''function closeViewer() {
  viewer.hidden = true;
  viewerContent.innerHTML = "";
  document.body.classList.remove("viewer-open");
}

$("closeViewer").onclick = closeViewer;

viewer.addEventListener("click", e => {
  if (e.target === viewer) {
    closeViewer();
  }
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape" && !viewer.hidden) {
    closeViewer();
  }
});'''

if old_close in a:
    a = a.replace(old_close, new_close, 1)
    print("✅ Close button fixed")
else:
    print("⚠️ Close handler pattern not found")

app.write_text(a, encoding="utf-8")

print()
print("==========================================")
print("      RAKIB GALLERY PATCH COMPLETE")
print("==========================================")
print("✅ Download API")
print("✅ Authenticated downloads")
print("✅ Viewer close button")
print("✅ Click outside to close")
print("✅ ESC key to close")
print()
print("Next:")
print("  node --check server.js")
print("  npm start")
