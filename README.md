# AnalizaTuPc

Sistema distribuido multiplataforma para analizar el hardware de ordenadores.

## ⚠️ Requisitos Previos

### Backend en Render
- **Primero activar** el backend en Render: `https://analizatupc-backend.onrender.com`
- Actualizar `DROPBOX_ACCESS_TOKEN` en el apartado Environment de Render
- Crear archivo `.env` en la carpeta backend con:
```
DROPBOX_ACCESS_TOKEN=tu_token_aqui
```

## 🚀 Instalación y Ejecución

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

### Aplicación Escritorio (Electron)
```bash
cd electron-app
npm install
npm start
```

## 📱 Plataformas Soportadas

| Plataforma | Detección Automática | Análisis Manual | Guardado en Dropbox |
|------------|---------------------|-----------------|---------------------|
| **Móvil** | ❌ | ✅ | ✅ |
| **Escritorio** | ✅ | ✅ | ✅ |

## 🔗 URLs Importantes

- **Backend Principal:** `https://analizatupc-backend.onrender.com`
- **Dashboard:** `/dashboard`
- **Documentación API:** `/docs`

## 📝 Notas

- El backend en Render debe estar activo para análisis completos.
- La aplicación móvil puede funcionar offline con análisis básico, pero no se guardan los informes en Dropbox.
- Los reportes se guardan automáticamente en Dropbox.
- Actualizar el token de Dropbox si expira.