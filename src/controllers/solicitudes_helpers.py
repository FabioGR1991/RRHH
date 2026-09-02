"""
===================================================================
ARCHIVO: src/controllers/solicitudes_helpers.py
DESCRIPCIÓN: Funciones auxiliares y reglas de negocio para solicitudes.
===================================================================
"""

import csv
import io
import logging
import os
from typing import Optional, Set

import requests
from sqlalchemy.orm import Session

from src.core.generator import sanitizar_string
from src.models.solicitud import SolicitudAlta

logger = logging.getLogger(__name__)


def obtener_siguiente_usuario_fn() -> int:
    """Descarga el CSV del Google Sheet 'FUERA DE NOMINA', busca el mayor
    número de usuario >= 7000 y retorna el siguiente (+1).
    """
    sheet_id = os.getenv("GSHEET_FUERA_NOMINA_ID")
    if not sheet_id:
        return 7345

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        csv_data = io.StringIO(response.text)
        reader = csv.DictReader(csv_data)

        max_usuario = 7000

        for row in reader:
            val = row.get("USUARIO") or row.get("Usuario") or row.get("usuario")
            if val and val.strip().isdigit():
                num = int(val.strip())
                if num >= 7000 and num > max_usuario:
                    max_usuario = num

        return max_usuario + 1

    except Exception as e:
        logger.warning(f"Error al consultar Google Sheet FN: {e}")
        return 7345


def obtener_usuario_neotel_desde_legajo(legajo: str) -> str:
    """Regla de Negocio NeoTel:
    Transforma el Legajo reemplazando el primer caracter '1' por '3'.
    Ejemplo: '1005' -> '3005'. Si no empieza con '1', antepone '3'.
    """
    legajo_str = str(legajo).strip()
    if not legajo_str:
        return ""
    if legajo_str.startswith("1"):
        return "3" + legajo_str[1:]
    return "3" + legajo_str


def obtener_usernames_pendientes_db(
    db: Session, solicitud_id_actual: Optional[int] = None
) -> Set[str]:
    """Consulta la BD buscando solicitudes anteriores o pendientes para extraer los usernames
    ya asignados o previstos y evitar colisiones al generar nuevas credenciales.
    """
    query = db.query(SolicitudAlta)
    if solicitud_id_actual:
        query = query.filter(SolicitudAlta.id < solicitud_id_actual)

    solicitudes_anteriores = query.filter(
        SolicitudAlta.estado.in_(["PENDIENTE", "EN_PROCESO", "COMPLETADO", "PROCESADO"])
    ).all()

    usernames_db = set()
    for s in solicitudes_anteriores:
        if hasattr(s, "propuesta_json") and s.propuesta_json:
            un = (
                s.propuesta_json.get("propuesta_credenciales", {})
                .get("active_directory", {})
                .get("username")
            )
            if un:
                usernames_db.add(un)
        else:
            nom_l = sanitizar_string(s.nombre)
            ape_l = sanitizar_string(s.apellido)
            if nom_l and ape_l:
                p_nombre = nom_l.split()[0] if " " in nom_l else nom_l
                usernames_db.add(f"{p_nombre[0]}{ape_l}")

    return usernames_db