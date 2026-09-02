"""
===================================================================
ARCHIVO: src/services/solicitudes_export_service.py
DESCRIPCIÓN: Servicio para la generación y exportación masiva de credenciales a Excel.
===================================================================
"""

import io
from typing import List, Set

from fastapi import HTTPException, Response
import pandas as pd
from sqlalchemy.orm import Session

from src.controllers.solicitudes_helpers import obtener_usernames_pendientes_db
from src.core.generator import generar_preview_credenciales
from src.models.solicitud import SolicitudAlta
from src.services.ad_service import ad_service
from src.services.fortinet_service import fortinet_service
from src.services.gadmin_service import gadmin_service
from src.services.neo_service import neo_service


async def exportar_solicitudes_excel_service(
    ids: List[int], db: Session
) -> Response:
    """Procesa una lista de IDs de solicitudes procesadas/aprobadas y genera
    un archivo Excel (.xlsx) dinámico con la estructura operativa de credenciales.
    """
    if not ids:
        raise HTTPException(
            status_code=400,
            detail="No se seleccionó ninguna solicitud para exportar.",
        )

    solicitudes = (
        db.query(SolicitudAlta).filter(SolicitudAlta.id.in_(ids)).all()
    )

    if not solicitudes:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron las solicitudes especificadas.",
        )

    check_services = {
        "ad": ad_service,
        "google": gadmin_service,
        "neotel": neo_service,
        "fortinet": fortinet_service,
    }

    filas = []

    # Conjunto para retener y reservar usuarios durante el procesamiento del lote en memoria
    usuarios_reservados: Set[str] = set()

    for s in solicitudes:
        # Obtener usernames de solicitudes previas/pendientes en BD para evitar solapamientos
        usernames_db_pendientes = obtener_usernames_pendientes_db(
            db, solicitud_id_actual=s.id
        )

        preview_full = await generar_preview_credenciales(
            nombre=s.nombre,
            apellido=s.apellido,
            dni=s.dni,
            legajo=s.legajo,
            perfil=s.perfil_ad,
            reporta_a=s.reporta_a,
            check_services=check_services,
            reservados_batch=usuarios_reservados,
            usernames_db_pendientes=usernames_db_pendientes,
        )
        creds = preview_full["propuesta_credenciales"]

        filas.append(
            {
                "Mail": (
                    creds["google_workspace"]["email"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "Clave Mail": (
                    creds["google_workspace"]["password_temp"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "Nro. Cel": s.telefono if getattr(s, "telefono", None) else "-",
                "Usuario AD": (
                    creds["active_directory"]["username"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "Clave AD": (
                    creds["active_directory"]["password_temp"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "Usuario Fortinet (VPN 100 F)": (
                    creds["forticlient"]["username"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "Clave Fortinet (DNI)": (
                    creds["forticlient"]["password_temp"]
                    if not s.es_fuera_de_nomina
                    else "-"
                ),
                "USUARIO NEO": creds["neotel"]["telemarketer_user"],
                "CLAVE 9": f"9{creds['neotel']['telemarketer_user']}",
                "NOMBRE": s.nombre.title(),
                "APELLIDO": s.apellido.title(),
                "Dispositivo posición (X-Lite)": creds["neotel"][
                    "posicion_user"
                ],
                "CLAVE": creds["neotel"]["posicion_pass"],
                "Superior": s.reporta_a,
            }
        )

    df = pd.DataFrame(filas)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Credenciales Altas")
    output.seek(0)

    headers = {
        "Content-Disposition": (
            'attachment; filename="Credenciales_Altas_RRHH.xlsx"'
        )
    }

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )