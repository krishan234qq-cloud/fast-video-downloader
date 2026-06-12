from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import yt_dlp
import os
import json
import subprocess
import sys
import re
import urllib.request
import urllib.error

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IS_FROZEN = getattr(sys, "frozen", False)
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
    resolution = f"{width} x {height}" if width and height else "Unknown"

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


SANKAKU_POST_RE = re.compile(
    r"(?:https?://)?(?:www\.)?sankakucomplex\.com/posts?/([A-Za-z0-9]+)",
    re.IGNORECASE,
)


def _get_http_cookies_from_browser(browser: str) -> dict:
    try:
        import browser_cookie3
    except ImportError:
        return {}
    try:
        loader = getattr(browser_cookie3, browser.lower(), None)
        if loader is None:
            return {}
        cj = loader(domain_name="sankakucomplex.com")
        return {c.name: c.value for c in cj}
    except Exception:
        return {}


def _sankakucomplex_extract(post_id: str, browser: str = None) -> dict | None:
    api_bases = [
        f"https://capi-v2.sankakucomplex.com/posts/{post_id}",
        f"https://sankakuapi.com/v2/posts/{post_id}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.sankakucomplex.com/",
    }

    cookies_header = ""
    if browser and browser.lower() != "none":
        cookies_dict = _get_http_cookies_from_browser(browser)
        if cookies_dict:
            cookies_header = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())

    for api_url in api_bases:
        try:
            req = urllib.request.Request(api_url, headers=dict(headers))
            if cookies_header:
                req.add_header("Cookie", cookies_header)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            post = data.get("post", data) if isinstance(data, dict) else data
            if not isinstance(post, dict):
                continue

            file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
            if not file_url:
                continue

            file_type = post.get("file_type", "") or ""
            ext_hint = (post.get("file_ext") or "").lower()
            if "video" not in file_type.lower() and ext_hint not in ("mp4", "webm", "mov", "avi", "mkv"):
                return None

            duration = post.get("video_duration") or post.get("duration") or 0
            try:
                duration = float(duration)
            except (TypeError, ValueError):
                duration = 0

            width = post.get("width") or 0
            height = post.get("height") or 0
            filesize = post.get("file_size") or 0

            thumbnail = (
                post.get("preview_url")
                or post.get("sample_url")
                or ""
            )
            if thumbnail and thumbnail.startswith("//"):
                thumbnail = "https:" + thumbnail

            title = (
                post.get("tags", [{}])[0].get("name_en") if isinstance(post.get("tags"), list) and post.get("tags") else None
            ) or f"Sankakucomplex {post_id}"

            uploader = post.get("author", {}).get("name") if isinstance(post.get("author"), dict) else "Sankakucomplex"

            info = {
                "id": post_id,
                "title": title,
                "url": file_url,
                "ext": ext_hint or "mp4",
                "width": width or None,
                "height": height or None,
                "filesize": filesize or None,
                "duration": duration or None,
                "thumbnail": thumbnail,
                "uploader": uploader or "Sankakucomplex",
                "webpage_url": f"https://www.sankakucomplex.com/posts/{post_id}",
                "extractor": "sankakucomplex",
                "formats": [
                    {
                        "url": file_url,
                        "ext": ext_hint or "mp4",
                        "width": width or None,
                        "height": height or None,
                        "filesize": filesize or None,
                        "vcodec": "h264",
                        "acodec": "aac",
                        "tbr": None,
                        "fps": None,
                    }
                ],
            }
            return info
        except Exception:
            continue

    return None


def _build_ydl_opts(browser: str = None, user_agent: str = None, force_generic: bool = False) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "check_formats": False,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "http_headers": {
            "User-Agent": user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }
    if force_generic:
        opts["force_generic_extractor"] = True
    if browser and browser.lower() != "none":
        opts["cookiesfrombrowser"] = (browser.lower(), None, None, None)
    if user_agent:
        opts["http_headers"]["User-Agent"] = user_agent
    return opts


def _is_network_error(msg: str) -> bool:
    lower = msg.lower()
    return any(k in lower for k in [
        "errno 22", "error 22", "[errno", "winapi", "connection reset",
        "connection refused", "timed out", "timeout", "network",
        "ssl", "certificate", "unable to connect",
    ])


def _extract_info_with_fallback(url: str, browser: str = None, user_agent: str = None):
    sk_match = SANKAKU_POST_RE.search(url)
    if sk_match:
        post_id = sk_match.group(1)
        sk_info = _sankakucomplex_extract(post_id, browser)
        if sk_info:
            return sk_info, False
        raise Exception(
            "Sankakucomplex video requires a premium/logged-in account. "
            "Open Settings and select the browser where you are logged into sankakucomplex.com, then try again."
        )

    last_error = None
    for attempt in range(2):
        force_generic = attempt == 1
        try:
            opts = _build_ydl_opts(browser, user_agent, force_generic=force_generic)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info, force_generic
        except Exception as err:
            err_msg = str(err)
            is_unsupported = (
                "unsupported url" in err_msg.lower()
                or "no video formats found" in err_msg.lower()
                or "unable to extract" in err_msg.lower()
                or "this video is not available" in err_msg.lower()
            )
            if attempt == 0 and is_unsupported:
                last_error = err
                continue
            last_error = err
            break

    raise last_error


@app.post("/api/info")
async def get_video_info(request: InfoRequest):
    try:
        info, used_generic = _extract_info_with_fallback(
            request.url, request.browser, request.user_agent
        )

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
            "formats": formats_details,
            "used_generic_extractor": used_generic,
        }
    except Exception as e:
        err_msg = str(e)
        if "sankakucomplex" in err_msg.lower():
            raise HTTPException(status_code=400, detail=err_msg)
        is_real_browser = request.browser and request.browser.lower() != "none"
        if is_real_browser and (
            "locked" in err_msg.lower()
            or ("permission" in err_msg.lower() and "cookie" in err_msg.lower())
            or "credentials" in err_msg.lower()
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Cookies extraction failed because the database is locked. Please close your {request.browser} browser and try again."
            )
        if "unsupported url" in err_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "This website is not supported and no embedded video was found. "
                    "Try enabling Browser Cookies Sync in Settings if the page needs a login, "
                    "or paste a direct video/stream URL."
                )
            )
        if _is_network_error(err_msg):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Network error while connecting to the video source. "
                    "Check your internet connection and try again. "
                    f"Detail: {err_msg}"
                )
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

    download_url = request.url
    needs_generic = False

    sk_match = SANKAKU_POST_RE.search(request.url)
    if sk_match:
        post_id = sk_match.group(1)
        sk_info = _sankakucomplex_extract(post_id, request.browser)
        if sk_info and sk_info.get("url"):
            download_url = sk_info["url"]
            out_template_for_ytdl = os.path.join(
                save_dir,
                f"sankaku_{post_id}.%(ext)s" if request.download_type != "custom"
                else f"sankaku_{post_id}.temp.%(ext)s"
            )
        else:
            def _err_stream():
                yield f"data: {json.dumps({'log': '[sankaku] ERROR: Could not resolve video URL. Make sure you are logged in and have selected the correct browser in Settings.'})}\\n\\n"
                yield f"data: {json.dumps({'status': 'error', 'detail': 'Sankakucomplex video could not be resolved. Enable Browser Cookies Sync in Settings.'})}\\n\\n"
            return StreamingResponse(_err_stream(), media_type="text/event-stream")
    else:
        try:
            probe_opts = _build_ydl_opts(request.browser, request.user_agent, force_generic=False)
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                ydl.extract_info(request.url, download=False)
        except Exception as probe_err:
            probe_msg = str(probe_err)
            if (
                "unsupported url" in probe_msg.lower()
                or "no video formats found" in probe_msg.lower()
                or "unable to extract" in probe_msg.lower()
            ):
                needs_generic = True

    cmd = get_ytdlp_command() + [
        "--format", fmt,
        "--output", out_template_for_ytdl,
        "--no-playlist",
        "--newline",
        "--no-check-formats",
        "--socket-timeout", "30",
        "--retries", "5",
        "--fragment-retries", "5",
        "--user-agent",
        request.user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "-N", str(request.concurrent_downloads),
    ]

    if needs_generic:
        cmd.append("--force-generic-extractor")

    if request.browser and request.browser.lower() != "none":
        cmd += ["--cookies-from-browser", request.browser.lower()]

    if is_audio:
        cmd += ["--extract-audio", "--audio-format", "mp3"]

    cmd.append(download_url)

    def stream_output():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            final_file = None
            has_lock_error = False
            for line in proc.stdout:
                line = line.strip()
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
                    lower_line = line.lower()
                    if "locked" in lower_line or "permission denied" in lower_line or ("cookie" in lower_line and "lock" in lower_line):
                        has_lock_error = True
                    if "[download] Destination:" in line:
                        final_file = line.split("[download] Destination:")[1].strip()
                    elif "has already been downloaded" in line and "[download]" in line:
                        parts = line.split("has already been downloaded")[0].replace("[download]", "").strip()
                        final_file = parts
                    elif "[Merger] Merging formats into" in line:
                        final_file = line.split("[Merger] Merging formats into")[1].replace('"', "").strip()

            proc.wait()
            if proc.returncode == 0:
                if request.download_type == "custom":
                    temp_files = [
                        os.path.join(save_dir, f) for f in os.listdir(save_dir)
                        if ".temp." in f and f.lower().endswith((".mp4", ".mkv", ".webm", ".mp3", ".m4a"))
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
                            stdin=subprocess.DEVNULL,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
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
        import tkinter
        import tkinter.filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        folder = tkinter.filedialog.askdirectory(parent=root)
        root.destroy()
        if folder:
            return {"path": folder}
        return {"path": None}
    except Exception:
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads, exist_ok=True)
        return {"path": downloads}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)