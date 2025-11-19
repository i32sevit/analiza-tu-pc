# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import bcrypt

# SQLite database - se creará en la carpeta backend
engine = create_engine('sqlite:///analizatupc.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación con los análisis
    analyses = relationship("SystemAnalysis", back_populates="user")

class SystemAnalysis(Base):
    __tablename__ = "system_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, unique=True, index=True)
    cpu_model = Column(String)
    cpu_speed_ghz = Column(Float)
    cores = Column(Integer)
    ram_gb = Column(Float)
    disk_type = Column(String)
    gpu_model = Column(String)
    gpu_vram_gb = Column(Float)
    main_profile = Column(String)
    main_score = Column(Float)
    pdf_url = Column(String, nullable=True)  # AÑADIDO: nullable=True
    json_url = Column(String, nullable=True)  # AÑADIDO: nullable=True
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # AÑADIDO: nullable=True para invitados
    
    # Relación con el usuario
    user = relationship("User", back_populates="analyses")

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas de base de datos creadas/verificadas")

def get_next_analysis_id(db):
    last_analysis = db.query(SystemAnalysis).order_by(SystemAnalysis.analysis_id.desc()).first()
    if last_analysis:
        return last_analysis.analysis_id + 1
    return 1

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funciones para manejo de contraseñas - ACTUALIZADAS para compatibilidad
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# AÑADIR ESTAS FUNCIONES NUEVAS:

def init_database():
    """Inicializa la base de datos y crea las tablas"""
    create_tables()
    print("✅ Base de datos inicializada correctamente")

def get_user_by_username(db, username: str):
    """Obtiene un usuario por su nombre de usuario"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db, email: str):
    """Obtiene un usuario por su email"""
    return db.query(User).filter(User.email == email).first()

def create_user(db, username: str, email: str, password: str):
    """Crea un nuevo usuario en la base de datos"""
    # Verificar si el usuario ya existe
    if get_user_by_username(db, username):
        raise ValueError("El nombre de usuario ya existe")
    if get_user_by_email(db, email):
        raise ValueError("El email ya está registrado")
    
    # Hashear la contraseña
    hashed_password = hash_password(password)
    
    # Crear el usuario
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_analyses(db, user_id: int, limit: int = 10):
    """Obtiene los análisis de un usuario específico"""
    return db.query(SystemAnalysis)\
        .filter(SystemAnalysis.user_id == user_id)\
        .order_by(SystemAnalysis.created_at.desc())\
        .limit(limit)\
        .all()

def get_total_analyses_count(db):
    """Obtiene el número total de análisis en la base de datos"""
    return db.query(SystemAnalysis).count()

def get_recent_analyses(db, limit: int = 10):
    """Obtiene los análisis más recientes"""
    return db.query(SystemAnalysis)\
        .order_by(SystemAnalysis.created_at.desc())\
        .limit(limit)\
        .all()

def save_analysis(db, analysis_data: dict, user_id: int = None):
    """Guarda un análisis en la base de datos"""
    # Obtener el siguiente ID de análisis
    analysis_id = get_next_analysis_id(db)
    
    # Crear el objeto de análisis
    analysis = SystemAnalysis(
        analysis_id=analysis_id,
        cpu_model=analysis_data.get('cpu_model', ''),
        cpu_speed_ghz=analysis_data.get('cpu_speed_ghz', 0),
        cores=analysis_data.get('cores', 0),
        ram_gb=analysis_data.get('ram_gb', 0),
        disk_type=analysis_data.get('disk_type', ''),
        gpu_model=analysis_data.get('gpu_model', ''),
        gpu_vram_gb=analysis_data.get('gpu_vram_gb', 0),
        main_profile=analysis_data.get('main_profile', ''),
        main_score=analysis_data.get('main_score', 0),
        pdf_url=analysis_data.get('pdf_url'),
        json_url=analysis_data.get('json_url'),
        user_id=user_id  # Puede ser None para invitados
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis

def delete_analysis(db, analysis_id: int):
    """Elimina un análisis por su ID"""
    analysis = db.query(SystemAnalysis).filter(SystemAnalysis.analysis_id == analysis_id).first()
    if analysis:
        db.delete(analysis)
        db.commit()
        return True
    return False

# Función para verificar el estado de la base de datos
def check_database_health():
    """Verifica que la base de datos esté funcionando correctamente"""
    try:
        db = SessionLocal()
        # Intentar una consulta simple
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Error de conexión a la base de datos: {e}")
        return False

# Inicializar la base de datos al importar el módulo
if __name__ != "__main__":
    create_tables()