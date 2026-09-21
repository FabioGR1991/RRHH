# ===================================================================
# ARCHIVO: src/services/fortinet_service/real_service.py
# DESCRIPCIÓN: Integración real con FortiGate via SSH (Paramiko).
#              Crea usuarios locales VPN con contraseña igual al DNI,
#              asigna el mail corporativo para 2FA y agrega al grupo
#              de túnel VPN configurado.
#
#              ALTERNATIVA REST API: Los métodos están comentados al
#              final del archivo. Descomentarlos si el FortiGate tiene
#              la API REST habilitada (/api/v2/cmdb/user/local).
# ===================================================================

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Variables de entorno para conexión FortiGate
FORTIGATE_HOST     = os.getenv("FORTIGATE_HOST", "192.168.1.1")
FORTIGATE_PORT     = int(os.getenv("FORTIGATE_PORT", 22))
FORTIGATE_USER     = os.getenv("FORTIGATE_USER", "admin_forti")
FORTIGATE_PASSWORD = os.getenv("FORTIGATE_PASSWORD", "")
FORTIGATE_VPN_GROUP = os.getenv("FORTIGATE_VPN_GROUP", "VPN_Usuarios_remotos")

# Control de disponibilidad de Paramiko
try:
    import paramiko
    _PARAMIKO_AVAILABLE = True
except ImportError:
    _PARAMIKO_AVAILABLE = False
    logger.warning("[REAL FORTINET_SERVICE] paramiko no disponible. Instalar con: pip install paramiko")


def _get_ssh_client() -> "paramiko.SSHClient":
    """Crea y retorna un cliente SSH conectado al FortiGate."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=FORTIGATE_HOST,
        port=FORTIGATE_PORT,
        username=FORTIGATE_USER,
        password=FORTIGATE_PASSWORD,
        timeout=15,
        look_for_keys=False,
        allow_agent=False
    )
    return client


def _ejecutar_comandos_forti(client: "paramiko.SSHClient", comandos: list[str]) -> str:
    """
    Ejecuta una secuencia de comandos en FortiOS CLI via SSH interactivo.

    Args:
        client: Cliente SSH conectado
        comandos: Lista de comandos CLI de FortiOS

    Returns:
        Salida concatenada de todos los comandos.
    """
    shell = client.invoke_shell()
    output = ""

    # Esperar prompt inicial
    import time
    time.sleep(1)
    shell.recv(4096)  # Vaciar buffer inicial

    for cmd in comandos:
        shell.send(cmd + "\n")
        time.sleep(0.5)
        if shell.recv_ready():
            output += shell.recv(4096).decode("utf-8", errors="ignore")

    # Leer salida final
    time.sleep(1)
    while shell.recv_ready():
        output += shell.recv(4096).decode("utf-8", errors="ignore")

    return output


class RealFortinetService:
    """
    Servicio de integración real con FortiGate via SSH (Paramiko).
    Requiere: FORTIGATE_HOST, FORTIGATE_PORT, FORTIGATE_USER, FORTIGATE_PASSWORD.
    """

    def __init__(self):
        if not _PARAMIKO_AVAILABLE:
            logger.error("[REAL FORTINET_SERVICE] paramiko no está instalado. Módulo inoperativo.")

    async def existe_usuario(self, username: str) -> bool:
        """
        Verifica si un usuario local ya existe en FortiGate.

        Args:
            username: Nombre del usuario VPN a verificar.
        Returns:
            True si existe, False si está disponible o en caso de error.
        """
        if not _PARAMIKO_AVAILABLE:
            return False
        try:
            client = _get_ssh_client()
            comandos = [
                "config user local",
                f"show | grep {username}",
                "end"
            ]
            output = _ejecutar_comandos_forti(client, comandos)
            client.close()
            existe = username in output
            logger.info(
                f"[REAL FORTINET_SERVICE] Usuario '{username}': "
                f"{'EXISTE' if existe else 'LIBRE'} en FortiGate."
            )
            return existe
        except Exception as e:
            logger.error(f"[REAL FORTINET_SERVICE] Error al verificar '{username}': {e}")
            return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un usuario local VPN en FortiGate via CLI SSH.

        Secuencia de comandos FortiOS:
        1. config user local / edit <username> → crea usuario local
        2. set type password → tipo de autenticación
        3. set passwd <dni> → contraseña = DNI del empleado
        4. set email-to <email> → email para 2FA
        5. end → confirmar usuario
        6. config user group / edit <grupo> → agregar al grupo VPN
        7. append member <username> → agregar miembro
        8. end → confirmar grupo

        Parámetros esperados:
            - username (str):   Nombre de usuario (ej. 'FabioGomez')
            - password_temp:    Contraseña (debe ser el DNI)
            - email_2fa:        Email corporativo para 2FA Fortinet
            - grupo_vpn:        Grupo VPN destino
            - nombre, apellido: Datos del empleado

        Retorna:
            Dict con status, mode y data con las credenciales VPN confirmadas.
        """
        if not _PARAMIKO_AVAILABLE:
            return {
                "status": "error",
                "mode": "REAL",
                "detail": "paramiko no está instalado en este entorno."
            }

        username    = str(datos.get("username") or datos.get("usuario") or "").strip()
        password    = str(datos.get("password_temp") or datos.get("dni") or "").strip()
        email_2fa   = datos.get("email_2fa", datos.get("email", ""))
        grupo_vpn   = datos.get("grupo_vpn", FORTIGATE_VPN_GROUP)
        nombre      = datos.get("nombre", "")
        apellido    = datos.get("apellido", "")

        if not username:
            return {"status": "error", "mode": "REAL", "detail": "El username es obligatorio."}
        if not password:
            return {"status": "error", "mode": "REAL", "detail": "La contraseña (DNI) es obligatoria."}

        # Pre-verificación de existencia
        if await self.existe_usuario(username):
            return {
                "status": "error",
                "mode": "REAL",
                "detail": f"El usuario '{username}' ya existe en FortiGate VPN.",
                "username": username
            }

        try:
            client = _get_ssh_client()

            # Comandos para crear el usuario local
            comandos_usuario = [
                "config user local",
                f"edit {username}",
                "set type password",
                f"set passwd {password}",
                f"set email-to {email_2fa}",
                "set two-factor email",   # Habilitar 2FA via email
                "next",
                "end",
            ]

            # Comandos para agregar al grupo VPN
            comandos_grupo = [
                "config user group",
                f"edit {grupo_vpn}",
                f"append member {username}",
                "end",
            ]

            output_usuario = _ejecutar_comandos_forti(client, comandos_usuario)
            logger.info(f"[REAL FORTINET_SERVICE] Comandos de usuario ejecutados. Output: {output_usuario[:200]}")

            output_grupo = _ejecutar_comandos_forti(client, comandos_grupo)
            logger.info(f"[REAL FORTINET_SERVICE] Comandos de grupo ejecutados. Output: {output_grupo[:200]}")

            client.close()

            nombre_completo = f"{nombre} {apellido}".strip()
            logger.info(
                f"[REAL FORTINET_SERVICE] Usuario VPN '{username}' creado "
                f"en grupo '{grupo_vpn}' con 2FA: '{email_2fa}'."
            )

            return {
                "status": "success",
                "mode": "REAL",
                "message": f"Usuario VPN '{username}' creado exitosamente en FortiGate.",
                "data": {
                    "username":        username,
                    "password_temp":   password,
                    "email_2fa":       email_2fa,
                    "grupo_vpn":       grupo_vpn,
                    "nombre_completo": nombre_completo,
                }
            }

        except Exception as e:
            msg = f"Error al crear usuario FortiGate '{username}' via SSH: {e}"
            logger.error(f"[REAL FORTINET_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}


# ===================================================================
# ALTERNATIVA: Integración via REST API FortiGate
# Descomentar si el appliance tiene la REST API habilitada.
# ===================================================================
# import requests
#
# FORTIGATE_API_URL  = os.getenv("FORTIGATE_API_URL", f"https://{FORTIGATE_HOST}/api/v2")
# FORTIGATE_API_KEY  = os.getenv("FORTIGATE_API_KEY", "")
#
# async def _crear_usuario_rest(username, password, email_2fa, grupo_vpn):
#     headers = {
#         "Authorization": f"Bearer {FORTIGATE_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "name":      username,
#         "type":      "password",
#         "passwd":    password,
#         "email-to":  email_2fa,
#         "status":    "enable"
#     }
#     url = f"{FORTIGATE_API_URL}/cmdb/user/local"
#     resp = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
#     resp.raise_for_status()
#     return resp.json()
