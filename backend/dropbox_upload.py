import dropbox
import os
from datetime import datetime

def upload_to_dropbox(access_token, local_file_path, dropbox_path):
    """
    Sube un archivo a Dropbox - versión corregida para manejar enlaces existentes
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
        
        print(f"✅ Archivo subido a Dropbox: {dropbox_path}")
        
        # Intentar crear enlace compartido
        try:
            shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            download_link = shared_link.url.replace('?dl=0', '?dl=1')
            print(f"✅ Nuevo enlace compartido creado: {download_link}")
            return download_link, None
            
        except dropbox.exceptions.ApiError as e:
            # Si el error es que el enlace ya existe, obtener el enlace existente
            if 'shared_link_already_exists' in str(e):
                try:
                    # Obtener enlaces compartidos existentes
                    shared_links = dbx.sharing_list_shared_links(dropbox_path).links
                    if shared_links:
                        existing_link = shared_links[0].url
                        download_link = existing_link.replace('?dl=0', '?dl=1')
                        print(f"✅ Usando enlace compartido existente: {download_link}")
                        return download_link, None
                    else:
                        return None, f"Error: Enlace ya existe pero no se pudo obtener: {e}"
                except Exception as list_error:
                    return None, f"Error obteniendo enlace existente: {list_error}"
            else:
                return None, f"Error creando enlace compartido: {e}"
        
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