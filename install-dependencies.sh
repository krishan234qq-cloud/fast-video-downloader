#!/bin/bash
# Fast Video Downloader — Dependency Installer (macOS / Linux)
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=================================================="
echo " Fast Video Downloader — Dependency Installer"
echo "=================================================="
echo ""

# -------------------------------------------------------
# 1. Check Python 3
# -------------------------------------------------------
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo ""
    echo "  macOS:  brew install python"
    echo "  Ubuntu: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3"
    echo ""
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo "[OK] $PYTHON_VERSION is installed."

# -------------------------------------------------------
# 2. Check Node.js / npm
# -------------------------------------------------------
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js / npm is not installed!"
    echo ""
    echo "  macOS:  brew install node"
    echo "  Ubuntu: sudo apt install nodejs npm"
    echo "  Or visit https://nodejs.org/"
    echo ""
    exit 1
fi
NODE_VERSION=$(node --version 2>&1)
echo "[OK] Node.js $NODE_VERSION is installed."

# -------------------------------------------------------
# 3. Check FFmpeg (WARNING only — not a hard requirement for dev mode)
# -------------------------------------------------------
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "[WARN] FFmpeg is not found in PATH."
    echo "       The app will still run, but video trimming (custom range)"
    echo "       will not work without FFmpeg."
    echo "  macOS:  brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    echo "  Or see: https://ffmpeg.org/download.html"
    echo ""
else
    echo "[OK] FFmpeg is installed."
fi

# -------------------------------------------------------
# 4. Install Backend Python packages
# -------------------------------------------------------
echo ""
echo "=================================================="
echo " Installing Backend Virtual Environment & Packages"
echo "=================================================="

if [ ! -d "$DIR/backend/venv" ]; then
    echo "Creating Python virtual environment in backend/venv..."
    python3 -m venv "$DIR/backend/venv"
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

echo "Upgrading pip..."
"$DIR/backend/venv/bin/pip" install --upgrade pip --quiet

echo "Installing Python packages from requirements.txt..."
"$DIR/backend/venv/bin/pip" install -r "$DIR/backend/requirements.txt"
echo "[OK] Python packages installed."

# -------------------------------------------------------
# 5. Install Frontend Node packages
# -------------------------------------------------------
echo ""
echo "=================================================="
echo " Installing Frontend Node.js Packages"
echo "=================================================="

cd "$DIR/frontend"
npm install
echo "[OK] Node packages installed."

# -------------------------------------------------------
# Done
# -------------------------------------------------------
echo ""
echo "=================================================="
echo " [SUCCESS] All dependencies installed successfully!"
echo "=================================================="
echo ""
