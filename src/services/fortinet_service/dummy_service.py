# ===================================================================
# ARCHIVO: src/services/fortinet_service/dummy_service.py
# DESCRIPCIÓN: Implementación simulada (MOCK) del servicio de
#              FortiGate VPN. Persiste usuarios en un CSV local
#              para verificación de colisiones y simula la creación
#              de usuarios locales con contraseña igual al DNI y
#              asignación al grupo VPN.
# ===================================================================

import os
import logging
import pandas as pd
from typing import Dict, Any
from config.settings import FORTINET_CSV_PATH

logger = logging.getLogger(__name__)

_COLUMNAS_CSV = ["Username", "NombreCompleto", "Email2FA", "GrupoVPN", "Perfil"]


class DummyFortinetService:
    """
    Servicio simulado de FortiGate VPN.
    Persiste usuarios en CSV para verificación de duplicados y registro de altas.
    """

    def __init__(self, csv_path: str = FORTINET_CSV_PATH):
        self.csv_path = csv_path
        # Usuarios de sistema siempre reservados
        self._reservados = {"admin", "JuanPerez", "LucianaGutierrez", "PamelaRoig"}
        self._asegurar_csv_existe()

    def _asegurar_csv_existe(self) -> None:
        """Crea el directorio y el CSV con cabeceras si no existen."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=_COLUMNAS_CSV)
            df.to_csv(self.csv_path, index=False, sep=";", encoding="utf-8")
            logger.info(f"[MOCK FORTINET_SERVICE] CSV inicial creado en: {self.csv_path}")

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
        Verifica si un usuario VPN ya existe en la base FortiGate dummy (CSV).

        Args:
            username: Nombre de usuario a verificar (ej. 'FabioGomez')
        Returns:
            True si existe, False si está disponible.
        """
        if username in self._reservados:
            return True
        try:
            df = self._leer_csv_seguro()
            if df.empty or "Username" not in df.columns:
                return False
            usuarios = df["Username"].astype(str).str.strip().values
            return username.strip() in usuarios
        except Exception as e:
            logger.error(f"[MOCK FORTINET_SERVICE] Error al verificar '{username}': {e}")
            return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simula la creación de un usuario local VPN en FortiGate.

        Parámetros esperados:
            - username (str):   Nombre de usuario (ej. 'FabioGomez')
            - password_temp (str): Contraseña — debe ser igual al DNI
            - email_2fa (str):  Email corporativo para autenticación 2FA
            - grupo_vpn (str):  Grupo de túnel VPN a asignar
            - nombre, apellido: Datos del empleado

        Retorna:
            Dict con status, mode y data con las credenciales VPN confirmadas.
        """
        username   = str(datos.get("username") or datos.get("usuario") or "").strip()
        password   = str(datos.get("password_temp") or datos.get("dni") or "").strip()
        email_2fa  = datos.get("email_2fa", datos.get("email", ""))
        grupo_vpn  = datos.get("grupo_vpn", "VPN_Usuarios_remotos")
        nombre     = datos.get("nombre", "")
        apellido   = datos.get("apellido", "")

        if not username:
            msg = "El username es obligatorio para crear usuario VPN en FortiGate."
            logger.error(f"[MOCK FORTINET_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}

        if not password:
            msg = f"La contraseña (DNI) es obligatoria para el usuario '{username}'."
            logger.error(f"[MOCK FORTINET_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}

        # Pre-verificación de existencia
        if await self.existe_usuario(username):
            msg = f"El usuario '{username}' ya existe en FortiGate VPN (MOCK)."
            logger.warning(f"[MOCK FORTINET_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg, "username": username}

        try:
            nombre_completo = f"{nombre} {apellido}".strip()
            nuevo_registro = pd.DataFrame([{
                "Username":       username,
                "NombreCompleto": nombre_completo,
                "Email2FA":       email_2fa,
                "GrupoVPN":       grupo_vpn,
                "Perfil":         datos.get("perfil", ""),
            }])
            nuevo_registro.to_csv(
                self.csv_path, mode="a", header=False, index=False, sep=";", encoding="utf-8"
            )
            logger.info(
                f"[MOCK FORTINET_SERVICE] Usuario VPN '{username}' creado "
                f"en grupo '{grupo_vpn}' con 2FA: '{email_2fa}'."
            )
            return {
                "status": "success",
                "mode": "MOCK",
                "message": f"Usuario VPN '{username}' creado exitosamente en FortiGate (simulado).",
                "data": {
                    "username":        username,
                    "password_temp":   password,
                    "email_2fa":       email_2fa,
                    "grupo_vpn":       grupo_vpn,
                    "nombre_completo": nombre_completo,
                }
            }
        except Exception as e:
            msg = f"Error al registrar usuario FortiGate en CSV: {str(e)}"
            logger.error(f"[MOCK FORTINET_SERVICE] {msg}")
            return {"status": "error", "mode": "MOCK", "detail": msg}
