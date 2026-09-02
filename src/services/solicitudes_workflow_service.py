"""
===================================================================
ARCHIVO: src/services/solicitudes_workflow_service.py
DESCRIPCIÓN: Workflow de generación de previsualización y aprovisionamiento.
===================================================================
"""

import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.controllers.solicitudes_helpers import obtener_usernames_pendientes_db
from src.core.generator import generar_preview_credenciales
from src.models.solicitud import SolicitudAlta
from src.services.ad_service import ad_service, crear_usuario_ad
from src.services.email_service import enviar_notificacion_alta
from src.services.fortinet_service import crear_usuario_fortinet, fortinet_service
from src.services.gadmin_service import crear_casilla_google, gadmin_service
from src.services.neo_service import crear_usuario_neotel, neo_service
from src.services.pdf_service import generar_pdf_credenciales

logger = logging.getLogger(__name__)


def obtener_usuario_neotel_desde_legajo(legajo: str) -> str:
    """Transforma el Legajo reemplazando el primer caracter '1' por '3'."""
    legajo_str = str(legajo).strip()
    if not legajo_str:
        return ""
    if legajo_str.startswith("1"):
        return "3" + legajo_str[1:]
    return "3" + legajo_str


def _obtener_mapa_servicios() -> dict:
    return {
        "ad": ad_service,
        "google": gadmin_service,
        "neotel": neo_service,
        "fortinet": fortinet_service,
    }


async def generar_preview_solicitud_service(solicitud_id: int, db: Session) -> dict:
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    usernames_db_pendientes = obtener_usernames_pendientes_db(
        db, solicitud_id_actual=solicitud_id
    )

    preview_full = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        check_services=_obtener_mapa_servicios(),
        usernames_db_pendientes=usernames_db_pendientes,
    )

    propuesta = preview_full["propuesta_credenciales"]

    return {
        "usuario_ad": propuesta["active_directory"]["username"],
        "email": propuesta["google_workspace"]["email"],
        "clave_ad_mail": propuesta["active_directory"]["password_temp"],
        "usuario_fortinet": propuesta["forticlient"]["username"],
        "clave_fortinet": propuesta["forticlient"]["password_temp"],
        "usuario_neo": propuesta["neotel"]["telemarketer_user"],
        "clave_neo": propuesta["neotel"]["telemarketer_pass"],
        "posicion_xlite": propuesta["neotel"]["posicion_user"],
        "clave_xlite": propuesta["neotel"]["posicion_pass"],
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
        "validaciones": preview_full.get("validaciones", {}),
    }


async def aprobar_y_aprovisionar_solicitud_service(solicitud_id: int, db: Session) -> dict:
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado == "PROCESADO":
        raise HTTPException(
            status_code=400, detail="La solicitud ya fue procesada previamente"
        )

    usernames_db_pendientes = obtener_usernames_pendientes_db(
        db, solicitud_id_actual=solicitud_id
    )

    preview_full = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        check_services=_obtener_mapa_servicios(),
        usernames_db_pendientes=usernames_db_pendientes,
    )
    creds = preview_full["propuesta_credenciales"]

    usuario_neo_calculado = creds["neotel"].get(
        "telemarketer_user"
    ) or obtener_usuario_neotel_desde_legajo(solicitud.legajo)

    payload_neotel = dict(creds["neotel"])
    payload_neotel.update(
        {
            "usuario": usuario_neo_calculado,
            "legajo_neo": usuario_neo_calculado,
            "legajo": solicitud.legajo,
            "nombre": solicitud.nombre,
            "apellido": solicitud.apellido,
            "nombre_apellido": f"{solicitud.nombre} {solicitud.apellido}".strip(),
        }
    )

    try:
        if not solicitud.es_fuera_de_nomina:
            await crear_usuario_ad(creds["active_directory"])
            await crear_casilla_google(creds["google_workspace"])
            await crear_usuario_fortinet(creds["forticlient"])

        await crear_usuario_neotel(payload_neotel)
    except Exception as e:
        logger.error(f"Fallo en aprovisionamiento de servicios para solicitud #{solicitud_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fallo en aprovisionamiento de servicios para solicitud #{solicitud_id}: {str(e)}",
        )

    datos_solicitud_dict = {
        "nombre": solicitud.nombre,
        "apellido": solicitud.apellido,
        "dni": solicitud.dni,
        "legajo": solicitud.legajo,
        "perfil_ad": solicitud.perfil_ad,
        "reporta_a": solicitud.reporta_a,
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
    }

    pdf_path = None
    try:
        pdf_path = generar_pdf_credenciales(datos_solicitud_dict, creds)
        logger.info(f"PDF de alta generado correctamente en: {pdf_path}")
    except Exception as e:
        logger.error(f"Error al generar PDF para la solicitud #{solicitud_id}: {e}")

    if pdf_path:
        nombre_completo = f"{solicitud.nombre} {solicitud.apellido}"
        await enviar_notificacion_alta(
            destinatario_email=solicitud.reporta_a,
            nombre_empleado=nombre_completo,
            pdf_path=pdf_path,
        )

    solicitud.estado = "PROCESADO"
    db.commit()
    db.refresh(solicitud)

    return {
        "status": "success",
        "message": f"Solicitud #{solicitud_id} aprobada, aprovisionada y notificada exitosamente",
        "data": {
            "id": solicitud.id,
            "empleado": f"{solicitud.nombre} {solicitud.apellido}",
            "reporta_a": solicitud.reporta_a,
            "estado": solicitud.estado,
            "pdf_generado": bool(pdf_path),
        },
    }