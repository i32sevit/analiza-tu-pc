import dropbox
import os
from datetime import datetime

def upload_to_dropbox(access_token, local_file_path, dropbox_path):
    """
    Sube un archivo a Dropbox
    """
    try:
        dbx = dropbox.Dropbox(access_token)
        
        # Verificar que el archivo local existe
        if not os.path.exists(local_file_path):
            return None, f"Archivo local no encontrado: {local_file_path}"
        
        # Subir el archivo
        with open(local_file_path, "rb") as f:
            file_data = f.read()
        
        # Subir con modo overwrite
        result = dbx.files_upload(
            file_data, 
            dropbox_path, 
            mode=dropbox.files.WriteMode.overwrite
        )
        
        # Crear enlace compartido
        shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        
        # Convertir a enlace de descarga directa
        download_link = shared_link.url.replace('?dl=0', '?dl=1')
        
        return download_link, None
        
    except dropbox.exceptions.ApiError as e:
        return None, f"Error de Dropbox API: {e}"
    except Exception as e:
        return None, f"Error inesperado: {e}"

def create_dropbox_folder_structure(access_token):
    """
    Crear solo la carpeta principal - super simple
    """
    try:
        dbx = dropbox.Dropbox(access_token)
        
        # Crear solo carpeta principal
        folder_path = "/AnalizaPC-Reports"
        try:
            dbx.files_create_folder_v2(folder_path)
            print(f"✅ Carpeta principal creada: {folder_path}")
        except dropbox.exceptions.ApiError as e:
            if not e.error.is_path() or not e.error.get_path().is_conflict():
                print(f"⚠️ Error creando carpeta {folder_path}: {e}")
                    
    except Exception as e:
        print(f"⚠️ Error creando estructura: {e}")