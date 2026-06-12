import sys
import os
import shutil
import urllib.request
import subprocess

def log(msg):
    print(f"\n>>> {msg}\n")

def get_real_ffmpeg_path():
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return None

    base, ext = os.path.splitext(ffmpeg_path)
    shim_path = base + ".shim"
    if os.path.exists(shim_path):
        try:
            with open(shim_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().lower().startswith("path"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            real_path = parts[1].strip().strip('"').strip("'")
                            real_path = os.path.expandvars(real_path)
                            if os.path.exists(real_path):
                                print(f"Resolved Scoop shim -> real ffmpeg: {real_path}")
                                return real_path
        except Exception as e:
            print(f"Error parsing scoop shim: {e}")

    winget_base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    if os.path.isdir(winget_base):
        for entry in os.listdir(winget_base):
            if "ffmpeg" in entry.lower() or "FFmpeg" in entry:
                candidate = os.path.join(winget_base, entry)
                for root_dir, dirs, files in os.walk(candidate):
                    for fname in files:
                        if fname.lower() == "ffmpeg.exe":
                            real_path = os.path.join(root_dir, fname)
                            print(f"Found ffmpeg via WinGet: {real_path}")
                            return real_path

    return ffmpeg_path

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    bin_dir = os.path.join(frontend_dir, "bin")

    dist_electron_dir = os.path.join(frontend_dir, "dist-electron")
    if os.path.exists(dist_electron_dir):
        log("Cleaning previous dist-electron directory to avoid EPERM file locks...")
        import time
        for i in range(5):
            try:
                shutil.rmtree(dist_electron_dir)
                log("Successfully cleared previous build directory.")
                break
            except Exception as e:
                log(f"Attempt {i+1} to clean directory failed: {e}. Retrying in 2s...")
                time.sleep(2)

    os.makedirs(bin_dir, exist_ok=True)

    log("Checking & Installing PyInstaller inside backend venv...")
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(backend_dir, "venv", "bin", "python")

    subprocess.run([python_exe, "-m", "pip", "install", "pyinstaller"], check=True)

    log("Compiling backend main.py into standalone sidecar...")
    pyinstaller_exe = os.path.join(backend_dir, "venv", "Scripts", "pyinstaller.exe") if sys.platform == "win32" else os.path.join(backend_dir, "venv", "bin", "pyinstaller")

    backend_name = "backend"
    subprocess.run([
        pyinstaller_exe,
        "--onefile",
        "--name", backend_name,
        "--distpath", bin_dir,
        "--clean",
        os.path.join(backend_dir, "main.py")
    ], check=True)

    log("Locating and copying FFmpeg...")
    ffmpeg_source = get_real_ffmpeg_path()
    if ffmpeg_source:
        log(f"Found FFmpeg at {ffmpeg_source}, copying to packaged bin...")
        ffmpeg_dest = os.path.join(bin_dir, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        shutil.copy2(ffmpeg_source, ffmpeg_dest)
        if sys.platform != "win32":
            os.chmod(ffmpeg_dest, 0o755)
    else:
        log("[WARNING] FFmpeg was not found on your system path. Please download it and copy it to frontend/bin/ manually.")

    log("Downloading latest standalone yt-dlp binary...")
    ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if sys.platform == "darwin":
        ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
    elif sys.platform == "linux":
        ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

    ytdlp_dest = os.path.join(bin_dir, "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
    try:
        urllib.request.urlretrieve(ytdlp_url, ytdlp_dest)
        if sys.platform != "win32":
            os.chmod(ytdlp_dest, 0o755)
        log("Successfully downloaded yt-dlp sidecar binary!")
    except Exception as e:
        log(f"[ERROR] Failed to download yt-dlp binary: {e}")
        sys.exit(1)

    log("Compiling React frontend bundle...")
    shell_val = sys.platform == "win32"
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, shell=shell_val, check=True)

    import tempfile
    temp_build_dir = os.path.join(tempfile.gettempdir(), "fast-video-downloader-build")
    log(f"Packaging Electron app to temporary folder to avoid EPERM locks: {temp_build_dir}")

    subprocess.run([
        "npx", "electron-builder", "build",
        f"-c.directories.output={temp_build_dir}"
    ], cwd=frontend_dir, shell=shell_val, check=True)

    release_dir = os.path.join(root_dir, "release")
    if os.path.exists(release_dir):
        try:
            shutil.rmtree(release_dir)
        except Exception:
            pass
    os.makedirs(release_dir, exist_ok=True)

    log(f"Copying final installer builds to workspace 'release/' folder...")
    copied_count = 0
    for filename in os.listdir(temp_build_dir):
        src_file = os.path.join(temp_build_dir, filename)
        if os.path.isfile(src_file) and not filename.endswith(".tmp"):
            shutil.copy2(src_file, os.path.join(release_dir, filename))
            log(f"Copied: {filename}")
            copied_count += 1

    if copied_count > 0:
        log(f"SUCCESS! Standalone installers are available inside root 'release/' folder!")
    else:
        log("[WARNING] No installers were copied. Please verify electron-builder execution logs.")

if __name__ == "__main__":
    main()
