@echo off
title Fast Video Downloader — Dependency Installer
setlocal EnableDelayedExpansion

echo ==================================================
echo  Fast Video Downloader — Dependency Installer
echo ==================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v is installed.

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm is not installed or not in PATH!
    echo.
    echo Please install Node.js (LTS) from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo [OK] Node.js %%v is installed.

where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [WARN] FFmpeg is not found in PATH.
    echo        The app will still work, but video trimming (custom range)
    echo        will not function without FFmpeg.
    echo        Download FFmpeg from https://ffmpeg.org/download.html
    echo        and add its "bin" folder to your system PATH.
    echo.
) else (
    echo [OK] FFmpeg is installed.
)

echo.
echo ==================================================
echo  Installing Backend Virtual Environment and Packages...
echo ==================================================

if not exist "%~dp0backend\venv" (
    echo Creating Python virtual environment in backend\venv...
    python -m venv "%~dp0backend\venv"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

echo Upgrading pip...
"%~dp0backend\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

echo Installing Python packages from requirements.txt...
"%~dp0backend\venv\Scripts\python.exe" -m pip install -r "%~dp0backend\requirements.txt"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)
echo [OK] Python packages installed.

echo.
echo ==================================================
echo  Installing Frontend Node.js Packages...
echo ==================================================

if not exist "%~dp0frontend\node_modules" (
    echo Installing node_modules (this may take a minute)...
) else (
    echo Updating node_modules...
)

pushd "%~dp0frontend"
call npm install
if !errorlevel! neq 0 (
    echo [ERROR] npm install failed.
    popd
    pause
    exit /b 1
)
popd
echo [OK] Node packages installed.

echo.
echo ==================================================
echo  [SUCCESS] All dependencies installed successfully!
echo ==================================================
echo.
endlocal
