import logging
import os
import requests

logger = logging.getLogger(__name__)

ZAMMAD_URL = os.getenv("ZAMMAD_URL", "https://tu-zammad.dominio.com/api/v1/tickets")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN", "TU_TOKEN_AQUI")


def crear_ticket_zammad(
    solicitud_data: dict, es_masivo: bool = False, total_registros: int = 1
):
    """Envía una solicitud de ticket a la API real de Zammad."""
    headers = {
        "Authorization": f"Token token={ZAMMAD_TOKEN}",
        "Content-Type": "application/json",
    }

    if es_masivo:
        title = f"[Alta RRHH - Masiva] {total_registros} colaboradores ingresados"
        body = (
            f"Se ha cargado una nómina masiva de {total_registros} solicitudes de alta desde el portal de RRHH.\n\n"
            f"Revisar el panel de aprobación para procesar."
        )
    else:
        nombre = solicitud_data.get("nombre", "")
        apellido = solicitud_data.get("apellido", "")
        legajo = solicitud_data.get("legajo", "")
        perfil = solicitud_data.get("perfil_ad", "")
        fn = "Sí" if solicitud_data.get("es_fuera_de_nomina") else "No"

        title = f"[Alta RRHH] {nombre} {apellido} - Legajo {legajo}"
        body = (
            f"Nueva solicitud de alta recibida:\n\n"
            f"• Colaborador: {nombre} {apellido}\n"
            f"• DNI: {solicitud_data.get('dni')}\n"
            f"• Legajo: {legajo}\n"
            f"• Perfil solicitante: {perfil}\n"
            f"• Fuera de Nómina: {fn}\n"
            f"• Reporta a: {solicitud_data.get('reporta_a')}\n"
            f"• Teléfono: {solicitud_data.get('telefono', 'N/A')}\n\n"
            f"Por favor procesar el alta según el procedimiento habitual."
        )

    payload = {
        "title": title,
        "group": "Users",
        "customer": "solicitudes.rrhh@dominio.com",
        "article": {
            "subject": title,
            "body": body,
            "type": "note",
            "internal": False,
        },
    }

    try:
        response = requests.post(
            ZAMMAD_URL, json=payload, headers=headers, timeout=10
        )
        response.raise_for_status()
        logger.info(f"[REAL ZAMMAD] Ticket creado exitosamente")
        return response.json()
    except Exception as e:
        logger.error(f"[REAL ZAMMAD] Error al crear ticket: {e}")
        return None
