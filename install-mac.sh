#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*"; exit 1; }
info() { echo "$*"; }

echo ""
echo "Fast Video Downloader — macOS Setup"
echo "------------------------------------"
echo ""

info "Checking Xcode Command Line Tools..."
if ! xcode-select -p &>/dev/null; then
    warn "Xcode Command Line Tools not found. Installing..."
    xcode-select --install 2>/dev/null || true
    echo ""
    echo "A dialog has opened asking you to install developer tools."
    echo "Click Install, wait for it to finish, then re-run this script."
    echo ""
    exit 0
fi
ok "Xcode Command Line Tools found."

info "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
fi
ok "Homebrew $(brew --version | head -1)"

info "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    warn "Python 3 not found. Installing..."
    brew install python
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 10 ]]; }; then
    warn "Python $PY_VER found, 3.10+ required. Upgrading..."
    brew install python@3.12
    brew link --overwrite python@3.12 2>/dev/null || true
fi
ok "Python $(python3 --version)"

info "Checking Node.js..."
if ! command -v node &>/dev/null; then
    warn "Node.js not found. Installing..."
    brew install node
fi

NODE_VER=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if [[ "$NODE_MAJOR" -lt 18 ]]; then
    warn "Node.js v$NODE_VER found, v18+ required. Upgrading..."
    brew install node
fi
ok "Node.js $(node --version), npm $(npm --version)"

info "Checking FFmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    warn "FFmpeg not found. Installing..."
    brew install ffmpeg
fi
ok "FFmpeg $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"

echo ""
info "Setting up Python backend..."

BACKEND_DIR="$DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created."
else
    ok "Virtual environment already exists."
fi

"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
ok "Python packages installed."

echo ""
info "Installing frontend packages..."
cd "$DIR/frontend"
npm install
ok "Node packages installed."

echo ""
echo "------------------------------------"
echo "Setup complete."
echo ""
echo "  Launch the app:"
echo -e "    ${BOLD}./start-desktop-app.sh${NC}"
echo ""
echo "  Build a .dmg installer:"
echo -e "    ${BOLD}python3 package.py${NC}"
echo ""
