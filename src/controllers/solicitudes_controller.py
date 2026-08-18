"""
===================================================================
ARCHIVO: src/controllers/solicitudes_controller.py
DESCRIPCIÓN: Controlador de Endpoints / Rutas API para las solicitudes.
Aquí residen los endpoints que consulta el Frontend para:
 - Crear nuevas solicitudes desde RRHH.
 - Listar todas las solicitudes (RRHH e IT).
 - Previsualizar credenciales propuestas antes de ejecutar (IT).
 - Aprobar / Procesar la solicitud.
===================================================================
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from config.database import get_db
from src.models.solicitud import SolicitudAlta
from src.core.generator import generar_preview_credenciales
from pydantic import BaseModel

router = APIRouter(prefix="/api/solicitudes", tags=["Solicitudes"])


# Esquema Pydantic para la creación
class SolicitudCreate(BaseModel):
    nombre: str
    apellido: str
    dni: str
    legajo: str
    perfil_ad: str
    reporta_a: str


@router.get("")
def listar_solicitudes(db: Session = Depends(get_db)):
    """Devuelve el historial completo de solicitudes ordenadas por ID descendente."""
    solicitudes = db.query(SolicitudAlta).order_by(SolicitudAlta.id.desc()).all()
    return solicitudes


@router.post("")
def crear_solicitud(solicitud: SolicitudCreate, db: Session = Depends(get_db)):
    """Crea una nueva solicitud enviada por RRHH."""
    existe = db.query(SolicitudAlta).filter(
        (SolicitudAlta.dni == solicitud.dni) | (SolicitudAlta.legajo == solicitud.legajo)
    ).first()

    if existe:
        raise HTTPException(status_code=400, detail="El DNI o Legajo ya se encuentra registrado.")

    nueva_solicitud = SolicitudAlta(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil_ad=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        estado="PENDIENTE"
    )
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)

    return {"status": "success", "message": "Solicitud creada", "data_id": nueva_solicitud.id}


@router.get("/{solicitud_id}/preview")
async def obtener_preview_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Formateo según plantilla
    inicial = solicitud.nombre[0].lower() if solicitud.nombre else ""
    apellido_clean = solicitud.apellido.lower().replace(" ", "")
    nombre_camel = solicitud.nombre.capitalize()
    apellido_camel = solicitud.apellido.capitalize()

    usuario_base = f"{inicial}{apellido_clean}"
    nombre_completo_junto = f"{nombre_camel}{apellido_camel}"

    return {
        "usuario_ad": usuario_base,
        "email": f"{usuario_base}@tandemtech.com.ar",
        "clave_ad_mail": "T4nd3m**",
        "usuario_fortinet": nombre_completo_junto,
        "clave_fortinet": solicitud.dni,
        "usuario_neo": solicitud.legajo,
        "clave_neo": solicitud.dni,
        "posicion_xlite": nombre_completo_junto,
        "clave_xlite": "Tandem123"
    }

    # Normalización del diccionario mapeando fallback seguro en caso de falta de claves
    usuario = preview.get("usuario_ad") or preview.get("usuario") or f"{solicitud.nombre[0].lower()}{solicitud.apellido.lower()}"
    
    return {
        "usuario_ad": usuario,
        "email": preview.get("email") or preview.get("correo") or f"{usuario}@empresa.com",
        "password": preview.get("password") or preview.get("contrasena") or "Tmp123456!",
        "neotel_legajo": preview.get("neotel_legajo") or preview.get("legajo") or solicitud.legajo,
        "fortinet_grupo": preview.get("fortinet_grupo") or preview.get("grupo_vpn") or f"VPN_{solicitud.perfil_ad}"
    }


@router.post("/{solicitud_id}/aprobar")
def aprobar_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Aprueba la solicitud cambiando su estado a PROCESADO."""
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado == "PROCESADO":
        raise HTTPException(status_code=400, detail="La solicitud ya fue procesada previamente")

    solicitud.estado = "PROCESADO"
    db.commit()
    db.refresh(solicitud)

    return {
        "status": "success",
        "message": f"Solicitud #{solicitud_id} aprobada exitosamente",
        "data": {
            "id": solicitud.id,
            "empleado": f"{solicitud.nombre} {solicitud.apellido}",
            "reporta_a": solicitud.reporta_a,
            "estado": solicitud.estado
        }
    }