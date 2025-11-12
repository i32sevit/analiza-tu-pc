from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fpdf import FPDF
import os, json, datetime
from dropbox_upload import upload_to_dropbox, create_dropbox_folder_structure
from dotenv import load_dotenv
import uvicorn
from io import BytesIO

# Cargar token de Dropbox
load_dotenv()
DROPBOX_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

app = FastAPI(title="AnalizaTuPc API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SysInfo(BaseModel):
    cpu_model: str
    cpu_speed_ghz: float
    cores: int
    ram_gb: float
    disk_type: str
    gpu_model: str
    gpu_vram_gb: float

def score_system(info):
    cpu = info['cpu_speed_ghz'] * info['cores']
    ram = info['ram_gb']
    gpu = info['gpu_vram_gb']
    disk = 1.0 if info['disk_type'].lower() == 'nvme' else 0.6 if 'ssd' in info['disk_type'].lower() else 0.2

    profiles = {
        "Ofimática": 0.4*cpu + 0.4*ram + 0.2*disk,
        "Gaming": 0.25*cpu + 0.4*gpu + 0.2*ram + 0.15*disk,
        "Virtualización": 0.45*cpu + 0.45*ram + 0.1*disk
    }
    sorted_profiles = sorted(profiles.items(), key=lambda x:x[1], reverse=True)
    main_profile, main_score = sorted_profiles[0]

    return {"scores": profiles, "main_profile": main_profile, "main_score": round(main_score,1)}

# --- Crear PDF en memoria ---
def create_pdf_bytes(sysinfo, result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"AnalizaTuPc - Informe",ln=True,align="C")
    pdf.ln(10)
    pdf.set_font("Arial","",12)
    pdf.cell(0,8,f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",ln=True)
    pdf.ln(5)
    pdf.cell(0,10,f"Perfil principal: {result['main_profile']} ({result['main_score']}%)",ln=True)
    pdf.ln(5)
    pdf.set_font("Arial","",10)
    pdf.cell(0,6,f"CPU: {sysinfo['cpu_model']} ({sysinfo['cores']} núcleos @ {sysinfo['cpu_speed_ghz']}GHz)",ln=True)
    pdf.cell(0,6,f"RAM: {sysinfo['ram_gb']} GB",ln=True)
    pdf.cell(0,6,f"GPU: {sysinfo['gpu_model']} ({sysinfo['gpu_vram_gb']} GB VRAM)",ln=True)
    pdf.cell(0,6,f"Disco: {sysinfo['disk_type']}",ln=True)

    pdf_bytes = BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)
    return pdf_bytes

@app.on_event("startup")
def startup_event():
    if DROPBOX_TOKEN:
        create_dropbox_folder_structure(DROPBOX_TOKEN)

@app.post("/api/analyze")
def analyze(sysinfo: SysInfo):
    info = sysinfo.dict()
    result = score_system(info)
    
    # Guardar JSON en disco temporal
    timestamp = int(datetime.datetime.now().timestamp())
    json_file = f"report_{timestamp}.json"
    with open(json_file,"w") as f:
        json.dump({"sysinfo":info,"result":result}, f, indent=2)

    pdf_bytes = create_pdf_bytes(info, result)

    pdf_url = None
    json_url = None
    if DROPBOX_TOKEN:
        # Guardar temporalmente PDF para subir a Dropbox
        temp_pdf_file = f"report_{timestamp}.pdf"
        with open(temp_pdf_file, "wb") as f:
            f.write(pdf_bytes.getbuffer())
        pdf_url,_ = upload_to_dropbox(DROPBOX_TOKEN,temp_pdf_file,f"/AnalizaTuPc/{temp_pdf_file}")
        json_url,_ = upload_to_dropbox(DROPBOX_TOKEN,json_file,f"/AnalizaTuPc/{json_file}")
        os.remove(temp_pdf_file)

    # Limpiar JSON local
    os.remove(json_file)

    # Retornar PDF en memoria + URLs Dropbox
    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{timestamp}.pdf"}
    )

# --- START SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # <-- importante para OpenShift
    uvicorn.run("main:app", host="0.0.0.0", port=port)
