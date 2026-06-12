const { app, BrowserWindow, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess = null;

ipcMain.handle('start-backend', async () => {
  if (!app.isPackaged) {
    if (backendProcess && backendProcess.exitCode === null) {
      return { status: 'already_running' };
    }
    const backendDir = path.join(__dirname, '..', 'backend');
    const pythonExe = process.platform === 'win32'
      ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
      : path.join(backendDir, 'venv', 'bin', 'python');
    backendProcess = spawn(pythonExe, ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], {
      cwd: backendDir,
      windowsHide: true,
    });
    return { status: 'started' };
  }
  if (backendProcess && backendProcess.exitCode === null) {
    return { status: 'already_running' };
  }
  startBackend();
  return { status: 'started' };
});

function startBackend() {
  if (!app.isPackaged) return;

  const backendPath = path.join(
    process.resourcesPath,
    'bin',
    process.platform === 'win32' ? 'backend.exe' : 'backend'
  );

  console.log(`Spawning sidecar backend at: ${backendPath}`);
  backendProcess = spawn(backendPath, [], {
    cwd: path.join(process.resourcesPath, 'bin'),
    windowsHide: true,
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data}`);
  });

  backendProcess.on('error', (err) => {
    console.error(`Backend failed to start: ${err.message}`);
  });
}

function waitForBackend(timeoutMs = 30000, intervalMs = 500) {
  return new Promise((resolve) => {
    if (!app.isPackaged) {
      return resolve();
    }

    const startTime = Date.now();

    function poll() {
      const req = http.request(
        { hostname: '127.0.0.1', port: 8000, path: '/health', method: 'GET', timeout: intervalMs },
        (res) => {
          if (res.statusCode === 200) {
            console.log('Backend is ready!');
            resolve();
          } else {
            retry();
          }
          res.resume();
        }
      );
      req.on('error', retry);
      req.on('timeout', () => { req.destroy(); retry(); });
      req.end();
    }

    function retry() {
      if (Date.now() - startTime > timeoutMs) {
        console.warn('Backend did not start in time — opening window anyway');
        resolve();
        return;
      }
      setTimeout(poll, intervalMs);
    }

    poll();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 768,
    minHeight: 620,
    title: "Fast Video Downloader",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs')
    },
    backgroundColor: '#09090b',
    autoHideMenuBar: true,
    show: false,
  });

  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  } else {
    mainWindow.loadURL('http://localhost:5174');
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', async () => {
  startBackend();
  await waitForBackend(30000, 500);
  createWindow();
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('will-quit', () => {
  if (backendProcess) {
    console.log('Terminating backend sidecar...');
    backendProcess.kill();
  }
});
