import sys
import os
import shutil
import urllib.request
import subprocess
import zipfile
import tarfile
import tempfile

def log(msg):
    print(f"\n>>> {msg}\n")

# ---------------------------------------------------------------------------
# FFmpeg static binary downloader — works on all platforms, no system install
# needed. Downloads pre-built static binaries from trusted GitHub releases.
# ---------------------------------------------------------------------------
FFMPEG_URLS = {
    "win32": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "extract": "zip",
        # Path inside the archive to ffmpeg.exe
        "bin_path": lambda root: _find_in_tree(root, "ffmpeg.exe"),
        "dest_name": "ffmpeg.exe",
    },
    "darwin": {
        # macOS static build — single binary download
        "url": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
        "extract": "zip",
        "bin_path": lambda root: _find_in_tree(root, "ffmpeg"),
        "dest_name": "ffmpeg",
    },
    "linux": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
        "extract": "tarxz",
        "bin_path": lambda root: _find_in_tree(root, "ffmpeg"),
        "dest_name": "ffmpeg",
    },
}


def _find_in_tree(root, filename):
    """Walk directory tree and return path of first matching filename."""
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f == filename:
                return os.path.join(dirpath, f)
    return None


def download_ffmpeg(bin_dir):
    """Download a static FFmpeg binary for the current platform into bin_dir."""
    plat = sys.platform  # "win32", "darwin", "linux"
    # Normalise linux variants
    if plat.startswith("linux"):
        plat = "linux"

    info = FFMPEG_URLS.get(plat)
    if not info:
        log(f"[WARNING] No static FFmpeg build known for platform '{plat}'. "
            "Please manually copy ffmpeg into frontend/bin/.")
        return False

    dest_name = info["dest_name"]
    dest_path = os.path.join(bin_dir, dest_name)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1_000_000:
        log(f"FFmpeg already present at {dest_path}, skipping download.")
        return True

    log(f"Downloading static FFmpeg for {plat} …")
    log(f"Source: {info['url']}")

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, "ffmpeg_archive")
        try:
            urllib.request.urlretrieve(info["url"], archive_path)
        except Exception as e:
            log(f"[ERROR] Could not download FFmpeg: {e}")
            return False

        extract_dir = os.path.join(tmp, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        if info["extract"] == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        elif info["extract"] == "tarxz":
            with tarfile.open(archive_path, "r:xz") as tf:
                tf.extractall(extract_dir)

        found = info["bin_path"](extract_dir)
        if not found:
            log("[ERROR] Could not locate ffmpeg binary inside the downloaded archive.")
            return False

        shutil.copy2(found, dest_path)
        if sys.platform != "win32":
            os.chmod(dest_path, 0o755)

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    log(f"FFmpeg downloaded successfully ({size_mb:.1f} MB) -> {dest_path}")
    return True


def download_ytdlp(bin_dir):
    """Download the latest standalone yt-dlp binary for the current platform."""
    plat = sys.platform

    if plat == "win32":
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        dest_name = "yt-dlp.exe"
    elif plat == "darwin":
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
        dest_name = "yt-dlp"
    else:
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        dest_name = "yt-dlp"

    dest_path = os.path.join(bin_dir, dest_name)

    log(f"Downloading latest yt-dlp binary…")
    try:
        urllib.request.urlretrieve(url, dest_path)
        if sys.platform != "win32":
            os.chmod(dest_path, 0o755)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        log(f"yt-dlp downloaded successfully ({size_mb:.1f} MB) -> {dest_path}")
        return True
    except Exception as e:
        log(f"[ERROR] Failed to download yt-dlp: {e}")
        return False


def compile_backend(backend_dir, bin_dir):
    """Compile backend/main.py into a standalone sidecar binary using PyInstaller."""
    if sys.platform == "win32":
        python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
        pyinstaller_exe = os.path.join(backend_dir, "venv", "Scripts", "pyinstaller.exe")
        backend_name = "backend"
    else:
        python_exe = os.path.join(backend_dir, "venv", "bin", "python")
        pyinstaller_exe = os.path.join(backend_dir, "venv", "bin", "pyinstaller")
        backend_name = "backend"

    log("Installing / upgrading PyInstaller in backend venv…")
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pyinstaller"], check=True)

    log("Compiling backend main.py into standalone sidecar binary…")
    try:
        subprocess.run([
            pyinstaller_exe,
            "--onefile",
            "--name", backend_name,
            "--distpath", bin_dir,
            "--clean",
            os.path.join(backend_dir, "main.py")
        ], check=True)
    except subprocess.CalledProcessError as e:
        binary = os.path.join(bin_dir, backend_name + (".exe" if sys.platform == "win32" else ""))
        if not (os.path.exists(binary) and os.path.getsize(binary) > 0):
            raise e

    binary = os.path.join(bin_dir, backend_name + (".exe" if sys.platform == "win32" else ""))
    if sys.platform != "win32":
        os.chmod(binary, 0o755)

    log(f"Backend compiled -> {binary}")


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    bin_dir = os.path.join(frontend_dir, "bin")

    # ── Clean previous Electron build to avoid EPERM file-lock issues ─────────
    dist_electron_dir = os.path.join(frontend_dir, "dist-electron")
    if os.path.exists(dist_electron_dir):
        log("Cleaning previous dist-electron directory…")
        import time
        for i in range(5):
            try:
                shutil.rmtree(dist_electron_dir)
                log("Cleared previous build directory.")
                break
            except Exception as e:
                log(f"Attempt {i+1} to clean failed: {e}. Retrying in 2s…")
                time.sleep(2)

    os.makedirs(bin_dir, exist_ok=True)

    # ── Step 1: Compile Python backend sidecar ────────────────────────────────
    compile_backend(backend_dir, bin_dir)

    # ── Step 2: Bundle FFmpeg (auto-downloaded static binary) ─────────────────
    log("Bundling FFmpeg static binary…")
    if not download_ffmpeg(bin_dir):
        log("[WARNING] FFmpeg was not bundled. Video trimming will NOT work in the packaged app.")
        log("You can manually copy ffmpeg.exe / ffmpeg into frontend/bin/ and re-run package.py.")

    # ── Step 3: Bundle yt-dlp sidecar binary ──────────────────────────────────
    log("Bundling yt-dlp binary…")
    if not download_ytdlp(bin_dir):
        log("[ERROR] yt-dlp download failed. Cannot build a working package.")
        sys.exit(1)

    # ── Step 4: Build React frontend bundle ───────────────────────────────────
    log("Compiling React frontend bundle…")
    shell_val = sys.platform == "win32"
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, shell=shell_val, check=True)

    # ── Step 5: Package with Electron Builder ─────────────────────────────────
    temp_build_dir = os.path.join(tempfile.gettempdir(), "fast-video-downloader-build")
    log(f"Packaging Electron app -> {temp_build_dir}")

    subprocess.run([
        "npx", "electron-builder", "build",
        f"-c.directories.output={temp_build_dir}"
    ], cwd=frontend_dir, shell=shell_val, check=True)

    # ── Step 6: Copy installer(s) to release/ ─────────────────────────────────
    release_dir = os.path.join(root_dir, "release")
    if os.path.exists(release_dir):
        try:
            shutil.rmtree(release_dir)
        except Exception:
            pass
    os.makedirs(release_dir, exist_ok=True)

    log("Copying final installer to release/ …")
    copied_count = 0
    for filename in os.listdir(temp_build_dir):
        src_file = os.path.join(temp_build_dir, filename)
        if os.path.isfile(src_file) and not filename.endswith(".tmp"):
            shutil.copy2(src_file, os.path.join(release_dir, filename))
            log(f"Copied: {filename}")
            copied_count += 1

    if copied_count > 0:
        log(f"SUCCESS! {copied_count} installer(s) available in release/")
    else:
        log("[WARNING] No installers were copied — check electron-builder logs above.")


if __name__ == "__main__":
    main()
