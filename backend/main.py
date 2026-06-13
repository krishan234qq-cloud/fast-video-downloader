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
import shutil
import tempfile
import glob
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
        name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        for d in [BASE_BIN_DIR, os.getcwd(), os.path.dirname(sys.executable)]:
            if d:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    return p
    return "ffmpeg"


def get_ytdlp_command():
    if IS_FROZEN:
        name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
        for d in [BASE_BIN_DIR, os.getcwd(), os.path.dirname(sys.executable)]:
            if d:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    return [p]
        return [name]
    return [sys.executable, "-u", "-m", "yt_dlp"]


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

ANIME_DOMAINS = [
    "9anime", "zoro.to", "aniwatch", "gogoanime", "animepahe",
    "animekisa", "4anime", "animesuge", "animefreak", "kickassanime",
    "animehub", "animeheaven", "animeultima", "animixplay", "crunchyroll",
    "funimation", "hidive",
]


def is_anime_url(url: str) -> bool:
    lower = url.lower()
    return any(domain in lower for domain in ANIME_DOMAINS)


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


def _browser_cookie_db_paths(browser: str) -> tuple[list[str], str | None]:
    b = browser.lower()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        roaming = os.environ.get("APPDATA", "")
        defs = {
            "chrome":  (os.path.join(local,   "Google",           "Chrome",        "User Data"), True),
            "edge":    (os.path.join(local,   "Microsoft",         "Edge",          "User Data"), True),
            "brave":   (os.path.join(local,   "BraveSoftware",     "Brave-Browser", "User Data"), True),
            "vivaldi": (os.path.join(local,   "Vivaldi",           "User Data"),                  True),
            "opera":   (os.path.join(roaming, "Opera Software",    "Opera Stable"),               True),
        }
        if b in defs:
            base, chromium = defs[b]
            if chromium:
                cookie_paths = [
                    os.path.join(base, "Default", "Network", "Cookies"),
                    os.path.join(base, "Default", "Cookies"),
                ]
                key_path = os.path.join(base, "Local State")
                return cookie_paths, key_path
        if b == "firefox":
            profiles_root = os.path.join(roaming, "Mozilla", "Firefox", "Profiles")
            paths = glob.glob(os.path.join(profiles_root, "*.default-release", "cookies.sqlite"))
            paths += glob.glob(os.path.join(profiles_root, "*", "cookies.sqlite"))
            return paths, None
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        sup = os.path.join(home, "Library", "Application Support")
        defs = {
            "chrome":  os.path.join(sup, "Google",          "Chrome",               "Default"),
            "edge":    os.path.join(sup, "Microsoft Edge",                           "Default"),
            "brave":   os.path.join(sup, "BraveSoftware",   "Brave-Browser",        "Default"),
            "vivaldi": os.path.join(sup, "Vivaldi",                                  "Default"),
            "opera":   os.path.join(sup, "com.operasoftware.Opera"),
        }
        if b in defs:
            base = defs[b]
            parent = os.path.dirname(base)
            cookie_paths = [
                os.path.join(base, "Network", "Cookies"),
                os.path.join(base, "Cookies"),
            ]
            key_path = os.path.join(parent, "Local State")
            return cookie_paths, key_path
        if b == "firefox":
            profiles_root = os.path.join(home, "Library", "Application Support", "Firefox", "Profiles")
            paths = glob.glob(os.path.join(profiles_root, "*.default-release", "cookies.sqlite"))
            paths += glob.glob(os.path.join(profiles_root, "*", "cookies.sqlite"))
            return paths, None
    else:
        home = os.path.expanduser("~")
        defs = {
            "chrome":  os.path.join(home, ".config", "google-chrome",   "Default"),
            "edge":    os.path.join(home, ".config", "microsoft-edge",   "Default"),
            "brave":   os.path.join(home, ".config", "BraveSoftware",    "Brave-Browser", "Default"),
        }
        if b in defs:
            base = defs[b]
            cookie_paths = [
                os.path.join(base, "Network", "Cookies"),
                os.path.join(base, "Cookies"),
            ]
            key_path = os.path.join(os.path.dirname(base), "Local State")
            return cookie_paths, key_path
        if b == "firefox":
            paths = glob.glob(os.path.join(home, ".mozilla", "firefox", "*.default-release", "cookies.sqlite"))
            paths += glob.glob(os.path.join(home, ".mozilla", "firefox", "*", "cookies.sqlite"))
            return paths, None
    return [], None


def _write_netscape_jar(cj, path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Generated by Fast Video Downloader\n\n")
        for cookie in cj:
            domain = cookie.domain or ""
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path_val = cookie.path or "/"
            secure = "TRUE" if cookie.secure else "FALSE"
            try:
                expires = str(int(cookie.expires)) if cookie.expires else "0"
            except Exception:
                expires = "0"
            f.write(f"{domain}\t{flag}\t{path_val}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value or ''}\n")


def _export_cookies_bypass_lock(browser: str) -> str | None:
    if not browser or browser.lower() == "none":
        return None
    b = browser.lower()
    try:
        import browser_cookie3
    except ImportError:
        return None

    loader = getattr(browser_cookie3, b, None)
    if loader is None:
        return None

    tmp_netscape_fd, tmp_netscape_path = tempfile.mkstemp(suffix="_cookies.txt")
    os.close(tmp_netscape_fd)

    try:
        cj = loader()
        _write_netscape_jar(cj, tmp_netscape_path)
        return tmp_netscape_path
    except Exception as direct_err:
        is_lock = any(k in str(direct_err).lower() for k in [
            "locked", "database", "permission", "access denied", "readonly",
            "could not copy", "unable to read",
        ])
        if not is_lock:
            try:
                os.unlink(tmp_netscape_path)
            except Exception:
                pass
            return None

    cookie_paths, key_path = _browser_cookie_db_paths(b)
    cookie_src = next((p for p in cookie_paths if os.path.exists(p)), None)
    if not cookie_src:
        try:
            os.unlink(tmp_netscape_path)
        except Exception:
            pass
        return None

    tmp_cookie_fd, tmp_cookie_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_cookie_fd)
    tmp_key_path = None

    try:
        shutil.copy2(cookie_src, tmp_cookie_path)

        if key_path and os.path.exists(key_path):
            tmp_key_fd, tmp_key_path = tempfile.mkstemp(suffix=".json")
            os.close(tmp_key_fd)
            shutil.copy2(key_path, tmp_key_path)

        try:
            import inspect
            loader_params = inspect.signature(loader).parameters
        except Exception:
            loader_params = {}

        if tmp_key_path and "key_file" in loader_params:
            try:
                cj = loader(cookie_file=tmp_cookie_path, key_file=tmp_key_path)
                _write_netscape_jar(cj, tmp_netscape_path)
                return tmp_netscape_path
            except Exception:
                pass

        try:
            cj = loader(cookie_file=tmp_cookie_path)
            _write_netscape_jar(cj, tmp_netscape_path)
            return tmp_netscape_path
        except Exception:
            pass

        try:
            import sqlite3
            uri = f"file:{tmp_cookie_path}?immutable=1"
            con = sqlite3.connect(uri, uri=True)
            cur = con.execute(
                "SELECT host_key, path, is_secure, expires_utc, name, value FROM cookies"
            )
            with open(tmp_netscape_path, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n# Generated by Fast Video Downloader\n\n")
                for row in cur.fetchall():
                    host, path_val, secure, expires, name, value = row
                    flag = "TRUE" if (host or "").startswith(".") else "FALSE"
                    secure_str = "TRUE" if secure else "FALSE"
                    try:
                        exp_sec = str(int(expires / 1000000 - 11644473600)) if expires else "0"
                    except Exception:
                        exp_sec = "0"
                    f.write(
                        f"{host}\t{flag}\t{path_val or '/'}\t{secure_str}\t"
                        f"{exp_sec}\t{name}\t{value or ''}\n"
                    )
            con.close()
            return tmp_netscape_path
        except Exception:
            pass

        try:
            os.unlink(tmp_netscape_path)
        except Exception:
            pass
        return None

    finally:
        try:
            os.unlink(tmp_cookie_path)
        except Exception:
            pass
        if tmp_key_path:
            try:
                os.unlink(tmp_key_path)
            except Exception:
                pass


def _get_http_cookies_from_browser(browser: str) -> dict:
    cookies_file = _export_cookies_bypass_lock(browser)
    if not cookies_file:
        return {}
    try:
        cookies = {}
        with open(cookies_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        return cookies
    except Exception:
        return {}
    finally:
        try:
            os.unlink(cookies_file)
        except Exception:
            pass


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


def _build_ydl_opts(browser: str = None, user_agent: str = None, force_generic: bool = False, cookies_file: str = None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "check_formats": False,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
    }
    if force_generic:
        opts["force_generic_extractor"] = True
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    if user_agent:
        opts["http_headers"] = {"User-Agent": user_agent}
    return opts


def _build_anime_ydl_opts(url: str = "", browser: str = None, user_agent: str = None) -> dict:
    ua = user_agent or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        referer = origin + "/"
    except Exception:
        origin = ""
        referer = ""

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "check_formats": False,
        "socket_timeout": 45,
        "retries": 10,
        "fragment_retries": 10,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": referer,
            "Origin": origin,
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        },
    }
    return opts


def _is_network_error(msg: str) -> bool:
    lower = msg.lower()
    if "errno 22" in lower or "invalid argument" in lower:
        return False
    return any(k in lower for k in [
        "[errno", "winapi", "connection reset",
        "connection refused", "timed out", "timeout",
        "ssl", "certificate", "unable to connect",
    ])


def _is_anime_extractor_error(msg: str) -> bool:
    lower = msg.lower()
    return any(k in lower for k in [
        "unsupported url", "no video formats found", "unable to extract",
        "this video is not available", "invalid argument", "errno 22",
        "cloudflare", "403", "access denied",
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

    cookies_file = _export_cookies_bypass_lock(browser)

    if is_anime_url(url):
        last_anime_err = None
        for impersonate in ["chrome", None]:
            try:
                opts = _build_anime_ydl_opts(url, browser, user_agent)
                if impersonate:
                    opts["impersonate"] = impersonate
                if cookies_file and os.path.exists(cookies_file):
                    opts["cookiefile"] = cookies_file
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return info, False
            except Exception as anime_err:
                last_anime_err = anime_err
                continue
        if cookies_file:
            try:
                os.unlink(cookies_file)
            except Exception:
                pass
        if last_anime_err:
            err_msg = str(last_anime_err)
            if _is_anime_extractor_error(err_msg):
                raise Exception(
                    "Could not extract video from this anime site. "
                    "Many anime sites use Cloudflare or JavaScript-protected players. "
                    "Try: 1) Select your browser in Settings to pass cookies, "
                    "2) Open the video in your browser, find the direct .m3u8 or .mp4 URL and paste that instead, "
                    "3) Try a mirror site (gogoanime, animepahe, etc.)."
                )
            raise last_anime_err

    last_error = None
    for attempt in range(2):
        force_generic = attempt == 1
        try:
            opts = _build_ydl_opts(browser, user_agent, force_generic=force_generic, cookies_file=cookies_file)
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

    if cookies_file:
        try:
            os.unlink(cookies_file)
        except Exception:
            pass
    raise last_error


def _reencode_to_universal(input_path: str, output_path: str, ffmpeg_path: str, is_audio: bool = False) -> tuple[bool, str]:
    if is_audio:
        cmd = [
            ffmpeg_path, "-y",
            "-i", input_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            output_path,
        ]
    else:
        cmd = [
            ffmpeg_path, "-y",
            "-i", input_path,
            "-vcodec", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-profile:v", "high",
            "-level", "4.1",
            "-pix_fmt", "yuv420p",
            "-acodec", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0, result.stderr


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
        if "could not extract video from this anime site" in err_msg.lower() or "cloudflare" in err_msg.lower():
            raise HTTPException(status_code=400, detail=err_msg)
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

    out_template = os.path.join(save_dir, "%(title)s.raw.%(ext)s")

    download_url = request.url
    needs_generic = False
    is_anime = is_anime_url(request.url)

    sk_match = SANKAKU_POST_RE.search(request.url)
    if sk_match:
        post_id = sk_match.group(1)
        sk_info = _sankakucomplex_extract(post_id, request.browser)
        if sk_info and sk_info.get("url"):
            download_url = sk_info["url"]
            out_template = os.path.join(save_dir, f"sankaku_{post_id}.raw.%(ext)s")
        else:
            def _err_stream():
                yield f"data: {json.dumps({'log': '[sankaku] ERROR: Could not resolve video URL. Make sure you are logged in and have selected the correct browser in Settings.'})}\n\n"
                yield f"data: {json.dumps({'status': 'error', 'detail': 'Sankakucomplex video could not be resolved. Enable Browser Cookies Sync in Settings.'})}\n\n"
            return StreamingResponse(_err_stream(), media_type="text/event-stream")
    elif is_anime:
        pass
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

    if is_anime:
        ua = request.user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        try:
            from urllib.parse import urlparse
            parsed = urlparse(request.url)
            site_origin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            site_origin = ""
        cmd = get_ytdlp_command() + [
            "--format", fmt,
            "--output", out_template,
            "--no-playlist",
            "--newline",
            "--no-check-formats",
            "--socket-timeout", "45",
            "--retries", "10",
            "--fragment-retries", "10",
            "-N", str(request.concurrent_downloads),
            "--geo-bypass",
            "--user-agent", ua,
            "--add-header", f"Referer:{site_origin}/",
            "--add-header", f"Origin:{site_origin}",
            "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "--add-header", "Accept-Language:en-US,en;q=0.5",
            "--add-header", "DNT:1",
        ]
    else:
        cmd = get_ytdlp_command() + [
            "--format", fmt,
            "--output", out_template,
            "--no-playlist",
            "--newline",
            "--no-check-formats",
            "--socket-timeout", "30",
            "--retries", "5",
            "--fragment-retries", "5",
            "-N", str(request.concurrent_downloads),
        ]

    if needs_generic:
        cmd.append("--force-generic-extractor")

    cookies_file = _export_cookies_bypass_lock(request.browser)
    if cookies_file:
        cmd += ["--cookies", cookies_file]

    if request.user_agent and not is_anime:
        cmd += ["--user-agent", request.user_agent]

    cmd.append(download_url)

    def stream_output():
        try:
            print(f"[downloader] Executing: {cmd}")
            yield f"data: {json.dumps({'log': f'[downloader] Starting download for {request.url}'})}\n\n"
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
            raw_file = None
            for line in proc.stdout:
                line = line.strip()
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
                    lower_line = line.lower()
                    if "[download] Destination:" in line:
                        raw_file = line.split("[download] Destination:")[1].strip()
                    elif "has already been downloaded" in line and "[download]" in line:
                        parts = line.split("has already been downloaded")[0].replace("[download]", "").strip()
                        raw_file = parts
                    elif "[Merger] Merging formats into" in line:
                        raw_file = line.split("[Merger] Merging formats into")[1].replace('"', "").strip()

            proc.wait()
            if proc.returncode != 0:
                yield f"data: {json.dumps({'status': 'error', 'detail': 'yt-dlp exited with an error'})}\n\n"
                return

            raw_files = [
                os.path.join(save_dir, f) for f in os.listdir(save_dir)
                if ".raw." in f and f.lower().endswith((".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".flac", ".ogg", ".ts", ".avi"))
            ]
            if raw_files:
                raw_file = max(raw_files, key=os.path.getmtime)

            if not raw_file or not os.path.exists(raw_file):
                yield f"data: {json.dumps({'status': 'error', 'detail': 'Downloaded file not found on disk'})}\n\n"
                return

            if request.download_type == "custom":
                yield f"data: {json.dumps({'log': '[trim] Trimming requested section...'})}\n\n"
                trimmed_raw = raw_file.replace(".raw.", ".trimmed_raw.")
                trim_cmd = [
                    get_ffmpeg_path(), "-y",
                    "-ss", request.start_time,
                    "-to", request.end_time,
                    "-i", raw_file,
                    "-c", "copy",
                    trimmed_raw,
                ]
                trim_result = subprocess.run(
                    trim_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if trim_result.returncode != 0:
                    yield f"data: {json.dumps({'status': 'error', 'detail': f'FFmpeg trim failed: {trim_result.stderr}'})}\n\n"
                    return
                try:
                    os.remove(raw_file)
                except Exception:
                    pass
                raw_file = trimmed_raw

            yield f"data: {json.dumps({'log': '[encode] Re-encoding to universal H.264/AAC format for maximum compatibility...'})}\n\n"

            base_name = os.path.basename(raw_file)
            for suffix in (".raw.", ".trimmed_raw."):
                base_name = base_name.replace(suffix, ".")
            if is_audio:
                ext = ".mp3"
                name_no_ext = os.path.splitext(base_name)[0]
                final_file = os.path.join(save_dir, name_no_ext + ext)
            else:
                name_no_ext = os.path.splitext(base_name)[0]
                final_file = os.path.join(save_dir, name_no_ext + ".mp4")

            encode_ok, encode_err = _reencode_to_universal(raw_file, final_file, get_ffmpeg_path(), is_audio)

            try:
                os.remove(raw_file)
            except Exception:
                pass

            if encode_ok:
                yield f"data: {json.dumps({'log': f'[encode] Done. Saved as: {final_file}'})}\n\n"
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'detail': f'FFmpeg re-encode failed: {encode_err[:500]}'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'detail': str(e)})}\n\n"
        finally:
            if cookies_file:
                try:
                    os.unlink(cookies_file)
                except Exception:
                    pass

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