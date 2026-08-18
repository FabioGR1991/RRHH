from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from config.database import Base

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
    
    # Estados: PENDIENTE, EN_PROCESO, COMPLETADO, ERROR_PARCIAL, RECHAZADO
    estado = Column(String(20), default="PENDIENTE")
    creado_por = Column(String(50), default="RRHH")
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)
    
    # Resultados de la ejecución de IT
    json_credenciales = Column(Text, nullable=True)
    log_errores = Column(Text, nullable=True)