@echo off
title Fast Video Downloader — Launcher
cd /d "%~dp0backend"
echo Starting launcher on port 9999...
python launcher.py
pause
