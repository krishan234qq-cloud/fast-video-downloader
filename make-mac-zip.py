"""
make-mac-zip.py
---------------
Creates "Fast Video Downloader - Mac Version.zip" in the release/ folder.

The ZIP contains only the files a Mac user needs — no node_modules, no
venv, no compiled build artefacts.

Run from the project root:
    python make-mac-zip.py
"""

import os
import sys
import zipfile
import shutil

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(ROOT, "release")
ZIP_NAME = "Fast Video Downloader - Mac Version.zip"
ZIP_PATH = os.path.join(RELEASE_DIR, ZIP_NAME)

# Name of the top-level folder inside the ZIP
ZIP_ROOT = "fast-video-downloader-mac"

# ── Files / folders to include ───────────────────────────────────────────────
# Each entry: (source_path_relative_to_ROOT, dest_path_inside_zip_root)
INCLUDE_FILES = [
    # ── Root scripts & guides ─────────────────────────────────────────────
    ("README-MAC.md",            "README-MAC.md"),
    ("install-mac.sh",           "install-mac.sh"),
    ("install-dependencies.sh",  "install-dependencies.sh"),
    ("start-desktop-app.sh",     "start-desktop-app.sh"),
    ("start-launcher.sh",        "start-launcher.sh"),
    ("package.py",               "package.py"),
]

# Whole directories to include (with exclusion filters)
INCLUDE_DIRS = [
    # (source_dir_relative, dest_in_zip, set_of_excluded_subdir_names)
    ("backend",  "backend",  {"venv", "__pycache__", "dist", "build"}),
    ("frontend", "frontend", {"node_modules", "dist", "dist-electron", "bin", ".vscode"}),
]

# ── Helpers ──────────────────────────────────────────────────────────────────
SKIP_EXTENSIONS = {".pyc", ".pyo"}
SKIP_NAMES      = {".DS_Store", "Thumbs.db", "desktop.ini"}


def should_skip(name: str) -> bool:
    _, ext = os.path.splitext(name)
    return name in SKIP_NAMES or ext in SKIP_EXTENSIONS


def add_dir(zf: zipfile.ZipFile, src_dir: str, zip_dir: str, exclude_dirs: set):
    """Recursively add a directory into the ZIP, skipping excluded sub-dirs."""
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
            print(f"  + {zip_path}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(RELEASE_DIR, exist_ok=True)

    # Remove old ZIP if it exists
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
        print(f"Removed old ZIP: {ZIP_PATH}")

    print(f"\nBuilding: {ZIP_NAME}")
    print(f"Destination: {RELEASE_DIR}\n")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

        # ── Individual files ──────────────────────────────────────────────
        for rel_src, rel_dest in INCLUDE_FILES:
            src = os.path.join(ROOT, rel_src)
            if not os.path.exists(src):
                print(f"  [SKIP — not found] {rel_src}")
                continue
            dest_in_zip = f"{ZIP_ROOT}/{rel_dest}"
            zf.write(src, dest_in_zip)
            print(f"  + {dest_in_zip}")

        # ── Directories ───────────────────────────────────────────────────
        for src_rel, dest_rel, excluded in INCLUDE_DIRS:
            src_dir = os.path.join(ROOT, src_rel)
            if not os.path.isdir(src_dir):
                print(f"  [SKIP — dir not found] {src_rel}/")
                continue
            zip_dir = f"{ZIP_ROOT}/{dest_rel}"
            add_dir(zf, src_dir, zip_dir, excluded)

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"\n[DONE]  {ZIP_NAME}  ({size_mb:.1f} MB)")
    print(f"   -> {ZIP_PATH}\n")


if __name__ == "__main__":
    main()
