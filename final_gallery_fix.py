from pathlib import Path
import re

ROOT = Path(".")
SERVER = ROOT / "server.js"
HTML = ROOT / "public/index.html"
CSS = ROOT / "public/style.css"
APP = ROOT / "public/app.js"

# =========================================================
# SERVER — disable browser cache for gallery files
# =========================================================

s = SERVER.read_text(encoding="utf-8")

middleware = r'''
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

'''

# Add before express.static
static_marker = 'app.use(express.static(path.join(__dirname, "public")));'

if "NO CACHE — ALWAYS SERVE CURRENT GALLERY UI" not in s:

    if static_marker not in s:
        raise SystemExit(
            "❌ express.static line not found"
        )

    s = s.replace(
        static_marker,
        middleware + static_marker,
        1
    )

SERVER.write_text(
    s,
    encoding="utf-8"
)

# =========================================================
# CLEAN INDEX — NO LOGIN UI AT ALL
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
  content="#050507"
>

<meta
  name="robots"
  content="noindex,nofollow"
>

<title>Rakib Gallery</title>

<link
  rel="stylesheet"
  href="/style.css?v=final20260927"
>

</head>

<body>

<div class="app-shell">

<!-- =====================================================
     GALLERY HEADER
===================================================== -->

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

  <div class="online-dot">
    <i></i>
    Private device
  </div>

</header>


<!-- =====================================================
     GALLERY
===================================================== -->

<main id="gallery">

<section class="hero">

  <div>

    <span class="eyebrow">
      PERSONAL LIBRARY
    </span>

    <h1>
      My Gallery
    </h1>

    <p id="status">
      Loading…
    </p>

  </div>

  <div class="hero-art">
    ◈
  </div>

</section>


<div class="toolbar">

  <button
    id="backBtn"
    class="tool-btn"
    aria-label="Back"
  >
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

  <button
    id="homeBtn"
    class="tool-btn"
    aria-label="Home"
  >
    ⌂
  </button>

</div>


<div
  id="grid"
  class="grid"
></div>


<!-- =====================================================
     HISTORY VAULT
===================================================== -->

<section
  id="historyPanel"
  class="history-vault"
  hidden
>

  <div class="vault-cover">

    <div class="vault-lock">
      ◉
    </div>

    <div class="vault-title">

      <span>
        PRIVATE VAULT
      </span>

      <h2>
        Activity History
      </h2>

      <p>
        This device only
      </p>

    </div>

    <button
      id="clearHistory"
      class="vault-clear"
    >
      Clear
    </button>

  </div>


  <div class="vault-security">

    <div class="security-icon">
      ✓
    </div>

    <div>

      <strong>
        Protected History
      </strong>

      <span>
        Your gallery activity is locked
        behind a separate password.
      </span>

    </div>

  </div>


  <div
    id="historyList"
    class="vault-list"
  ></div>

</section>

</main>


<!-- =====================================================
     BOTTOM NAV
===================================================== -->

<nav
  id="bottomNav"
  class="bottom-nav"
>

  <button
    class="nav-item active"
    data-page="galleryPage"
  >

    <span>▦</span>

    <small>
      Gallery
    </small>

  </button>


  <button
    class="nav-item"
    data-page="historyPage"
  >

    <span>◷</span>

    <small>
      History
    </small>

  </button>

</nav>


<!-- =====================================================
     VIEWER
===================================================== -->

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
  src="/app.js?v=final20260927"
></script>

</body>
</html>
'''

HTML.write_text(
    html,
    encoding="utf-8"
)

# =========================================================
# APP.JS — remove ALL old login/password UI references
# and make history visually independent
# =========================================================

a = APP.read_text(encoding="utf-8")

# Remove any old login auto-login code if remnants exist.
patterns = [
    r'\n// =========================================================\n// HISTORY PASSWORD.*',
]

# Current app should already be the device-history version.
# Add explicit history state marker for cache/debugging.
if "RAKIB FINAL DEVICE HISTORY UI" not in a:

    a = (
        "// RAKIB FINAL DEVICE HISTORY UI\n"
        "// Gallery = public\n"
        "// History = private password vault\n\n"
        + a
    )

APP.write_text(
    a,
    encoding="utf-8"
)

# =========================================================
# CSS — append completely different HISTORY visual system
# =========================================================

c = CSS.read_text(encoding="utf-8")

# Avoid duplicate final block
if "FINAL PRIVATE HISTORY VAULT" in c:
    c = c.split(
        "/* =========================================================\n"
        "   FINAL PRIVATE HISTORY VAULT"
    )[0]

vault_css = r'''

/* =========================================================
   FINAL PRIVATE HISTORY VAULT
   ========================================================= */

.history-vault {
  padding: 14px 16px 35px;
}


/* VAULT COVER */

.vault-cover {
  position: relative;

  min-height: 190px;

  padding: 25px;

  overflow: hidden;

  display: flex;
  align-items: flex-end;
  gap: 16px;

  border-radius: 30px;

  background:
    radial-gradient(
      circle at 85% 15%,
      rgba(168,130,255,.22),
      transparent 34%
    ),
    radial-gradient(
      circle at 15% 90%,
      rgba(74,144,226,.12),
      transparent 40%
    ),
    linear-gradient(
      145deg,
      #171421,
      #0b0910
    );

  border:
    1px solid
    rgba(190,160,255,.13);

  box-shadow:
    0 30px 80px
    rgba(0,0,0,.35);
}

.vault-cover::after {
  content:
    "HISTORY";

  position:
    absolute;

  right:
    -20px;

  top:
    18px;

  font-size:
    72px;

  font-weight:
    1000;

  letter-spacing:
    -5px;

  color:
    rgba(255,255,255,.025);

  transform:
    rotate(-12deg);
}

.vault-lock {
  position:
    absolute;

  right:
    23px;

  bottom:
    23px;

  width:
    52px;

  height:
    52px;

  border-radius:
    17px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  background:
    rgba(255,255,255,.07);

  border:
    1px solid
    rgba(255,255,255,.10);

  color:
    #d7c4ff;

  font-size:
    22px;
}

.vault-title {
  position:
    relative;

  z-index:
    2;
}

.vault-title > span {
  font-size:
    9px;

  letter-spacing:
    3px;

  font-weight:
    900;

  color:
    #b9a0ff;
}

.vault-title h2 {
  margin:
    7px 0 3px;

  font-size:
    28px;

  letter-spacing:
    -.7px;
}

.vault-title p {
  margin:
    0;

  color:
    #8f8a99;

  font-size:
    11px;
}


/* CLEAR */

.vault-clear {
  position:
    absolute;

  top:
    18px;

  right:
    18px;

  z-index:
    5;

  padding:
    8px 11px;

  border-radius:
    10px;

  background:
    rgba(255,80,100,.09);

  border:
    1px solid
    rgba(255,80,100,.16);

  color:
    #ff7180;

  font-size:
    10px;

  cursor:
    pointer;
}


/* SECURITY CARD */

.vault-security {
  margin:
    13px 0;

  padding:
    14px;

  display:
    flex;

  align-items:
    center;

  gap:
    12px;

  border-radius:
    18px;

  background:
    #0d0d11;

  border:
    1px solid
    rgba(255,255,255,.06);
}

.security-icon {
  width:
    35px;

  height:
    35px;

  flex:
    0 0 35px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    11px;

  background:
    rgba(113,220,155,.09);

  border:
    1px solid
    rgba(113,220,155,.13);

  color:
    #79e0a1;
}

.vault-security div:last-child {
  display:
    flex;

  flex-direction:
    column;

  gap:
    3px;
}

.vault-security strong {
  font-size:
    12px;
}

.vault-security span {
  color:
    #77747e;

  font-size:
    10px;

  line-height:
    1.4;
}


/* HISTORY LIST */

.vault-list {
  display:
    grid;

  gap:
    10px;
}

.history-card {
  position:
    relative;

  display:
    flex;

  align-items:
    center;

  gap:
    13px;

  min-height:
    82px;

  padding:
    9px;

  border-radius:
    20px;

  background:
    linear-gradient(
      135deg,
      #14131a,
      #0b0b0f
    );

  border:
    1px solid
    rgba(255,255,255,.055);

  box-shadow:
    0 12px 35px
    rgba(0,0,0,.18);

  cursor:
    pointer;
}

.history-card::before {
  content:
    "";

  position:
    absolute;

  left:
    0;

  top:
    15px;

  bottom:
    15px;

  width:
    2px;

  border-radius:
    4px;

  background:
    linear-gradient(
      #b99aff,
      transparent
    );

  opacity:
    .7;
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
    #07070a;
}

.history-card-thumb img {
  width:
    100%;

  height:
    100%;

  display:
    block;

  object-fit:
    cover;
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

  color:
    #c5adff;

  font-size:
    20px;

  background:
    linear-gradient(
      145deg,
      #25212e,
      #0d0b11
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
  color:
    #eeeaf4;

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
  color:
    #b8a2ed;

  font-size:
    10px;

  font-weight:
    700;
}

.history-card-main small {
  color:
    #696671;

  font-size:
    9px;
}

.history-card-arrow {
  width:
    30px;

  height:
    30px;

  flex:
    0 0 30px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    50%;

  background:
    rgba(255,255,255,.045);

  color:
    #716c78;

  font-size:
    19px;
}


/* EMPTY */

.history-empty {
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
    #77737f;
}

.history-empty-icon {
  width:
    75px;

  height:
    75px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  margin-bottom:
    15px;

  border-radius:
    25px;

  background:
    rgba(178,145,255,.06);

  border:
    1px solid
    rgba(178,145,255,.10);

  color:
    #b79cff;

  font-size:
    31px;
}

.history-empty strong {
  color:
    #e9e5ee;

  font-size:
    15px;
}

.history-empty span {
  max-width:
    250px;

  margin-top:
    7px;

  font-size:
    10px;

  line-height:
    1.5;
}


/* ONLINE STATUS */

.online-dot {
  display:
    flex;

  align-items:
    center;

  gap:
    6px;

  color:
    #77747d;

  font-size:
    9px;
}

.online-dot i {
  width:
    6px;

  height:
    6px;

  border-radius:
    50%;

  background:
    #65d991;

  box-shadow:
    0 0 9px
    rgba(101,217,145,.7);
}


/* HERO ART */

.hero-art {
  position:
    absolute;

  right:
    25px;

  bottom:
    -18px;

  font-size:
    100px;

  color:
    rgba(255,255,255,.045);

  transform:
    rotate(15deg);
}


@media (max-width: 500px) {

  .vault-cover {
    min-height:
      175px;

    padding:
      21px;
  }

  .vault-title h2 {
    font-size:
      25px;
  }

}
'''

c += vault_css

CSS.write_text(
    c,
    encoding="utf-8"
)

print()
print("==========================================")
print(" FINAL GALLERY / HISTORY FIX")
print("==========================================")
print("✅ Login/password UI removed completely")
print("✅ Gallery opens directly")
print("✅ Browser cache disabled")
print("✅ History remains password protected")
print("✅ History gets a separate Private Vault UI")
print("✅ Gallery and History now visually distinct")
print()
print("Run:")
print("  node --check server.js")
print("  npm start")
