#!/usr/bin/env python3

import os
import sys
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests


# ============================================================
# CONFIG
# ============================================================

SERVER = os.environ.get(
    "RAKIB_GALLERY_URL",
    "https://rakib-gallery-api6.onrender.com"
).rstrip("/")

STORAGE = Path(
    os.environ.get(
        "RAKIB_GALLERY_STORAGE",
        "/storage/emulated/0"
    )
)

STATE_FILE = Path.home() / ".rakib_gallery_sync.json"

SYNC_INTERVAL = int(
    os.environ.get("RAKIB_GALLERY_INTERVAL", "60")
)

MAX_FILE_SIZE = 500 * 1024 * 1024

SKIP_DIRS = {
    ".thumbnails",
    ".cache",
    "Android/data",
    "Android/obb",
}


# ============================================================
# STATE
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(
            STATE_FILE.read_text()
        )
    except Exception:
        return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2
        )
    )


# ============================================================
# PATH HELPERS
# ============================================================

def normalize_path(path):
    return str(path).replace("\\", "/").lstrip("/")


def should_skip(path):
    text = str(path).replace("\\", "/")

    for skip in SKIP_DIRS:
        if skip in text:
            return True

    return False


# ============================================================
# PAIR DEVICE
# ============================================================

def pair(code):

    print()
    print("🔗 Pairing with Rakib Gallery...")
    print("Server:", SERVER)
    print()

    try:
        response = requests.post(
            SERVER + "/api/device/pair/claim",
            json={
                "code": str(code).strip()
            },
            timeout=30
        )
    except Exception as e:
        print("❌ Connection error:", e)
        return False

    try:
        data = response.json()
    except Exception:
        print("❌ Invalid server response")
        print(response.text[:500])
        return False

    if not response.ok or not data.get("ok"):
        print(
            "❌ Pairing failed:",
            data.get("error", "Unknown error")
        )
        return False

    state = {
        "server": SERVER,
        "deviceId": data["device"]["id"],
        "deviceName": data["device"]["name"],
        "token": data["token"],
        "pairedAt": int(time.time()),
        "files": {}
    }

    save_state(state)

    print()
    print("✅ Pairing successful!")
    print()
    print("Device :", state["deviceName"])
    print("ID     :", state["deviceId"])
    print("State  :", STATE_FILE)
    print()

    return True


# ============================================================
# SCAN FILES
# ============================================================

# Only these Android storage folders are synced.
ALLOWED_ROOTS = {
    "DCIM",
    "Pictures",
    "Movies",
    "Videos",
    "Music",
    "Download",
    "Documents",
}

# Media/document extensions allowed inside those folders.
ALLOWED_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".webp",
    ".gif", ".bmp", ".heic", ".heif",
    ".avif", ".tif", ".tiff",

    # Videos
    ".mp4", ".mkv", ".webm", ".mov",
    ".avi", ".m4v", ".3gp", ".ts",

    # Audio
    ".mp3", ".m4a", ".aac", ".wav",
    ".flac", ".ogg", ".opus",

    # Documents
    ".pdf", ".txt", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx",

    # Common archives occasionally kept in Download
    ".zip", ".rar", ".7z",
}


def is_allowed_file(path):
    """
    Allow only useful gallery/media/document files.
    APKs, databases, logs, cache files, etc. are ignored.
    """

    name = path.name.lower()
    suffix = path.suffix.lower()

    # Hidden/system files
    if name.startswith("."):
        return False

    # Explicit unwanted files
    blocked_extensions = {
        ".apk",
        ".apks",
        ".xapk",
        ".aab",
        ".exe",
        ".msi",
        ".bat",
        ".sh",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".log",
        ".tmp",
        ".cache",
        ".bak",
        ".bin",
        ".nomedia",
    }

    if suffix in blocked_extensions:
        return False

    return suffix in ALLOWED_EXTENSIONS


def scan_files():

    if not STORAGE.exists():
        print(
            "❌ Android storage not found:",
            STORAGE
        )
        return []

    files = []

    for root_name in sorted(ALLOWED_ROOTS):

        root = STORAGE / root_name

        if not root.exists():
            continue

        print(
            f"📂 Scanning {root_name}/ ..."
        )

        for current_root, dirs, filenames in os.walk(root):

            current_path = Path(current_root)

            # Never descend into hidden directories.
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
            ]

            for filename in filenames:

                path = current_path / filename

                try:

                    if not path.is_file():
                        continue

                    if should_skip(path):
                        continue

                    if not is_allowed_file(path):
                        continue

                    files.append(path)

                except OSError:
                    continue

    # Optional extra screenshot folder
    screenshot_dirs = [
        STORAGE / "Screenshots",
        STORAGE / "ScreenRecorder",
    ]

    for root in screenshot_dirs:

        if not root.exists():
            continue

        print(
            f"📂 Scanning {root.name}/ ..."
        )

        for current_root, dirs, filenames in os.walk(root):

            current_path = Path(current_root)

            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
            ]

            for filename in filenames:

                path = current_path / filename

                try:

                    if (
                        path.is_file()
                        and not path.name.startswith(".")
                        and is_allowed_file(path)
                    ):
                        files.append(path)

                except OSError:
                    continue

    # Remove duplicates while preserving order.
    unique = []
    seen = set()

    for path in files:

        key = str(path)

        if key in seen:
            continue

        seen.add(key)
        unique.append(path)

    return unique


# ============================================================
# UPLOAD
# ============================================================

def upload_file(session, token, path):

    try:
        relative = normalize_path(
            path.relative_to(STORAGE)
        )

        size = path.stat().st_size

    except (OSError, ValueError):
        return False

    if size > MAX_FILE_SIZE:
        print(
            "⚠️ Skipping large file:",
            relative
        )
        return False

    headers = {
        "x-device-token": token,
        "x-file-path": quote(
            relative,
            safe="/"
        )
    }

    try:

        with path.open("rb") as file:

            response = session.put(
                SERVER + "/api/sync/file",
                headers=headers,
                data=file,
                timeout=300
            )

        if response.ok:

            print(
                "⬆️",
                relative,
                f"({size / 1024 / 1024:.1f} MB)"
            )

            return True

        print(
            "❌ Upload failed:",
            relative,
            response.status_code,
            response.text[:200]
        )

    except Exception as e:

        print(
            "❌ Upload error:",
            relative,
            e
        )

    return False


# ============================================================
# ONE SYNC
# ============================================================

def sync_once():

    state = load_state()

    token = state.get("token")

    if not token:

        print()
        print("❌ Device is not paired.")
        print()
        print("Use:")
        print("python3 sync.py --pair CODE")
        print()

        return False

    session = requests.Session()

    files = scan_files()

    print()
    print(
        f"📱 Found {len(files)} files"
    )
    print()

    uploaded = 0

    known_files = state.setdefault(
        "files",
        {}
    )

    for path in files:

        try:

            relative = normalize_path(
                path.relative_to(STORAGE)
            )

            stat = path.stat()

            current = {
                "size": stat.st_size,
                "mtime": stat.st_mtime_ns
            }

            old = known_files.get(relative)

            if old == current:
                continue

            if upload_file(
                session,
                token,
                path
            ):

                known_files[relative] = current

                save_state(state)

                uploaded += 1

        except (
            FileNotFoundError,
            PermissionError,
            OSError
        ):
            continue

    save_state(state)

    print()
    print(
        f"✅ Sync complete | uploaded: {uploaded}"
    )
    print()

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) >= 3:

        if sys.argv[1] == "--pair":

            pair(sys.argv[2])
            return

    if "--once" in sys.argv:

        sync_once()
        return

    print()
    print("╔══════════════════════════════════════╗")
    print("║       RAKIB GALLERY SYNC             ║")
    print("╚══════════════════════════════════════╝")
    print()

    print("Server :", SERVER)
    print("Storage:", STORAGE)
    print("Every  :", SYNC_INTERVAL, "seconds")
    print()

    while True:

        try:

            sync_once()

        except KeyboardInterrupt:

            print()
            print("👋 Sync stopped.")
            break

        except Exception as e:

            print(
                "❌ Sync error:",
                e
            )

        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()

