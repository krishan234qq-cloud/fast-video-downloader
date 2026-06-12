# Fast Video Downloader

> A premium, zero-dependency desktop app to download and trim video & audio from 1000+ websites — no browser extensions, no watermarks, no limits.

**Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)**

---

## The Problem

Most video downloaders are either:
- Web-based tools that break constantly due to API changes
- Browser extensions that get removed from stores
- CLI tools that require technical knowledge to install and use
- Apps that bundle malware or show ads

**Fast Video Downloader** solves all of that — it's a clean native desktop app. Install it once, open it, paste a link, done. No terminal. No Python knowledge. No dependency hell.

---

## What It Does

- **Download from 1000+ websites** — YouTube, Vimeo, Twitter/X, Instagram, Reddit, TikTok, Twitch, SoundCloud,and thousands more via `yt-dlp`
- **Quality selection** — 4K, 1080p60, 1080p30, 720p, or audio-only MP3
- **Custom range trimmer** — download only a specific clip (e.g. 00:01:30 → 00:03:45) without downloading the full video first
- **Age-gated / login-walled content** — sync cookies directly from your browser (Chrome, Firefox, Edge, Brave, Opera, Safari, Vivaldi) to bypass restrictions
- **Custom User-Agent** — spoof your HTTP identity to bypass bot-blockers
- **Parallel download threads** — configurable 1–16 concurrent streams for maximum speed
- **Real-time download console** — watch the live progress log as fragments are fetched and merged
- **Native folder picker** — choose exactly where files are saved
- **Standalone installer** — ships with `ffmpeg` and `yt-dlp` bundled. No installs required on the target machine

---

## Features At a Glance

| Feature | Details |
|---|---|
| Supported sites | 1000+ via yt-dlp |
| Video qualities | 4K · 1080p60 · 1080p30 · 720p · Audio MP3 |
| Range trim | Server-side ffmpeg trim, no re-encode |
| Cookie auth | Chrome, Firefox, Edge, Brave, Opera, Safari, Vivaldi |
| Download threads | 1–16 parallel streams (configurable) |
| Custom User-Agent | Full HTTP identity spoofing |
| Progress | Live streaming SSE console |
| Destination | Native OS folder picker |
| Packaging | Windows EXE · macOS DMG · Linux AppImage |

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI Framework | React 19 + Vite |
| Styling | Tailwind CSS + custom glassmorphism CSS |
| Desktop Shell | Electron 42 |
| Backend API | FastAPI (Python) + Uvicorn |
| Downloader Engine | yt-dlp |
| Trimmer | ffmpeg |
| Packaging | PyInstaller + electron-builder |

---

## Project Structure

```
fast-video-downloader/
├── backend/
│   ├── main.py              # FastAPI server — /api/info, /api/download, /api/select-folder
│   ├── launcher.py          # Lightweight launcher on port 9999 (dev mode only)
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Entire UI — single component, ~800 lines
│   │   └── index.css        # Tailwind base + custom design tokens
│   ├── main.cjs             # Electron main process — spawns backend sidecar when packaged
│   ├── preload.cjs          # Electron preload (context bridge)
│   ├── index.html           # HTML entry point
│   ├── package.json         # Electron + electron-builder config
│   └── vite.config.js       # Vite dev server config (port 5174)
│
├── package.py               # One-command build script (Windows/Mac/Linux)
├── install-dependencies.bat # Windows dev setup
├── install-dependencies.sh  # macOS/Linux dev setup
├── start-desktop-app.bat    # Windows dev launcher
└── start-desktop-app.sh     # macOS/Linux dev launcher
```

---

## Running in Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- ffmpeg on system PATH

### Windows
```bat
install-dependencies.bat
start-desktop-app.bat
```

### macOS / Linux
```sh
chmod +x install-dependencies.sh start-desktop-app.sh
./install-dependencies.sh
./start-desktop-app.sh
```

The app will open as an Electron window. The React dev server runs on `http://localhost:5174` and the FastAPI backend on `http://localhost:8000`.

---

## Building the Standalone Installer

Run this once on the target OS (Windows builds on Windows, macOS on Mac, Linux on Linux):

```bash
python package.py
```

This script will automatically:
1. Install PyInstaller into the backend venv
2. Compile `backend/main.py` → `backend.exe` (or `backend` on Mac/Linux)
3. Copy the real `ffmpeg` binary from your system
4. Download the latest standalone `yt-dlp` binary from GitHub
5. Build the React frontend bundle
6. Package everything with `electron-builder`
7. Copy the final installer to `release/`

### Output

| Platform | Output |
|---|---|
| Windows | `release/Fast Video Downloader Setup 1.0.0.exe` (NSIS installer) |
| macOS | `release/Fast Video Downloader-1.0.0.dmg` |
| Linux | `release/Fast Video Downloader-1.0.0.AppImage` |

> **Note:** Add your custom icon to `frontend/build-resources/` before building:
> - `icon.ico` — Windows
> - `icon.icns` — macOS
> - `icon.png` — Linux

---

## How It Works

```
User pastes URL
      │
      ▼
React frontend (Electron)
      │  POST /api/info
      ▼
FastAPI backend
      │  yt-dlp (Python library) — extracts metadata, formats, thumbnail
      ▼
Video info returned → UI displays title, duration, quality options
      │
User clicks Download
      │  POST /api/download (SSE streaming response)
      ▼
FastAPI spawns yt-dlp subprocess
      │  streams stdout line-by-line → frontend console
      ▼
[If custom range] → ffmpeg trims the downloaded file locally
      │
Done → file saved to chosen folder
```

---

## Settings Panel

Open the ⚙️ gear icon in the top-right corner to configure:

- **Browser Cookies Sync** — select your browser to import session cookies (bypasses age gates, login walls, adult site restrictions)
- **Download Speed (Threads)** — set 1–16 parallel download streams
- **Custom Network Identity** — override the HTTP User-Agent string

All settings are persisted in `localStorage` and sent with every request.

---

## Credits

Built by **[NioKrishan](https://www.instagram.com/nightlander_krishan/)** using open-source tools:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — the downloader engine
- [ffmpeg](https://ffmpeg.org/) — media trimming and muxing
- [FastAPI](https://fastapi.tiangolo.com/) — Python backend
- [Electron](https://www.electronjs.org/) — desktop shell
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) — UI framework
- [Tailwind CSS](https://tailwindcss.com/) — styling
- [electron-builder](https://www.electron.build/) — cross-platform packaging
- [PyInstaller](https://pyinstaller.org/) — Python → standalone binary

---

*Fast Video Downloader is intended for personal use only. Always respect content creators' rights and platform terms of service.*
