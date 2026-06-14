# Future Enhancements Roadmap

This document outlines the plans and technical implementation guidelines for future features.

---

## 1. GPU Auto-Detection with CPU Fallback (Fast Encoding)

### Goal
Utilize hardware-accelerated video encoding to decrease encoding times for large videos by offloading the task to the GPU (NVIDIA, Intel QSV, AMD AMF, or macOS VideoToolbox), with a fallback to CPU `ultrafast` encoding.

### Implementation Blueprint
Modify `_reencode_to_universal` in `backend/main.py` to probe for hardware acceleration capability before falling back to CPU.

```python
def _get_hardware_encoder(ffmpeg_path: str) -> str:
    try:
        res = subprocess.run(
            [ffmpeg_path, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        encoders = res.stdout.lower()
        if "h264_nvenc" in encoders:
            return "h264_nvenc"
        if "h264_qsv" in encoders:
            return "h264_qsv"
        if "h264_amf" in encoders:
            return "h264_amf"
        if "h264_videotoolbox" in encoders:
            return "h264_videotoolbox"
    except Exception:
        pass
    return "libx264"
```

Integrate this into the FFmpeg command generation:
- If a hardware encoder is found (e.g. `h264_nvenc`), use it:
  `cmd = [ffmpeg_path, "-y", "-i", input_path, "-vcodec", hw_encoder, "-pix_fmt", "yuv420p", "-acodec", "aac", "-b:a", "192k", output_path]`
- If no hardware encoder is found, use CPU with the fastest preset:
  `cmd = [ffmpeg_path, "-y", "-i", input_path, "-vcodec", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", "-acodec", "aac", "-b:a", "192k", output_path]`

---

## 2. Adding a 2K Quality Option

### Goal
Provide users with an export quality option of 2K (1440p) resolution.

### Implementation Blueprint

1. **Frontend Update (`frontend/src/App.jsx`)**:
   Add the 2K option to the `QUALITY_OPTIONS` array:
   ```javascript
   { id: '2k', label: '2K', fps: '30fps', tag: 'QHD', audio: false }
   ```

2. **Backend Update (`backend/main.py`)**:
   - Add the format mapping to `QUALITY_FORMAT_MAP`:
     ```python
     "2k": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best"
     ```
   - Update `extract_quality_details` target height mapping:
     ```python
     target_height = {"4k": 2160, "2k": 1440, "1080p60": 1080, "1080p30": 1080, "720p": 720}.get(quality_id)
     ```

---

## 3. Free Auto-Update System

### Goal
Distribute application updates seamlessly without requiring manual ZIP downloads.

### Implementation Options

#### Option A: Electron-Builder + GitHub Releases (Standard & Easiest)
Use `electron-updater` package to pull updates directly from public GitHub releases.
1. Install `electron-updater` in the frontend app.
2. Configure `publish` provider in `frontend/package.json`:
   ```json
   "build": {
     "publish": {
       "provider": "github",
       "owner": "krishan234qq-cloud",
       "repo": "fast-video-downloader"
     }
   }
   ```
3. Initialize the update check in Electron's main process:
   ```javascript
   const { autoUpdater } = require("electron-updater");
   autoUpdater.checkForUpdatesAndNotify();
   ```

#### Option B: Launcher-Based Update Check
Have the app's startup launcher script check a static JSON file hosted on GitHub pages (e.g. `https://krishan234qq-cloud.github.io/fast-video-downloader/version.json`).
1. If the remote version is greater than the local version, download the new installer URL.
2. Run the installer silently in the background and relaunch the application.
