# Fast Video Downloader — macOS

> Download and trim video & audio from 1000+ websites.  
> No browser extensions, no watermarks, no limits.

**Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)**

---

## Installing the App

This package includes a ready-to-install `.dmg`. No Python, no Node.js, no Homebrew — nothing extra required.

1. Open the `release/` folder in this ZIP
2. Double-click `Fast Video Downloader-1.0.0.dmg`
3. Drag **Fast Video Downloader** into your **Applications** folder
4. Open **Finder → Applications**, find the app, right-click it and choose **Open**

That's it. The app opens and you're ready to use it.

Works on both Intel Macs and Apple Silicon (M1 / M2 / M3).

---

### First Launch Warning

On first open, macOS may say the app is from an unidentified developer. This is normal for apps distributed outside the Mac App Store.

- Click **Cancel** on the first warning
- Go to **System Settings → Privacy & Security**, scroll down, click **Open Anyway**
- Click **Open** in the confirmation dialog

Or run this once in Terminal if you see "App is damaged":

```bash
xattr -cr "/Applications/Fast Video Downloader.app"
```

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

### The app doesn't open / "unidentified developer"

1. Open **System Settings → Privacy & Security**
2. Scroll down and click **Open Anyway**
3. Click **Open**

### "App is damaged and can't be opened"

```bash
xattr -cr "/Applications/Fast Video Downloader.app"
```

---

## For Developers — Running from Source

If you want to run the app from source code or build your own `.dmg`, you will need Python 3.10+, Node.js 18+, and FFmpeg. Use the included installer script to set everything up automatically:

```bash
chmod +x install-mac.sh && ./install-mac.sh
```

Then launch in dev mode:

```bash
./start-desktop-app.sh
```

To build a new `.dmg`:

```bash
python3 package.py
```

Output goes to `release/Fast Video Downloader-1.0.0.dmg`.

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

---

## Legal

Fast Video Downloader is intended for personal use only. Always respect content creators' rights and the terms of service of the platforms you use. All bundled tools retain their original licenses.

---

*Fast Video Downloader — macOS Edition*  
*Made by [NioKrishan](https://www.instagram.com/nightlander_krishan/)*
