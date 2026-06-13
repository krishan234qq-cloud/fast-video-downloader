#!/bin/bash
# ============================================================
#  Fast Video Downloader — macOS One-Click Installer
#  Run this ONCE to set everything up on your Mac.
#  Usage: chmod +x install-mac.sh && ./install-mac.sh
# ============================================================
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ---------- colours ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[✔]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✘]${NC} $*"; exit 1; }
info() { echo -e "${CYAN}[→]${NC} $*"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     Fast Video Downloader — macOS Installer      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────────────────────
# 1. Xcode Command Line Tools (needed for git, make, clang)
# ─────────────────────────────────────────────────────────────
info "Checking Xcode Command Line Tools..."
if ! xcode-select -p &>/dev/null; then
    warn "Xcode Command Line Tools not found. Installing... (this may take a few minutes)"
    xcode-select --install 2>/dev/null || true
    echo ""
    echo -e "${YELLOW}  A dialog has opened asking you to install developer tools.${NC}"
    echo -e "${YELLOW}  Click 'Install', wait for it to finish, then re-run this script.${NC}"
    echo ""
    exit 0
fi
ok "Xcode Command Line Tools are installed."

# ─────────────────────────────────────────────────────────────
# 2. Homebrew
# ─────────────────────────────────────────────────────────────
info "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
fi
ok "Homebrew is installed: $(brew --version | head -1)"

# ─────────────────────────────────────────────────────────────
# 3. Python 3 (3.10+)
# ─────────────────────────────────────────────────────────────
info "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    warn "Python 3 not found. Installing via Homebrew..."
    brew install python
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 10 ]]; }; then
    warn "Python $PY_VER found but 3.10+ is required. Upgrading via Homebrew..."
    brew install python@3.12
    # Re-link
    brew link --overwrite python@3.12 2>/dev/null || true
fi

ok "Python $(python3 --version) is installed."

# ─────────────────────────────────────────────────────────────
# 4. Node.js 18+ / npm
# ─────────────────────────────────────────────────────────────
info "Checking Node.js..."
if ! command -v node &>/dev/null; then
    warn "Node.js not found. Installing via Homebrew..."
    brew install node
fi

NODE_VER=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if [[ "$NODE_MAJOR" -lt 18 ]]; then
    warn "Node.js v$NODE_VER found but v18+ is required. Upgrading..."
    brew install node
fi

ok "Node.js $(node --version) and npm $(npm --version) are installed."

# ─────────────────────────────────────────────────────────────
# 5. FFmpeg
# ─────────────────────────────────────────────────────────────
info "Checking FFmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    warn "FFmpeg not found. Installing via Homebrew..."
    brew install ffmpeg
fi
ok "FFmpeg is installed: $(ffmpeg -version 2>&1 | head -1 | awk '{print $1,$2,$3}')"

# ─────────────────────────────────────────────────────────────
# 6. Backend Python virtual environment & packages
# ─────────────────────────────────────────────────────────────
echo ""
info "Setting up Python backend virtual environment..."

BACKEND_DIR="$DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created at backend/venv"
else
    ok "Virtual environment already exists."
fi

info "Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet

info "Installing Python packages from requirements.txt..."
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
ok "Python packages installed."

# ─────────────────────────────────────────────────────────────
# 7. Frontend Node packages
# ─────────────────────────────────────────────────────────────
echo ""
info "Installing frontend Node.js packages..."
cd "$DIR/frontend"
npm install
ok "Node packages installed."

# ─────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   ✅  Installation Complete!                      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  To launch the app, run:"
echo -e "${BOLD}    ./start-desktop-app.sh${NC}"
echo ""
echo -e "  To build a distributable .dmg installer, run:"
echo -e "${BOLD}    python3 package.py${NC}"
echo ""
