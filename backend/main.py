from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fpdf import FPDF
import datetime
import json
import os
from dropbox_upload import upload_to_dropbox, create_dropbox_folder_structure
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
access_token = os.getenv("DROPBOX_ACCESS_TOKEN")

app = FastAPI(title="AnalizaPC API", version="1.0.0")

# Configurar CORS para permitir requests desde Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SysInfo(BaseModel):
    cpu_model: str = ""
    cpu_speed_ghz: float = 1.0
    cores: int = 1
    ram_gb: float = 1.0
    disk_type: str = "HDD"
    gpu_model: str = ""
    gpu_vram_gb: float = 0.0

def score_system(info: dict):
    """
    Calcula scores para diferentes perfiles de uso
    """
    cpu = info.get('cpu_speed_ghz', 1.0) * info.get('cores', 1)
    ram = info.get('ram_gb', 1.0)
    gpu = info.get('gpu_vram_gb', 0.0)
    disk = 1.0 if info.get('disk_type','').lower() == 'nvme' else 0.6 if 'ssd' in info.get('disk_type','').lower() else 0.2

    # Normalizar valores
    cpu_norm = min(cpu / 8.0, 1.0)
    ram_norm = min(ram / 32.0, 1.0)
    gpu_norm = min(gpu / 8.0, 1.0)

    # Pesos para cada perfil
    profiles = {
        "Ofimática": 0.4 * cpu_norm + 0.4 * ram_norm + 0.2 * disk,
        "Gaming": 0.25 * cpu_norm + 0.4 * gpu_norm + 0.2 * ram_norm + 0.15 * disk,
        "Edición vídeo": 0.3 * cpu_norm + 0.3 * gpu_norm + 0.3 * ram_norm + 0.1 * disk,
        "Virtualización": 0.45 * cpu_norm + 0.45 * ram_norm + 0.1 * disk,
        "ML ligero": 0.2 * cpu_norm + 0.6 * gpu_norm + 0.2 * ram_norm,
    }
    
    sorted_profiles = sorted(profiles.items(), key=lambda x: x[1], reverse=True)
    main_profile, main_score = sorted_profiles[0]
    
    return {
        "scores": profiles, 
        "main_profile": main_profile, 
        "main_score": round(main_score * 100, 1)
    }

def create_pdf_report(sysinfo: dict, result: dict):
    """
    Crea un reporte PDF con los resultados del análisis
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "AnalizaPC - Informe de Sistema", ln=True, align="C")
    pdf.ln(10)
    
    # Fecha
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    
    # Perfil principal
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Perfil principal: {result['main_profile']} ({result['main_score']}%)", ln=True)
    pdf.ln(5)
    
    # Hardware detectado
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Hardware detectado:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"CPU: {sysinfo.get('cpu_model', 'N/A')} ({sysinfo.get('cores', 1)} núcleos)", ln=True)
    pdf.cell(0, 6, f"RAM: {sysinfo.get('ram_gb', 0)} GB", ln=True)
    pdf.cell(0, 6, f"GPU: {sysinfo.get('gpu_model', 'N/A')} ({sysinfo.get('gpu_vram_gb', 0)} GB VRAM)", ln=True)
    pdf.cell(0, 6, f"Almacenamiento: {sysinfo.get('disk_type', 'N/A')}", ln=True)
    pdf.ln(5)
    
    # Scores por perfil
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Adecuación por perfiles:", ln=True)
    pdf.set_font("Arial", "", 10)
    
    for profile, score in result['scores'].items():
        pdf.cell(0, 6, f"- {profile}: {round(score * 100, 1)}%", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 6, "Generado por AnalizaPC - Sistema de análisis gratuito", ln=True)
    
    # Guardar localmente
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"report_{timestamp}.pdf"
    pdf.output(pdf_filename)
    
    return pdf_filename

@app.on_event("startup")
async def startup_event():
    """Crear carpeta en Dropbox al iniciar"""
    if access_token:
        create_dropbox_folder_structure(access_token)
        print("✅ Dropbox listo")

@app.get("/")
def read_root():
    return {"message": "AnalizaPC API funcionando correctamente"}

@app.post("/api/analyze")
def analyze(sysinfo: SysInfo):
    """
    Endpoint principal para analizar el sistema - VERSIÓN SIMPLE
    """
    info = sysinfo.dict()
    result = score_system(info)
    
    # Crear reporte PDF
    pdf_filename = create_pdf_report(info, result)
    
    # Crear archivo JSON con datos completos
    json_filename = pdf_filename.replace(".pdf", ".json")
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "sysinfo": info, 
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    # URLs para los resultados
    pdf_url = None
    json_url = None
    
    # Subir a Dropbox si hay token configurado
    if access_token and access_token != "tu_token_de_dropbox_aqui":
        try:
            # 📁 SUBIR DIRECTAMENTE A CARPETA PRINCIPAL
            # Sin organizar por desarrollador - TODO VA A LA MISMA CARPETA
            pdf_dropbox_path = f"/AnalizaPC-Reports/{pdf_filename}"
            pdf_url, pdf_error = upload_to_dropbox(access_token, pdf_filename, pdf_dropbox_path)
            
            json_dropbox_path = f"/AnalizaPC-Reports/{json_filename}"
            json_url, json_error = upload_to_dropbox(access_token, json_filename, json_dropbox_path)
            
            if pdf_error:
                print(f"❌ Error subiendo PDF: {pdf_error}")
            if json_error:
                print(f"❌ Error subiendo JSON: {json_error}")
            else:
                print(f"✅ Archivos subidos a Dropbox: {pdf_filename}, {json_filename}")
                
        except Exception as e:
            print(f"❌ Error en subida a Dropbox: {e}")
    else:
        print("⚠️ Token de Dropbox no configurado - Saltando subida")
    
    # Limpiar archivos locales
    try:
        os.remove(pdf_filename)
        os.remove(json_filename)
    except Exception as e:
        print(f"⚠️ Error limpiando archivos locales: {e}")
    
    return {
        "status": "success",
        "pdf_url": pdf_url,
        "json_url": json_url, 
        "result": result,
        "message": "Análisis completado correctamente"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)