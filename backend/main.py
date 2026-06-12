from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import yt_dlp
import os
import json
import subprocess
import sys
import tkinter
import tkinter.filedialog

app = FastAPI()

IS_FROZEN = getattr(sys, 'frozen', False)
if IS_FROZEN:
    BASE_BIN_DIR = os.path.dirname(sys.executable)
else:
    BASE_BIN_DIR = os.path.dirname(os.path.abspath(__file__))

def get_ffmpeg_path():
    if IS_FROZEN:
        p = os.path.join(BASE_BIN_DIR, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if os.path.exists(p):
            return p
    return "ffmpeg"

def get_ytdlp_command():
    if IS_FROZEN:
        p = os.path.join(BASE_BIN_DIR, "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
        if os.path.exists(p):
            return [p]
    return [sys.executable, "-m", "yt_dlp"]


@app.get("/health")
async def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUALITY_FORMAT_MAP = {
    "4k":      "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best",
    "1080p60": "bestvideo[height<=1080][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080][fps>=60]+bestaudio/best",
    "1080p30": "bestvideo[height<=1080][fps<=30][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
    "720p":    "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
    "audio":   "bestaudio[ext=m4a]/bestaudio",
}


def seconds_to_hhmmss(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def hhmmss_to_seconds(t: str) -> int:
    parts = t.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return int(parts[0])


def extract_quality_details(formats, quality_id, duration_secs=0):
    if not formats:
        return {"resolution": "Unknown", "size": "N/A", "codec": "Unknown"}

    if quality_id == "audio":
        audio_candidates = [
            f for f in formats
            if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
        ]
        if not audio_candidates:
            audio_candidates = [f for f in formats if f.get("acodec") not in (None, "none")]

        if not audio_candidates:
            return {"resolution": "Audio Only", "size": "N/A", "codec": "AUDIO"}

        best_audio = max(audio_candidates, key=lambda f: f.get("abr") or f.get("tbr") or 0)
        acodec = (best_audio.get("acodec") or "").split(".")[0].upper()

        size_str = "N/A"
        filesize = best_audio.get("filesize") or best_audio.get("filesize_approx")
        if not filesize and best_audio.get("tbr") and duration_secs:
            filesize = int((best_audio.get("tbr") * 1000 * duration_secs) / 8)
        if filesize:
            size_str = f"{filesize / (1024 * 1024):.1f} MB"

        return {
            "resolution": "Audio Only",
            "size": size_str,
            "codec": acodec if acodec else "AUDIO"
        }

    target_height = {"4k": 2160, "1080p60": 1080, "1080p30": 1080, "720p": 720}.get(quality_id)
    target_fps_min = 60 if quality_id == "1080p60" else None
    target_fps_max = 30 if quality_id == "1080p30" else None

    video_candidates = [f for f in formats if f.get("vcodec") not in (None, "none")]
    if not video_candidates:
        return {"resolution": "Unknown", "size": "N/A", "codec": "Unknown"}

    if target_height:
        filtered = [f for f in video_candidates if (f.get("height") or 0) <= target_height]
        if filtered:
            video_candidates = filtered

    if target_fps_min:
        filtered = [f for f in video_candidates if (f.get("fps") or 0) >= target_fps_min]
        if filtered:
            video_candidates = filtered
    elif target_fps_max:
        filtered = [f for f in video_candidates if (f.get("fps") or 0) <= target_fps_max]
        if filtered:
            video_candidates = filtered

    best_video = max(video_candidates, key=lambda f: (f.get("height") or 0, f.get("fps") or 0, f.get("tbr") or 0))

    best_audio = None
    if best_video.get("acodec") in (None, "none"):
        audio_candidates = [
            f for f in formats
            if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
        ]
        if audio_candidates:
            best_audio = max(audio_candidates, key=lambda f: f.get("abr") or f.get("tbr") or 0)

    width = best_video.get("width")
    height = best_video.get("height")
    resolution = f"{width} × {height}" if width and height else "Unknown"

    vcodec = (best_video.get("vcodec") or "").split(".")[0].upper()
    acodec = ""
    if best_audio:
        acodec = (best_audio.get("acodec") or "").split(".")[0].upper()
    else:
        acodec = (best_video.get("acodec") or "").split(".")[0].upper()

    codec = f"{vcodec} / {acodec}" if acodec and acodec != "NONE" else vcodec

    v_size = best_video.get("filesize") or best_video.get("filesize_approx") or 0
    if not v_size and best_video.get("tbr") and duration_secs:
        v_size = int((best_video.get("tbr") * 1000 * duration_secs) / 8)

    a_size = (best_audio.get("filesize") or best_audio.get("filesize_approx") or 0) if best_audio else 0
    if not a_size and best_audio and best_audio.get("tbr") and duration_secs:
        a_size = int((best_audio.get("tbr") * 1000 * duration_secs) / 8)

    total_size = v_size + a_size
    size_str = "N/A"
    if total_size > 0:
        size_str = f"{total_size / (1024 * 1024):.1f} MB"

    return {
        "resolution": resolution,
        "size": size_str,
        "codec": codec
    }


class InfoRequest(BaseModel):
    url: str
    browser: str = None
    user_agent: str = None


class DownloadRequest(BaseModel):
    url: str
    quality: str
    download_type: str
    start_time: str
    end_time: str
    save_dir: str
    browser: str = None
    user_agent: str = None
    concurrent_downloads: int = 8


class FolderRequest(BaseModel):
    pass


@app.post("/api/info")
async def get_video_info(request: InfoRequest):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "check_formats": False,
    }
    if request.browser and request.browser.lower() != "none":
        ydl_opts["cookiesfrombrowser"] = (request.browser.lower(), None, None, None)
    if request.user_agent:
        ydl_opts["http_headers"] = {"User-Agent": request.user_agent}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)

            duration_secs = info.get("duration") or 0
            duration_str = seconds_to_hhmmss(int(duration_secs))

            formats = info.get("formats") or []

            formats_details = {}
            for q_id in ["4k", "1080p60", "1080p30", "720p", "audio"]:
                formats_details[q_id] = extract_quality_details(formats, q_id, duration_secs)

            return {
                "title": info.get("title") or "Unknown",
                "duration": duration_str,
                "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                "thumbnail": info.get("thumbnail") or "",
                "formats": formats_details
            }
    except Exception as e:
        err_msg = str(e)
        if "locked" in err_msg.lower() or "permission" in err_msg.lower() or "credentials" in err_msg.lower() or "cookie" in err_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Cookies extraction failed because the database is locked. Please close your {request.browser} browser and try again."
            )
        raise HTTPException(status_code=400, detail=err_msg)


@app.post("/api/download")
async def download_video(request: DownloadRequest):
    fmt = QUALITY_FORMAT_MAP.get(request.quality, QUALITY_FORMAT_MAP["1080p30"])
    is_audio = request.quality == "audio"

    save_dir = request.save_dir
    if not save_dir:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)
    out_template = os.path.join(save_dir, "%(title)s.%(ext)s")

    if request.download_type == "custom":
        out_template_for_ytdl = os.path.join(save_dir, "%(title)s.temp.%(ext)s")
    else:
        out_template_for_ytdl = out_template

    cmd = get_ytdlp_command() + [
        "--format", fmt,
        "--output", out_template_for_ytdl,
        "--no-playlist",
        "--newline",
        "--no-check-formats",
        "-N", str(request.concurrent_downloads),
    ]

    if request.browser and request.browser.lower() != "none":
        cmd += ["--cookies-from-browser", request.browser.lower()]
    if request.user_agent:
        cmd += ["--user-agent", request.user_agent]

    if is_audio:
        cmd += ["--extract-audio", "--audio-format", "mp3"]

    cmd.append(request.url)

    def stream_output():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            final_file = None
            has_lock_error = False
            for line in proc.stdout:
                line = line.strip()
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
                    if "locked" in line.lower() or "permission denied" in line.lower() or ("cookie" in line.lower() and "lock" in line.lower()):
                        has_lock_error = True
                    if "[download] Destination:" in line:
                        final_file = line.split("[download] Destination:")[1].strip()
                    elif "has already been downloaded" in line and "[download]" in line:
                        parts = line.split("has already been downloaded")[0].replace("[download]", "").strip()
                        final_file = parts
                    elif "[Merger] Merging formats into" in line:
                        final_file = line.split("[Merger] Merging formats into")[1].replace('"', '').strip()

            proc.wait()
            if proc.returncode == 0:
                if request.download_type == "custom":
                    temp_files = [
                        os.path.join(save_dir, f) for f in os.listdir(save_dir)
                        if ".temp." in f and f.lower().endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a'))
                    ]
                    if temp_files:
                        final_file = max(temp_files, key=os.path.getmtime)

                    if final_file:
                        yield f"data: {json.dumps({'log': f'[trim] Found temporary download at {final_file}'})}\n\n"
                        yield f"data: {json.dumps({'log': '[trim] Trimming requested section locally...'})}\n\n"

                        actual_final_file = final_file.replace(".temp.", ".")

                        trim_cmd = [
                            get_ffmpeg_path(), "-y",
                            "-ss", request.start_time,
                            "-to", request.end_time,
                            "-i", final_file,
                            "-c", "copy",
                            actual_final_file
                        ]

                        trim_proc = subprocess.run(
                            trim_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        if trim_proc.returncode == 0:
                            try:
                                os.remove(final_file)
                            except Exception:
                                pass
                            yield f"data: {json.dumps({'log': f'[trim] Successfully trimmed section to {actual_final_file}'})}\n\n"
                            yield f"data: {json.dumps({'status': 'done'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'status': 'error', 'detail': f'FFmpeg trim failed: {trim_proc.stderr}'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'status': 'error', 'detail': 'Temporary download file not found on disk'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"
            else:
                detail = "yt-dlp exited with an error"
                if has_lock_error:
                    detail = f"Cookies extraction failed because the database is locked. Please close your {request.browser} browser and try again."
                yield f"data: {json.dumps({'status': 'error', 'detail': detail})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(stream_output(), media_type="text/event-stream")


@app.post("/api/select-folder")
async def select_folder():
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        folder = tkinter.filedialog.askdirectory(parent=root)
        root.destroy()
        if folder:
            return {"path": folder}
        return {"path": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))