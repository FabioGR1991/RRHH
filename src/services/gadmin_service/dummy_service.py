# ===================================================================
# ARCHIVO: src/services/gadmin_service/dummy_service.py
# DESCRIPCIÓN: Implementación simulada (MOCK) del servicio de
#              Google Workspace Admin SDK. Persiste casillas en un
#              CSV local para verificar colisiones de disponibilidad.
# ===================================================================

import os
import logging
import pandas as pd
from typing import Dict, Any
from config.settings import GADMIN_CSV_PATH

logger = logging.getLogger(__name__)

_COLUMNAS_CSV = ["Email", "Username", "NombreCompleto", "OrgUnit", "Perfil"]


class DummyGAdminService:
    """
    Servicio simulado de Google Workspace Admin SDK.
    Persiste las casillas creadas en un CSV para verificación de duplicados.
    """

    def __init__(self, csv_path: str = GADMIN_CSV_PATH):
        self.csv_path = csv_path
        # Casillas de sistema que siempre se consideran ocupadas
        self._reservados = {
            "admin@tandemtech.com.ar",
            "soporte@tandemtech.com.ar",
            "noreply@tandemtech.com.ar",
        }
        self._asegurar_csv_existe()

    def _asegurar_csv_existe(self) -> None:
        """Crea el directorio y el CSV con cabeceras si no existen."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=_COLUMNAS_CSV)
            df.to_csv(self.csv_path, index=False, sep=";", encoding="utf-8")
            logger.info(f"[MOCK GADMIN_SERVICE] CSV inicial creado en: {self.csv_path}")

    def _leer_csv_seguro(self) -> pd.DataFrame:
        """Lee el CSV tolerando encodings utf-8 y latin-1."""
        if not os.path.exists(self.csv_path):
            return pd.DataFrame(columns=_COLUMNAS_CSV)
        try:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="utf-8", on_bad_lines="skip").fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="latin-1", on_bad_lines="skip").fillna("")

    async def existe_usuario(self, email: str) -> bool:
        """
        Verifica si una casilla de correo ya existe en el workspace dummy (CSV).

        Args:
            email: Dirección de correo completa (ej. 'fgomez@tandemtech.com.ar')
        Returns:
            True si la casilla ya existe, False si está disponible.
        """
        email_lower = email.lower().strip()
        if email_lower in self._reservados:
            return True
        try:
            df = self._leer_csv_seguro()
            if df.empty or "Email" not in df.columns:
                return False
            emails = df["Email"].astype(str).str.strip().str.lower().values
            return email_lower in emails
        except Exception as e:
            logger.error(f"[MOCK GADMIN_SERVICE] Error al verificar '{email}': {e}")
            return False

    async def crear_casilla(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simula la creación de una casilla corporativa en Google Workspace.

        Parámetros esperados:
            - email (str):        Correo corporativo a crear (ej. 'fgomez@tandemtech.com.ar')
            - password_temp (str): Contraseña inicial (default 'T4nd3m**')
            - org_unit (str):      Unidad organizativa (ej. '/Operador')
            - nombre, apellido:    Datos del empleado
            - username (str):      sAMAccountName / parte local del email

        Retorna:
            Dict con status, mode y data con los datos de la casilla creada.
        """
        email        = str(datos.get("email") or "").strip()
        password     = datos.get("password_temp", "T4nd3m**")
        org_unit     = datos.get("org_unit", "/")
        nombre       = datos.get("nombre", "")
        apellido     = datos.get("apellido", "")
        username     = datos.get("username") or (email.split("@")[0] if "@" in email else "")
        perfil       = datos.get("perfil", org_unit.strip("/"))

        if not email or "@" not in email:
            msg = "El email corporativo es obligatorio y debe ser una dirección válida."
            logger.error(f"[MOCK GADMIN_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}

        # Pre-verificación de disponibilidad
        if await self.existe_usuario(email):
            msg = f"La casilla '{email}' ya existe en Google Workspace (MOCK)."
            logger.warning(f"[MOCK GADMIN_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg, "email": email}

        try:
            nombre_completo = f"{nombre} {apellido}".strip()
            nuevo_registro = pd.DataFrame([{
                "Email":          email,
                "Username":       username,
                "NombreCompleto": nombre_completo,
                "OrgUnit":        org_unit,
                "Perfil":         perfil,
            }])
            nuevo_registro.to_csv(
                self.csv_path, mode="a", header=False, index=False, sep=";", encoding="utf-8"
            )
            logger.info(
                f"[MOCK GADMIN_SERVICE] Casilla '{email}' creada en OrgUnit='{org_unit}'."
            )
            return {
                "status": "success",
                "mode": "MOCK",
                "message": f"Casilla '{email}' creada exitosamente en Google Workspace (simulado).",
                "data": {
                    "email":              email,
                    "username":           username,
                    "password_temp":      password,
                    "org_unit":           org_unit,
                    "nombre_completo":    nombre_completo,
                    "change_password_at_next_login": True,
                }
            }
        except Exception as e:
            msg = f"Error al registrar casilla GAdmin en CSV: {str(e)}"
            logger.error(f"[MOCK GADMIN_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}
