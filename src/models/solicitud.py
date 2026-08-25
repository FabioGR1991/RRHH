from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from config.database import Base

# ==========================================
# 1. MODELO SQLALCHEMY (TABLA EN BASE DE DATOS)
# ==========================================
class SolicitudAlta(Base):
    __tablename__ = "solicitudes_alta"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    dni = Column(String(20), nullable=False, unique=True)
    legajo = Column(String(10), nullable=False, unique=True)
    perfil_ad = Column(String(50), nullable=False)  # Operador, TeamLeader, Admin
    
    # Campo para indicar el responsable/jefe directo al que reportará
    reporta_a = Column(String(150), nullable=False, default="No especificado")
    
    # Bandera para identificar si es un empleado fuera de nómina (sin legajo tradicional)
    es_fuera_de_nomina = Column(Boolean, default=False, nullable=False)
    
    # Estados: PENDIENTE, EN_PROCESO, COMPLETADO, ERROR_PARCIAL, RECHAZADO
    estado = Column(String(20), default="PENDIENTE")
    creado_por = Column(String(50), default="RRHH")
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)
    
    # Resultados de la ejecución de IT
    json_credenciales = Column(Text, nullable=True)
    log_errores = Column(Text, nullable=True)


# ==========================================
# 2. ESQUEMAS PYDANTIC (VALIDACIÓN Y API)
# ==========================================
class SolicitudAltaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    dni: str = Field(..., min_length=5, max_length=20)
    legajo: str = Field(..., min_length=1, max_length=10)
    perfil_ad: str = Field(..., min_length=2, max_length=50)
    reporta_a: Optional[str] = "No especificado"
    es_fuera_de_nomina: bool = False

    class Config:
        from_attributes = True


class SolicitudAltaResponse(SolicitudAltaCreate):
    id: int
    estado: str
    creado_por: str
    fecha_solicitud: datetime
    json_credenciales: Optional[str] = None
    log_errores: Optional[str] = None

    class Config:
        from_attributes = True