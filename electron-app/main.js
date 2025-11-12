const { app, BrowserWindow } = require('electron');

function createWindow() {
  const win = new BrowserWindow({
    width: 600,
    height: 500,
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  });
  win.loadFile('renderer/index.html');
}

app.whenReady().then(createWindow);
