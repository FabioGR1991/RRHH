"""
===================================================================
ARCHIVO: src/services/zammad_service/dummy_service.py
===================================================================
"""

import logging
import random

logger = logging.getLogger(__name__)


def crear_ticket_zammad(
    solicitud_data: dict, es_masivo: bool = False, total_registros: int = 1
):
    """Simula la creación de un ticket en Zammad reflejando los campos correctos del payload."""
    ticket_id_simulado = random.randint(1000, 9999)
    customer_email = "rrhh@tandemtech.com.ar"  # Casilla emisora de la solicitud en Zammad

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
        reporta_a = solicitud_data.get("reporta_a", "No especificado")
        fn = "Sí" if solicitud_data.get("es_fuera_de_nomina") else "No"

        title = f"[Alta RRHH] {nombre} {apellido} - Legajo {legajo}"
        body = (
            f"Nueva solicitud de alta recibida:\n\n"
            f"• Colaborador: {nombre} {apellido}\n"
            f"• DNI: {solicitud_data.get('dni')}\n"
            f"• Legajo: {legajo}\n"
            f"• Perfil solicitante: {perfil}\n"
            f"• Fuera de Nómina: {fn}\n"
            f"• Reporta a (Responsable): {reporta_a}\n"
            f"• Teléfono: {solicitud_data.get('telefono', 'N/A')}\n\n"
            f"Por favor procesar el alta según el procedimiento habitual."
        )

    payload_simulado = {
        "title": title,
        "group": "Users",
        "customer": customer_email,
        "type": "RRHH - Solicitud de contratación",
        "state": "new",
        "priority": "2 normal",
        "article": {
            "subject": title,
            "body": body,
            "type": "note",
            "internal": False,
        },
    }

    print("\n" + "="*60)
    print(f"🎫 [ZAMMAD DUMMY] TICKET GENERADO #{ticket_id_simulado}")
    print(f"   ► Título: {title}")
    print(f"   ► Tipo: RRHH - Solicitud de contratación")
    print(f"   ► Cliente/Solicitante (Customer): {customer_email}")
    print(f"   ► Responsable asignado (Reporta a): {solicitud_data.get('reporta_a', 'N/A')}")
    print("="*60 + "\n")

    return {
        "status": "success",
        "mode": "DUMMY",
        "ticket_id": ticket_id_simulado,
        "payload": payload_simulado,
        "message": "Ticket creado exitosamente en modo simulación",
    }