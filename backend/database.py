# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

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
    pdf_url = Column(String, nullable=True)
    json_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="analyses")

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_next_analysis_id(db):
    last = db.query(SystemAnalysis).order_by(SystemAnalysis.analysis_id.desc()).first()
    return last.analysis_id + 1 if last else 1

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
