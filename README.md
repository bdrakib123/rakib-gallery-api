# rakib-gallery-api

Private Android Gallery API + mobile web viewer for Termux.

## Features

- Browse Android internal storage folders
- Images and videos
- Fullscreen image/video viewer
- Search
- Folder navigation
- Download files
- Password protection
- JSON API
- No file upload endpoint by default

## Termux setup

```bash
termux-setup-storage
pkg update
pkg install nodejs -y
cd rakib-gallery-api
npm install
cp .env.example .env
nano .env
npm start
```

Default local URL:

```text
http://127.0.0.1:3000
```

From another device on the same Wi-Fi, use the phone's LAN IP:

```text
http://PHONE-IP:3000
```

## Environment

```env
PORT=3000
GALLERY_ROOT=/storage/emulated/0
GALLERY_PASSWORD=change-this-password
HOST=0.0.0.0
```

Change `GALLERY_PASSWORD` before exposing the server outside your phone.

## API

```text
GET /api/health
GET /api/list?path=
GET /api/search?q=
GET /api/file?path=
```

The server prevents path traversal outside `GALLERY_ROOT`.

## Important

For an internet-accessible HTTPS URL, run this server on the phone and expose it through a secure tunnel/reverse proxy. Do not expose an unauthenticated gallery server directly to the public internet.
