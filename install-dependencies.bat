@echo off
title Fast Video Downloader — Dependency Installer

echo ==================================================
echo Analyzing System Dependencies...
echo ==================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is missing!
    echo Please install Python 3.10+ from https://www.python.org/ and ensure "Add Python to PATH" is checked.
    exit /b 1
)
echo [OK] Python is installed.

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm is missing!
    echo Please install Node.js from https://nodejs.org/ to run the frontend client.
    exit /b 1
)
echo [OK] Node.js / npm is installed.

where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] FFmpeg is missing!
    echo Fast Video Downloader requires FFmpeg to merge high-quality video/audio and trim sections.
    echo Please download FFmpeg and add its "bin" directory to your PATH.
    exit /b 1
)
echo [OK] FFmpeg is installed.

echo ==================================================
echo Installing Backend Virtual Environment & Packages...
echo ==================================================
if not exist "%~dp0backend\venv" (
    echo Creating virtual environment in backend\venv...
    python -m venv "%~dp0backend\venv"
)
echo Upgrading pip and installing python packages...
cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe -m pip install --upgrade pip && venv\Scripts\python.exe -m pip install -r requirements.txt"

echo ==================================================
echo Installing Frontend Packages...
echo ==================================================
if not exist "%~dp0frontend\node_modules" (
    echo Installing node modules in frontend...
)
cmd /c "cd /d %~dp0frontend && npm install"

echo ==================================================
echo [SUCCESS] All dependencies have been installed successfully!
echo ==================================================
