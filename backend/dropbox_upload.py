import dropbox, os

def upload_to_dropbox(token, local_path, dropbox_path):
    dbx = dropbox.Dropbox(token)
    if not os.path.exists(local_path): return None, "Archivo no encontrado"
    with open(local_path,"rb") as f:
        dbx.files_upload(f.read(),dropbox_path,mode=dropbox.files.WriteMode.overwrite)
    shared = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    return shared.url.replace("?dl=0","?dl=1"), None

def create_dropbox_folder_structure(token):
    dbx = dropbox.Dropbox(token)
    try:
        dbx.files_create_folder_v2("/AnalizaTuPc")
    except dropbox.exceptions.ApiError:
        pass
