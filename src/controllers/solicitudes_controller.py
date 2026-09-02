"""
===================================================================
ARCHIVO: src/controllers/solicitudes_controller.py
DESCRIPCIÓN: Controlador de Endpoints / Rutas API para las solicitudes.
===================================================================
"""

import logging
from typing import List, Optional

from config.database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.solicitud import SolicitudAlta
from src.services.gsheet_service import obtener_siguiente_usuario_fn
from src.services.neo_service import neo_service
from src.services.reportantes_service import buscar_reportantes_estaticos
from src.services.solicitudes_export_service import exportar_solicitudes_excel_service
from src.services.solicitudes_import_service import procesar_importacion_masiva_excel
from src.services.solicitudes_workflow_service import (
    aprobar_y_aprovisionar_solicitud_service,
    generar_preview_solicitud_service,
)
from src.services.zammad_service import crear_ticket_zammad

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/solicitudes", tags=["Solicitudes"])


# ==========================================
# ESQUEMAS PYDANTIC
# ==========================================
class SolicitudCreate(BaseModel):
    nombre: str
    apellido: str
    dni: str
    legajo: str
    perfil_ad: str
    reporta_a: str
    telefono: Optional[str] = None
    es_fuera_de_nomina: bool = False


class ExportarSchema(BaseModel):
    ids: List[int]


# ==========================================
# ENDPOINTS API
# ==========================================
@router.get("/reportantes/buscar")
def buscar_reportantes(q: str = ""):
    """Devuelve coincidencias de correos/nombres de superiores almacenados en memoria."""
    return buscar_reportantes_estaticos(query=q)


@router.get("/siguiente-legajo-fn")
def get_siguiente_legajo_fn():
    """Consulta el Google Sheet y devuelve el próximo ID disponible (>= 7000)."""
    siguiente_num = obtener_siguiente_usuario_fn()
    return {"legajo": str(siguiente_num)}


@router.get("")
def listar_solicitudes(db: Session = Depends(get_db)):
    """Devuelve el historial completo de solicitudes ordenadas por ID descendente."""
    return db.query(SolicitudAlta).order_by(SolicitudAlta.id.desc()).all()


@router.post("")
def crear_solicitud(solicitud: SolicitudCreate, db: Session = Depends(get_db)):
    """Crea una nueva solicitud individual enviada por RRHH."""

    # 1. Validación en BD SQL Local
    existe = (
        db.query(SolicitudAlta)
        .filter(
            (SolicitudAlta.dni == solicitud.dni)
            | (SolicitudAlta.legajo == solicitud.legajo)
        )
        .first()
    )

    if existe:
        raise HTTPException(
            status_code=400,
            detail="El DNI o Legajo ya se encuentra registrado en el sistema.",
        )

    # 2. Validación en la base CSV de NeoTel (Crosscheck)
    check_neo = neo_service.legajo_o_dni_existe(solicitud.legajo, solicitud.dni)
    if check_neo["existe_legajo"]:
        raise HTTPException(
            status_code=400,
            detail=f"El Legajo {solicitud.legajo} ya existe en la base de NeoTel.",
        )
    if check_neo["existe_dni"]:
        raise HTTPException(
            status_code=400,
            detail=f"El DNI {solicitud.dni} ya existe en la base de NeoTel.",
        )

    # 3. Creación de la solicitud
    nueva_solicitud = SolicitudAlta(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil_ad=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        es_fuera_de_nomina=solicitud.es_fuera_de_nomina,
        estado="PENDIENTE",
    )

    try:
        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)
    except IntegrityError as ie:
        db.rollback()
        logger.error(f"Error de integridad en BD: {ie}")
        raise HTTPException(
            status_code=400,
            detail="El DNI o Legajo ingresado ya existe en la base de datos.",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado al guardar solicitud: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno al guardar la solicitud."
        )

    # Notificar automáticamente a Zammad
    try:
        crear_ticket_zammad(solicitud.dict(), es_masivo=False)
    except Exception as e:
        logger.error(f"Error no bloqueante al generar ticket en Zammad: {e}")

    return {
        "status": "success",
        "message": "Solicitud creada exitosamente",
        "data_id": nueva_solicitud.id,
    }


@router.post("/masiva")
async def cargar_solicitudes_masiva(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Procesa un archivo Excel cargado desde RRHH mediante el servicio de importación."""
    return await procesar_importacion_masiva_excel(file=file, db=db)


@router.get("/{solicitud_id}/preview")
async def obtener_preview_solicitud(
    solicitud_id: int, db: Session = Depends(get_db)
):
    """Genera la previsualización de credenciales para IT."""
    return await generar_preview_solicitud_service(
        solicitud_id=solicitud_id, db=db
    )


@router.post("/{solicitud_id}/aprobar")
async def aprobar_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Aprueba la solicitud, aprovisiona servicios y notifica."""
    return await aprobar_y_aprovisionar_solicitud_service(
        solicitud_id=solicitud_id, db=db
    )


@router.post("/exportar-excel")
async def exportar_solicitudes_excel(
    payload: ExportarSchema, db: Session = Depends(get_db)
):
    """Delegación del proceso de generación y descarga del Excel al servicio."""
    return await exportar_solicitudes_excel_service(
        ids=payload.ids, db=db
    )