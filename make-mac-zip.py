import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(ROOT, "release")
ZIP_NAME = "Fast Video Downloader - Mac Version.zip"
ZIP_PATH = os.path.join(RELEASE_DIR, ZIP_NAME)


def find_dmg():
    for f in os.listdir(RELEASE_DIR):
        if f.endswith(".dmg"):
            return os.path.join(RELEASE_DIR, f), f
    return None, None


def main():
    os.makedirs(RELEASE_DIR, exist_ok=True)

    dmg_path, dmg_name = find_dmg()
    if not dmg_path:
        print("No .dmg found in release/")
        print("Build the Mac installer first by running 'python3 package.py' on a Mac.")
        return

    readme_path = os.path.join(ROOT, "README-MAC.md")
    if not os.path.exists(readme_path):
        print("README-MAC.md not found.")
        return

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    print(f"Building {ZIP_NAME}...")
    print()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.write(dmg_path, dmg_name)
        print(f"  {dmg_name}")

        zf.write(readme_path, "README.md")
        print(f"  README.md")

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print()
    print(f"Done. {ZIP_NAME} ({size_mb:.1f} MB)")
    print(f"  {ZIP_PATH}")


if __name__ == "__main__":
    main()
