#!/bin/bash
# Fast Video Downloader — Desktop App Launcher (macOS / Linux)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=================================================="
echo " Fast Video Downloader — Starting Desktop App"
echo "=================================================="
echo ""

# ── Install / verify dependencies ──────────────────────────────────────────
bash "$DIR/install-dependencies.sh"
if [ $? -ne 0 ]; then
    echo "[ERROR] Dependency installation failed. Cannot continue."
    exit 1
fi

# ── Start backend API server ───────────────────────────────────────────────
echo "Starting Backend API Server (port 8000)..."
"$DIR/backend/venv/bin/python" -m uvicorn main:app \
    --host 127.0.0.1 --port 8000 \
    --app-dir "$DIR/backend" &
BACKEND_PID=$!

# ── Start frontend dev server ──────────────────────────────────────────────
echo "Starting Frontend Dev Server (port 5174)..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# ── Wait for servers to be ready ──────────────────────────────────────────
echo ""
echo "Waiting for servers to initialize (10 seconds)..."
sleep 10

# ── Launch Electron desktop app ────────────────────────────────────────────
echo "Launching Fast Video Downloader Desktop Application..."
cd "$DIR/frontend"
npm run app
APP_EXIT=$?

# ── Cleanup ────────────────────────────────────────────────────────────────
echo ""
echo "Application closed. Stopping background servers..."
kill $BACKEND_PID 2>/dev/null || true
kill $FRONTEND_PID 2>/dev/null || true
wait $BACKEND_PID 2>/dev/null || true
wait $FRONTEND_PID 2>/dev/null || true
echo "Done."
exit $APP_EXIT
