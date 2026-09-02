"""
===================================================================
ARCHIVO: src/controllers/solicitudes_controller.py
DESCRIPCIÓN: Controlador de Endpoints / Rutas API para las solicitudes.
===================================================================
"""

import csv
import io
import logging
import os
from typing import List, Optional

from config.database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
import openpyxl
import pandas as pd
from pydantic import BaseModel
import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.core.generator import generar_preview_credenciales, sanitizar_string
from src.models.solicitud import SolicitudAlta
from src.services.ad_service import ad_service, crear_usuario_ad
from src.services.email_service import enviar_notificacion_alta
from src.services.fortinet_service import (
    crear_usuario_fortinet,
    fortinet_service,
)
from src.services.gadmin_service import crear_casilla_google, gadmin_service
from src.services.neo_service import crear_usuario_neotel, neo_service
from src.services.pdf_service import generar_pdf_credenciales
from src.services.xlite_service import xlite_service
from src.services.zammad_service import crear_ticket_zammad

logger = logging.getLogger(__name__)

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
    telefono: Optional[str] = None
    es_fuera_de_nomina: bool = False


class ExportarSchema(BaseModel):
    ids: List[int]


# ==========================================
# FUNCIONES AUXILIARES (GOOGLE SHEETS & LOGIC)
# ==========================================
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


def obtener_usernames_pendientes_db(db: Session, solicitud_id_actual: Optional[int] = None) -> set:
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
        if hasattr(s, 'propuesta_json') and s.propuesta_json:
            un = s.propuesta_json.get("propuesta_credenciales", {}).get("active_directory", {}).get("username")
            if un:
                usernames_db.add(un)
        else:
            nom_l = sanitizar_string(s.nombre)
            ape_l = sanitizar_string(s.apellido)
            if nom_l and ape_l:
                p_nombre = nom_l.split()[0] if " " in nom_l else nom_l
                usernames_db.add(f"{p_nombre[0]}{ape_l}")

    return usernames_db


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
    
    # 1. Validación en BD SQL Local
    existe = (
        db.query(SolicitudAlta)
        .filter(
            (SolicitudAlta.dni == solicitud.dni)
            | (SolicitudAlta.legajo == solicitud.legajo)
        )
        .first()
    )

    if existe:
        raise HTTPException(
            status_code=400, detail="El DNI o Legajo ya se encuentra registrado en el sistema."
        )

    # 2. Validación en la base CSV de NeoTel (Crosscheck)
    check_neo = neo_service.legajo_o_dni_existe(solicitud.legajo, solicitud.dni)
    if check_neo["existe_legajo"]:
        raise HTTPException(
            status_code=400, detail=f"El Legajo {solicitud.legajo} ya existe en la base de NeoTel."
        )
    if check_neo["existe_dni"]:
        raise HTTPException(
            status_code=400, detail=f"El DNI {solicitud.dni} ya existe en la base de NeoTel."
        )

    # 3. Creación de la solicitud
    nueva_solicitud = SolicitudAlta(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil_ad=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        es_fuera_de_nomina=solicitud.es_fuera_de_nomina,
        estado="PENDIENTE",
    )
    
    try:
        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)
    except IntegrityError as ie:
        db.rollback()
        logger.error(f"Error de integridad en BD: {ie}")
        raise HTTPException(
            status_code=400, detail="El DNI o Legajo ingresado ya existe en la base de datos."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado al guardar solicitud: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar la solicitud.")

    # Notificar automáticamente a Zammad
    try:
        crear_ticket_zammad(solicitud.dict(), es_masivo=False)
    except Exception as e:
        logger.error(f"Error no bloqueante al generar ticket en Zammad: {e}")

    return {
        "status": "success",
        "message": "Solicitud creada exitosamente",
        "data_id": nueva_solicitud.id,
    }


@router.post("/masiva")
async def cargar_solicitudes_masiva(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Procesa un archivo Excel cargado desde RRHH. Valida colisiones de DNI o Legajo
    por cada registro y retorna la lista detallada de errores.
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
            status_code=400, detail=f"Error al procesar el archivo Excel: {str(e)}"
        )

    df.columns = [str(col).strip().lower() for col in df.columns]

    exitos = 0
    errores = []

    # 1. SETS EN MEMORIA PARA CONTROLAR DUPLICADOS EN EL MISMO EXCEL
    reservados_batch = set()  # Para usernames/credenciales (si generas preview)
    dnis_en_lote = set()      # Evita que el mismo Excel traiga DNI duplicado
    legajos_en_lote = set()   # Evita que el mismo Excel traiga Legajo duplicado

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
                f"Fila {num_fila}: Datos incompletos (Nombre, Apellido, DNI y Legajo son obligatorios)."
            )
            continue

        # 2. VALIDAR SI EL DNI O LEGAJO YA VIENEN DUPLICADOS EN FILAS ANTERIORES DEL MISMO EXCEL
        if dni in dnis_en_lote:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El DNI {dni} está duplicado dentro de este mismo Excel."
            )
            continue

        if legajo in legajos_en_lote:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El Legajo {legajo} está duplicado dentro de este mismo Excel."
            )
            continue

        # 3. VALIDAR CONTRA BASE DE DATOS EXISTENTE
        existe_dni = (
            db.query(SolicitudAlta).filter(SolicitudAlta.dni == dni).first()
        )
        if existe_dni:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El DNI {dni} ya está registrado en el sistema."
            )
            continue

        existe_legajo = (
            db.query(SolicitudAlta).filter(SolicitudAlta.legajo == legajo).first()
        )
        if existe_legajo:
            errores.append(
                f"Fila {num_fila} ({nombre} {apellido}): El Legajo {legajo} ya está registrado en el sistema."
            )
            continue

        # 4. RESERVAR EN MEMORIA PARA LAS SIGUIENTES FILAS
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
            # Notificar a Zammad sobre la carga masiva realizada
            try:
                crear_ticket_zammad({}, es_masivo=True, total_registros=exitos)
            except Exception as e:
                logger.error(f"Error no bloqueante al generar ticket masivo en Zammad: {e}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error al commitear lote masivo: {e}")
            raise HTTPException(status_code=500, detail="Error al guardar el lote de solicitudes en BD.")

    return {
        "status": "success",
        "exitos": exitos,
        "fallos": len(errores),
        "detalles_error": errores,
    }


@router.get("/{solicitud_id}/preview")
async def obtener_preview_solicitud(
    solicitud_id: int, db: Session = Depends(get_db)
):
    """Genera la previsualización de credenciales para IT consumiendo generator.py con verificación de servicios."""
    solicitud = (
        db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    )

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    check_services = {
        "ad": ad_service,
        "google": gadmin_service,
        "neotel": neo_service,
        "fortinet": fortinet_service,
    }

    # Obtener usernames de solicitudes previas/pendientes en BD
    usernames_db_pendientes = obtener_usernames_pendientes_db(db, solicitud_id_actual=solicitud_id)

    preview_full = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        check_services=check_services,
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
        "validaciones": preview_full.get("validaciones", {})
    }


@router.post("/{solicitud_id}/aprobar")
async def aprobar_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Aprueba la solicitud, aprovisiona los servicios, genera la ficha PDF,
    envía la notificación por email al responsable y actualiza el estado a
    PROCESADO.
    """
    solicitud = (
        db.query(SolicitudAlta).filter(SolicitudAlta.id == solicitud_id).first()
    )

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado == "PROCESADO":
        raise HTTPException(
            status_code=400, detail="La solicitud ya fue procesada previamente"
        )

    check_services = {
        "ad": ad_service,
        "google": gadmin_service,
        "neotel": neo_service,
        "fortinet": fortinet_service,
    }

    # Obtener usernames de solicitudes previas/pendientes en BD
    usernames_db_pendientes = obtener_usernames_pendientes_db(db, solicitud_id_actual=solicitud_id)

    preview_full = await generar_preview_credenciales(
        nombre=solicitud.nombre,
        apellido=solicitud.apellido,
        dni=solicitud.dni,
        legajo=solicitud.legajo,
        perfil=solicitud.perfil_ad,
        reporta_a=solicitud.reporta_a,
        check_services=check_services,
        usernames_db_pendientes=usernames_db_pendientes,
    )
    creds = preview_full["propuesta_credenciales"]

    # Preparar payload extendido con mapeo de Legajo -> Usuario NeoTel (3xxx)
    usuario_neo_calculado = creds["neotel"].get("telemarketer_user") or obtener_usuario_neotel_desde_legajo(solicitud.legajo)
    
    payload_neotel = dict(creds["neotel"])
    payload_neotel.update({
        "usuario": usuario_neo_calculado,
        "legajo_neo": usuario_neo_calculado,
        "legajo": solicitud.legajo,
        "nombre": solicitud.nombre,
        "apellido": solicitud.apellido,
        "nombre_apellido": f"{solicitud.nombre} {solicitud.apellido}".strip()
    })

    try:
        if not solicitud.es_fuera_de_nomina:
            await crear_usuario_ad(creds["active_directory"])
            await crear_casilla_google(creds["google_workspace"])
            await crear_usuario_fortinet(creds["forticlient"])

        await crear_usuario_neotel(payload_neotel)
    except Exception as e:
        logger.error(
            f"Fallo en aprovisionamiento de servicios para solicitud #{solicitud_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Fallo en aprovisionamiento de servicios para solicitud #{solicitud_id}: {str(e)}"
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
        logger.error(
            f"Error al generar PDF para la solicitud #{solicitud_id}: {e}"
        )

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
        "message": (
            f"Solicitud #{solicitud_id} aprobada, aprovisionada y notificada"
            " exitosamente"
        ),
        "data": {
            "id": solicitud.id,
            "empleado": f"{solicitud.nombre} {solicitud.apellido}",
            "reporta_a": solicitud.reporta_a,
            "estado": solicitud.estado,
            "pdf_generado": bool(pdf_path),
        },
    }


# ==========================================
# ENDPOINT: EXPORTAR A EXCEL MASIVO
# ==========================================
@router.post("/exportar-excel")
async def exportar_solicitudes_excel(
    payload: ExportarSchema, db: Session = Depends(get_db)
):
    """Recibe una lista de IDs de solicitudes procesadas/aprobadas y genera
    un archivo Excel (.xlsx) dinámico con la estructura operativa de credenciales.
    """
    ids = payload.ids

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
    usuarios_reservados = set()

    for s in solicitudes:
        # Obtener usernames de solicitudes previas/pendientes en BD para evitar solapamientos
        usernames_db_pendientes = obtener_usernames_pendientes_db(db, solicitud_id_actual=s.id)

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

        filas.append({
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
                creds["forticlient"]["username"] if not s.es_fuera_de_nomina else "-"
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
            "Dispositivo posición (X-Lite)": creds["neotel"]["posicion_user"],
            "CLAVE": creds["neotel"]["posicion_pass"],
            "Superior": s.reporta_a,
        })
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