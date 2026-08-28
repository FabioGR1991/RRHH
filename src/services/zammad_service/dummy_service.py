import logging
import random

logger = logging.getLogger(__name__)


def crear_ticket_zammad(
    solicitud_data: dict, es_masivo: bool = False, total_registros: int = 1
):
    """Simula la creación de un ticket en Zammad sin realizar peticiones HTTP."""
    ticket_id_simulado = random.randint(1000, 9999)

    if es_masivo:
        logger.info(
            f"[DUMMY ZAMMAD] Ticket Masivo Simulado #{ticket_id_simulado} | "
            f"Total solicitudes: {total_registros}"
        )
    else:
        nombre = solicitud_data.get("nombre", "")
        apellido = solicitud_data.get("apellido", "")
        legajo = solicitud_data.get("legajo", "")
        logger.info(
            f"[DUMMY ZAMMAD] Ticket Simulado #{ticket_id_simulado} | "
            f"Alta para: {nombre} {apellido} (Legajo: {legajo})"
        )

    return {
        "status": "success",
        "mode": "DUMMY",
        "ticket_id": ticket_id_simulado,
        "message": "Ticket creado exitosamente en modo simulación",
    }
