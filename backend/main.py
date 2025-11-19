from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, ConfigDict  # ACTUALIZADO: añadir ConfigDict
from fpdf import FPDF
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from database import (
    get_db, create_tables, get_next_analysis_id, User, SystemAnalysis  # AÑADIDO: User, SystemAnalysis
)
from auth import create_access_token, get_password_hash, verify_password, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
import datetime
import json
import os
from dropbox_upload import upload_to_dropbox, create_dropbox_folder_structure
from dotenv import load_dotenv
from typing import List, Optional
from jose import JWTError, jwt
from datetime import timedelta

# Cargar variables de entorno
load_dotenv()
access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_muy_segura_aqui_cambiar_en_produccion")
ALGORITHM = "HS256"

app = FastAPI(title="AnalizaTuPC API", version="2.0.0")

print("🚀 CARGANDO VERSIÓN NUEVA MEJORADA CON AUTENTICACIÓN- " + datetime.datetime.now().strftime("%H:%M:%S"))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
#   MODELO DE ENTRADA (ACTUALIZADO)
# -------------------------
class SysInfo(BaseModel):
    cpu_model: str = ""
    cpu_speed_ghz: float = 1.0
    cores: int = 1
    ram_gb: float = 1.0
    disk_type: str = "HDD"
    gpu_model: str = ""
    gpu_vram_gb: float = 0.0

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# ACTUALIZADO: Nueva sintaxis Pydantic v2
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # NUEVA SINTÁXIS
    
    id: int
    username: str
    email: str
    created_at: datetime.datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AnalysisHistory(BaseModel):
    analyses: List[dict]
    total_count: int

# -------------------------
#   FUNCIONES AUXILIARES PARA USUARIOS NO REGISTRADOS
# -------------------------
def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
):
    """
    Función opcional para obtener el usuario actual.
    Si no hay token o es inválido, retorna None.
    """
    if credentials is None:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

def generate_guest_analysis_id():
    """Genera un ID temporal para análisis de invitados"""
    return int(datetime.datetime.now().timestamp())

# -------------------------
#   FUNCIONES DE SCORE (se mantienen igual)
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
#   CLASE PDF (se mantiene igual)
# -------------------------
class PDF(FPDF):
    def __init__(self, analysis_id: int):
        super().__init__()
        self.analysis_id = f"APC-{analysis_id:04d}"
    
    def header(self):
        # ENCABEZADO CON AZUL CELESTE
        self.set_fill_color(173, 216, 230)
        self.rect(0, 0, 210, 45, 'F')
        
        self.set_fill_color(135, 206, 235)
        self.rect(0, 0, 210, 15, 'F')
        
        self.set_font("Arial", "B", 28)
        self.set_text_color(0, 0, 139)
        
        self.set_text_color(70, 130, 180)
        self.cell(0, 28, "AnalizaTuPc", ln=True, align="C")
        
        self.set_y(20)
        self.set_text_color(0, 0, 139)
        self.set_font("Arial", "B", 28)
        self.cell(0, 8, "AnalizaTuPc", ln=True, align="C")
        
        self.set_y(32)
        self.set_font("Arial", "I", 12)
        self.set_text_color(0, 0, 100)
        self.cell(0, 8, "ANÁLISIS PROFESIONAL DE HARDWARE", ln=True, align="C")
        
        self.set_draw_color(0, 0, 139)
        self.set_line_width(1.5)
        self.line(30, 42, 180, 42)
        
        self.set_draw_color(0, 0, 139)
        self.set_line_width(1)
        self.line(10, 10, 25, 10)
        self.line(10, 10, 10, 25)
        self.line(185, 10, 200, 10)
        self.line(200, 10, 200, 25)
        
        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
        self.cell(0, 6, f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y')} a las {datetime.datetime.now().strftime('%H:%M')}", align="C")
        self.ln(4)
        self.cell(0, 6, f"Página {self.page_no()}", align="C")
        self.ln(4)
        
        self.set_font("Arial", "B", 9)
        self.set_text_color(70, 130, 180)
        self.cell(0, 6, f"ID del análisis: {self.analysis_id}", align="C")

    def add_section_title(self, title):
        self.ln(12)
        self.set_font("Arial", "B", 18)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(135, 206, 235)
        self.cell(0, 14, f" {title.upper()} ", ln=True, fill=True, align='L')
        
        self.set_draw_color(0, 0, 139)
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
        
        if score >= 80:
            color = (200, 230, 255)
            label = "EXCELENTE"
        elif score >= 60:
            color = (220, 240, 255)
            label = "BUENO"
        elif score >= 40:
            color = (240, 248, 255)
            label = "REGULAR"
        else:
            color = (245, 250, 255)
            label = "MEJORABLE"
        
        self.set_fill_color(color[0], color[1], color[2])
        self.set_text_color(0, 0, 0)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.cell(0, 10, f" {label} - {profile}: {score}% ({rank})", border=1, ln=True, fill=True)
        self.ln(5)

# -------------------------
#   GENERACIÓN DEL PDF (se mantiene igual)
# -------------------------
def create_pdf_report(sysinfo: dict, result: dict, analysis_id: int):
    pdf = PDF(analysis_id)
    pdf.add_page()

    # PORTADA
    pdf.set_fill_color(240, 248, 255)
    pdf.rect(0, 45, 210, 160, 'F')
    
    pdf.set_y(60)
    pdf.set_font("Arial", "B", 32)
    pdf.set_text_color(70, 130, 180)
    
    pdf.set_text_color(100, 149, 237)
    pdf.cell(0, 15, "INFORME PROFESIONAL", ln=True, align="C")
    pdf.set_text_color(70, 130, 180)
    pdf.set_y(75)
    pdf.cell(0, 15, "INFORME PROFESIONAL", ln=True, align="C")
    
    pdf.set_y(100)
    pdf.set_font("Arial", "I", 18)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Análisis Completo de Hardware", ln=True, align="C")
    
    pdf.set_draw_color(135, 206, 235)
    pdf.set_line_width(1)
    pdf.line(50, 115, 160, 115)
    pdf.set_draw_color(0, 0, 139)
    pdf.set_line_width(0.5)
    pdf.line(55, 117, 155, 117)
    
    pdf.ln(40)
    
    # PERFIL PRINCIPAL
    pdf.set_fill_color(200, 230, 255)
    pdf.set_draw_color(173, 216, 230)
    pdf.set_line_width(1)
    
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(52, pdf.get_y() + 2, 106, 54, 'F')
    
    pdf.set_fill_color(200, 230, 255)
    pdf.rect(50, pdf.get_y(), 106, 50, 'F')
    
    pdf.set_y(pdf.get_y() + 8)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 0, 139)
    pdf.cell(0, 8, "PERFIL RECOMENDADO", ln=True, align="C")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(0, 0, 100)
    pdf.cell(0, 12, f"{result['main_profile']}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(70, 130, 180)
    pdf.cell(0, 10, f"{result['main_score']}% DE EFICIENCIA", ln=True, align="C")
    
    pdf.ln(40)

    # DETALLES TÉCNICOS
    pdf.add_page()
    
    pdf.add_section_title("Especificaciones del Sistema")
    
    pdf.set_fill_color(200, 230, 255)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(80, 10, "COMPONENTE", border=1, fill=True, align='C')
    pdf.cell(0, 10, "ESPECIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
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
        fill_color = (245, 250, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        pdf.set_text_color(0, 0, 0)
        pdf.cell(80, 10, f"   {component}", border=1, fill=True)
        pdf.cell(0, 10, spec, border=1, fill=True, align='C')
        pdf.ln()
    
    pdf.add_section_title("Resultados del Análisis")
    
    sorted_scores = sorted(result['scores'].items(), key=lambda x: x[1], reverse=True)
    
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        rank = f"#{i+1}"
        pdf.add_score_meter(profile, score_percent, rank)
    
    pdf.add_section_title("Tabla de Puntuaciones Detalladas")
    
    pdf.set_fill_color(200, 230, 255)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 10, "PERFIL DE USO", border=1, fill=True, align='C')
    pdf.cell(45, 10, "PUNTUACIÓN", border=1, fill=True, align='C')
    pdf.cell(0, 10, "CLASIFICACIÓN", border=1, fill=True, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", "", 10)
    for i, (profile, score) in enumerate(sorted_scores):
        score_percent = round(score * 100, 1)
        
        fill_color = (245, 250, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, f"   {profile}", border=1, fill=True)
        
        if score_percent >= 80:
            text_color = (0, 0, 139)
            classification = "Excelente"
        elif score_percent >= 60:
            text_color = (70, 130, 180)
            classification = "Bueno"
        elif score_percent >= 40:
            text_color = (100, 149, 237)
            classification = "Regular"
        else:
            text_color = (135, 206, 235)
            classification = "Mejorable"
        
        pdf.set_text_color(*text_color)
        pdf.cell(45, 10, f"{score_percent}%", border=1, fill=True, align='C')
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, classification, border=1, fill=True, align='C')
        pdf.ln()

    pdf.add_section_title("Recomendaciones y Observaciones")
    
    recommendations = []
    
    cpu_model = sysinfo.get('cpu_model', '').lower()
    if any(x in cpu_model for x in ['i3', 'ryzen 3']):
        recommendations.append("Considera actualizar a un procesador de gama media para mejor rendimiento")
    elif any(x in cpu_model for x in ['i9', 'ryzen 9']):
        recommendations.append("Tu procesador es excelente para cualquier tarea demandante")
    
    ram_gb = sysinfo.get('ram_gb', 0)
    if ram_gb < 8:
        recommendations.append("Se recomienda aumentar la RAM a al menos 8GB para multitarea")
    elif ram_gb >= 32:
        recommendations.append("Tienes suficiente RAM incluso para tareas muy demandantes")
    
    disk_type = sysinfo.get('disk_type', '').lower()
    if disk_type == 'hdd':
        recommendations.append("Cambiar a SSD mejorará drásticamente los tiempos de carga")
    elif disk_type == 'nvme':
        recommendations.append("Tu almacenamiento NVMe es óptimo para máximo rendimiento")
    
    gpu_vram = sysinfo.get('gpu_vram_gb', 0)
    if gpu_vram < 4:
        recommendations.append("Considera una GPU con más VRAM para gaming y aplicaciones gráficas")
    
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
    
    recommendations.append("Realiza mantenimiento regular del sistema")
    recommendations.append("Mantén el sistema operativo actualizado")
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(80, 80, 80)
    
    for i, rec in enumerate(recommendations):
        pdf.cell(10, 8, f"{i+1}.", border=0)
        pdf.multi_cell(0, 8, f" {rec}")
        pdf.ln(2)

    pdf_filename = f"analisis_{analysis_id:04d}.pdf"
    pdf.output(pdf_filename)

    print(f"✅ PDF elegante generado: {pdf_filename}")
    return pdf_filename

# -------------------------
#   FUNCIONES AUXILIARES DASHBOARD
# -------------------------
def get_score_class(score):
    if score >= 80:
        return "score-excelent"
    elif score >= 60:
        return "score-good"
    elif score >= 40:
        return "score-regular"
    else:
        return "score-poor"

def get_score_color(score):
    if score >= 80:
        return "#38a169"
    elif score >= 60:
        return "#3182ce"
    elif score >= 40:
        return "#d69e2e"
    else:
        return "#e53e3e"

# -------------------------
#   API ENDPOINTS
# -------------------------

# ENDPOINTS DE AUTENTICACIÓN 
@app.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
    or_(User.username == user_data.username, User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

# ENDPOINTS DE ANÁLISIS
@app.post("/api/analyze")
def analyze(
    sysinfo: SysInfo, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    info = sysinfo.dict()
    result = score_system(info)

    is_guest = current_user is None
    
    if is_guest:
        analysis_id = generate_guest_analysis_id()
        user_id = None
        print(f"🔍 Análisis para usuario INVITADO - ID temporal: {analysis_id}")
    else:
        user_analyses = db.query(SystemAnalysis).filter(SystemAnalysis.user_id == current_user.id).all()
        analysis_id = get_next_analysis_id(db)
        user_id = current_user.id
        print(f"🔍 Análisis para usuario REGISTRADO {current_user.username} - ID: {analysis_id}")

    pdf_filename = create_pdf_report(info, result, analysis_id)

    json_filename = f"analisis_{analysis_id:04d}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "sysinfo": info,
            "result": result,
            "analysis_id": analysis_id,
            "user_id": user_id,
            "is_guest": is_guest,
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

    if not is_guest:
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
            json_url=json_url,
            user_id=user_id
        )
        
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)

        print(f"💾 Análisis guardado en BD con ID: {analysis_id} para usuario: {current_user.username}")
    else:
        print(f"📝 Análisis temporal generado para invitado - ID: {analysis_id}")

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
        "is_guest": is_guest,
        "message": "Análisis completado correctamente" + (" (modo invitado)" if is_guest else ""),
        "version": "2.0.0"
    }

# ENDPOINTS EXCLUSIVOS PARA USUARIOS REGISTRADOS
@app.get("/api/analyses", response_model=List[dict])
def get_user_analyses(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analyses = db.query(SystemAnalysis)\
        .filter(SystemAnalysis.user_id == current_user.id)\
        .order_by(SystemAnalysis.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return [
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

@app.get("/api/analyses/{analysis_id}")
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(SystemAnalysis)\
        .filter(
            SystemAnalysis.analysis_id == analysis_id,
            SystemAnalysis.user_id == current_user.id
        )\
        .first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
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

@app.get("/api/analyses/history", response_model=AnalysisHistory)
def get_analysis_history(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analyses = db.query(SystemAnalysis)\
        .filter(SystemAnalysis.user_id == current_user.id)\
        .order_by(SystemAnalysis.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    total_count = db.query(SystemAnalysis)\
        .filter(SystemAnalysis.user_id == current_user.id)\
        .count()
    
    analysis_list = [
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
    
    return AnalysisHistory(analyses=analysis_list, total_count=total_count)

# ENDPOINT PARA ANÁLISIS RÁPIDO
@app.post("/api/quick-analyze")
def quick_analyze(
    sysinfo: SysInfo, 
    db: Session = Depends(get_db)
):
    info = sysinfo.dict()
    result = score_system(info)

    analysis_id = generate_guest_analysis_id()
    
    print(f"🚀 Análisis RÁPIDO para INVITADO - ID temporal: {analysis_id}")

    pdf_filename = create_pdf_report(info, result, analysis_id)

    json_filename = f"analisis_{analysis_id:04d}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "sysinfo": info,
            "result": result,
            "analysis_id": analysis_id,
            "is_guest": True,
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

            if not pdf_error and not json_error:
                print(f"✅ Archivos subidos a Dropbox para análisis rápido")
        except Exception as e:
            print(f"❌ Error en subida a Dropbox: {e}")

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
        "is_guest": True,
        "message": "Análisis rápido completado (modo invitado)",
        "note": "Regístrate para guardar tu historial de análisis",
        "version": "2.0.0"
    }

# ENDPOINTS PÚBLICOS
@app.on_event("startup")
async def startup_event():
    if access_token:
        create_dropbox_folder_structure(access_token)
        print("✅ Dropbox configurado")
    
    create_tables()
    print("✅ Base de datos configurada")

@app.get("/")
def read_root():
    return {
        "message": "AnalizaTuPC API v2.0 funcionando", 
        "version": "2.0.0",
        "features": {
            "auth_required": "Análisis con historial persistente",
            "no_auth": "Análisis rápido sin registro",
            "endpoints": {
                "POST /api/analyze": "Análisis (con/sin autenticación)",
                "POST /api/quick-analyze": "Análisis rápido sin autenticación",
                "POST /register": "Registro de usuario",
                "POST /login": "Inicio de sesión"
            }
        }
    }

# ==================== DASHBOARD EMPRESARIAL ELEGANTE ====================

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Dashboard empresarial elegante con la misma paleta de colores de los PDFs"""
    
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
        <title>AnalizaTuPC - Dashboard Corporativo</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {{
                /* PALETA IDÉNTICA A LOS PDFs */
                --azul-celeste-claro: #add8e6;
                --azul-celeste-medio: #87ceeb;
                --azul-oscuro: #00008b;
                --azul-acero: #4682b4;
                --azul-muy-claro: #c8e6ff;
                --azul-alice: #f0f8ff;
                --azul-casi-blanco: #f5faff;
                --texto-oscuro: #2d3748;
                --texto-medio: #4a5568;
                --texto-claro: #718096;
                --borde-claro: #e2e8f0;
                --sombra-suave: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                --sombra-media: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                background: linear-gradient(135deg, var(--azul-celeste-claro) 0%, var(--azul-celeste-medio) 100%);
                min-height: 100vh;
                color: var(--texto-oscuro);
                line-height: 1.6;
            }}
            
            .dashboard-container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 30px;
            }}
            
            /* HEADER EMPRESARIAL */
            .corporate-header {{
                background: var(--azul-oscuro);
                color: white;
                padding: 40px;
                border-radius: 20px;
                margin-bottom: 40px;
                box-shadow: var(--sombra-media);
                position: relative;
                overflow: hidden;
            }}
            
            .corporate-header::before {{
                content: '';
                position: absolute;
                top: 0;
                right: 0;
                width: 300px;
                height: 300px;
                background: var(--azul-acero);
                border-radius: 50%;
                transform: translate(100px, -100px);
                opacity: 0.1;
            }}
            
            .header-content {{
                position: relative;
                z-index: 2;
            }}
            
            .corporate-header h1 {{
                font-size: 3.2em;
                font-weight: 700;
                margin-bottom: 10px;
                letter-spacing: -0.5px;
            }}
            
            .corporate-header .subtitle {{
                font-size: 1.3em;
                opacity: 0.9;
                font-weight: 300;
            }}
            
            /* STATS GRID ELEGANTE */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 50px;
            }}
            
            .stat-card {{
                background: white;
                padding: 35px;
                border-radius: 20px;
                box-shadow: var(--sombra-suave);
                text-align: center;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                border: 1px solid var(--borde-claro);
                position: relative;
                overflow: hidden;
            }}
            
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: linear-gradient(90deg, var(--azul-celeste-medio), var(--azul-oscuro));
            }}
            
            .stat-card:hover {{
                transform: translateY(-8px);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            }}
            
            .stat-icon {{
                font-size: 2.5em;
                color: var(--azul-oscuro);
                margin-bottom: 20px;
                opacity: 0.8;
            }}
            
            .stat-number {{
                font-size: 3.5em;
                font-weight: 800;
                color: var(--azul-oscuro);
                margin-bottom: 10px;
                line-height: 1;
            }}
            
            .stat-label {{
                color: var(--texto-medio);
                font-size: 1.1em;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            /* CHARTS SECTION */
            .charts-section {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                margin-bottom: 50px;
                box-shadow: var(--sombra-media);
                border: 1px solid var(--borde-claro);
            }}
            
            .section-title {{
                font-size: 2em;
                font-weight: 700;
                color: var(--azul-oscuro);
                margin-bottom: 35px;
                text-align: center;
                position: relative;
            }}
            
            .section-title::after {{
                content: '';
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 80px;
                height: 4px;
                background: linear-gradient(90deg, var(--azul-celeste-medio), var(--azul-oscuro));
                border-radius: 2px;
            }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
                gap: 40px;
            }}
            
            .chart-container {{
                background: var(--azul-alice);
                border-radius: 16px;
                padding: 30px;
                border: 1px solid var(--azul-muy-claro);
            }}
            
            .chart-title {{
                font-size: 1.3em;
                font-weight: 600;
                color: var(--azul-oscuro);
                margin-bottom: 25px;
                text-align: center;
            }}
            
            .chart-wrapper {{
                position: relative;
                height: 320px;
            }}
            
            /* ANALYSES SECTION */
            .analyses-section {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: var(--sombra-media);
                border: 1px solid var(--borde-claro);
            }}
            
            .analysis-card {{
                background: var(--azul-casi-blanco);
                border: 1px solid var(--azul-muy-claro);
                border-radius: 16px;
                padding: 30px;
                margin-bottom: 25px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .analysis-card::before {{
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                width: 6px;
                background: var(--azul-acero);
            }}
            
            .analysis-card:hover {{
                transform: translateX(8px);
                box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
                border-color: var(--azul-celeste-medio);
            }}
            
            .analysis-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
            }}
            
            .analysis-id {{
                background: var(--azul-oscuro);
                color: white;
                padding: 10px 25px;
                border-radius: 25px;
                font-weight: 700;
                font-size: 1.1em;
                letter-spacing: 0.5px;
            }}
            
            .analysis-score {{
                font-size: 2.2em;
                font-weight: 800;
            }}
            
            .score-excelent {{ color: #38a169; }}
            .score-good {{ color: #3182ce; }}
            .score-regular {{ color: #d69e2e; }}
            .score-poor {{ color: #e53e3e; }}
            
            .hardware-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 25px;
            }}
            
            .hardware-item {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                border-left: 4px solid var(--azul-acero);
                box-shadow: var(--sombra-suave);
            }}
            
            .hardware-label {{
                font-weight: 600;
                color: var(--texto-medio);
                font-size: 0.9em;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .hardware-value {{
                color: var(--texto-oscuro);
                font-size: 1.1em;
                font-weight: 500;
            }}
            
            .profile-badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: linear-gradient(135deg, var(--azul-celeste-medio), var(--azul-oscuro));
                color: white;
                padding: 12px 25px;
                border-radius: 25px;
                font-weight: 600;
                font-size: 1em;
                margin: 15px 0;
            }}
            
            .analysis-links {{
                display: flex;
                gap: 15px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            
            .analysis-link {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: var(--azul-oscuro);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
                border: 2px solid transparent;
            }}
            
            .analysis-link:hover {{
                background: white;
                color: var(--azul-oscuro);
                border-color: var(--azul-oscuro);
                transform: translateY(-2px);
            }}
            
            .analysis-link.json {{
                background: var(--azul-acero);
            }}
            
            .analysis-link.json:hover {{
                background: white;
                color: var(--azul-acero);
                border-color: var(--azul-acero);
            }}
            
            .analysis-meta {{
                margin-top: 20px;
                color: var(--texto-claro);
                font-size: 0.9em;
                font-style: italic;
                border-top: 1px solid var(--borde-claro);
                padding-top: 15px;
            }}
            
            /* NO DATA STATE */
            .no-data {{
                text-align: center;
                padding: 80px 40px;
                color: var(--texto-claro);
            }}
            
            .no-data i {{
                font-size: 4em;
                margin-bottom: 20px;
                opacity: 0.5;
            }}
            
            .no-data h3 {{
                font-size: 1.5em;
                margin-bottom: 10px;
                color: var(--texto-medio);
            }}
            
            /* FOOTER */
            .dashboard-footer {{
                text-align: center;
                margin-top: 60px;
                padding: 30px;
                color: white;
                opacity: 0.9;
            }}
            
            .api-links {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 30px;
                flex-wrap: wrap;
            }}
            
            .api-link {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                text-decoration: none;
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            
            .api-link:hover {{
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }}
            
            /* RESPONSIVE */
            @media (max-width: 768px) {{
                .dashboard-container {{
                    padding: 20px;
                }}
                
                .corporate-header h1 {{
                    font-size: 2.5em;
                }}
                
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .charts-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .hardware-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .analysis-header {{
                    flex-direction: column;
                    gap: 15px;
                    align-items: flex-start;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <!-- HEADER CORPORATIVO -->
            <header class="corporate-header">
                <div class="header-content" style="text-align: center;">
                    <h1><i class="fas fa-chart-line"></i> AnalizaTuPC Dashboard</h1>
                        <p class="subtitle">Panel de control corporativo - Análisis de hardware en tiempo real</p>
                </div>
            </header>
            
            <!-- ESTADÍSTICAS PRINCIPALES -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-chart-bar"></i>
                    </div>
                    <div class="stat-number">{total_analyses}</div>
                    <div class="stat-label">Total de Análisis</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-percentage"></i>
                    </div>
                    <div class="stat-number">{round(avg_score, 1)}%</div>
                    <div class="stat-label">Puntuación Promedia</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-layer-group"></i>
                    </div>
                    <div class="stat-number">{len(profile_counts)}</div>
                    <div class="stat-label">Perfiles Diferentes</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-trophy"></i>
                    </div>
                    <div class="stat-number">{best_analysis.main_score if best_analysis else 0}%</div>
                    <div class="stat-label">Mejor Puntuación</div>
                </div>
            </div>
            
            <!-- SECCIÓN DE GRÁFICOS -->
            <section class="charts-section">
                <h2 class="section-title">Métricas y Análisis</h2>
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">
                            <i class="fas fa-chart-pie"></i> Distribución por Perfiles
                        </div>
                        <div class="chart-wrapper">
                            <canvas id="profileChart"></canvas>
                        </div>
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-title">
                            <i class="fas fa-chart-bar"></i> Rangos de Puntuación
                        </div>
                        <div class="chart-wrapper">
                            <canvas id="scoreChart"></canvas>
                        </div>
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-title">
                            <i class="fas fa-chart-line"></i> Evolución Reciente
                        </div>
                        <div class="chart-wrapper">
                            <canvas id="timelineChart"></canvas>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- SECCIÓN DE ANÁLISIS DETALLADOS -->
            <section class="analyses-section">
                <h2 class="section-title">Análisis Detallados del Sistema</h2>
                
                {"".join([f"""
                <div class="analysis-card">
                    <div class="analysis-header">
                        <div class="analysis-id">
                            <i class="fas fa-desktop"></i> Análisis #{analysis.analysis_id}
                        </div>
                        <div class="analysis-score {get_score_class(analysis.main_score)}">
                            {analysis.main_score}%
                        </div>
                    </div>
                    
                    <div class="hardware-grid">
                        <div class="hardware-item">
                            <div class="hardware-label">Procesador</div>
                            <div class="hardware-value">{analysis.cpu_model or "No especificado"}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">Núcleos</div>
                            <div class="hardware-value">{analysis.cores}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">Memoria RAM</div>
                            <div class="hardware-value">{analysis.ram_gb} GB</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">Tarjeta Gráfica</div>
                            <div class="hardware-value">{analysis.gpu_model or "No especificado"}</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">VRAM</div>
                            <div class="hardware-value">{analysis.gpu_vram_gb} GB</div>
                        </div>
                        <div class="hardware-item">
                            <div class="hardware-label">Almacenamiento</div>
                            <div class="hardware-value">{analysis.disk_type}</div>
                        </div>
                    </div>
                    
                    <div class="profile-badge">
                        <i class="fas fa-bullseye"></i> Perfil Recomendado: {analysis.main_profile}
                    </div>
                    
                    <div class="analysis-links">
                        {"<a href='"+analysis.pdf_url+"' class='analysis-link' target='_blank'><i class='fas fa-file-pdf'></i> Ver Informe PDF</a>" if analysis.pdf_url else ""}
                        {"<a href='"+analysis.json_url+"' class='analysis-link json' target='_blank'><i class='fas fa-code'></i> Ver Datos JSON</a>" if analysis.json_url else ""}
                    </div>
                    
                    <div class="analysis-meta">
                        <i class="fas fa-clock"></i> Generado el {analysis.created_at.strftime("%d/%m/%Y a las %H:%M") if analysis.created_at else "Fecha no disponible"}
                    </div>
                </div>
                """ for analysis in analyses]) if analyses else '''
                <div class="no-data">
                    <i class="fas fa-inbox"></i>
                    <h3>No hay análisis disponibles</h3>
                    <p>Realiza el primer análisis para ver los datos en este dashboard</p>
                </div>
                '''}
            </section>
            
            <!-- FOOTER Y ENLACES -->
            <footer class="dashboard-footer">
                <div class="api-links">
                    <a href="/api/analyses" class="api-link" target="_blank">
                        <i class="fas fa-database"></i> API de Análisis
                    </a>
                    <a href="/api/stats" class="api-link" target="_blank">
                        <i class="fas fa-chart-bar"></i> API de Estadísticas
                    </a>
                    <a href="/" class="api-link" target="_blank">
                        <i class="fas fa-rocket"></i> Documentación API
                    </a>
                </div>
                <p>AnalizaTuPC Dashboard Corporativo • {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </footer>
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
                        borderWidth: 3,
                        borderColor: '#ffffff',
                        hoverOffset: 15
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 25,
                                usePointStyle: true,
                                font: {{
                                    size: 12,
                                    family: "'Segoe UI', sans-serif"
                                }}
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {{
                                size: 14
                            }},
                            bodyFont: {{
                                size: 13
                            }}
                        }}
                    }},
                    cutout: '60%'
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
                        borderRadius: 8,
                        borderSkipped: false,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1,
                                font: {{
                                    family: "'Segoe UI', sans-serif"
                                }}
                            }},
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.1)'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{
                                    family: "'Segoe UI', sans-serif"
                                }}
                            }},
                            grid: {{
                                display: false
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
                        label: 'Puntuación del Sistema',
                        data: timelineData.scores,
                        borderColor: '#00008b',
                        backgroundColor: 'rgba(0, 0, 139, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: timelineData.colors,
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 3,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            callbacks: {{
                                label: function(context) {{
                                    return `Puntuación: ${{context.parsed.y}}%`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }},
                                font: {{
                                    family: "'Segoe UI', sans-serif"
                                }}
                            }},
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.1)'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{
                                    family: "'Segoe UI', sans-serif"
                                }}
                            }},
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Auto-refresh cada 60 segundos
            setTimeout(() => {{
                window.location.reload();
            }}, 60000);
            
            // Efectos de hover mejorados
            document.querySelectorAll('.analysis-card').forEach(card => {{
                card.addEventListener('mouseenter', function() {{
                    this.style.transform = 'translateX(12px)';
                }});
                card.addEventListener('mouseleave', function() {{
                    this.style.transform = 'translateX(0)';
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    print("🚀 INICIANDO VERSIÓN ELEGANTE...")
    uvicorn.run(app, host="0.0.0.0", port=8000)