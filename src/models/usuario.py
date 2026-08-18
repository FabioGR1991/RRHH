from sqlalchemy import Column, Integer, String, Boolean
from config.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False)  # 'RRHH' o 'SISTEMAS'
    activo = Column(Boolean, default=True)