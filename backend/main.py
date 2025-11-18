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

app = FastAPI(title="AnalizaPC API", version="2.0.0")

print("🚀 CARGANDO VERSION NUEVA MEJORADA - " + datetime.datetime.now().strftime("%H:%M:%S"))

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
        "Ofimatica": 0.4 * cpu_norm + 0.4 * ram_norm + 0.2 * disk,
        "Gaming": 0.25 * cpu_norm + 0.4 * gpu_norm + 0.2 * ram_norm + 0.15 * disk,
        "Edicion video": 0.3 * cpu_norm + 0.3 * gpu_norm + 0.3 * ram_norm + 0.1 * disk,
        "Virtualizacion": 0.45 * cpu_norm + 0.45 * ram_norm + 0.1 * disk,
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
#   PDF COMPATIBLE CON ASCII
# -------------------------
class PDF(FPDF):
    def header(self):
        # Encabezado moderno
        self.set_fill_color(30, 60, 120)
        self.rect(0, 0, 210, 35, 'F')
        
        # Titulo principal
        self.set_font("Arial", "B", 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 25, "ANALIZAPC PRO", ln=True, align="C")
        
        # Linea decorativa
        self.set_draw_color(70, 130, 180)
        self.line(50, 32, 160, 32)
        
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        
        # Linea separadora
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)
        
        # Informacion del footer
        self.cell(0, 6, f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y')} a las {datetime.datetime.now().strftime('%H:%M')}", align="C")
        self.ln(4)
        self.cell(0, 6, f"Pagina {self.page_no()} | www.analizapc.com", align="C")

    def add_section(self, title):
        self.ln(10)
        self.set_font("Arial", "B", 16)
        self.set_text_color(30, 60, 120)
        self.set_fill_color(240, 245, 255)
        self.cell(0, 12, f">> {title.upper()}", ln=True, fill=True)
        self.ln(8)

    def add_feature(self, title, value):
        self.set_font("Arial", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(60, 8, f"{title}:", border=0)
        
        self.set_font("Arial", "", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, str(value), ln=True)
        self.ln(3)

    def add_score_card(self, profile, score, rank):
        self.set_font("Arial", "B", 12)
        
        # Determinar color segun puntuacion
        if score >= 80:
            color = (46, 204, 113)  # Verde
            symbol = "[EXCELENTE]"
        elif score >= 60:
            color = (52, 152, 219)  # Azul
            symbol = "[BUENO]"
        elif score >= 40:
            color = (241, 196, 15)  # Amarillo
            symbol = "[REGULAR]"
        else:
            color = (231, 76, 60)   # Rojo
            symbol = "[BAJO]"
        
        # Fondo de la tarjeta
        self.set_fill_color(color[0], color[1], color[2])
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f" {symbol} {profile}: {score}% ({rank})", ln=True, fill=True)
        self.ln(5)

# -------------------------
#   GENERACION DEL PDF
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict):
    pdf = PDF()
    pdf.add_page()

    # PORTADA
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 50, "INFORME TECNICO", ln=True, align="C")
    
    pdf.set_font("Arial", "I", 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 20, "Analisis Profesional de Hardware", ln=True, align="C")
    
    # Linea decorativa
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(1)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(30)
    
    # PERFIL PRINCIPAL
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(46, 204, 113)
    pdf.cell(0, 15, " PERFIL RECOMENDADO ", ln=True, align="C", fill=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, f"{result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(46, 204, 113)
    pdf.cell(0, 12, f"{result['main_score']}% DE EFICIENCIA", ln=True, align="C")
    
    pdf.ln(30)
    
    # INFORMACION ADICIONAL
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, f"ID del analisis: APC-{int(datetime.datetime.now().timestamp())}", ln=True, align="C")

    # NUEVA PAGINA - DETALLES TECNICOS
    pdf.add_page()
    
    # SECCION: HARDWARE DETECTADO
    pdf.add_section("Especificaciones del Sistema")
    
    specs = [
        ("Procesador", f"{sysinfo.get('cpu_model', 'No detectado')}"),
        ("Nucleos", f"{sysinfo.get('cores', '?')} nucleos"),
        ("Velocidad CPU", f"{sysinfo.get('cpu_speed_ghz', '?')} GHz"),
        ("Memoria RAM", f"{sysinfo.get('ram_gb', '?')} GB"),
        ("Tarjeta Grafica", f"{sysinfo.get('gpu_model', 'No detectado')}"),
        ("VRAM GPU", f"{sysinfo.get('gpu_vram_gb', '0')} GB"),
        ("Almacenamiento", f"{sysinfo.get('disk_type', 'No detectado')}"),
    ]
    
    for title, value in specs:
        pdf.add_feature(title, value)
    
    # SECCION: RESULTADOS DEL ANALISIS
    pdf.add_section("Resultados del Analisis")
    
    # Ordenar perfiles por puntuacion
    sorted_scores = sorted(result['scores'].items(), key=lambda x: x[1], reverse=True)
    
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        rank = f"#{i+1}"
        pdf.add_score_card(profile, score_percent, rank)
    
    # SECCION: TABLA DETALLADA
    pdf.add_section("Tabla de Puntuaciones")
    
    # Cabecera de tabla
    pdf.set_fill_color(30, 60, 120)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, "PERFIL", border=1, fill=True, align='C')
    pdf.cell(45, 10, "PUNTUACION", border=1, fill=True, align='C')
    pdf.cell(0, 10, "CLASIFICACION", border=1, fill=True, align='C')
    pdf.ln()
    
    # Filas de tabla
    pdf.set_font("Arial", "", 10)
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        
        # Fondo alternado
        fill_color = (250, 250, 250) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        # Perfil
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, f"   {profile}", border=1, fill=True)
        
        # Puntuacion con color
        if score_percent >= 80:
            text_color = (46, 204, 113)
            classification = "Excelente"
        elif score_percent >= 60:
            text_color = (52, 152, 219)
            classification = "Bueno"
        elif score_percent >= 40:
            text_color = (241, 196, 15)
            classification = "Regular"
        else:
            text_color = (231, 76, 60)
            classification = "Mejorable"
        
        pdf.set_text_color(*text_color)
        pdf.cell(45, 10, f"{score_percent}%", border=1, fill=True, align='C')
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, classification, border=1, fill=True, align='C')
        pdf.ln()

    # Guardar PDF
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"analisis_pro_{timestamp}.pdf"
    pdf.output(pdf_filename)

    print(f"✅ PDF generado: {pdf_filename}")
    return pdf_filename

# -------------------------
#   API
# -------------------------
@app.on_event("startup")
async def startup_event():
    if access_token:
        create_dropbox_folder_structure(access_token)
        print("✅ Dropbox configurado")

@app.get("/")
def read_root():
    return {"message": "AnalizaPC API v2.0 funcionando", "version": "2.0.0"}

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
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "2.0.0"
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
        "message": "Analisis completado",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO VERSION NUEVA...")
    uvicorn.run(app, host="0.0.0.0", port=8000)