# ===================================================================
# ARCHIVO: src/services/ad_service/dummy_service.py
# DESCRIPCIÓN: Implementación simulada (MOCK) del servicio de
#              Active Directory. Persiste usuarios en un CSV local
#              para crosscheck de colisiones y simula la creación
#              de usuarios con clave temporal y flag de cambio.
# ===================================================================

import os
import logging
import pandas as pd
from typing import Dict, Any
from config.settings import AD_CSV_PATH

logger = logging.getLogger(__name__)

# Columnas del CSV de persistencia dummy
_COLUMNAS_CSV = ["Username", "NombreCompleto", "OU", "Email", "Perfil", "MustChangePass"]


class DummyActiveDirectoryService:
    """
    Servicio simulado de Active Directory.
    Usa un archivo CSV como base de datos dummy para verificar colisiones
    y registrar las altas ejecutadas durante pruebas.
    """

    def __init__(self, csv_path: str = AD_CSV_PATH):
        self.csv_path = csv_path
        self._asegurar_csv_existe()

    def _asegurar_csv_existe(self) -> None:
        """Crea el directorio y el CSV con cabeceras si no existen."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=_COLUMNAS_CSV)
            df.to_csv(self.csv_path, index=False, sep=";", encoding="utf-8")
            logger.info(f"[MOCK AD_SERVICE] CSV inicial creado en: {self.csv_path}")

    def _leer_csv_seguro(self) -> pd.DataFrame:
        """Lee el CSV tolerando encodings utf-8 y latin-1."""
        if not os.path.exists(self.csv_path):
            return pd.DataFrame(columns=_COLUMNAS_CSV)
        try:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="utf-8", on_bad_lines="skip").fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="latin-1", on_bad_lines="skip").fillna("")

    async def existe_usuario(self, username: str) -> bool:
        """
        Verifica si un username ya existe en la base AD dummy (CSV).
        También incluye un set estático de usuarios reservados del sistema.
        """
        _reservados = {"admin", "administrator", "lsanchez", "soporte", "guest"}
        if username.lower() in _reservados:
            return True
        try:
            df = self._leer_csv_seguro()
            if df.empty or "Username" not in df.columns:
                return False
            usuarios = df["Username"].astype(str).str.strip().str.lower().values
            return username.lower() in usuarios
        except Exception as e:
            logger.error(f"[MOCK AD_SERVICE] Error al verificar existencia de '{username}': {e}")
            return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simula la creación de un usuario en Active Directory.

        Parámetros esperados en datos:
            - username (str): Nombre de usuario a crear (ej. 'fgomez')
            - password_temp (str): Contraseña temporal (default 'T4nd3m**')
            - ou_destino (str): Ruta OU destino (ej. 'OU=Operador,OU=Usuarios,...')
            - must_change_pass (bool): Flag de cambio obligatorio al primer login
            - email (str): Email corporativo asociado
            - nombre (str): Nombre del empleado
            - apellido (str): Apellido del empleado
            - perfil (str): Perfil AD (Operador, Administrativo, etc.)

        Retorna:
            Dict con status, mode, data con las credenciales confirmadas.
        """
        username = str(datos.get("username") or "").strip()
        password_temp = datos.get("password_temp", "T4nd3m**")
        ou_destino = datos.get("ou_destino", "OU=Usuarios,DC=tandemtech,DC=com,DC=ar")
        must_change_pass = datos.get("must_change_pass", True)
        email = datos.get("email", "")
        nombre = datos.get("nombre", "")
        apellido = datos.get("apellido", "")
        perfil = datos.get("perfil", datos.get("org_unit", "").strip("/"))

        if not username:
            msg = "El username es obligatorio para crear usuario en AD."
            logger.error(f"[MOCK AD_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}

        # Pre-verificación de existencia
        if await self.existe_usuario(username):
            msg = f"El usuario '{username}' ya existe en Active Directory (MOCK)."
            logger.warning(f"[MOCK AD_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg, "username": username}

        try:
            nombre_completo = f"{nombre} {apellido}".strip()
            nuevo_registro = pd.DataFrame([{
                "Username": username,
                "NombreCompleto": nombre_completo,
                "OU": ou_destino,
                "Email": email,
                "Perfil": perfil,
                "MustChangePass": str(must_change_pass)
            }])
            nuevo_registro.to_csv(
                self.csv_path, mode="a", header=False, index=False, sep=";", encoding="utf-8"
            )
            logger.info(
                f"[MOCK AD_SERVICE] Usuario '{username}' creado en OU='{ou_destino}' "
                f"(MustChangePass={must_change_pass})."
            )
            return {
                "status": "success",
                "mode": "MOCK",
                "message": f"Usuario '{username}' creado exitosamente en Active Directory (simulado).",
                "data": {
                    "username": username,
                    "password_temp": password_temp,
                    "ou_destino": ou_destino,
                    "must_change_pass": must_change_pass,
                    "email": email,
                    "nombre_completo": nombre_completo,
                    "perfil": perfil,
                }
            }
        except Exception as e:
            msg = f"Error al registrar usuario AD en CSV: {str(e)}"
            logger.error(f"[MOCK AD_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}
