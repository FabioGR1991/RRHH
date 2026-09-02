"""
===================================================================
ARCHIVO: src/services/solicitudes_import_service.py
DESCRIPCIÓN: Lógica de procesamiento e importación masiva de solicitudes Excel.
===================================================================
"""

import io
import logging
import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.models.solicitud import SolicitudAlta
from src.services.zammad_service import crear_ticket_zammad

logger = logging.getLogger(__name__)


async def procesar_importacion_masiva_excel(file: UploadFile, db: Session) -> dict:
    """Lee y valida un archivo Excel con solicitudes de alta, verifica
    duplicados en memoria y BD, e inserta el lote.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo inválido. Debe ser un Excel (.xlsx o .xls).",
        )

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al procesar el archivo Excel: {str(e)}",
        )

    df.columns = [str(col).strip().lower() for col in df.columns]

    exitos = 0
    errores = []

    # Sets para evitar duplicados dentro del mismo lote Excel
    dnis_en_lote = set()
    legajos_en_lote = set()

    for idx, row in df.iterrows():
        num_fila = idx + 2

        nombre = (
            str(row.get("nombre", "")).strip()
            if pd.notna(row.get("nombre"))
            else ""
        )
        apellido = (
            str(row.get("apellido", "")).strip()
            if pd.notna(row.get("apellido"))
            else ""
        )
        dni = (
            str(row.get("dni", "")).strip().split(".")[0]
            if pd.notna(row.get("dni"))
            else ""
        )
        legajo = (
            str(row.get("legajo", "")).strip().split(".")[0]
            if pd.notna(row.get("legajo"))
            else ""
        )
        perfil_ad = (
            str(row.get("perfil_ad", row.get("perfil", ""))).strip()
            if pd.notna(row.get("perfil_ad", row.get("perfil")))
            else ""
        )
        reporta_a = (
            str(row.get("reporta_a", "")).strip()
            if pd.notna(row.get("reporta_a"))
            else ""
        )

        if not nombre or not apellido or not dni or not legajo:
            errores.append(
                f"Fila {num_fila}: Datos incompletos (Nombre, Apellido, DNI y"
                " Legajo son obligatorios)."
            )
            continue

        if dni in dnis_en_lote:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El DNI {dni} está"
                " duplicado dentro de este mismo Excel."
            )
            continue

        if legajo in legajos_en_lote:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El Legajo {legajo}"
                " está duplicado dentro de este mismo Excel."
            )
            continue

        # Validaciones contra Base de Datos
        if db.query(SolicitudAlta).filter(SolicitudAlta.dni == dni).first():
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El DNI {dni} ya está"
                " registrado en el sistema."
            )
            continue

        if db.query(SolicitudAlta).filter(SolicitudAlta.legajo == legajo).first():
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El Legajo {legajo} ya"
                " está registrado en el sistema."
            )
            continue

        dnis_en_lote.add(dni)
        legajos_en_lote.add(legajo)

        nueva_solicitud = SolicitudAlta(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            legajo=legajo,
            perfil_ad=perfil_ad if perfil_ad else "Operador",
            reporta_a=reporta_a if reporta_a else "No especificado",
            es_fuera_de_nomina=False,
            estado="PENDIENTE",
        )
        db.add(nueva_solicitud)
        exitos += 1

    if exitos > 0:
        try:
            db.commit()
            try:
                crear_ticket_zammad({}, es_masivo=True, total_registros=exitos)
            except Exception as e:
                logger.error(f"Error no bloqueante al generar ticket masivo en Zammad: {e}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error al commitear lote masivo: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error al guardar el lote de solicitudes en BD.",
            )

    return {
        "status": "success",
        "exitos": exitos,
        "fallos": len(errores),
        "detalles_error": errores,
    }