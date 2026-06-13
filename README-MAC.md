# Fast Video Downloader — macOS

> A desktop app to download and trim video & audio from 1000+ websites.  
> No browser extensions, no watermarks, no limits.

**Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)**

---

## What You Need

| Requirement | Minimum Version | Handled automatically |
|-------------|----------------|-----------------------|
| macOS       | 11 Big Sur+    |                       |
| Python      | 3.10+          | yes, via Homebrew     |
| Node.js     | 18+            | yes, via Homebrew     |
| FFmpeg      | any            | yes, via Homebrew     |
| Homebrew    | any            | yes                   |

Works on both Intel Macs and Apple Silicon (M1 / M2 / M3).

---

## Installation

### Step 1 — Open Terminal

Press **Cmd + Space**, type **Terminal**, press **Enter**.

---

### Step 2 — Go to This Folder

Type `cd ` (with a space after it), then drag this folder from Finder into the Terminal window and press **Enter**.

```
cd /path/to/fast-video-downloader-mac
```

---

### Step 3 — Run the Installer

```bash
chmod +x install-mac.sh && ./install-mac.sh
```

The first run downloads Homebrew, Python, Node.js, and FFmpeg. This takes about 5–15 minutes depending on your internet speed. You may be asked for your Mac login password — that is normal.

---

## Launching the App

After installation finishes, run this every time you want to open the app:

```bash
./start-desktop-app.sh
```

---

## Building a .dmg (Developers Only)

If you want to produce a standalone `.dmg` that anyone can install without needing Python or Node.js:

```bash
python3 package.py
```

This compiles the backend, bundles `ffmpeg` and `yt-dlp`, builds the frontend, and outputs the installer to `release/Fast Video Downloader-1.0.0.dmg`.

---

## How to Use

1. Paste a URL — YouTube, Vimeo, TikTok, Instagram, Twitter/X, Reddit, SoundCloud, Twitch, and 1000+ other sites
2. Click **Get Info** — the app fetches the title, thumbnail, and available qualities
3. Choose a quality — 4K, 1080p60, 1080p30, 720p, or Audio MP3
4. Set a range (optional) — enter start and end timestamps to download only a clip
5. Choose a folder — pick where to save the file
6. Click **Download**

### Settings (gear icon, top-right)

- **Browser Cookies** — import cookies from Chrome, Firefox, Safari, Edge, or Brave to access age-gated or login-walled content
- **Download Threads** — set 1–16 parallel streams
- **Custom User-Agent** — override the HTTP identity sent with requests

---

## Troubleshooting

### Permission denied when running a script

```bash
chmod +x install-mac.sh start-desktop-app.sh install-dependencies.sh
```

### macOS says the app is from an unidentified developer

1. Open **System Settings → Privacy & Security**
2. Scroll down and click **Open Anyway**
3. Click **Open** in the confirmation dialog

### App is damaged and can't be opened

```bash
xattr -cr "/Applications/Fast Video Downloader.app"
```

### Port 8000 already in use

```bash
lsof -ti:8000 | xargs kill -9
./start-desktop-app.sh
```

### Homebrew password prompt

Type your Mac login password and press **Enter**. Characters will not appear as you type — that is normal.

### brew not found after install on Apple Silicon

```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
```

---

## Files in This Package

| File | Purpose |
|------|---------|
| `install-mac.sh` | Run this first — sets up all dependencies |
| `start-desktop-app.sh` | Launches the app |
| `package.py` | Builds a distributable .dmg |
| `install-dependencies.sh` | Lightweight dependency check without auto-Homebrew |
| `backend/` | Python FastAPI server source |
| `frontend/` | React + Electron source |

---

## Credits

Built by **[NioKrishan](https://www.instagram.com/nightlander_krishan/)** using open-source tools:

| Tool | Role | License |
|------|------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Downloads video/audio from 1000+ sites | Unlicense |
| [FFmpeg](https://ffmpeg.org/) | Media trimming, muxing, and conversion | LGPL 2.1+ |
| [FastAPI](https://fastapi.tiangolo.com/) | Python backend API framework | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server | BSD |
| [Electron](https://www.electronjs.org/) | Desktop shell | MIT |
| [React](https://react.dev/) | UI framework | MIT |
| [Vite](https://vitejs.dev/) | Frontend build tool | MIT |
| [Tailwind CSS](https://tailwindcss.com/) | CSS framework | MIT |
| [electron-builder](https://www.electron.build/) | App packaging | MIT |
| [PyInstaller](https://pyinstaller.org/) | Python to standalone binary | GPL + exception |
| [browser-cookie3](https://github.com/borisbabic/browser_cookie3) | Cookie extraction | MIT |
| [Homebrew](https://brew.sh/) | macOS package manager | BSD 2-Clause |

---

## Legal

Fast Video Downloader is intended for personal use only. Always respect content creators' rights and the terms of service of the platforms you use. All bundled tools retain their original licenses.

---

*Fast Video Downloader — macOS Edition*  
*Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)*
