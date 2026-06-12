const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  startBackend: () => ipcRenderer.invoke('start-backend'),
  isElectron: true,
});
