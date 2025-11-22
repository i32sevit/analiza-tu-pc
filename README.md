# AnalizaTuPc

Sistema distribuido multiplataforma para analizar el hardware de ordenadores.

## Requisitos Previos

### Backend en Render
- **Primero activar** el backend en Render: `https://analizatupc-backend.onrender.com`.
- Actualizar `DROPBOX_ACCESS_TOKEN` en el apartado Environment de Render.
- Crear archivo `.env` en /backend/.venv con:
```
DROPBOX_ACCESS_TOKEN=tu_token_aqui
```

## Instalación y Ejecución

### Backend Local
```bash
cd backend
pip install -r requirements.txt
```

### Aplicación Móvil (React Native/Expo)
```bash
cd AnalizaTuPc
npm install
npx expo start
```
Para probar en móvil:

- Instalar la app Expo Go desde tu tienda de aplicaciones.
- Escanear el código QR que aparece en la terminal al ejecutar `npx expo start`.
- La aplicación se cargará en tu dispositivo móvil.

### Aplicación Escritorio (Electron)
```bash
cd electron-app
npm install
npm start
```

### Aplicación Web (Electron)
Para abrir en el navegador:
- Presionar la tecla **W** en la terminal después de ejecutar `npx expo start`.
- Se abrirá automáticamente en `http://localhost:8081`.

## Plataformas Soportadas

| Plataforma | Detección Automática | Análisis Manual | Guardado en Dropbox |
|------------|---------------------|-----------------|---------------------|
| **Móvil** | NO | SÍ | SÍ |
| **Escritorio** | SÍ | SÍ | SÍ |
| **Web** | NO | SÍ | SÍ |

## URLs Importantes

- **Backend Principal:** `https://analizatupc-backend.onrender.com`
- **Dashboard:** `/dashboard`
- **Documentación API:** `/docs`

## Notas

- El backend en Render debe estar activo para análisis completos.
- La aplicación móvil puede funcionar offline con análisis básico, pero no se guardan los informes en Dropbox.
- Los reportes se guardan automáticamente en Dropbox.
- Actualizar el token de Dropbox si expira.
- **Para móvil:** Es necesario tener instalada la app **Expo Go** y escanear el QR generado.
- **Para web:** Después de `npx expo start`, presionar **W** para abrir en el navegador en `localhost:8081`.