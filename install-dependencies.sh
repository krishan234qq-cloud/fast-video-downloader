#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=================================================="
echo "Analyzing System Dependencies..."
echo "=================================================="

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is missing!"
    echo "Please install Python 3.10+ using your package manager (brew install python on macOS, or apt install python3 on Ubuntu)."
    exit 1
fi
echo "[OK] Python 3 is installed."

# Check Node/NPM
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js / npm is missing!"
    echo "Please install Node.js (brew install node on macOS, or apt install nodejs on Ubuntu)."
    exit 1
fi
echo "[OK] Node.js / npm is installed."

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] FFmpeg is missing!"
    echo "Fast Video Downloader requires FFmpeg to merge video/audio streams and trim sections."
    echo "Please install FFmpeg (brew install ffmpeg on macOS, or apt install ffmpeg on Ubuntu)."
    exit 1
fi
echo "[OK] FFmpeg is installed."

echo "=================================================="
echo "Installing Backend Virtual Environment & Packages..."
echo "=================================================="
if [ ! -d "$DIR/backend/venv" ]; then
    echo "Creating virtual environment in backend/venv..."
    python3 -m venv "$DIR/backend/venv"
fi
echo "Upgrading pip and installing python packages..."
"$DIR/backend/venv/bin/pip" install --upgrade pip
"$DIR/backend/venv/bin/pip" install -r "$DIR/backend/requirements.txt"

echo "=================================================="
echo "Installing Frontend Packages..."
echo "=================================================="
cd "$DIR/frontend"
npm install

echo "=================================================="
echo "[SUCCESS] All dependencies have been installed successfully!"
echo "=================================================="
