# ===================================================================
# ARCHIVO: src/services/gadmin_service.py
# DESCRIPCIÓN: Servicio para la integración con Google Workspace Admin SDK.
# Soporta verificación de existencia y creación de usuarios con
# modo de simulación (MOCK) y conexión real vía Service Account.
# ===================================================================

import os
import logging
from typing import Dict, Any
from config.settings import SIMULATE_INTEGRATIONS, DOMINIO_EMAIL

logger = logging.getLogger(__name__)

# Intentamos importar las librerías oficiales de Google Admin SDK
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_SDK_AVAILABLE = False


class GoogleAdminService:
    def __init__(self):
        self.domain = os.getenv("GOOGLE_DOMAIN", DOMINIO_EMAIL)
        self.admin_email = os.getenv("GOOGLE_ADMIN_EMAIL", f"admin@{self.domain}")
        self.credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self.scopes = ['https://www.googleapis.com/auth/admin.directory.user']
        
        self.service = None
        self.mock_mode = True

        self._inicializar_conexion()

    def _inicializar_conexion(self):
        """
        Evalúa si existen las credenciales reales para Google Admin API.
        Si SIMULATE_INTEGRATIONS es True o faltan requerimientos, conmuta a modo Mock.
        """
        if SIMULATE_INTEGRATIONS:
            logger.info("ℹ️ Flag SIMULATE_INTEGRATIONS activo. Google Admin operando en MODO MOCK.")
            self.mock_mode = True
            return

        if not GOOGLE_SDK_AVAILABLE:
            logger.info("ℹ️ SDK de Google no instalado. Operando en MODO SIMULACIÓN (Mock).")
            self.mock_mode = True
            return

        if not os.path.exists(self.credentials_file):
            logger.info(f"ℹ️ Archivo '{self.credentials_file}' no encontrado. Operando en MODO SIMULACIÓN (Mock).")
            self.mock_mode = True
            return

        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=self.scopes
            )
            delegated_creds = creds.with_subject(self.admin_email)
            self.service = build('admin', 'directory_v1', credentials=delegated_creds)
            self.mock_mode = False
            logger.info("✅ Conexión con Google Workspace Admin SDK establecida exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al inicializar Google Admin SDK: {e}. Cambiando a MODO SIMULACIÓN.")
            self.mock_mode = True

    async def verificar_email_existe(self, email: str) -> bool:
        """
        Consulta a Google Workspace si la casilla corporativa ya existe.
        """
        if self.mock_mode:
            emails_existentes_mock = [
                f"admin@{self.domain}",
                f"soporte@{self.domain}",
                f"proig@{self.domain}",
                f"jperez@{self.domain}"
            ]
            existe = email.lower() in emails_existentes_mock
            logger.info(f"[MOCK Google Admin] Verificando {email}: {'EXISTE' if existe else 'DISPONIBLE'}")
            return existe

        try:
            results = self.service.users().get(userKey=email).execute()
            return True if results else False
        except HttpError as err:
            if err.resp.status == 404:
                return False
            logger.error(f"Error consultando usuario en Google: {err}")
            raise err

    async def crear_usuario(
        self, 
        nombre: str, 
        apellido: str, 
        email: str, 
        password: str = "T4nd3m**", 
        org_unit_path: str = "/"
    ) -> Dict[str, Any]:
        """
        Crea un nuevo usuario corporativo en Google Workspace.
        """
        if self.mock_mode:
            logger.info(f"[MOCK Google Admin] Usuario creado exitosamente: {email}")
            return {
                "status": "success",
                "mode": "MOCK",
                "email": email,
                "nombre_completo": f"{nombre} {apellido}",
                "org_unit": org_unit_path,
                "change_password_next_login": True
            }

        user_body = {
            'primaryEmail': email,
            'name': {
                'givenName': nombre,
                'familyName': apellido
            },
            'password': password,
            'changePasswordAtNextLogin': True,
            'orgUnitPath': org_unit_path
        }

        try:
            created_user = self.service.users().insert(body=user_body).execute()
            logger.info(f"✅ Usuario {email} creado con éxito en Google Workspace.")
            return {
                "status": "success",
                "mode": "REAL",
                "id": created_user.get('id'),
                "email": created_user.get('primaryEmail'),
                "nombre_completo": f"{nombre} {apellido}"
            }
        except HttpError as err:
            logger.error(f"❌ Error al crear usuario {email} en Google Workspace: {err}")
            return {
                "status": "error",
                "mode": "REAL",
                "detail": str(err)
            }


# Instancia global exportada
gadmin_service = GoogleAdminService()