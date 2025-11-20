# backend/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configuración de la base de datos - PostgreSQL para producción, SQLite para desarrollo
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

if not DATABASE_URL:
    # SQLite para desarrollo local
    DATABASE_URL = 'sqlite:///analizatupc.db'

# Configurar el engine según la base de datos
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL con psycopg3
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    pdf_url = Column(String, nullable=True)
    json_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)

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