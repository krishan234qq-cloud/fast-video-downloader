@echo off
title Fast Video Downloader Desktop App
setlocal EnableDelayedExpansion

echo ==================================================
echo  Fast Video Downloader — Starting Desktop App
echo ==================================================
echo.

call "%~dp0install-dependencies.bat"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dependency check/installation failed. Cannot continue.
    pause
    exit /b 1
)

echo.
echo Starting Backend API Server (port 8000)...
start "FVD-Backend" /min cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo Starting Frontend Dev Server (port 5174)...
start "FVD-Frontend" /min cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo Waiting for servers to initialize (10 seconds)...
timeout /t 10 /nobreak > nul

echo.
echo Launching Fast Video Downloader Desktop Application...
cd /d "%~dp0frontend"
call npm run app

echo.
echo Application closed. Stopping background servers...
taskkill /f /fi "WindowTitle eq FVD-Backend*" >nul 2>nul
taskkill /f /fi "WindowTitle eq FVD-Frontend*" >nul 2>nul

echo Done.
endlocal
