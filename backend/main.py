from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fpdf import FPDF
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, SystemAnalysis, create_tables, get_next_analysis_id
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
#   PDF SUPER ELEGANTE - COLORES MÁS CLAROS
# -------------------------
class PDF(FPDF):
    def __init__(self, analysis_id: int):
        super().__init__()
        self.analysis_id = f"APC-{analysis_id:04d}"
    
    def header(self):
        # ENCABEZADO CON AZUL CELESTE
        # Fondo con azul celeste
        self.set_fill_color(173, 216, 230)  # Azul celeste claro
        self.rect(0, 0, 210, 45, 'F')
        
        # Efecto de gradiente (simulado con rectángulos superpuestos)
        self.set_fill_color(135, 206, 235)  # Azul celeste medio
        self.rect(0, 0, 210, 15, 'F')
        
        # TÍTULO PRINCIPAL
        self.set_font("Arial", "B", 28)
        self.set_text_color(0, 0, 139)  # Azul oscuro para contraste
        
        # Efecto de sombra para el título
        self.set_text_color(70, 130, 180)  # Azul acero para sombra
        self.cell(0, 28, "AnalizaTuPc", ln=True, align="C")
        
        # Título principal (sobre la sombra)
        self.set_y(20)
        self.set_text_color(0, 0, 139)  # Azul oscuro principal
        self.set_font("Arial", "B", 28)
        self.cell(0, 8, "AnalizaTuPc", ln=True, align="C")
        
        # Subtítulo elegante
        self.set_y(32)
        self.set_font("Arial", "I", 12)
        self.set_text_color(0, 0, 100)  # Azul oscuro
        self.cell(0, 8, "ANÁLISIS PROFESIONAL DE HARDWARE", ln=True, align="C")
        
        # LÍNEA DECORATIVA MEJORADA
        self.set_draw_color(0, 0, 139)  # Azul oscuro
        self.set_line_width(1.5)
        self.line(30, 42, 180, 42)
        
        # Elementos decorativos en las esquinas
        self.set_draw_color(0, 0, 139)
        self.set_line_width(1)
        # Esquina superior izquierda
        self.line(10, 10, 25, 10)
        self.line(10, 10, 10, 25)
        # Esquina superior derecha
        self.line(185, 10, 200, 10)
        self.line(200, 10, 200, 25)
        
        self.ln(20)

    def footer(self):
        self.set_y(-25)  # Más espacio para el footer
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        
        # Línea separadora
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
        # Información del footer CON EL ID DEL ANÁLISIS
        self.cell(0, 6, f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y')} a las {datetime.datetime.now().strftime('%H:%M')}", align="C")
        self.ln(4)
        self.cell(0, 6, f"Página {self.page_no()}", align="C")
        self.ln(4)
        # ID DEL ANÁLISIS SIEMPRE EN EL FOOTER
        self.set_font("Arial", "B", 9)
        self.set_text_color(70, 130, 180)  # Azul acero
        self.cell(0, 6, f"ID del análisis: {self.analysis_id}", align="C")

    def add_section_title(self, title):
        self.ln(12)
        self.set_font("Arial", "B", 18)
        self.set_text_color(255, 255, 255)  # Texto blanco
        self.set_fill_color(135, 206, 235)  # Azul celeste para fondo
        
        # Borde redondeado simulado
        self.cell(0, 14, f" {title.upper()} ", ln=True, fill=True, align='L')
        
        # Línea decorativa debajo del título
        self.set_draw_color(0, 0, 139)  # Azul oscuro
        self.set_line_width(0.8)
        self.line(15, self.get_y() - 2, 60, self.get_y() - 2)
        self.ln(10)

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
        
        # COLORES MÁS CLAROS Y SUAVES para las puntuaciones
        if score >= 80:
            color = (200, 230, 255)  # Azul muy claro y suave - EXCELENTE
            label = "EXCELENTE"
        elif score >= 60:
            color = (220, 240, 255)  # Azul casi blanco - BUENO
            label = "BUENO"
        elif score >= 40:
            color = (240, 248, 255)  # Azul alice muy claro - REGULAR
            label = "REGULAR"
        else:
            color = (245, 250, 255)  # Casi blanco con tono azul - MEJORABLE
            label = "MEJORABLE"
        
        # Tarjeta de puntuación con borde sutil
        self.set_fill_color(color[0], color[1], color[2])
        self.set_text_color(0, 0, 0)  # Texto negro para mejor contraste
        self.set_draw_color(200, 200, 200)  # Borde gris claro
        self.set_line_width(0.2)  # Borde más delgado
        self.cell(0, 10, f" {label} - {profile}: {score}% ({rank})", border=1, ln=True, fill=True)
        self.ln(5)

# -------------------------
#   GENERACIÓN DEL PDF ELEGANTE
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict, analysis_id: int):
    pdf = PDF(analysis_id)
    pdf.add_page()

    # PORTADA CON AZUL CELESTE
    # Fondo de portada
    pdf.set_fill_color(240, 248, 255)  # Azul alice muy claro
    pdf.rect(0, 45, 210, 160, 'F')
    
    # TÍTULO PRINCIPAL DE PORTADA
    pdf.set_y(60)
    pdf.set_font("Arial", "B", 32)
    pdf.set_text_color(70, 130, 180)  # Azul acero
    
    # Efecto de sombra para el título principal
    pdf.set_text_color(100, 149, 237)  # Azul cornflower para sombra
    pdf.cell(0, 15, "INFORME PROFESIONAL", ln=True, align="C")
    pdf.set_text_color(70, 130, 180)  # Azul acero principal
    pdf.set_y(75)
    pdf.cell(0, 15, "INFORME PROFESIONAL", ln=True, align="C")
    
    # Subtítulo elegante
    pdf.set_y(100)
    pdf.set_font("Arial", "I", 18)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Análisis Completo de Hardware", ln=True, align="C")
    
    # Línea decorativa doble en azules
    pdf.set_draw_color(135, 206, 235)  # Azul celeste
    pdf.set_line_width(1)
    pdf.line(50, 115, 160, 115)
    pdf.set_draw_color(0, 0, 139)  # Azul oscuro
    pdf.set_line_width(0.5)
    pdf.line(55, 117, 155, 117)
    
    pdf.ln(40)
    
    # PERFIL PRINCIPAL DESTACADO CON AZUL CELESTE
    pdf.set_fill_color(200, 230, 255)  # Azul muy claro y suave
    pdf.set_draw_color(173, 216, 230)  # Azul celeste claro para borde
    pdf.set_line_width(1)
    
    # Sombra del recuadro (más sutil)
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(52, pdf.get_y() + 2, 106, 54, 'F')
    
    # Recuadro principal
    pdf.set_fill_color(200, 230, 255)  # Azul muy claro y suave
    pdf.rect(50, pdf.get_y(), 106, 50, 'F')
    
    # Contenido del recuadro
    pdf.set_y(pdf.get_y() + 8)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 0, 139)  # Azul oscuro
    pdf.cell(0, 8, "PERFIL RECOMENDADO", ln=True, align="C")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(0, 0, 100)  # Azul muy oscuro
    pdf.cell(0, 12, f"{result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(70, 130, 180)  # Azul acero
    pdf.cell(0, 10, f"{result['main_score']}% DE EFICIENCIA", ln=True, align="C")
    
    pdf.ln(40)

    # NUEVA PÁGINA - DETALLES TÉCNICOS
    pdf.add_page()
    
    # SECCIÓN: ESPECIFICACIONES DEL SISTEMA EN TABLA
    pdf.add_section_title("Especificaciones del Sistema")
    
    # Crear tabla elegante para especificaciones CON AZUL CELESTE
    pdf.set_fill_color(200, 230, 255)  # Azul muy claro para cabecera
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)  # Texto negro para mejor contraste
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
        fill_color = (245, 250, 255) if i % 2 == 0 else (255, 255, 255)  # Azul muy claro alternado
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
    
    # Cabecera de tabla CON AZUL MUY CLARO
    pdf.set_fill_color(200, 230, 255)  # Azul muy claro
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(0, 0, 0)  # Texto negro
    pdf.cell(100, 10, "PERFIL DE USO", border=1, fill=True, align='C')
    pdf.cell(45, 10, "PUNTUACIÓN", border=1, fill=True, align='C')
    pdf.cell(0, 10, "CLASIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
    # Filas de tabla
    pdf.set_font("Arial", "", 10)
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        
        # Fondo alternado muy suave
        fill_color = (245, 250, 255) if i % 2 == 0 else (255, 255, 255)  # Azul muy claro alternado
        pdf.set_fill_color(*fill_color)
        
        # Perfil
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, f"   {profile}", border=1, fill=True)
        
        # Puntuación con color EN TONOS AZULES MUY CLAROS
        if score_percent >= 80:
            text_color = (0, 0, 139)  # Azul oscuro para contraste
            classification = "Excelente"
        elif score_percent >= 60:
            text_color = (70, 130, 180)  # Azul acero
            classification = "Bueno"
        elif score_percent >= 40:
            text_color = (100, 149, 237)  # Azul cornflower
            classification = "Regular"
        else:
            text_color = (135, 206, 235)  # Azul celeste
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

    # Guardar PDF CON NUEVO NOMBRE
    pdf_filename = f"analisis_{analysis_id:04d}.pdf"  # Ej: analisis_0001.pdf, analisis_0002.pdf
    pdf.output(pdf_filename)

    print(f"✅ PDF elegante generado: {pdf_filename}")
    return pdf_filename

# -------------------------
#   FUNCIONES AUXILIARES DASHBOARD
# -------------------------
def get_score_class(score):
    """Devuelve la clase CSS según la puntuación"""
    if score >= 80:
        return "score-excelent"
    elif score >= 60:
        return "score-good"
    elif score >= 40:
        return "score-regular"
    else:
        return "score-poor"

def get_score_color(score):
    """Devuelve color hexadecimal según puntuación"""
    if score >= 80:
        return "#38a169"  # Verde
    elif score >= 60:
        return "#3182ce"  # Azul
    elif score >= 40:
        return "#d69e2e"  # Amarillo
    else:
        return "#e53e3e"  # Rojo

# -------------------------
#   API ENDPOINTS
# -------------------------
@app.on_event("startup")
async def startup_event():
    if access_token:
        create_dropbox_folder_structure(access_token)
        print("✅ Dropbox configurado")
    
    # Crear tablas si no existen
    create_tables()
    print("✅ Base de datos configurada")

@app.get("/")
def read_root():
    return {"message": "AnalizaTuPC API v2.0 funcionando", "version": "2.0.0"}

@app.post("/api/analyze")
def analyze(sysinfo: SysInfo, db: Session = Depends(get_db)):
    info = sysinfo.dict()
    result = score_system(info)

    # DEBUG: Ver qué hay en la base de datos
    print("🔍 === DEBUG INICIO ===")
    all_analyses = db.query(SystemAnalysis).all()
    print(f"🔍 ANALISIS EN BD: {len(all_analyses)} registros")
    for analysis in all_analyses:
        print(f"   - ID: {analysis.analysis_id}, CPU: {analysis.cpu_model}, Score: {analysis.main_score}%")

    # OBTENER EL PRÓXIMO ID
    analysis_id = get_next_analysis_id(db)
    print(f"📊 NUEVO ID CALCULADO: {analysis_id}")
    print("🔍 === DEBUG FIN ===")
    
    # Crear PDF ELEGANTE con el ID
    pdf_filename = create_pdf_report(info, result, analysis_id)

    # Guardar JSON
    json_filename = f"analisis_{analysis_id:04d}.json"  # Mismo nombre base
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "sysinfo": info,
            "result": result,
            "analysis_id": analysis_id,
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

    # GUARDAR EN BASE DE DATOS
    db_analysis = SystemAnalysis(
        analysis_id=analysis_id,
        cpu_model=info.get('cpu_model', ''),
        cpu_speed_ghz=info.get('cpu_speed_ghz', 0),
        cores=info.get('cores', 0),
        ram_gb=info.get('ram_gb', 0),
        disk_type=info.get('disk_type', ''),
        gpu_model=info.get('gpu_model', ''),
        gpu_vram_gb=info.get('gpu_vram_gb', 0),
        main_profile=result['main_profile'],
        main_score=result['main_score'],
        pdf_url=pdf_url,
        json_url=json_url
    )
    
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    print(f"💾 Análisis guardado en BD con ID: {analysis_id}")

    # Limpiar archivos locales
    try:
        os.remove(pdf_filename)
        os.remove(json_filename)
    except:
        pass

    return {
        "status": "success",
        "analysis_id": analysis_id,
        "pdf_url": pdf_url,
        "json_url": json_url,
        "result": result,
        "message": "Análisis completado correctamente",
        "version": "2.0.0"
    }

# ==================== DASHBOARD CON GRÁFICOS ====================

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Dashboard HTML con gráficos para visualizar la base de datos"""
    
    # Obtener datos para el dashboard
    analyses = db.query(SystemAnalysis).order_by(SystemAnalysis.analysis_id.desc()).all()
    total_analyses = len(analyses)
    
    # Calcular estadísticas
    avg_score = db.query(func.avg(SystemAnalysis.main_score)).scalar() or 0
    best_analysis = db.query(SystemAnalysis).order_by(SystemAnalysis.main_score.desc()).first()
    latest_analysis = db.query(SystemAnalysis).order_by(SystemAnalysis.created_at.desc()).first()
    
    # Distribución por perfiles
    profiles = db.query(SystemAnalysis.main_profile).all()
    profile_counts = {}
    for profile in profiles:
        profile_name = profile[0]
        profile_counts[profile_name] = profile_counts.get(profile_name, 0) + 1
    
    # Distribución por rangos de puntuación
    score_ranges = {
        "Excelente (80-100%)": db.query(SystemAnalysis).filter(SystemAnalysis.main_score >= 80).count(),
        "Bueno (60-79%)": db.query(SystemAnalysis).filter(SystemAnalysis.main_score >= 60, SystemAnalysis.main_score < 80).count(),
        "Regular (40-59%)": db.query(SystemAnalysis).filter(SystemAnalysis.main_score >= 40, SystemAnalysis.main_score < 60).count(),
        "Mejorable (0-39%)": db.query(SystemAnalysis).filter(SystemAnalysis.main_score < 40).count()
    }
    
    # Datos para gráficos
    profile_chart_data = []
    for profile, count in profile_counts.items():
        profile_chart_data.append(f"{{label: '{profile}', data: {count}, color: '#{hash(profile) % 0xFFFFFF:06x}'}}")
    
    score_chart_data = []
    score_colors = ["#38a169", "#3182ce", "#d69e2e", "#e53e3e"]
    for i, (range_name, count) in enumerate(score_ranges.items()):
        score_chart_data.append(f"{{label: '{range_name}', data: {count}, color: '{score_colors[i]}'}}")
    
    # Evolución temporal (últimos 10 análisis)
    recent_analyses = analyses[:10][::-1]  # Últimos 10, ordenados por fecha
    timeline_labels = []
    timeline_scores = []
    timeline_colors = []
    
    for analysis in recent_analyses:
        timeline_labels.append(f"#{analysis.analysis_id}")
        timeline_scores.append(analysis.main_score)
        timeline_colors.append(get_score_color(analysis.main_score))
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AnalizaTuPC - Dashboard Avanzado</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                color: white;
                margin-bottom: 40px;
                padding: 30px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }}
            
            .header h1 {{
                font-size: 3em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .header p {{
                font-size: 1.3em;
                opacity: 0.9;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }}
            
            .stat-card {{
                background: white;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 12px 35px rgba(0,0,0,0.15);
                text-align: center;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            
            .stat-card:hover {{
                transform: translateY(-8px);
                box-shadow: 0 20px 45px rgba(0,0,0,0.25);
            }}
            
            .stat-number {{
                font-size: 3em;
                font-weight: bold;
                color: #4a5568;
                margin-bottom: 15px;
            }}
            
            .stat-label {{
                color: #718096;
                font-size: 1.2em;
                font-weight: 500;
            }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }}
            
            .chart-container {{
                background: white;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 12px 35px rgba(0,0,0,0.15);
            }}
            
            .chart-title {{
                color: #2d3748;
                margin-bottom: 20px;
                font-size: 1.4em;
                font-weight: 600;
                text-align: center;
            }}
            
            .analyses-section {{
                background: white;
                border-radius: 20px;
                padding: 35px;
                box-shadow: 0 12px 35px rgba(0,0,0,0.15);
                margin-bottom: 40px;
            }}
            
            .section-title {{
                color: #2d3748;
                margin-bottom: 25px;
                font-size: 1.8em;
                font-weight: 600;
                text-align: center;
                border-bottom: 3px solid #e2e8f0;
                padding-bottom: 15px;
            }}
            
            .analysis-card {{
                background: #f7fafc;
                border: 2px solid #e2e8f0;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .analysis-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 5px;
                height: 100%;
                background: #667eea;
            }}
            
            .analysis-card:hover {{
                background: #edf2f7;
                transform: translateX(10px);
                border-color: #cbd5e0;
            }}
            
            .analysis-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            
            .analysis-id {{
                background: #4a5568;
                color: white;
                padding: 8px 20px;
                border-radius: 25px;
                font-weight: bold;
                font-size: 1.1em;
            }}
            
            .analysis-score {{
                font-size: 1.8em;
                font-weight: bold;
            }}
            
            .score-excelent {{ color: #38a169; }}
            .score-good {{ color: #3182ce; }}
            .score-regular {{ color: #d69e2e; }}
            .score-poor {{ color: #e53e3e; }}
            
            .hardware-info {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }}
            
            .hardware-item {{
                background: white;
                padding: 15px;
                border-radius: 12px;
                border-left: 5px solid #667eea;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            }}
            
            .hardware-label {{
                font-weight: bold;
                color: #4a5568;
                font-size: 0.95em;
                margin-bottom: 5px;
            }}
            
            .hardware-value {{
                color: #2d3748;
                font-size: 1.1em;
            }}
            
            .profile-badge {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                font-size: 1em;
                font-weight: 500;
                margin: 10px 0;
            }}
            
            .no-data {{
                text-align: center;
                color: #718096;
                padding: 60px;
                font-size: 1.3em;
            }}
            
            .links {{
                margin-top: 20px;
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }}
            
            .link {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #48bb78;
                color: white;
                padding: 10px 20px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
            }}
            
            .link:hover {{
                background: #38a169;
                transform: translateY(-2px);
            }}
            
            .link-json {{
                background: #4299e1;
            }}
            
            .link-json:hover {{
                background: #3182ce;
            }}
            
            .timestamp {{
                margin-top: 15px;
                color: #718096;
                font-size: 0.9em;
                font-style: italic;
            }}
            
            .chart-wrapper {{
                position: relative;
                height: 300px;
                margin-top: 20px;
            }}
            
            .api-links {{
                text-align: center;
                margin-top: 30px;
            }}
            
            .api-link {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                text-decoration: none;
                margin: 0 10px;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .api-link:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
            }}
            
            @media (max-width: 768px) {{
                .charts-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .hardware-info {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 AnalizaTuPC - Dashboard Avanzado</h1>
                <p>Visualización en tiempo real con gráficos interactivos</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_analyses}</div>
                    <div class="stat-label">Total de Análisis</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{round(avg_score, 1)}%</div>
                    <div class="stat-label">Puntuación Promedio</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(profile_counts)}</div>
                    <div class="stat-label">Perfiles Diferentes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{best_analysis.main_score if best_analysis else 0}%</div>
                    <div class="stat-label">Mejor Puntuación</div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">📈 Distribución por Perfiles</div>
                    <div class="chart-wrapper">
                        <canvas id="profileChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">🎯 Rangos de Puntuación</div>
                    <div class="chart-wrapper">
                        <canvas id="scoreChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">📅 Evolución Reciente</div>
                    <div class="chart-wrapper">
                        <canvas id="timelineChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="analyses-section">
                <h2 class="section-title">🔍 Análisis Detallados</h2>
                
                {"".join([f"""
                <div class="analysis-card">
                    <div class="analysis-header">
                        <div class="analysis-id">Análisis #{analysis.analysis_id}</div>
                        <div class="analysis-score {get_score_class(analysis.main_score)}">{analysis.main_score}%</div>
                    </div>
                    
                    <div class="hardware-info">
                        <div class="hardware-item">
                            <div class="hardware-label">🖥️ CPU</div>
                            <div class="hardware-value">{analysis.cpu_model or "No especificado"}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">⚡ Núcleos</div>
                            <div class="hardware-value">{analysis.cores}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">💾 RAM</div>
                            <div class="hardware-value">{analysis.ram_gb} GB</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">🎮 GPU</div>
                            <div class="hardware-value">{analysis.gpu_model or "No especificado"}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">🚀 VRAM</div>
                            <div class="hardware-value">{analysis.gpu_vram_gb} GB</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">💿 Almacenamiento</div>
                            <div class="hardware-value">{analysis.disk_type}</div>
                        </div>
                    </div>
                    
                    <div class="profile-badge">🎯 {analysis.main_profile}</div>
                    
                    <div class="links">
                        {"<a href='"+analysis.pdf_url+"' class='link' target='_blank'>📄 Ver PDF</a>" if analysis.pdf_url else ""}
                        {"<a href='"+analysis.json_url+"' class='link link-json' target='_blank'>📊 Ver JSON</a>" if analysis.json_url else ""}
                    </div>
                    
                    <div class="timestamp">
                        ⏰ Creado: {analysis.created_at.strftime("%d/%m/%Y %H:%M") if analysis.created_at else "Fecha no disponible"}
                    </div>
                </div>
                """ for analysis in analyses]) if analyses else '<div class="no-data">🎉 ¡No hay análisis en la base de datos!<br><small>Realiza el primer análisis para ver datos aquí.</small></div>'}
            </div>
            
            <div class="api-links">
                <a href="/api/analyses" class="api-link" target="_blank">📋 API - Todos los análisis</a>
                <a href="/api/stats" class="api-link" target="_blank">📊 API - Estadísticas</a>
                <a href="/" class="api-link" target="_blank">🚀 API Principal</a>
            </div>
            
            <div style="text-align: center; color: white; margin-top: 50px; opacity: 0.8;">
                <p>AnalizaTuPC Dashboard Avanzado • {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </div>
        </div>
        
        <script>
            // Datos para gráficos
            const profileData = [{', '.join(profile_chart_data)}];
            const scoreData = [{', '.join(score_chart_data)}];
            const timelineData = {{
                labels: {json.dumps(timeline_labels)},
                scores: {json.dumps(timeline_scores)},
                colors: {json.dumps(timeline_colors)}
            }};
            
            // Gráfico de distribución por perfiles
            new Chart(document.getElementById('profileChart'), {{
                type: 'doughnut',
                data: {{
                    labels: profileData.map(p => p.label),
                    datasets: [{{
                        data: profileData.map(p => p.data),
                        backgroundColor: profileData.map(p => p.color),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 20,
                                usePointStyle: true
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Distribución por Perfil'
                        }}
                    }}
                }}
            }});
            
            // Gráfico de rangos de puntuación
            new Chart(document.getElementById('scoreChart'), {{
                type: 'bar',
                data: {{
                    labels: scoreData.map(s => s.label),
                    datasets: [{{
                        data: scoreData.map(s => s.data),
                        backgroundColor: scoreData.map(s => s.color),
                        borderWidth: 0,
                        borderRadius: 8
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: true,
                            text: 'Análisis por Rango de Puntuación'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }}
                        }}
                    }}
                }}
            }});
            
            // Gráfico de evolución temporal
            new Chart(document.getElementById('timelineChart'), {{
                type: 'line',
                data: {{
                    labels: timelineData.labels,
                    datasets: [{{
                        label: 'Puntuación',
                        data: timelineData.scores,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: timelineData.colors,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Evolución de Puntuaciones'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
            
            // Auto-refresh cada 45 segundos
            setTimeout(() => {{
                window.location.reload();
            }}, 45000);
            
            // Efectos de hover mejorados
            document.querySelectorAll('.analysis-card').forEach(card => {{
                card.addEventListener('mouseenter', function() {{
                    this.style.boxShadow = '0 15px 40px rgba(0,0,0,0.2)';
                }});
                card.addEventListener('mouseleave', function() {{
                    this.style.boxShadow = 'none';
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# ==================== ENDPOINTS DE BASE DE DATOS ====================

@app.get("/api/analyses")
def get_all_analyses(db: Session = Depends(get_db)):
    """Obtener todos los análisis"""
    try:
        analyses = db.query(SystemAnalysis).order_by(SystemAnalysis.analysis_id.desc()).all()
        
        return {
            "status": "success",
            "total": len(analyses),
            "analyses": [
                {
                    "analysis_id": a.analysis_id,
                    "cpu_model": a.cpu_model,
                    "cpu_speed_ghz": a.cpu_speed_ghz,
                    "cores": a.cores,
                    "ram_gb": a.ram_gb,
                    "gpu_model": a.gpu_model,
                    "main_profile": a.main_profile,
                    "main_score": a.main_score,
                    "pdf_url": a.pdf_url,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in analyses
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Obtener un análisis específico por ID"""
    try:
        analysis = db.query(SystemAnalysis).filter(SystemAnalysis.analysis_id == analysis_id).first()
        
        if not analysis:
            return {"status": "error", "message": "Análisis no encontrado"}
        
        return {
            "status": "success",
            "analysis": {
                "analysis_id": analysis.analysis_id,
                "cpu_model": analysis.cpu_model,
                "cpu_speed_ghz": analysis.cpu_speed_ghz,
                "cores": analysis.cores,
                "ram_gb": analysis.ram_gb,
                "disk_type": analysis.disk_type,
                "gpu_model": analysis.gpu_model,
                "gpu_vram_gb": analysis.gpu_vram_gb,
                "main_profile": analysis.main_profile,
                "main_score": analysis.main_score,
                "pdf_url": analysis.pdf_url,
                "json_url": analysis.json_url,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Estadísticas de los análisis"""
    try:
        total_analyses = db.query(SystemAnalysis).count()
        
        # Análisis por perfil
        profiles = db.query(SystemAnalysis.main_profile).all()
        profile_counts = {}
        for profile in profiles:
            profile_name = profile[0]
            profile_counts[profile_name] = profile_counts.get(profile_name, 0) + 1
        
        # Promedio de puntuación
        avg_score = db.query(func.avg(SystemAnalysis.main_score)).scalar()
        
        return {
            "status": "success",
            "total_analyses": total_analyses,
            "average_score": round(avg_score, 2) if avg_score else 0,
            "profiles_distribution": profile_counts
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/analyses/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Eliminar un análisis por ID"""
    try:
        analysis = db.query(SystemAnalysis).filter(SystemAnalysis.analysis_id == analysis_id).first()
        
        if not analysis:
            return {"status": "error", "message": "Análisis no encontrado"}
        
        db.delete(analysis)
        db.commit()
        
        return {"status": "success", "message": f"Análisis {analysis_id} eliminado correctamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO VERSIÓN ELEGANTE...")
    uvicorn.run(app, host="0.0.0.0", port=8000)