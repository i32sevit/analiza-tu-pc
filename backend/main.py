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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
#   MODELO DE ENTRADA
# -------------------------
class SysInfo(BaseModel):
    cpu_model: str = ""
    cpu_speed_ghz: float = 1.0
    cores: int = 1
    ram_gb: float = 1.0
    disk_type: str = "HDD"
    gpu_model: str = ""
    gpu_vram_gb: float = 0.0

# -------------------------
#   FUNCIONES DE SCORE
# -------------------------
def score_system(info: dict):
    cpu = info.get('cpu_speed_ghz', 1.0) * info.get('cores', 1)
    ram = info.get('ram_gb', 1.0)
    gpu = info.get('gpu_vram_gb', 0.0)
    disk = 1.0 if info.get('disk_type', '').lower() == 'nvme' else 0.6 if 'ssd' in info.get('disk_type', '').lower() else 0.2

    cpu_norm = min(cpu / 8.0, 1.0)
    ram_norm = min(ram / 32.0, 1.0)
    gpu_norm = min(gpu / 8.0, 1.0)

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

# -------------------------
#   PDF PERSONALIZADO CON ARIAL
# -------------------------
class PDF(FPDF):
    def header(self):
        logo_path = "logo.png"  # si quieres meter uno
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 30)

        self.set_font("Arial", "B", 16)  # Cambiado a Arial
        self.cell(0, 10, "AnalizaPC - Informe de Sistema", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 8)  # Cambiado a Arial
        self.cell(0, 10, "Generado automáticamente por AnalizaPC", align="C")

# -------------------------
#   CREACIÓN DEL PDF CON ARIAL
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict):
    pdf = PDF()

    # ELIMINADO: No necesitas cargar fuentes externas
    # pdf.add_font("Roboto-Regular", "", "fonts/Roboto-Regular.ttf", uni=True)
    # pdf.add_font("Roboto-Bold", "", "fonts/Roboto-Bold.ttf", uni=True)

    pdf.add_page()

    # Fecha
    pdf.set_font("Arial", "", 12)  # Cambiado a Arial
    pdf.cell(0, 8, f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Perfil principal
    pdf.set_font("Arial", "B", 14)  # Cambiado a Arial
    pdf.cell(0, 10, "Perfil principal detectado:", ln=True)

    pdf.set_font("Arial", "", 12)  # Cambiado a Arial
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f"  {result['main_profile']}  ({result['main_score']}%)", ln=True, fill=True)

    pdf.ln(10)

    # Hardware detectado
    pdf.set_font("Arial", "B", 13)  # Cambiado a Arial
    pdf.cell(0, 10, "Hardware detectado:", ln=True)

    items = [
        ("CPU", f"{sysinfo.get('cpu_model')} ({sysinfo.get('cores')} núcleos)"),
        ("RAM", f"{sysinfo.get('ram_gb')} GB"),
        ("GPU", f"{sysinfo.get('gpu_model')} ({sysinfo.get('gpu_vram_gb')} GB VRAM)"),
        ("Almacenamiento", sysinfo.get('disk_type')),
    ]

    pdf.set_font("Arial", "", 11)  # Cambiado a Arial
    for label, value in items:
        pdf.set_font("Arial", "B", 11)  # Cambiado a Arial
        pdf.cell(50, 8, f"{label}:", border=0)
        pdf.set_font("Arial", "", 11)  # Cambiado a Arial
        pdf.cell(0, 8, value, ln=True)

    pdf.ln(8)

    # Scores por perfil
    pdf.set_font("Arial", "B", 13)  # Cambiado a Arial
    pdf.cell(0, 10, "Adecuación por perfiles:", ln=True)

    pdf.set_font("Arial", "", 11)  # Cambiado a Arial
    pdf.set_fill_color(245, 245, 245)

    for profile, score in result['scores'].items():
        pdf.cell(80, 8, profile, border=1, fill=True)
        pdf.cell(0, 8, f"{round(score * 100, 1)} %", border=1, ln=True)

    pdf.ln(15)

    # Guardar
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"report_{timestamp}.pdf"
    pdf.output(pdf_filename)

    return pdf_filename

# -------------------------
#   API
# -------------------------
@app.on_event("startup")
async def startup_event():
    if access_token:
        create_dropbox_folder_structure(access_token)
        print("✅ Dropbox listo")

@app.get("/")
def read_root():
    return {"message": "AnalizaPC API funcionando correctamente"}

@app.post("/api/analyze")
def analyze(sysinfo: SysInfo):
    info = sysinfo.dict()
    result = score_system(info)

    # Crear PDF
    pdf_filename = create_pdf_report(info, result)

    # Guardar JSON
    json_filename = pdf_filename.replace(".pdf", ".json")
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "sysinfo": info,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    pdf_url = None
    json_url = None

    if access_token and access_token != "tu_token_de_dropbox_aqui":
        try:
            pdf_dropbox_path = f"/AnalizaPC-Reports/{pdf_filename}"
            pdf_url, pdf_error = upload_to_dropbox(access_token, pdf_filename, pdf_dropbox_path)

            json_dropbox_path = f"/AnalizaPC-Reports/{json_filename}"
            json_url, json_error = upload_to_dropbox(access_token, json_filename, json_dropbox_path)

            if pdf_error:
                print(f"❌ Error subiendo PDF: {pdf_error}")
            if json_error:
                print(f"❌ Error subiendo JSON: {json_error}")
            else:
                print(f"✅ Archivos subidos a Dropbox")
        except Exception as e:
            print(f"❌ Error en subida a Dropbox: {e}")

    else:
        print("⚠️ Token Dropbox no configurado")

    # Limpiar archivos locales
    try:
        os.remove(pdf_filename)
        os.remove(json_filename)
    except:
        pass

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