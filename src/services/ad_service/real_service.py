# ===================================================================
# ARCHIVO: src/services/ad_service/real_service.py
# DESCRIPCIÓN: Integración real con Active Directory mediante ldap3.
#              Verifica existencia de usuarios y crea cuentas en la OU
#              correspondiente con clave temporal y flag de cambio
#              obligatorio en el primer inicio de sesión.
# ===================================================================

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Variables de entorno para conexión AD
AD_SERVER   = os.getenv("AD_SERVER", "192.168.1.10")
AD_DOMAIN   = os.getenv("AD_DOMAIN", "tandemtech.com.ar")
AD_USER     = os.getenv("AD_ADMIN_USER", "admin_it")
AD_PASSWORD = os.getenv("AD_ADMIN_PASSWORD", "")
AD_BASE_DN  = os.getenv("AD_BASE_DN", "DC=tandemtech,DC=com,DC=ar")

# Contraseña temporal predeterminada para nuevos usuarios
TEMP_PASSWORD = "T4nd3m**"

# Control de estado de import (ldap3 puede no estar instalado en algunos entornos)
try:
    from ldap3 import Server, Connection, ALL, MODIFY_REPLACE, NTLM, SUBTREE
    from ldap3.core.exceptions import LDAPException, LDAPBindError
    _LDAP3_AVAILABLE = True
except ImportError:
    _LDAP3_AVAILABLE = False
    logger.warning("[REAL AD_SERVICE] ldap3 no disponible. Instalar con: pip install ldap3")


def _get_connection() -> "Connection":
    """Crea y devuelve una conexión autenticada al servidor AD."""
    server = Server(AD_SERVER, get_info=ALL)
    bind_user = f"{AD_DOMAIN}\\{AD_USER}"
    conn = Connection(
        server,
        user=bind_user,
        password=AD_PASSWORD,
        authentication=NTLM,
        auto_bind=True
    )
    return conn


def _encode_password(password: str) -> bytes:
    """Codifica la contraseña en formato Unicode requerido por AD."""
    return ('"%s"' % password).encode("utf-16-le")


class RealActiveDirectoryService:
    """
    Servicio de integración real con Active Directory via ldap3.
    Requiere variables de entorno: AD_SERVER, AD_DOMAIN, AD_ADMIN_USER, AD_ADMIN_PASSWORD.
    """

    def __init__(self):
        if not _LDAP3_AVAILABLE:
            logger.error("[REAL AD_SERVICE] ldap3 no está instalado. Módulo inoperativo.")

    async def existe_usuario(self, username: str) -> bool:
        """
        Consulta el AD para verificar si el sAMAccountName ya existe.

        Args:
            username: Nombre de usuario a verificar (sin dominio).
        Returns:
            True si el usuario existe, False en caso contrario.
        """
        if not _LDAP3_AVAILABLE:
            return False
        try:
            conn = _get_connection()
            filtro = f"(sAMAccountName={username})"
            conn.search(
                search_base=AD_BASE_DN,
                search_filter=filtro,
                search_scope=SUBTREE,
                attributes=["sAMAccountName"]
            )
            existe = len(conn.entries) > 0
            conn.unbind()
            logger.info(f"[REAL AD_SERVICE] Verificación AD para '{username}': {'EXISTE' if existe else 'LIBRE'}")
            return existe
        except LDAPBindError as e:
            logger.error(f"[REAL AD_SERVICE] Error de autenticación AD: {e}")
            return False
        except LDAPException as e:
            logger.error(f"[REAL AD_SERVICE] Error LDAP al verificar '{username}': {e}")
            return False
        except Exception as e:
            logger.error(f"[REAL AD_SERVICE] Error inesperado al verificar '{username}': {e}")
            return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un usuario en Active Directory con clave temporal y flag de cambio obligatorio.

        Parámetros esperados:
            - username:       sAMAccountName del nuevo usuario (ej. 'fgomez')
            - password_temp:  Contraseña temporal (default TEMP_PASSWORD)
            - ou_destino:     DN de la OU destino
            - nombre, apellido: Datos personales para displayName y cn
            - email:          Correo corporativo (mail attribute)
            - perfil:         Perfil/Departamento

        Retorna:
            Dict con status, mode y data con credenciales confirmadas.
        """
        if not _LDAP3_AVAILABLE:
            return {
                "status": "error",
                "mode": "REAL",
                "detail": "ldap3 no está instalado en este entorno."
            }

        username     = str(datos.get("username") or "").strip()
        password     = datos.get("password_temp", TEMP_PASSWORD)
        ou_destino   = datos.get("ou_destino", f"OU=Usuarios,{AD_BASE_DN}")
        nombre       = datos.get("nombre", "")
        apellido     = datos.get("apellido", "")
        email        = datos.get("email", "")
        perfil       = datos.get("perfil", "")

        if not username:
            return {"status": "error", "mode": "REAL", "detail": "El username es obligatorio."}

        nombre_completo = f"{nombre} {apellido}".strip()
        display_name    = nombre_completo or username
        dn_usuario      = f"CN={display_name},{ou_destino}"

        # Atributos del objeto de usuario AD
        atributos_usuario = {
            "objectClass":       ["top", "person", "organizationalPerson", "user"],
            "sAMAccountName":    username,
            "userPrincipalName": f"{username}@{AD_DOMAIN}",
            "givenName":         nombre,
            "sn":                apellido,
            "displayName":       display_name,
            "mail":              email,
            "department":        perfil,
            # 512 = cuenta normal habilitada | 544 = usuario debe cambiar pass al siguiente logon
            "userAccountControl": "544",
        }

        try:
            conn = _get_connection()

            # Verificación previa de existencia
            if await self.existe_usuario(username):
                conn.unbind()
                return {
                    "status": "error",
                    "mode": "REAL",
                    "detail": f"El usuario '{username}' ya existe en Active Directory.",
                    "username": username
                }

            # 1. Crear el objeto de usuario
            conn.add(dn_usuario, attributes=atributos_usuario)
            if not conn.result["result"] == 0:
                raise LDAPException(f"Error al crear usuario: {conn.result['description']}")

            # 2. Establecer la contraseña (requiere conexión SSL/TLS en producción)
            conn.modify(
                dn_usuario,
                {"unicodePwd": [(MODIFY_REPLACE, [_encode_password(password)])]}
            )

            # 3. Habilitar la cuenta y marcar cambio de contraseña obligatorio
            conn.modify(
                dn_usuario,
                {
                    "userAccountControl": [(MODIFY_REPLACE, [512])],
                    "pwdLastSet":         [(MODIFY_REPLACE, [0])]   # 0 = fuerza cambio al próximo login
                }
            )

            conn.unbind()
            logger.info(
                f"[REAL AD_SERVICE] Usuario '{username}' creado exitosamente en '{ou_destino}'."
            )
            return {
                "status": "success",
                "mode": "REAL",
                "message": f"Usuario '{username}' creado en Active Directory.",
                "data": {
                    "username":         username,
                    "dn":               dn_usuario,
                    "password_temp":    password,
                    "ou_destino":       ou_destino,
                    "must_change_pass": True,
                    "email":            email,
                    "nombre_completo":  nombre_completo,
                }
            }

        except LDAPBindError as e:
            msg = f"Error de autenticación AD al crear usuario '{username}': {e}"
            logger.error(f"[REAL AD_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
        except LDAPException as e:
            msg = f"Error LDAP al crear usuario '{username}': {e}"
            logger.error(f"[REAL AD_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
        except Exception as e:
            msg = f"Error inesperado al crear usuario AD '{username}': {e}"
            logger.error(f"[REAL AD_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
