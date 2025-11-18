# backend/models.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Modelos para autenticación
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Modelos para análisis
class AnalysisBase(BaseModel):
    cpu_model: str
    cpu_speed_ghz: float
    cores: int
    ram_gb: float
    disk_type: str
    gpu_model: str
    gpu_vram_gb: float
    main_profile: str
    main_score: float
    pdf_url: Optional[str] = None
    json_url: Optional[str] = None

class AnalysisCreate(AnalysisBase):
    pass

class AnalysisResponse(AnalysisBase):
    id: int
    analysis_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AnalysisHistory(BaseModel):
    analyses: List[AnalysisResponse]
    total_count: int