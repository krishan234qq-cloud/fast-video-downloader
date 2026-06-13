import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(ROOT, "release")
ZIP_NAME = "Fast Video Downloader - Mac Version.zip"
ZIP_PATH = os.path.join(RELEASE_DIR, ZIP_NAME)
ZIP_ROOT = "fast-video-downloader-mac"

INCLUDE_FILES = [
    ("README-MAC.md",           "README-MAC.md"),
    ("install-mac.sh",          "install-mac.sh"),
    ("install-dependencies.sh", "install-dependencies.sh"),
    ("start-desktop-app.sh",    "start-desktop-app.sh"),
    ("start-launcher.sh",       "start-launcher.sh"),
    ("package.py",              "package.py"),
]

INCLUDE_DIRS = [
    ("backend",  "backend",  {"venv", "__pycache__", "dist", "build"}),
    ("frontend", "frontend", {"node_modules", "dist", "dist-electron", "bin", ".vscode"}),
]

SKIP_EXTENSIONS = {".pyc", ".pyo"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def should_skip(name):
    _, ext = os.path.splitext(name)
    return name in SKIP_NAMES or ext in SKIP_EXTENSIONS


def add_dir(zf, src_dir, zip_dir, exclude_dirs):
    for entry in sorted(os.listdir(src_dir)):
        if should_skip(entry):
            continue
        src_path = os.path.join(src_dir, entry)
        zip_path = zip_dir + "/" + entry
        if os.path.isdir(src_path):
            if entry in exclude_dirs:
                continue
            add_dir(zf, src_path, zip_path, exclude_dirs)
        else:
            zf.write(src_path, zip_path)
            print(f"  {zip_path}")


def main():
    os.makedirs(RELEASE_DIR, exist_ok=True)

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    print(f"Building {ZIP_NAME}...")
    print()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel_src, rel_dest in INCLUDE_FILES:
            src = os.path.join(ROOT, rel_src)
            if not os.path.exists(src):
                print(f"  skipped (not found): {rel_src}")
                continue
            zf.write(src, f"{ZIP_ROOT}/{rel_dest}")
            print(f"  {ZIP_ROOT}/{rel_dest}")

        for src_rel, dest_rel, excluded in INCLUDE_DIRS:
            src_dir = os.path.join(ROOT, src_rel)
            if not os.path.isdir(src_dir):
                print(f"  skipped (not found): {src_rel}/")
                continue
            add_dir(zf, src_dir, f"{ZIP_ROOT}/{dest_rel}", excluded)

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print()
    print(f"Done. {ZIP_NAME} ({size_mb:.1f} MB)")
    print(f"  {ZIP_PATH}")


if __name__ == "__main__":
    main()
