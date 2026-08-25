"""
===================================================================
ARCHIVO: src/controllers/solicitudes_controller.py
DESCRIPCIÓN: Controlador de Endpoints / Rutas API para las solicitudes.
Aquí residen los endpoints que consulta el Frontend para:
 - Obtener el siguiente legajo de Fuera de Nómina (Google Sheets).
 - Crear nuevas solicitudes desde RRHH (Individual y Masiva Excel).
 - Listar todas las solicitudes (RRHH e IT).
 - Previsualizar credenciales propuestas antes de ejecutar (IT).
 - Aprobar / Procesar la solicitud.
===================================================================
"""

import csv
import io
import os
import requests
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from src.models.solicitud import SolicitudAlta
from src.core.generator import generar_preview_credenciales

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
    es_fuera_de_nomina: bool = False


# ==========================================
# FUNCIONES AUXILIARES (GOOGLE SHEETS)
# ==========================================
def obtener_siguiente_usuario_fn() -> int:
    """
    Descarga el CSV del Google Sheet 'FUERA DE NOMINA', busca el mayor 
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
            val = row.get('USUARIO') or row.get('Usuario') or row.get('usuario')
            if val and val.strip().isdigit():
                num = int(val.strip())
                if num >= 7000 and num > max_usuario:
                    max_usuario = num
                    
        return max_usuario + 1

    except Exception as e:
        print(f"[WARN] Error al consultar Google Sheet FN: {e}")
        return 7345


# ==========================================
# ENDPOINTS API
# ==========================================
@router.get("/siguiente-legajo-fn")
def get_siguiente_legajo_fn():
    """Consulta el Google Sheet y devuelve el próximo ID disponible (>= 7000)."""
    siguiente_num = obtener_siguiente_usuario_fn()
    return {"legajo": str(siguiente_num)}


@router.get("")
def listar_solicitudes(db: Session = Depends(get_db)):
    """Devuelve el historial completo de solicitudes ordenadas por ID descendente."""
    solicitudes = db.query(SolicitudAlta).order_by(SolicitudAlta.id.desc()).all()
    return solicitudes


@router.post("")
def crear_solicitud(solicitud: SolicitudCreate, db: Session = Depends(get_db)):
    """Crea una nueva solicitud individual enviada por RRHH."""
    existe = db.query(SolicitudAlta).filter(
        (SolicitudAlta.dni == solicitud.dni) | (SolicitudAlta.legajo == solicitud.legajo)
    ).first()

    if existe:
        raise HTTPException(status_code=400, detail="El DNI o Legajo ya se encuentra registrado.")

    nueva_solicitud = SolicitudAlta(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil_ad=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        es_fuera_de_nomina=solicitud.es_fuera_de_nomina,
        estado="PENDIENTE"
    )
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)

    return {"status": "success", "message": "Solicitud creada", "data_id": nueva_solicitud.id}


@router.post("/masiva")
async def cargar_solicitudes_masiva(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Procesa un archivo Excel cargado desde RRHH. Valida colisiones de DNI o Legajo 
    por cada registro y retorna la lista detallada de errores.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Debe ser un Excel (.xlsx o .xls).")

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el archivo Excel: {str(e)}")

    # Normalizar nombres de columnas a minúsculas y sin espacios laterales
    df.columns = [str(col).strip().lower() for col in df.columns]

    exitos = 0
    errores = []

    for idx, row in df.iterrows():
        num_fila = idx + 2  # +2 por el índice 0 y la fila de encabezados en Excel
        
        nombre = str(row.get('nombre', '')).strip() if pd.notna(row.get('nombre')) else ""
        apellido = str(row.get('apellido', '')).strip() if pd.notna(row.get('apellido')) else ""
        dni = str(row.get('dni', '')).strip().split('.')[0] if pd.notna(row.get('dni')) else ""
        legajo = str(row.get('legajo', '')).strip().split('.')[0] if pd.notna(row.get('legajo')) else ""
        perfil_ad = str(row.get('perfil_ad', row.get('perfil', ''))).strip() if pd.notna(row.get('perfil_ad', row.get('perfil'))) else ""
        reporta_a = str(row.get('reporta_a', '')).strip() if pd.notna(row.get('reporta_a')) else ""
        
        # Validación de campos obligatorios
        if not nombre or not apellido or not dni or not legajo:
            errores.append(f"Fila {num_fila}: Datos incompletos (Nombre, Apellido, DNI y Legajo son obligatorios).")
            continue

        # Validaciones contra Base de Datos
        existe_dni = db.query(SolicitudAlta).filter(SolicitudAlta.dni == dni).first()
        if existe_dni:
            errores.append(f"Fila {num_fila} ({nombre} {apellido}): El DNI {dni} ya está registrado.")
            continue

        existe_legajo = db.query(SolicitudAlta).filter(SolicitudAlta.legajo == legajo).first()
        if existe_legajo:
            errores.append(f"Fila {num_fila} ({nombre} {apellido}): El Legajo {legajo} ya está registrado.")
            continue

        # Creación del registro si supera las validaciones
        nueva_solicitud = SolicitudAlta(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            legajo=legajo,
            perfil_ad=perfil_ad,
            reporta_a=reporta_a,
            es_fuera_de_nomina=False,
            estado="PENDIENTE"
        )
        db.add(nueva_solicitud)
        exitos += 1

    if exitos > 0:
        db.commit()

    return {
        "status": "success",
        "exitos": exitos,
        "fallos": len(errores),
        "detalles_error": errores
    }


@router.get("/{solicitud_id}/preview")
async def obtener_preview_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Genera la previsualización de credenciales para IT consumiendo generator.py."""
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    preview_full = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a
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
        "es_fuera_de_nomina": solicitud.es_fuera_de_nomina
    }


@router.post("/{solicitud_id}/aprobar")
def aprobar_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Aprueba la solicitud cambiando su estado a PROCESADO."""
    solicitud = db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado == "PROCESADO":
        raise HTTPException(status_code=400, detail="La solicitud ya fue procesada previamente")

    solicitud.estado = "PROCESADO"
    db.commit()
    db.refresh(solicitud)

    return {
        "status": "success",
        "message": f"Solicitud #{solicitud_id} aprobada exitosamente",
        "data": {
            "id": solicitud.id,
            "empleado": f"{solicitud.nombre} {solicitud.apellido}",
            "reporta_a": solicitud.reporta_a,
            "estado": solicitud.estado
        }
    }