@echo off
title Fast Video Downloader Desktop App

rem Run the dependency installer to ensure everything is set up
call "%~dp0install-dependencies.bat"
if %errorlevel% neq 0 (
    echo Dependency check failed. Exiting...
    pause
    exit /b 1
)

echo Starting Backend Services...
start /b cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe launcher.py"
start /b cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo Starting Frontend Dev Server...
cd /d "%~dp0frontend"
start /b cmd /c "npm run dev"

echo Waiting for application servers to spin up...
timeout /t 1 /nobreak > nul

echo Launching Fast Video Downloader Desktop Application...
npm run app

echo Application closed.
pause
