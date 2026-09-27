from pathlib import Path

app = Path("public/app.js")
css = Path("public/style.css")
html = Path("public/index.html")

# =========================================================
# APP.JS — replace viewer-related logic
# =========================================================

s = app.read_text(encoding="utf-8")

start = s.find("function openViewer(item) {")
end = s.find("\nfunction escapeHtml", start)

if start == -1 or end == -1:
    raise SystemExit("❌ Could not find openViewer()")

new_viewer = r'''function openViewer(item) {
  const url = fileUrl(item);

  viewerContent.innerHTML = "";

  if (item.type === "image") {
    const img = document.createElement("img");
    img.src = url;
    img.alt = item.name || "";
    img.draggable = false;
    viewerContent.appendChild(img);
  } else {
    const video = document.createElement("video");
    video.src = url;
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;
    viewerContent.appendChild(video);
  }

  downloadBtn.href =
    api("/api/download?path=" + encodeURIComponent(item.path));

  downloadBtn.setAttribute("download", item.name || "download");
  downloadBtn.target = "_self";

  viewer.hidden = false;
  viewer.style.display = "flex";
  viewer.style.pointerEvents = "auto";

  document.body.classList.add("viewer-open");
}

function closeGalleryViewer() {
  viewer.hidden = true;
  viewer.style.display = "none";
  viewer.style.pointerEvents = "none";

  viewerContent.innerHTML = "";
  document.body.classList.remove("viewer-open");
}

'''

s = s[:start] + new_viewer + s[end:]

# Remove old close section if present
old_start = s.find('$("closeViewer").onclick')
if old_start != -1:
    old_end = s.find("\nlet searchTimer", old_start)
    if old_end != -1:
        s = s[:old_start] + s[old_end:]

# Insert robust event handlers before search
marker = "\nlet searchTimer;"

handlers = r'''
// ==========================================
// GALLERY VIEWER CONTROLS
// ==========================================

const closeButton = $("closeViewer");

closeButton.addEventListener("click", function(e) {
  e.preventDefault();
  e.stopPropagation();
  closeGalleryViewer();
});

downloadBtn.addEventListener("click", function(e) {
  e.stopPropagation();

  if (!downloadBtn.href) {
    e.preventDefault();
    return;
  }

  // Let browser navigate to authenticated download URL.
});

viewer.addEventListener("click", function(e) {
  if (e.target === viewer) {
    closeGalleryViewer();
  }
});

viewerContent.addEventListener("click", function(e) {
  e.stopPropagation();
});

document.addEventListener("keydown", function(e) {
  if (e.key === "Escape" && !viewer.hidden) {
    closeGalleryViewer();
  }
});

// Make sure viewer starts closed.
viewer.hidden = true;
viewer.style.display = "none";
viewer.style.pointerEvents = "none";

'''

if marker not in s:
    raise SystemExit("❌ Could not find search section")

s = s.replace(marker, "\n" + handlers + marker, 1)

app.write_text(s, encoding="utf-8")


# =========================================================
# CSS — force clickable controls above overlay
# =========================================================

c = css.read_text(encoding="utf-8")

extra_css = r'''

/* ==========================================
   RAKIB GALLERY VIEWER FIX
   ========================================== */

.viewer {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;

  display: none;
  align-items: center;
  justify-content: center;

  background: rgba(0, 0, 0, 0.96);

  z-index: 999999 !important;

  pointer-events: none;
  touch-action: manipulation;
}

.viewer:not([hidden]) {
  display: flex !important;
  pointer-events: auto !important;
}

.viewer[hidden] {
  display: none !important;
  pointer-events: none !important;
}

.viewer #viewerContent {
  position: relative;
  z-index: 1000000 !important;

  max-width: 95vw;
  max-height: 82vh;

  display: flex;
  align-items: center;
  justify-content: center;

  pointer-events: auto !important;
}

.viewer #viewerContent img,
.viewer #viewerContent video {
  max-width: 95vw;
  max-height: 82vh;

  object-fit: contain;

  display: block;

  pointer-events: auto !important;
}

.viewer .close {
  position: fixed !important;

  top: max(18px, env(safe-area-inset-top)) !important;
  right: 18px !important;

  width: 58px !important;
  height: 58px !important;

  display: flex !important;
  align-items: center !important;
  justify-content: center !important;

  z-index: 1000002 !important;

  pointer-events: auto !important;
  touch-action: manipulation !important;

  cursor: pointer !important;

  font-size: 32px !important;
  line-height: 1 !important;
}

.viewer .download {
  position: fixed !important;

  left: 50% !important;
  bottom: max(24px, env(safe-area-inset-bottom)) !important;

  transform: translateX(-50%) !important;

  z-index: 1000002 !important;

  pointer-events: auto !important;
  touch-action: manipulation !important;

  cursor: pointer !important;

  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;

  min-width: 130px;
  min-height: 48px;

  text-decoration: none !important;
}

body.viewer-open {
  overflow: hidden !important;
}

'''

if "RAKIB GALLERY VIEWER FIX" not in c:
    c += extra_css

css.write_text(c, encoding="utf-8")


# =========================================================
# INDEX — cache-bust JS so old browser JS isn't used
# =========================================================

h = html.read_text(encoding="utf-8")

h = h.replace(
    '<script src="/app.js"></script>',
    '<script src="/app.js?v=20260927-fix2"></script>'
)

html.write_text(h, encoding="utf-8")

print("==========================================")
print("   RAKIB GALLERY VIEWER FIXED")
print("==========================================")
print("✅ Viewer click layer fixed")
print("✅ X button forced above overlay")
print("✅ Download button forced above overlay")
print("✅ ESC closes viewer")
print("✅ Outside click closes viewer")
print("✅ Viewer starts hidden")
print("✅ CSS cache-busted")
print()
print("Next:")
print("  node --check server.js")
print("  npm start")
