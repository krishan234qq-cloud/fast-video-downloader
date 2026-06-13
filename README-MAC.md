# 🍎 Fast Video Downloader — macOS Edition

> A premium, zero-dependency desktop app to download and trim video & audio  
> from 1000+ websites — no browser extensions, no watermarks, no limits.

**Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)**

---

## ✅ What You Need (Before You Start)

| Requirement | Minimum Version | The installer handles it for you |
|-------------|----------------|----------------------------------|
| macOS       | 11 Big Sur+    | —                                |
| Python      | 3.10+          | ✅ Auto-installed via Homebrew   |
| Node.js     | 18+            | ✅ Auto-installed via Homebrew   |
| FFmpeg      | Any            | ✅ Auto-installed via Homebrew   |
| Homebrew    | Any            | ✅ Auto-installed                |

> **Works on both Intel Macs and Apple Silicon (M1 / M2 / M3)**

---

## 🚀 Installation — 3 Steps

### Step 1 — Open Terminal

Press **⌘ + Space**, type **Terminal**, press **Enter**.

---

### Step 2 — Go to This Folder

In Terminal, type `cd ` (with a space after), then **drag this folder** from Finder  
into the Terminal window. Press **Enter**.

```
cd /path/to/fast-video-downloader-mac
```

---

### Step 3 — Run the One-Click Installer

Copy and paste this into Terminal, then press **Enter**:

```bash
chmod +x install-mac.sh && ./install-mac.sh
```

> ⏳ The first run downloads Homebrew, Python, Node.js, and FFmpeg.  
> This takes **5–15 minutes** depending on your internet speed.  
> You may be asked for your Mac **login password** — that's normal and safe.

---

## ▶️ Launching the App

After installation completes, run this every time you want to open the app:

```bash
./start-desktop-app.sh
```

The **Fast Video Downloader** window will open automatically.

---

## 📦 Building a Distributable .dmg (Developers Only)

Want to make a standalone `.dmg` you can share with others (they won't need  
Python or Node.js installed)?

```bash
python3 package.py
```

This will:
1. Compile the Python backend → standalone binary (no Python needed by users)
2. Bundle `ffmpeg` + `yt-dlp` inside the app
3. Build the React/Electron frontend
4. Output: `release/Fast Video Downloader-1.0.0.dmg`

Share that single `.dmg` file — **no technical setup required for the recipient**.

---

## 🎬 How to Use the App

1. **Paste a URL** — any YouTube, Vimeo, TikTok, Instagram, Twitter/X, Reddit,  
   SoundCloud, Twitch, or 1000+ other site link
2. **Click "Get Info"** — the app fetches the title, thumbnail, and available qualities
3. **Choose Quality** — 4K, 1080p60, 1080p30, 720p, or Audio MP3
4. **Set Range (optional)** — enter start/end timestamps to download only a clip
5. **Choose Folder** — pick where to save the file
6. **Click Download** — watch the live progress log

### ⚙️ Settings (gear icon, top-right)
- **Browser Cookies** — sync cookies from Chrome/Firefox/Safari/Edge/Brave to  
  bypass age gates and login-walled content
- **Download Threads** — set 1–16 parallel streams for maximum speed
- **Custom User-Agent** — spoof your browser identity to bypass bot-blockers

---

## 🔧 Troubleshooting

### "Permission denied" error
```bash
chmod +x install-mac.sh start-desktop-app.sh install-dependencies.sh
```

### macOS says "app can't be opened because it's from an unidentified developer"
1. Go to **System Settings → Privacy & Security**
2. Scroll down and click **"Open Anyway"**
3. Click **Open** in the confirmation dialog

### "App is damaged and can't be opened"
```bash
xattr -cr "/Applications/Fast Video Downloader.app"
```

### Port 8000 already in use
```bash
lsof -ti:8000 | xargs kill -9
./start-desktop-app.sh
```

### Homebrew install asks for password
Type your Mac login password — characters won't appear as you type (that's normal). Press **Enter** when done.

### Apple Silicon (M1/M2/M3) — "brew not found" after install
```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
```

---

## 📁 Files in This Package

| File | What it does |
|------|-------------|
| `install-mac.sh` | **Run this first** — installs all dependencies automatically |
| `start-desktop-app.sh` | Launches the app in development mode |
| `package.py` | Builds a distributable `.dmg` installer |
| `install-dependencies.sh` | Lightweight dependency check (no auto-Homebrew install) |
| `backend/` | Python FastAPI server source code |
| `frontend/` | React + Electron source code |

---

## 💡 Credits

Built by **[NioKrishan](https://www.instagram.com/nightlander_krishan/)** using these incredible open-source tools:

| Tool | Role | License |
|------|------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Downloads video/audio from 1000+ sites | Unlicense |
| [FFmpeg](https://ffmpeg.org/) | Media trimming, muxing, and conversion | LGPL 2.1+ |
| [FastAPI](https://fastapi.tiangolo.com/) | Python backend API framework | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server for the backend | BSD |
| [Electron](https://www.electronjs.org/) | Cross-platform desktop shell | MIT |
| [React](https://react.dev/) | UI component framework | MIT |
| [Vite](https://vitejs.dev/) | Frontend build tool | MIT |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first CSS framework | MIT |
| [electron-builder](https://www.electron.build/) | Cross-platform app packaging | MIT |
| [PyInstaller](https://pyinstaller.org/) | Python → standalone binary | GPL + exception |
| [browser-cookie3](https://github.com/borisbabic/browser_cookie3) | Cookie extraction from browsers | MIT |
| [Homebrew](https://brew.sh/) | macOS package manager | BSD 2-Clause |

---

## 📜 License & Legal

Fast Video Downloader is intended for **personal use only**.  
Always respect content creators' rights and the terms of service of the platforms you use.

The app itself is provided as-is, without warranty.  
All bundled tools retain their original licenses (see table above).

---

*Fast Video Downloader — macOS Edition*  
*Made with ❤️ by [NioKrishan](https://www.instagram.com/nightlander_krishan/)*
