#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/backend"
if [ -f "venv/bin/python" ]; then
    venv/bin/python launcher.py
else
    python3 launcher.py
fi
