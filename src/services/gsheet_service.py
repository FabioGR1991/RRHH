"""
===================================================================
ARCHIVO: src/services/gsheet_service.py
DESCRIPCIÓN: Servicio para integración y lectura de Google Sheets.
===================================================================
"""

import csv
import io
import logging
import os
import requests

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