# 📸 Rakib Gallery

A lightweight personal Android Gallery Web App built with Node.js + Express.

## ✨ Features

- 📂 File-manager style Gallery
- 🖼️ Image preview
- 🎥 Video preview
- 📁 Folder navigation
- 🔍 File search
- 📥 File download
- 📊 File size and date information
- 🕘 Private History Vault
- 🔐 Separate History password
- 📱 Device-specific browsing history
- ⚡ Lightweight Express server
- 📱 Android / Termux friendly
- 🛡️ Path traversal protection
- 🚫 No password required for normal Gallery

## 🚀 Installation

    git clone <YOUR-REPOSITORY-URL>
    cd rakib-gallery-api
    npm install

## ⚙️ Configuration

Create a .env file:

    PORT=3000
    ROOT=/sdcard
    HISTORY_PASSWORD=your-strong-password

Change HISTORY_PASSWORD to your own strong password.

## ▶️ Start

    npm start

Open:

    http://127.0.0.1:3000

For LAN access:

    http://YOUR-PHONE-IP:3000

## 🗂️ Supported Images

- JPG
- JPEG
- PNG
- GIF
- WEBP
- BMP
- HEIC
- HEIF
- AVIF

## 🎥 Supported Videos

- MP4
- MKV
- WEBM
- MOV
- AVI
- M4V
- 3GP

## 🔐 History Vault

Normal Gallery browsing does not require a password.

History is protected separately using HISTORY_PASSWORD.

History is also separated by browser/device ID.

Each browser generates its own device ID and stores it locally.

## 🛡️ Security

The server includes path traversal protection.

For public internet access:

- Use HTTPS.
- Use a strong History password.
- Avoid directly exposing port 3000.
- Prefer a secure tunnel or reverse proxy.
- Do not store highly sensitive files in a public gallery.

## 📱 Android / Termux

Example:

    pkg update
    pkg install nodejs
    termux-setup-storage
    cd ~/rakib-gallery-api
    npm install
    npm start

The default gallery root is /sdcard.

## 🧪 Health Check

    curl http://127.0.0.1:3000/api/health

## 🧰 Development

Check server syntax:

    node --check server.js

Check Git formatting:

    git diff --check

## 📁 Project Structure

    rakib-gallery-api/
    ├── public/
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    ├── server.js
    ├── package.json
    ├── package-lock.json
    ├── .env
    ├── history.json
    ├── README.md
    ├── LICENSE
    └── .gitignore

## 📜 License

This project is released under the MIT License.

See LICENSE for details.

## 👤 Author

Rakib Hasan

Personal Android / Termux Gallery project.

---

 If you find this project useful, consider giving it a star on GitHub.
