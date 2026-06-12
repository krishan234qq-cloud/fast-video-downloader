#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run dependency installer
"$DIR/install-dependencies.sh"

echo "Starting Backend Services..."
cd "$DIR/backend"
"$DIR/backend/venv/bin/python" launcher.py &
"$DIR/backend/venv/bin/python" -m uvicorn main:app --host 127.0.0.1 --port 8000 &

echo "Starting Frontend Dev Server..."
cd "$DIR/frontend"
npm run dev &

echo "Waiting for application servers to spin up..."
sleep 1

echo "Launching Fast Video Downloader Desktop Application..."
npm run app

echo "Application closed. Cleaning up background services..."
kill $(jobs -p)
