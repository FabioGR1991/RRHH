# ===================================================================
# ARCHIVO: src/services/gadmin_service/real_service.py
# DESCRIPCIÓN: Integración real con Google Workspace Admin SDK via
#              Service Account. Verifica disponibilidad de casillas
#              y crea usuarios con contraseña temporal y cambio
#              obligatorio al primer acceso.
# ===================================================================

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Variables de entorno para la integración Google
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "./credentials.json"
)
GOOGLE_ADMIN_EMAIL = os.getenv("GOOGLE_ADMIN_EMAIL", "admin@tandemtech.com.ar")
GOOGLE_DOMAIN      = os.getenv("DOMINIO_EMAIL", "tandemtech.com.ar")

# Scopes necesarios para la Admin SDK
_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
]

# Control de disponibilidad del SDK de Google
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GOOGLE_SDK_AVAILABLE = True
except ImportError:
    _GOOGLE_SDK_AVAILABLE = False
    logger.warning("[REAL GADMIN_SERVICE] google-api-python-client no disponible.")


def _get_admin_service():
    """Construye y retorna el cliente autenticado del Admin SDK."""
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=_SCOPES
    )
    # Impersonar la cuenta de administrador del dominio
    delegated_credentials = credentials.with_subject(GOOGLE_ADMIN_EMAIL)
    service = build("admin", "directory_v1", credentials=delegated_credentials)
    return service


class RealGAdminService:
    """
    Servicio de integración real con Google Workspace Admin SDK.
    Requiere: credentials.json (Service Account con Domain-Wide Delegation).
    Variables de entorno: GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_ADMIN_EMAIL, DOMINIO_EMAIL.
    """

    def __init__(self):
        if not _GOOGLE_SDK_AVAILABLE:
            logger.error("[REAL GADMIN_SERVICE] Google Admin SDK no disponible.")

    async def existe_usuario(self, email: str) -> bool:
        """
        Verifica si una casilla de correo ya existe en el workspace.

        Args:
            email: Dirección de correo completa a verificar.
        Returns:
            True si existe, False si está disponible o en caso de error.
        """
        if not _GOOGLE_SDK_AVAILABLE:
            return False
        try:
            service = _get_admin_service()
            service.users().get(userKey=email).execute()
            # Si no lanza excepción, el usuario existe
            logger.info(f"[REAL GADMIN_SERVICE] Casilla '{email}' YA EXISTE en Workspace.")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                # 404 significa que no existe — estado esperado para usuarios nuevos
                return False
            logger.error(f"[REAL GADMIN_SERVICE] Error HTTP al verificar '{email}': {e}")
            return False
        except Exception as e:
            logger.error(f"[REAL GADMIN_SERVICE] Error inesperado al verificar '{email}': {e}")
            return False

    async def crear_casilla(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una casilla corporativa en Google Workspace.

        Parámetros esperados:
            - email (str):         Correo a crear
            - password_temp (str): Contraseña inicial
            - org_unit (str):      Ruta de la unidad organizativa (ej. '/Operador')
            - nombre, apellido:    Datos para el perfil de usuario
            - username:            Parte local del email

        Retorna:
            Dict con status, mode y data con la información del usuario creado.
        """
        if not _GOOGLE_SDK_AVAILABLE:
            return {
                "status": "error",
                "mode": "REAL",
                "detail": "Google Admin SDK no está disponible en este entorno."
            }

        email        = str(datos.get("email") or "").strip()
        password     = datos.get("password_temp", "T4nd3m**")
        org_unit     = datos.get("org_unit", f"/{GOOGLE_DOMAIN}")
        nombre       = datos.get("nombre", "")
        apellido     = datos.get("apellido", "")
        username     = datos.get("username") or (email.split("@")[0] if "@" in email else "")

        if not email or "@" not in email:
            return {"status": "error", "mode": "REAL", "detail": "Email inválido o vacío."}

        # Pre-verificación de disponibilidad
        if await self.existe_usuario(email):
            return {
                "status": "error",
                "mode": "REAL",
                "detail": f"La casilla '{email}' ya existe en Google Workspace.",
                "email": email
            }

        cuerpo_usuario = {
            "primaryEmail": email,
            "name": {
                "givenName":  nombre,
                "familyName": apellido,
                "fullName":   f"{nombre} {apellido}".strip()
            },
            "password":                     password,
            "changePasswordAtNextLogin":    True,
            "orgUnitPath":                  org_unit,
            "suspended":                    False,
        }

        try:
            service = _get_admin_service()
            resultado = service.users().insert(body=cuerpo_usuario).execute()
            logger.info(
                f"[REAL GADMIN_SERVICE] Casilla '{email}' creada exitosamente "
                f"en OrgUnit='{org_unit}'."
            )
            return {
                "status": "success",
                "mode": "REAL",
                "message": f"Casilla '{email}' creada en Google Workspace.",
                "data": {
                    "email":                     resultado.get("primaryEmail", email),
                    "username":                  username,
                    "org_unit":                  org_unit,
                    "password_temp":             password,
                    "change_password_at_next_login": True,
                    "nombre_completo":           f"{nombre} {apellido}".strip(),
                    "google_id":                 resultado.get("id"),
                }
            }
        except HttpError as e:
            msg = f"Error HTTP al crear casilla '{email}' en Google Workspace: {e}"
            logger.error(f"[REAL GADMIN_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
        except Exception as e:
            msg = f"Error inesperado al crear casilla '{email}': {e}"
            logger.error(f"[REAL GADMIN_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
