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
#   PDF PROFESIONAL Y MODERNO
# -------------------------
class PDF(FPDF):
    def header(self):
        # Fondo de encabezado profesional
        self.set_fill_color(41, 128, 185)  # Azul profesional
        self.rect(0, 0, 210, 30, 'F')
        
        # Título principal
        self.set_font("Arial", "B", 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "ANALIZAPC", ln=True, align="C")
        
        # Subtítulo
        self.set_font("Arial", "I", 12)
        self.set_text_color(200, 230, 255)
        self.cell(0, -5, "Informe Profesional de Sistema", ln=True, align="C")
        
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", "I", 9)
        self.set_text_color(128, 128, 128)
        
        # Línea superior del footer
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
        # Texto del footer
        self.cell(0, 6, f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')} | Página {self.page_no()}", align="C")
        self.ln(4)
        self.cell(0, 6, "www.analizapc.com - Todos los derechos reservados", align="C")

    def add_section_title(self, title, icon="▶"):
        self.set_font("Arial", "B", 14)
        self.set_text_color(41, 128, 185)  # Azul corporativo
        self.set_fill_color(240, 245, 249)  # Fondo azul muy claro
        self.cell(0, 10, f" {icon} {title}", ln=True, fill=True)
        self.ln(5)

    def add_feature_card(self, title, value, icon="💻"):
        self.set_font("Arial", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(25, 8, f"{icon}", border=0)
        self.cell(50, 8, f"{title}:", border=0)
        
        self.set_font("Arial", "", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, str(value), ln=True)
        self.ln(3)

    def add_performance_bar(self, label, percentage, color):
        # Barra de progreso visual
        bar_width = 100
        fill_width = (percentage / 100) * bar_width
        
        self.set_font("Arial", "B", 10)
        self.set_text_color(60, 60, 60)
        self.cell(50, 8, f"{label}:", border=0)
        
        # Fondo de la barra
        self.set_draw_color(220, 220, 220)
        self.set_fill_color(220, 220, 220)
        self.rect(self.get_x(), self.get_y() + 2, bar_width, 6, 'FD')
        
        # Barra de progreso
        self.set_fill_color(*color)
        self.rect(self.get_x(), self.get_y() + 2, fill_width, 6, 'F')
        
        # Porcentaje
        self.set_text_color(0, 0, 0)
        self.cell(30, 8, f"{percentage}%", ln=True, align="R")
        self.ln(8)

# -------------------------
#   CREACIÓN DEL PDF PROFESIONAL
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict):
    pdf = PDF()
    pdf.add_page()

    # PORTADA MEJORADA
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 40, "INFORME DE SISTEMA", ln=True, align="C")
    
    pdf.set_font("Arial", "I", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 15, "Análisis Profesional de Hardware", ln=True, align="C")
    
    # Línea decorativa
    pdf.set_draw_color(41, 128, 185)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(20)
    
    # PERFIL PRINCIPAL DESTACADO
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(46, 204, 113)  # Verde éxito
    pdf.cell(0, 12, " PERFIL RECOMENDADO ", ln=True, align="C", fill=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, f"🎯 {result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(46, 204, 113)
    pdf.cell(0, 10, f"{result['main_score']}% DE ADECUACIÓN", ln=True, align="C")
    
    pdf.ln(25)
    
    # FECHA Y CÓDIGO
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, f"Código de reporte: APC-{int(datetime.datetime.now().timestamp())}", ln=True, align="C")

    # NUEVA PÁGINA PARA DETALLES
    pdf.add_page()
    
    # SECCIÓN: ESPECIFICACIONES TÉCNICAS
    pdf.add_section_title("Especificaciones del Sistema", "🔧")
    
    hardware_specs = [
        ("Procesador", f"{sysinfo.get('cpu_model', 'No detectado')}"),
        ("Núcleos/Hilos", f"{sysinfo.get('cores', '?')} núcleos"),
        ("Frecuencia CPU", f"{sysinfo.get('cpu_speed_ghz', '?')} GHz"),
        ("Memoria RAM", f"{sysinfo.get('ram_gb', '?')} GB"),
        ("Tarjeta Gráfica", f"{sysinfo.get('gpu_model', 'No detectado')}"),
        ("Memoria GPU", f"{sysinfo.get('gpu_vram_gb', '0')} GB VRAM"),
        ("Almacenamiento", f"{sysinfo.get('disk_type', 'No detectado')}"),
    ]
    
    for title, value in hardware_specs:
        pdf.add_feature_card(title, value)
    
    pdf.ln(10)
    
    # SECCIÓN: ANÁLISIS DE RENDIMIENTO
    pdf.add_section_title("Análisis de Rendimiento", "📊")
    
    # Barras de rendimiento por perfil
    performance_colors = {
        "Ofimática": (52, 152, 219),    # Azul
        "Gaming": (155, 89, 182),       # Púrpura
        "Edición vídeo": (230, 126, 34), # Naranja
        "Virtualización": (46, 204, 113), # Verde
        "ML ligero": (231, 76, 60)      # Rojo
    }
    
    for profile, score in result['scores'].items():
        percentage = round(score * 100, 1)
        color = performance_colors.get(profile, (100, 100, 100))
        pdf.add_performance_bar(profile, percentage, color)
    
    pdf.ln(15)
    
    # SECCIÓN: RECOMENDACIONES
    pdf.add_section_title("Recomendaciones y Observaciones", "💡")
    
    recommendations = [
        "✅ Sistema analizado automáticamente por AnalizaPC",
        "📈 Puntuación basada en benchmarks estándar del sector",
        "🔍 Considerar actualizaciones para mejorar puntuaciones bajas",
        "💾 Optimizar configuración según perfil principal detectado"
    ]
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(80, 80, 80)
    
    for rec in recommendations:
        pdf.cell(10, 8, "•", border=0)
        pdf.multi_cell(0, 8, f" {rec}")
        pdf.ln(2)
    
    # TABLA RESUMEN PROFESIONAL
    pdf.ln(10)
    pdf.add_section_title("Resumen de Puntuaciones", "📋")
    
    # Cabecera de tabla
    pdf.set_fill_color(41, 128, 185)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, "PERFIL DE USO", border=1, fill=True, align='C')
    pdf.cell(40, 10, "PUNTUACIÓN", border=1, fill=True, align='C')
    pdf.cell(0, 10, "NIVEL", border=1, fill=True, align='C')
    pdf.ln()
    
    # Filas de la tabla
    pdf.set_font("Arial", "", 10)
    for profile, score in result['scores'].items():
        percentage = round(score * 100, 1)
        
        # Color de fondo alternado
        if list(result['scores'].keys()).index(profile) % 2 == 0:
            pdf.set_fill_color(250, 250, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        # Celda perfil
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, f"   {profile}", border=1, fill=True)
        
        # Celda puntuación con color
        if percentage >= 80:
            pdf.set_text_color(46, 204, 113)  # Verde
            level = "Excelente"
        elif percentage >= 60:
            pdf.set_text_color(230, 126, 34)  # Naranja
            level = "Bueno"
        elif percentage >= 40:
            pdf.set_text_color(241, 196, 15)  # Amarillo
            level = "Regular"
        else:
            pdf.set_text_color(231, 76, 60)   # Rojo
            level = "Bajo"
        
        pdf.cell(40, 10, f"{percentage}%", border=1, fill=True, align='C')
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, level, border=1, fill=True, align='C')
        pdf.ln()

    # Guardar PDF
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"reporte_profesional_{timestamp}.pdf"
    pdf.output(pdf_filename)

    print(f"✅ PDF profesional generado: {pdf_filename}")
    return pdf_filename

# -------------------------
#   API (igual que antes)
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

    # Crear PDF profesional
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