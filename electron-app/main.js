const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let authWindow;
let mainWindow;

function createAuthWindow() {
  authWindow = new BrowserWindow({
    width: 500,
    height: 700,
    show: false,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      webSecurity: false // ← AÑADIR ESTA LÍNEA
    },
    titleBarStyle: 'default'
  });

  authWindow.loadFile('auth.html');

  // Ocultar la barra de menú
  authWindow.setMenuBarVisibility(false);

  authWindow.once('ready-to-show', () => {
    authWindow.show();
    authWindow.center();
  });

  // PERMITIR NAVEGACIÓN EXTERNA
  authWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  authWindow.on('closed', () => {
    authWindow = null;
  });

  return authWindow;
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    resizable: true,  
    minWidth: 800,   
    minHeight: 600, 
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      webSecurity: false
    }
  });

  mainWindow.loadFile('index.html');

  // Ocultar la barra de menú
  mainWindow.setMenuBarVisibility(false);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.center();
  });

  // PERMITIR NAVEGACIÓN EXTERNA
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  // MANEJAR NAVEGACIÓN EN ENLACES
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    
    // Permitir solo navegación local
    if (parsedUrl.protocol !== 'file:') {
      event.preventDefault();
      require('electron').shell.openExternal(navigationUrl);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  return mainWindow;
}

// Verificar el estado de autenticación al iniciar
function checkAuthStatus() {
  // Esta función verifica si hay un token válido o modo invitado
  // En una implementación real, podrías verificar la validez del token
  const token = require('fs').existsSync(path.join(__dirname, 'auth.json')) 
    ? require('./auth.json').token 
    : null;
  
  const isGuest = require('fs').existsSync(path.join(__dirname, 'auth.json')) 
    ? require('./auth.json').isGuest 
    : false;

  return { token, isGuest };
}

app.whenReady().then(() => {
  // Crear ventana de autenticación primero
  createAuthWindow();

  // Manejar el evento de autenticación exitosa desde el renderer
  ipcMain.handle('auth-success', (event, userData) => {
    console.log('Autenticación exitosa:', userData);
    
    // Guardar datos de autenticación (opcional)
    if (userData) {
      const fs = require('fs');
      fs.writeFileSync(
        path.join(__dirname, 'auth.json'),
        JSON.stringify(userData, null, 2)
      );
    }
    
    // Cerrar ventana de auth y abrir ventana principal
    if (authWindow && !authWindow.isDestroyed()) {
      authWindow.close();
    }
    
    createMainWindow();
  });

  // Manejar cierre de ventana de auth (si el usuario cierra la app)
  ipcMain.handle('auth-window-close', () => {
    if (authWindow && !authWindow.isDestroyed()) {
      authWindow.close();
    }
  });

  // Manejar logout
  ipcMain.handle('logout', () => {
    // Eliminar archivo de autenticación
    const fs = require('fs');
    const authFile = path.join(__dirname, 'auth.json');
    if (fs.existsSync(authFile)) {
      fs.unlinkSync(authFile);
    }
    
    // Cerrar ventana principal y abrir ventana de auth
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close();
    }
    
    createAuthWindow();
  });

  // Manejar modo invitado
  ipcMain.handle('guest-mode', () => {
    const fs = require('fs');
    fs.writeFileSync(
      path.join(__dirname, 'auth.json'),
      JSON.stringify({ isGuest: true, timestamp: new Date().toISOString() }, null, 2)
    );
    
    if (authWindow && !authWindow.isDestroyed()) {
      authWindow.close();
    }
    
    createMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createAuthWindow();
  }
});

// Manejar protocolo personalizado (opcional)
app.setAsDefaultProtocolClient('analizatupc');

// Prevenir ventanas múltiples
app.on('second-instance', (event, commandLine, workingDirectory) => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  } else if (authWindow) {
    if (authWindow.isMinimized()) authWindow.restore();
    authWindow.focus();
  }
});

// Solo permitir una instancia de la aplicación
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

// IPC handlers para comunicación entre procesos
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-user-data', () => {
  const fs = require('fs');
  const authFile = path.join(__dirname, 'auth.json');
  if (fs.existsSync(authFile)) {
    return JSON.parse(fs.readFileSync(authFile, 'utf8'));
  }
  return null;
});

ipcMain.handle("open-history", (event, token) => {
    let historyWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    historyWindow.loadURL("http://localhost:8000/history", {
        extraHeaders: `Authorization: Bearer ${token}`
    });
});