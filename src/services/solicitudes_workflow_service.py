"""
===================================================================
ARCHIVO: src/services/solicitudes_workflow_service.py
DESCRIPCIÓN: Workflow de generación de previsualización y aprovisionamiento.
             Orquesta la secuencia de servicios y actualiza el estado en BD
             con manejo granular de errores por módulo.
===================================================================
"""

import json
import logging
import os
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.controllers.solicitudes_helpers import obtener_usernames_pendientes_db
from src.core.generator import generar_preview_credenciales
from src.core.orchestrator import orchestrator
from src.models.solicitud import SolicitudAlta
from src.services.email_service import enviar_notificacion_alta
from src.services.pdf_service import generar_pdf_credenciales
from config.settings import BASE_DIR

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
    from src.services.ad_service import ad_service
    from src.services.gadmin_service import gadmin_service
    from src.services.neo_service import neo_service
    from src.services.fortinet_service import fortinet_service
    return {
        "ad":       ad_service,
        "google":   gadmin_service,
        "neotel":   neo_service,
        "fortinet": fortinet_service,
    }


# =====================================================================
# SERVICIO: Generar Preview de Credenciales
# =====================================================================

async def generar_preview_solicitud_service(solicitud_id: int, db: Session) -> dict:
    """
    Genera la previsualización de credenciales propuestas para IT.
    Consulta disponibilidad en los servicios y retorna el payload
    estructurado para el modal del dashboard.
    """
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Si la solicitud ya fue procesada, retornar las credenciales reales guardadas
    if solicitud.estado in ("COMPLETADO", "PROCESADO", "ERROR_PARCIAL") and solicitud.json_credenciales:
        try:
            propuesta = json.loads(solicitud.json_credenciales)
            return {
                "usuario_ad":         propuesta.get("active_directory", {}).get("username", ""),
                "email":              propuesta.get("google_workspace", {}).get("email", ""),
                "clave_ad_mail":      propuesta.get("active_directory", {}).get("password_temp", ""),
                "usuario_fortinet":   propuesta.get("forticlient", {}).get("username", ""),
                "clave_fortinet":     propuesta.get("forticlient", {}).get("password_temp", ""),
                "usuario_neo":        propuesta.get("neotel", {}).get("telemarketer_user", ""),
                "clave_neo":          propuesta.get("neotel", {}).get("telemarketer_pass", ""),
                "posicion_xlite":     propuesta.get("neotel", {}).get("posicion_user", ""),
                "clave_xlite":        propuesta.get("neotel", {}).get("posicion_pass", ""),
                "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
                "validaciones":       {},
            }
        except Exception as e:
            logger.warning(f"Error parseando json_credenciales para #{solicitud_id}: {e}")

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
        "usuario_ad":         propuesta["active_directory"]["username"],
        "email":              propuesta["google_workspace"]["email"],
        "clave_ad_mail":      propuesta["active_directory"]["password_temp"],
        "usuario_fortinet":   propuesta["forticlient"]["username"],
        "clave_fortinet":     propuesta["forticlient"]["password_temp"],
        "usuario_neo":        propuesta["neotel"]["telemarketer_user"],
        "clave_neo":          propuesta["neotel"]["telemarketer_pass"],
        "posicion_xlite":     propuesta["neotel"]["posicion_user"],
        "clave_xlite":        propuesta["neotel"]["posicion_pass"],
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
        "validaciones":       preview_full.get("validaciones", {}),
    }


# =====================================================================
# SERVICIO: Aprobar y Aprovisionar Solicitud
# =====================================================================

async def aprobar_y_aprovisionar_solicitud_service(solicitud_id: int, db: Session) -> dict:
    """
    Aprueba la solicitud y ejecuta el aprovisionamiento completo via el Orquestador.

    Flujo:
    1. Valida estado actual de la solicitud.
    2. Invoca orchestrator.ejecutar_alta_confirmada() con secuencia AD→Gmail→NeoTel→FortiClient.
    3. Actualiza el estado en BD (COMPLETADO o ERROR_PARCIAL).
    4. Guarda json_credenciales y log_errores en la solicitud.
    5. Genera el PDF de credenciales.
    6. Envía notificación por email al supervisor.
    7. Retorna el resultado con credenciales para el modal del dashboard.
    """
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado in ("COMPLETADO", "PROCESADO"):
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud #{solicitud_id} ya fue procesada previamente (estado: {solicitud.estado})."
        )

    usernames_db_pendientes = obtener_usernames_pendientes_db(
        db, solicitud_id_actual=solicitud_id
    )

    datos_solicitud = {
        "id":               solicitud.id,
        "solicitud_id":     solicitud.id,
        "nombre":           solicitud.nombre,
        "apellido":         solicitud.apellido,
        "dni":              solicitud.dni,
        "legajo":           solicitud.legajo,
        "perfil_ad":        solicitud.perfil_ad,
        "perfil":           solicitud.perfil_ad,
        "reporta_a":        solicitud.reporta_a,
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
    }

    # ── Actualizar estado a EN_PROCESO antes de ejecutar ─────────────────
    solicitud.estado = "EN_PROCESO"
    db.commit()

    # ── Ejecutar aprovisionamiento via Orquestador ─────────────────────────
    resultado = await orchestrator.ejecutar_alta_confirmada(
        datos_solicitud=datos_solicitud,
        check_services=_obtener_mapa_servicios(),
        reservados_batch=usernames_db_pendientes,
        es_fuera_de_nomina=solicitud.es_fuera_de_nomina,
    )

    estado_final    = resultado.get("estado_final", "ERROR_PARCIAL")
    credenciales    = resultado.get("credenciales_finales", {})
    detalles        = resultado.get("detalles", {})
    log_errores_raw = resultado.get("log_errores")

    # ── Extraer vista plana de credenciales para el frontend ──────────────
    propuesta_creds = credenciales.get("propuesta_credenciales", {})
    credenciales_frontend = {
        "usuario_ad":         propuesta_creds.get("active_directory", {}).get("username", ""),
        "email":              propuesta_creds.get("google_workspace", {}).get("email", ""),
        "clave_ad_mail":      propuesta_creds.get("active_directory", {}).get("password_temp", ""),
        "usuario_fortinet":   propuesta_creds.get("forticlient", {}).get("username", ""),
        "clave_fortinet":     propuesta_creds.get("forticlient", {}).get("password_temp", ""),
        "usuario_neo":        propuesta_creds.get("neotel", {}).get("telemarketer_user", ""),
        "clave_neo":          propuesta_creds.get("neotel", {}).get("telemarketer_pass", ""),
        "posicion_xlite":     propuesta_creds.get("neotel", {}).get("posicion_user", ""),
        "clave_xlite":        propuesta_creds.get("neotel", {}).get("posicion_pass", ""),
        "qr_path":            propuesta_creds.get("neotel", {}).get("qr_path", ""),
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
    }

    # ── Construir estado por servicio para el frontend ─────────────────────
    estado_servicios = {}
    servicios_mapeados = {
        "active_directory": "AD",
        "google_workspace": "Gmail",
        "neotel":           "NeoTel",
        "forticlient":      "FortiGate"
    }
    for clave, etiqueta in servicios_mapeados.items():
        if solicitud.es_fuera_de_nomina and clave in ("active_directory", "google_workspace", "forticlient"):
            estado_servicios[clave] = {"label": etiqueta, "status": "omitido", "msg": "Fuera de Nómina"}
        elif clave in detalles:
            estado_servicios[clave] = {
                "label":  etiqueta,
                "status": detalles[clave].get("status", "error"),
                "msg":    detalles[clave].get("message") or detalles[clave].get("detail", ""),
            }
        else:
            estado_servicios[clave] = {"label": etiqueta, "status": "omitido", "msg": "No ejecutado"}

    # ── Actualizar BD con el resultado ────────────────────────────────────
    solicitud.estado = estado_final
    solicitud.json_credenciales = json.dumps(propuesta_creds, ensure_ascii=False)
    if log_errores_raw:
        solicitud.log_errores = log_errores_raw

    # ── Generar PDF de credenciales ────────────────────────────────────────
    pdf_path = resultado.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        try:
            from src.services.pdf_service import generar_pdf_bienvenida
            datos_para_pdf = {
                "nombre":    solicitud.nombre,
                "apellido":  solicitud.apellido,
                "dni":       solicitud.dni,
                "legajo":    solicitud.legajo,
                "perfil_ad": solicitud.perfil_ad,
                "reporta_a": solicitud.reporta_a,
                "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
            }
            qr_path_neo = detalles.get("neotel", {}).get("data", {}).get("qr_path", "")
            if qr_path_neo and "neotel" in propuesta_creds:
                propuesta_creds["neotel"]["qr_path"] = qr_path_neo

            payload_pdf = {
                "datos_personales": datos_para_pdf,
                "propuesta_credenciales": propuesta_creds,
                "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
                "qr_path": qr_path_neo,
            }
            pdf_path = generar_pdf_bienvenida(solicitud_id=solicitud.id, credenciales=payload_pdf)
            logger.info(f"[WORKFLOW] PDF de bienvenida generado: {pdf_path}")
        except Exception as e:
            logger.error(f"[WORKFLOW] Error al generar PDF para solicitud #{solicitud_id}: {e}")

    # Guardar ruta del PDF en la solicitud
    if pdf_path:
        solicitud.log_errores = (solicitud.log_errores or "") + f" | PDF: {pdf_path}"

    # Confirmar cambios en BD
    db.commit()
    db.refresh(solicitud)

    # ── Enviar notificación por email ──────────────────────────────────────
    if pdf_path and estado_final == "COMPLETADO":
        try:
            nombre_completo = f"{solicitud.nombre} {solicitud.apellido}"
            await enviar_notificacion_alta(
                destinatario_email=solicitud.reporta_a,
                nombre_empleado=nombre_completo,
                pdf_path=pdf_path,
            )
            logger.info(f"[WORKFLOW] Notificación enviada a: {solicitud.reporta_a}")
        except Exception as e:
            logger.error(f"[WORKFLOW] Error al enviar email para solicitud #{solicitud_id}: {e}")

    return {
        "status":            "success" if resultado.get("exito") else "partial_error",
        "message":           resultado.get("mensaje", ""),
        "estado_final":      estado_final,
        "estado_servicios":  estado_servicios,
        "credenciales":      credenciales_frontend,
        "pdf_generado":      bool(pdf_path),
        "pdf_path":          pdf_path or "",
        "data": {
            "id":                solicitud.id,
            "empleado":          f"{solicitud.nombre} {solicitud.apellido}",
            "reporta_a":         solicitud.reporta_a,
            "estado":            solicitud.estado,
            "modulos_fallidos":  resultado.get("modulos_fallidos", []),
        }
    }


# =====================================================================
# SERVICIO: Obtener PDF de una solicitud ya procesada
# =====================================================================

def obtener_pdf_solicitud(solicitud_id: int, db: Session) -> str:
    """
    Retorna la ruta del PDF generado para una solicitud ya procesada.

    Args:
        solicitud_id: ID de la solicitud
        db: Sesión de base de datos

    Returns:
        Ruta absoluta del PDF si existe.

    Raises:
        HTTPException 404 si la solicitud no existe o el PDF no fue generado.
    """
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Intentar reconstruir la ruta del PDF por convención de nombres
    import re
    from src.services.pdf_service import generar_pdf_bienvenida

    pdf_dir = os.path.join(BASE_DIR, "storage", "pdfs")
    apellido_sanitizado = re.sub(r"[^a-zA-Z0-9]", "", solicitud.apellido or "") or "Colaborador"

    candidatos = [
        os.path.join(pdf_dir, f"Manual_Bienvenida_{solicitud.legajo}_{apellido_sanitizado}.pdf"),
        os.path.join(pdf_dir, f"Manual_Bienvenida_{solicitud.legajo}_{solicitud.apellido}.pdf"),
        os.path.join(pdf_dir, f"Alta_{solicitud.legajo}_{solicitud.apellido}.pdf"),
    ]

    for p in candidatos:
        if os.path.exists(p):
            return p

    # Buscar por log_errores (donde se guarda la ruta)
    if solicitud.log_errores and "PDF:" in solicitud.log_errores:
        for part in solicitud.log_errores.split("|"):
            if "PDF:" in part:
                path_candidate = part.replace("PDF:", "").strip()
                if os.path.exists(path_candidate):
                    return path_candidate

    # Si la solicitud ya está completada/procesada y tiene json_credenciales, generar en vivo
    if solicitud.estado in ("COMPLETADO", "PROCESADO", "ERROR_PARCIAL") and solicitud.json_credenciales:
        try:
            creds_data = json.loads(solicitud.json_credenciales)
            payload_pdf = {
                "datos_personales": {
                    "nombre": solicitud.nombre,
                    "apellido": solicitud.apellido,
                    "dni": solicitud.dni,
                    "legajo": solicitud.legajo,
                    "perfil": solicitud.perfil_ad,
                    "reporta_a": solicitud.reporta_a,
                },
                "propuesta_credenciales": creds_data,
                "es_fuera_de_nomina": solicitud.es_fuera_de_nomina,
            }
            nuevo_pdf = generar_pdf_bienvenida(solicitud_id=solicitud.id, credenciales=payload_pdf)
            if os.path.exists(nuevo_pdf):
                solicitud.log_errores = (solicitud.log_errores or "") + f" | PDF: {nuevo_pdf}"
                db.commit()
                return nuevo_pdf
        except Exception as e:
            logger.warning(f"[WORKFLOW] No se pudo generar PDF en demanda para #{solicitud_id}: {e}")

    raise HTTPException(
        status_code=404,
        detail=f"PDF no encontrado para la solicitud #{solicitud_id}. "
               "Verifique que la solicitud haya sido aprobada correctamente."
    )