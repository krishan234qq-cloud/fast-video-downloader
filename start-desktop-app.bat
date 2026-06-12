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
powershell -windowstyle hidden -Command "Start-Process venv\Scripts\python.exe -ArgumentList '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000' -WorkingDirectory '%~dp0backend' -WindowStyle Hidden"

echo Starting Frontend Dev Server (port 5174)...
powershell -windowstyle hidden -Command "Start-Process npm.cmd -ArgumentList 'run', 'dev' -WorkingDirectory '%~dp0frontend' -WindowStyle Hidden"

echo.
echo Waiting for servers to initialize (10 seconds)...
ping 127.0.0.1 -n 11 > nul

echo.
echo Launching Fast Video Downloader Desktop Application...
cd /d "%~dp0frontend"
call npm run app

echo.
echo Application closed. Stopping background servers...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
powershell -Command "Get-NetTCPConnection -LocalPort 5174 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo Done.
endlocal
