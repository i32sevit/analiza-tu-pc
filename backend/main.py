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

app = FastAPI(title="AnalizaTuPC API", version="2.0.0")

print("🚀 CARGANDO VERSIÓN NUEVA MEJORADA - " + datetime.datetime.now().strftime("%H:%M:%S"))

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
        "Edición Vídeo": 0.3 * cpu_norm + 0.3 * gpu_norm + 0.3 * ram_norm + 0.1 * disk,
        "Virtualización": 0.45 * cpu_norm + 0.45 * ram_norm + 0.1 * disk,
        "ML Ligero": 0.2 * cpu_norm + 0.6 * gpu_norm + 0.2 * ram_norm,
    }

    sorted_profiles = sorted(profiles.items(), key=lambda x: x[1], reverse=True)
    main_profile, main_score = sorted_profiles[0]

    return {
        "scores": profiles,
        "main_profile": main_profile,
        "main_score": round(main_score * 100, 1)
    }

# -------------------------
#   PDF SUPER ELEGANTE - ESTILO ANALIZATUPC
# -------------------------
class PDF(FPDF):
    def header(self):
        # Encabezado estilo moderno con gradiente
        self.set_fill_color(30, 60, 120)  # Azul oscuro elegante
        self.rect(0, 0, 210, 40, 'F')
        
        # Título principal con estilo
        self.set_font("Arial", "B", 24)
        self.set_text_color(76, 201, 240)  # Azul claro del diseño
        self.cell(0, 25, "ANALIZA TU PC", ln=True, align="C")
        
        # Línea decorativa
        self.set_draw_color(76, 201, 240)
        self.set_line_width(1)
        self.line(50, 37, 160, 37)
        
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        
        # Línea separadora
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)
        
        # Información del footer
        self.cell(0, 6, f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y')} a las {datetime.datetime.now().strftime('%H:%M')}", align="C")
        self.ln(4)
        self.cell(0, 6, f"Página {self.page_no()}", align="C")

    def add_section_title(self, title):
        self.ln(10)
        self.set_font("Arial", "B", 16)
        self.set_text_color(30, 60, 120)
        self.set_fill_color(240, 245, 255)  # Fondo azul muy claro
        self.cell(0, 12, f" {title.upper()}", ln=True, fill=True)
        self.ln(8)

    def add_feature_card(self, title, value, highlight=False):
        self.set_font("Arial", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(60, 8, f"{title}:", border=0)
        
        self.set_font("Arial", "B" if highlight else "", 11)
        if highlight:
            self.set_text_color(220, 0, 0)
        else:
            self.set_text_color(0, 0, 0)
            
        self.cell(0, 8, str(value), ln=True)
        self.ln(3)

    def add_score_meter(self, profile, score, rank):
        self.set_font("Arial", "B", 12)
        
        # Determinar color según puntuación (igual que en tu HTML)
        if score >= 80:
            color = (0, 245, 212)  # Verde éxito
            label = "EXCELENTE"
        elif score >= 60:
            color = (76, 201, 240)  # Azul primario
            label = "BUENO"
        elif score >= 40:
            color = (247, 37, 133)  # Rosa warning
            label = "REGULAR"
        else:
            color = (114, 9, 183)   # Púrpura accent
            label = "MEJORABLE"
        
        # Tarjeta de puntuación
        self.set_fill_color(color[0], color[1], color[2])
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f" {label} - {profile}: {score}% ({rank})", ln=True, fill=True)
        self.ln(5)

# -------------------------
#   GENERACIÓN DEL PDF ELEGANTE
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict):
    pdf = PDF()
    pdf.add_page()

    # PORTADA ELEGANTE
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 50, "INFORME PROFESIONAL", ln=True, align="C")
    
    pdf.set_font("Arial", "I", 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 20, "Análisis Completo de Hardware", ln=True, align="C")
    
    # Línea decorativa
    pdf.set_draw_color(76, 201, 240)
    pdf.set_line_width(1)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(30)
    
    # PERFIL PRINCIPAL DESTACADO
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(0, 245, 212)  # Verde éxito
    pdf.cell(0, 15, " PERFIL RECOMENDADO ", ln=True, align="C", fill=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, f"{result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(0, 245, 212)
    pdf.cell(0, 12, f"{result['main_score']}% DE EFICIENCIA", ln=True, align="C")
    
    pdf.ln(30)
    
    # INFORMACIÓN ADICIONAL
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, f"ID del análisis: APC-{int(datetime.datetime.now().timestamp())}", ln=True, align="C")

    # NUEVA PÁGINA - DETALLES TÉCNICOS
    pdf.add_page()
    
    # SECCIÓN: ESPECIFICACIONES DEL SISTEMA EN TABLA
    pdf.add_section_title("Especificaciones del Sistema")
    
    # Crear tabla elegante para especificaciones
    pdf.set_fill_color(30, 60, 120)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(80, 10, "COMPONENTE", border=1, fill=True, align='C')
    pdf.cell(0, 10, "ESPECIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
    # Datos de la tabla
    specs_data = [
        ("Procesador (CPU)", f"{sysinfo.get('cpu_model', 'No detectado')}"),
        ("Núcleos", f"{sysinfo.get('cores', '?')} núcleos"),
        ("Velocidad CPU", f"{sysinfo.get('cpu_speed_ghz', '?')} GHz"),
        ("Memoria RAM", f"{sysinfo.get('ram_gb', '?')} GB"),
        ("Tarjeta Gráfica (GPU)", f"{sysinfo.get('gpu_model', 'No detectado')}"),
        ("VRAM GPU", f"{sysinfo.get('gpu_vram_gb', '0')} GB"),
        ("Almacenamiento", f"{sysinfo.get('disk_type', 'No detectado')}"),
    ]
    
    pdf.set_font("Arial", "", 10)
    for i, (component, spec) in enumerate(specs_data):
        # Fondo alternado para mejor lectura
        fill_color = (250, 250, 250) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        # Componente
        pdf.set_text_color(0, 0, 0)
        pdf.cell(80, 10, f"   {component}", border=1, fill=True)
        
        # Especificación
        pdf.cell(0, 10, spec, border=1, fill=True, align='C')
        pdf.ln()
    
    # SECCIÓN: RESULTADOS DEL ANÁLISIS
    pdf.add_section_title("Resultados del Análisis")
    
    # Ordenar perfiles por puntuación
    sorted_scores = sorted(result['scores'].items(), key=lambda x: x[1], reverse=True)
    
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        rank = f"#{i+1}"
        pdf.add_score_meter(profile, score_percent, rank)
    
    # SECCIÓN: TABLA DETALLADA DE PUNTUACIONES
    pdf.add_section_title("Tabla de Puntuaciones Detalladas")
    
    # Cabecera de tabla
    pdf.set_fill_color(30, 60, 120)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, "PERFIL DE USO", border=1, fill=True, align='C')
    pdf.cell(45, 10, "PUNTUACIÓN", border=1, fill=True, align='C')
    pdf.cell(0, 10, "CLASIFICACIÓN", border=1, fill=True, align='C')
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
        
        # Puntuación con color
        if score_percent >= 80:
            text_color = (0, 245, 212)  # Verde éxito
            classification = "Excelente"
        elif score_percent >= 60:
            text_color = (76, 201, 240)  # Azul primario
            classification = "Bueno"
        elif score_percent >= 40:
            text_color = (247, 37, 133)  # Rosa warning
            classification = "Regular"
        else:
            text_color = (114, 9, 183)   # Púrpura accent
            classification = "Mejorable"
        
        pdf.set_text_color(*text_color)
        pdf.cell(45, 10, f"{score_percent}%", border=1, fill=True, align='C')
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, classification, border=1, fill=True, align='C')
        pdf.ln()

    # SECCIÓN: RECOMENDACIONES
    pdf.add_section_title("Recomendaciones y Observaciones")
    
    # Análisis de componentes para recomendaciones
    recommendations = []
    
    # Análisis de CPU
    cpu_model = sysinfo.get('cpu_model', '').lower()
    if any(x in cpu_model for x in ['i3', 'ryzen 3']):
        recommendations.append("Considera actualizar a un procesador de gama media para mejor rendimiento")
    elif any(x in cpu_model for x in ['i9', 'ryzen 9']):
        recommendations.append("Tu procesador es excelente para cualquier tarea demandante")
    
    # Análisis de RAM
    ram_gb = sysinfo.get('ram_gb', 0)
    if ram_gb < 8:
        recommendations.append("Se recomienda aumentar la RAM a al menos 8GB para multitarea")
    elif ram_gb >= 32:
        recommendations.append("Tienes suficiente RAM incluso para tareas muy demandantes")
    
    # Análisis de almacenamiento
    disk_type = sysinfo.get('disk_type', '').lower()
    if disk_type == 'hdd':
        recommendations.append("Cambiar a SSD mejorará drásticamente los tiempos de carga")
    elif disk_type == 'nvme':
        recommendations.append("Tu almacenamiento NVMe es óptimo para máximo rendimiento")
    
    # Análisis de GPU
    gpu_vram = sysinfo.get('gpu_vram_gb', 0)
    if gpu_vram < 4:
        recommendations.append("Considera una GPU con más VRAM para gaming y aplicaciones gráficas")
    
    # Recomendaciones generales basadas en puntuación principal
    main_score = result['main_score']
    if main_score >= 80:
        recommendations.append("Tu sistema está excelentemente equilibrado para la mayoría de tareas")
        recommendations.append("Mantén los controladores actualizados para mantener el rendimiento")
    elif main_score >= 60:
        recommendations.append("Tu sistema tiene un buen equilibrio para uso general")
        recommendations.append("Considera optimizaciones de software para mejorar aún más")
    else:
        recommendations.append("Se recomiendan mejoras de hardware para un rendimiento óptimo")
        recommendations.append("Prioriza actualizar los componentes con menor puntuación")
    
    # Añadir recomendaciones generales
    recommendations.append("Realiza mantenimiento regular del sistema")
    recommendations.append("Mantén el sistema operativo actualizado")
    
    # Escribir recomendaciones
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(80, 80, 80)
    
    for i, rec in enumerate(recommendations):
        pdf.cell(10, 8, f"{i+1}.", border=0)
        pdf.multi_cell(0, 8, f" {rec}")
        pdf.ln(2)

    # Guardar PDF
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"analiza_tu_pc_{timestamp}.pdf"
    pdf.output(pdf_filename)

    print(f"✅ PDF elegante generado: {pdf_filename}")
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
    return {"message": "AnalizaTuPC API v2.0 funcionando", "version": "2.0.0"}

@app.post("/api/analyze")
def analyze(sysinfo: SysInfo):
    info = sysinfo.dict()
    result = score_system(info)

    # Crear PDF ELEGANTE
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
        "message": "Análisis completado correctamente",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO VERSIÓN ELEGANTE...")
    uvicorn.run(app, host="0.0.0.0", port=8000)