"""
===================================================================
ARCHIVO: src/controllers/solicitudes_controller.py
DESCRIPCIÓN: Controlador de Endpoints / Rutas API para las solicitudes.
Aquí residen los endpoints que consulta el Frontend para:
 - Crear nuevas solicitudes desde RRHH.
 - Obtener la lista de solicitudes enviadas.
 - Previsualizar credenciales propuestas antes de ejecutar (IT).
===================================================================
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from src.models.solicitud import SolicitudAlta
from src.core.generator import generar_preview_credenciales

router = APIRouter(prefix="/api/solicitudes", tags=["Solicitudes"])


@router.get("/{solicitud_id}/preview")
async def obtener_preview_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """
    Genera y devuelve la propuesta de credenciales (User, Mail, Pass, NeoTel, Fortinet)
    para que IT la revise en el modal antes de confirmar el alta.
    """
    # 1. Buscar la solicitud en la base de datos por ID
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # 2. Generar el preview utilizando generator.py
    preview = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        check_services=None  # Sin servicios por ahora hasta desarrollarlos en la Fase 2
    )

    return preview