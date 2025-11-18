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

print("🚀 CARGANDO VERSIÓN COMPATIBLE CON RENDER - " + datetime.datetime.now().strftime("%H:%M:%S"))

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
#   PDF COMPATIBLE CON RENDER - FUENTES POR DEFECTO
# -------------------------
class PDF(FPDF):
    def header(self):
        # FONDO DE ENCABEZADO
        self.set_fill_color(10, 15, 30)
        self.rect(0, 0, 210, 50, 'F')
        
        # TÍTULO PRINCIPAL CON HELVETICA (BOLD) - CENTRADO
        self.set_font("Helvetica", "B", 34)  # Helvetica es gruesa y moderna
        self.set_text_color(76, 201, 240)
        self.cell(0, 20, "ANALIZATUPC", ln=True, align="C")
        
        # SUBTÍTULO CON HELVETICA ITALIC - CENTRADO
        self.set_font("Helvetica", "I", 16)
        self.set_text_color(200, 230, 255)
        self.cell(0, 10, "Análisis Profesional de Hardware", ln=True, align="C")
        
        # LÍNEA DECORATIVA
        self.set_draw_color(0, 245, 212)
        self.set_line_width(2)
        self.line(40, 42, 170, 42)
        
        self.ln(20)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 9)  # Helvetica para consistencia
        self.set_text_color(100, 100, 100)
        
        # LÍNEA SEPARADORA
        self.set_draw_color(76, 201, 240)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)
        
        # INFORMACIÓN DEL FOOTER
        self.cell(0, 6, f"Reporte profesional • Generado el {datetime.datetime.now().strftime('%d/%m/%Y')} • Página {self.page_no()}", align="C")

    def add_section_title(self, title):
        self.ln(12)
        # TÍTULO DE SECCIÓN CENTRADO CON HELVETICA BOLD
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(76, 201, 240)
        
        # CALCULAR ANCHO PARA CENTRAR PERFECTAMENTE
        title_width = self.get_string_width(f" {title.upper()} ")
        page_width = 210
        x_position = (page_width - title_width) / 2
        
        self.set_x(x_position)
        self.cell(title_width, 12, f" {title.upper()} ", ln=True, fill=True, align='C')
        self.ln(8)

    def add_feature_card(self, title, value, highlight=False):
        # TEXTO CON HELVETICA
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 30, 30)
        self.cell(65, 8, f"{title}:", border=0)
        
        self.set_font("Helvetica", "B" if highlight else "", 11)
        if highlight:
            self.set_text_color(247, 37, 133)
        else:
            self.set_text_color(0, 0, 0)
            
        self.cell(0, 8, str(value), ln=True)
        self.ln(4)

    def add_score_meter(self, profile, score, rank):
        self.set_font("Helvetica", "B", 12)
        
        # DETERMINAR COLOR SEGÚN PUNTUACIÓN
        if score >= 80:
            color = (0, 245, 212)  # Verde neón
            symbol = "★★★★★"
        elif score >= 60:
            color = (76, 201, 240)  # Azul neón
            symbol = "★★★★"
        elif score >= 40:
            color = (255, 193, 7)   # Amarillo dorado
            symbol = "★★★"
        else:
            color = (247, 37, 133)  # Rosa neón
            symbol = "★★"
        
        # TARJETA DE PUNTUACIÓN
        self.set_draw_color(*color)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f" {symbol} {profile}: {score}% • Posición {rank} ", ln=True, fill=True, border=1)
        self.ln(6)

# -------------------------
#   GENERACIÓN DEL PDF COMPATIBLE
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict):
    pdf = PDF()
    pdf.add_page()

    # PORTADA ESPECTACULAR
    pdf.set_font("Helvetica", "B", 38)  # Helvetica para título grande
    pdf.set_text_color(76, 201, 240)
    pdf.cell(0, 60, "INFORME DE SISTEMA", ln=True, align="C")
    
    pdf.set_font("Helvetica", "I", 20)  # Helvetica italic para subtítulo
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 25, "Evaluación Profesional de Hardware", ln=True, align="C")
    
    # LÍNEA DECORATIVA CENTRAL
    pdf.set_draw_color(0, 245, 212)
    pdf.set_line_width(3)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(40)
    
    # PERFIL PRINCIPAL SUPER DESTACADO
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(247, 37, 133)
    pdf.cell(0, 18, " PERFIL PRINCIPAL RECOMENDADO ", ln=True, align="C", fill=True)
    
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 30)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 20, f"{result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(0, 245, 212)
    pdf.cell(0, 15, f"{result['main_score']}% DE EFECTIVIDAD", ln=True, align="C")
    
    pdf.ln(35)
    
    # CÓDIGO DE REPORTE ELEGANTE
    pdf.set_font("Helvetica", "I", 12)  # Helvetica para texto normal
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"ID: APC-{int(datetime.datetime.now().timestamp())}", ln=True, align="C")

    # NUEVA PÁGINA - DETALLES TÉCNICOS
    pdf.add_page()
    
    # SECCIÓN: ESPECIFICACIONES EN TABLA MEJORADA - TÍTULO CENTRADO
    pdf.add_section_title("Especificaciones del Sistema")
    
    # CABECERA DE TABLA MEJORADA
    pdf.set_fill_color(30, 60, 120)
    pdf.set_font("Helvetica", "B", 13)  # Helvetica en negrita para cabecera
    pdf.set_text_color(255, 255, 255)
    pdf.cell(85, 12, "COMPONENTE", border=1, fill=True, align='C')
    pdf.cell(0, 12, "ESPECIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
    # DATOS DE LA TABLA CON MEJOR FORMATO
    specs_data = [
        ("Procesador (CPU)", f"{sysinfo.get('cpu_model', 'No detectado')}"),
        ("Núcleos / Hilos", f"{sysinfo.get('cores', '?')} núcleos"),
        ("Velocidad de CPU", f"{sysinfo.get('cpu_speed_ghz', '?')} GHz"),
        ("Memoria RAM", f"{sysinfo.get('ram_gb', '?')} GB"),
        ("Tarjeta Gráfica (GPU)", f"{sysinfo.get('gpu_model', 'No detectado')}"),
        ("Memoria de Video", f"{sysinfo.get('gpu_vram_gb', '0')} GB VRAM"),
        ("Sistema de Almacenamiento", f"{sysinfo.get('disk_type', 'No detectado')}"),
    ]
    
    pdf.set_font("Helvetica", "", 11)  # Helvetica normal para contenido
    for i, (component, spec) in enumerate(specs_data):
        # FONDO ALTERNADO MÁS SUAVE
        fill_color = (245, 248, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        # COMPONENTE
        pdf.set_text_color(30, 30, 30)
        pdf.cell(85, 10, f"   {component}", border=1, fill=True)
        
        # ESPECIFICACIÓN
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 10, spec, border=1, fill=True, align='C')
        pdf.set_font("Helvetica", "", 11)
        pdf.ln()
    
    # SECCIÓN: RESULTADOS DEL ANÁLISIS - TÍTULO CENTRADO
    pdf.add_section_title("Resultados del Análisis")
    
    # ORDENAR PERFILES POR PUNTUACIÓN
    sorted_scores = sorted(result['scores'].items(), key=lambda x: x[1], reverse=True)
    
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        rank = f"#{i+1}"
        pdf.add_score_meter(profile, score_percent, rank)
    
    # SECCIÓN: TABLA DETALLADA MEJORADA - TÍTULO CENTRADO
    pdf.add_section_title("Tabla de Puntuaciones Detalladas")
    
    # CABECERA DE TABLA MEJORADA
    pdf.set_fill_color(30, 60, 120)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(105, 12, "PERFIL DE USO", border=1, fill=True, align='C')
    pdf.cell(50, 12, "PUNTUACIÓN", border=1, fill=True, align='C')
    pdf.cell(0, 12, "CLASIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
    # FILAS DE TABLA MEJORADAS
    pdf.set_font("Helvetica", "", 11)
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        
        # FONDO ALTERNADO
        fill_color = (245, 248, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        # PERFIL
        pdf.set_text_color(30, 30, 30)
        pdf.cell(105, 10, f"   {profile}", border=1, fill=True)
        
        # PUNTUACIÓN CON COLOR
        if score_percent >= 80:
            text_color = (0, 245, 212)
            classification = "EXCELENTE"
        elif score_percent >= 60:
            text_color = (76, 201, 240)
            classification = "BUENO"
        elif score_percent >= 40:
            text_color = (255, 193, 7)
            classification = "REGULAR"
        else:
            text_color = (247, 37, 133)
            classification = "MEJORABLE"
        
        pdf.set_text_color(*text_color)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(50, 10, f"{score_percent}%", border=1, fill=True, align='C')
        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 10, classification, border=1, fill=True, align='C')
        pdf.ln()

    # SECCIÓN: RECOMENDACIONES MEJORADA - TÍTULO CENTRADO
    pdf.add_section_title("Recomendaciones y Optimizaciones")
    
    # ANÁLISIS INTELIGENTE PARA RECOMENDACIONES
    recommendations = []
    
    # ANÁLISIS DETALLADO POR COMPONENTE
    cpu_model = sysinfo.get('cpu_model', '').lower()
    ram_gb = sysinfo.get('ram_gb', 0)
    disk_type = sysinfo.get('disk_type', '').lower()
    gpu_vram = sysinfo.get('gpu_vram_gb', 0)
    main_score = result['main_score']
    
    # RECOMENDACIONES ESPECÍFICAS
    if any(x in cpu_model for x in ['i3', 'ryzen 3', 'celeron', 'athlon']):
        recommendations.append("PROCESADOR: Considera actualizar a un procesador de gama media-alta para mejor rendimiento en multitarea")
    elif any(x in cpu_model for x in ['i9', 'ryzen 9', 'threadripper']):
        recommendations.append("PROCESADOR: Excelente elección, ideal para tareas profesionales y gaming exigente")
    
    if ram_gb < 8:
        recommendations.append("MEMORIA RAM: Se recomienda aumentar a mínimo 8GB para un rendimiento básico óptimo")
    elif ram_gb < 16:
        recommendations.append("MEMORIA RAM: 16GB sería ideal para gaming y aplicaciones demandantes")
    elif ram_gb >= 32:
        recommendations.append("MEMORIA RAM: Capacidad excelente para trabajo profesional y multitarea intensiva")
    
    if disk_type == 'hdd':
        recommendations.append("ALMACENAMIENTO: Cambiar a SSD mejorará drásticamente velocidad del sistema")
    elif disk_type == 'nvme':
        recommendations.append("ALMACENAMIENTO: NVMe proporciona la máxima velocidad disponible")
    
    if gpu_vram < 4:
        recommendations.append("GRÁFICA: Considera GPU con más VRAM para gaming y aplicaciones gráficas")
    elif gpu_vram >= 8:
        recommendations.append("GRÁFICA: VRAM suficiente para gaming en alta resolución y edición profesional")
    
    # RECOMENDACIONES GENERALES
    if main_score >= 80:
        recommendations.append("SISTEMA: Excelente equilibrio general, mantén actualizados los controladores")
        recommendations.append("OPTIMIZACIÓN: Considera overclocking controlado para máximo rendimiento")
    elif main_score >= 60:
        recommendations.append("SISTEMA: Buen equilibrio, optimiza configuración de software")
        recommendations.append("MEJORA: Enfócate en el componente con menor puntuación para mejoras")
    else:
        recommendations.append("SISTEMA: Se recomiendan mejoras de hardware para rendimiento óptimo")
        recommendations.append("PRIORIDAD: Actualiza los componentes identificados como críticos")
    
    # RECOMENDACIONES UNIVERSALES
    recommendations.append("MANTENIMIENTO: Limpieza regular y actualización de controladores")
    recommendations.append("SEGURIDAD: Sistema antivirus actualizado y copias de seguridad")
    
    # ESCRIBIR RECOMENDACIONES MEJORADAS
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    
    for i, rec in enumerate(recommendations):
        # DESTACAR CATEGORÍAS EN NEGRITA
        if ':' in rec:
            parts = rec.split(':', 1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(25, 8, f"{i+1}. {parts[0]}:", border=0)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 8, parts[1])
        else:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(15, 8, f"{i+1}.", border=0)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 8, f" {rec}")
        pdf.ln(3)

    # GUARDAR PDF
    timestamp = int(datetime.datetime.now().timestamp())
    pdf_filename = f"AnalizaTuPC_Reporte_{timestamp}.pdf"
    pdf.output(pdf_filename)

    print(f"✅ PDF COMPATIBLE CON RENDER generado: {pdf_filename}")
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

    # CREAR PDF COMPATIBLE
    pdf_filename = create_pdf_report(info, result)

    # GUARDAR JSON
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

    # LIMPIAR ARCHIVOS LOCALES
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
        "message": "Análisis profesional completado",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO ANALIZATUPC - COMPATIBLE CON RENDER...")
    uvicorn.run(app, host="0.0.0.0", port=8000)