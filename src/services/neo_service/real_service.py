# ===================================================================
# ARCHIVO: src/services/neo_service/real_service.py
# DESCRIPCIÓN: Integración real con la API de NeoTel.
#              Crea el Telemarketer con legajo transformado (3xxx),
#              extrae y guarda el QR del token 2FA, y da de alta la
#              posición SIP con nat='yes'.
# ===================================================================

import os
import base64
import logging
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)

# Variables de entorno para la API de NeoTel
NEOTEL_API_URL  = os.getenv("NEOTEL_API_URL", "https://neotel.tuempresa.com/api")
NEOTEL_API_KEY  = os.getenv("NEOTEL_API_KEY", "")

# Directorio de almacenamiento de QRs
from config.settings import BASE_DIR
QR_DIR = os.path.join(BASE_DIR, "storage", "qrs")


class RealNeoService:
    """
    Servicio de integración real con la API REST de NeoTel.
    Variables de entorno requeridas: NEOTEL_API_URL, NEOTEL_API_KEY.
    """

    def __init__(self):
        os.makedirs(QR_DIR, exist_ok=True)
        self._headers = {
            "Authorization": f"Bearer {NEOTEL_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def usuario_existe(self, usuario_neo: str) -> bool:
        """
        Verifica si un Telemarketer ya existe en NeoTel.

        Args:
            usuario_neo: Código de usuario transformado (ej. '3005')
        Returns:
            True si existe, False si está disponible.
        """
        try:
            url = f"{NEOTEL_API_URL}/telemarketer/{usuario_neo}"
            response = requests.get(url, headers=self._headers, timeout=10)
            if response.status_code == 200:
                logger.info(f"[REAL NEO_SERVICE] Telemarketer '{usuario_neo}' YA EXISTE.")
                return True
            if response.status_code == 404:
                return False
            logger.warning(f"[REAL NEO_SERVICE] Respuesta inesperada al verificar '{usuario_neo}': {response.status_code}")
            return False
        except requests.RequestException as e:
            logger.error(f"[REAL NEO_SERVICE] Error de red al verificar '{usuario_neo}': {e}")
            return False

    def _guardar_qr_desde_base64(self, usuario_neo: str, nombre_apellido: str, qr_base64: str) -> str:
        """
        Guarda el QR recibido como base64 en un archivo PNG.

        Args:
            usuario_neo:    Código de usuario NeoTel
            nombre_apellido: Nombre completo del empleado
            qr_base64:      Contenido del QR en base64

        Returns:
            Ruta absoluta del archivo PNG guardado.
        """
        try:
            nombre_safe = "".join(c for c in nombre_apellido if c.isalnum() or c in "-_")
            filename = f"qr_neo_{usuario_neo}_{nombre_safe}.png"
            filepath = os.path.join(QR_DIR, filename)

            # Limpiar prefijo data URI si viene incluido
            if "," in qr_base64:
                qr_base64 = qr_base64.split(",", 1)[1]

            img_data = base64.b64decode(qr_base64)
            with open(filepath, "wb") as f:
                f.write(img_data)

            logger.info(f"[REAL NEO_SERVICE] QR guardado en: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[REAL NEO_SERVICE] Error al guardar QR de '{usuario_neo}': {e}")
            return ""

    async def _crear_telemarketer(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Alta del Telemarketer con legajo 3xxx y contraseña=DNI."""
        payload = {
            "usuario":   datos.get("usuario"),      # ej. '3005'
            "legajo":    datos.get("legajo"),        # ej. '1005'
            "password":  datos.get("dni", ""),       # Contraseña = DNI
            "nombre":    datos.get("nombre", ""),
            "apellido":  datos.get("apellido", ""),
        }
        url = f"{NEOTEL_API_URL}/telemarketer"
        response = requests.post(url, json=payload, headers=self._headers, timeout=15)
        response.raise_for_status()
        return response.json()

    async def _crear_posicion_sip(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Alta de la posición SIP (X-Lite) con nat='yes'."""
        nombre   = datos.get("nombre", "")
        apellido = datos.get("apellido", "")
        posicion_user = datos.get("posicion_user") or f"{nombre}{apellido}".replace(" ", "")

        payload = {
            "usuario":   posicion_user,    # ej. 'FabioGomez'
            "password":  "Tandem123",
            "protocolo": "SIP",
            "nat":       "yes",
            "nombre":    nombre,
            "apellido":  apellido,
        }
        url = f"{NEOTEL_API_URL}/posicion/sip"
        response = requests.post(url, json=payload, headers=self._headers, timeout=15)
        response.raise_for_status()
        return response.json()

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orquesta la creación completa en NeoTel:
        1. Alta de Telemarketer (usuario 3xxx, clave=DNI)
        2. Extracción/guardado del QR del token 2FA
        3. Alta de Posición SIP (nat='yes')

        Args:
            datos: Dict con usuario, legajo, dni, nombre, apellido, posicion_user

        Returns:
            Dict con status, mode y data incluyendo qr_path.
        """
        usuario_neo    = str(datos.get("usuario") or datos.get("legajo_neo") or "").strip()
        nombre_apellido = datos.get("nombre_apellido") or \
                          f"{datos.get('nombre', '')} {datos.get('apellido', '')}".strip()

        if not usuario_neo:
            return {"status": "error", "mode": "REAL", "detail": "El usuario NeoTel es obligatorio."}

        if self.usuario_existe(usuario_neo):
            return {
                "status": "error",
                "mode": "REAL",
                "detail": f"El usuario NeoTel '{usuario_neo}' ya existe.",
                "usuario": usuario_neo
            }

        qr_path = ""
        try:
            # 1. Alta Telemarketer
            resp_telemarketer = await self._crear_telemarketer(datos)
            logger.info(f"[REAL NEO_SERVICE] Telemarketer '{usuario_neo}' creado.")

            # 2. Extraer QR del 2FA (se asume que la API retorna campo 'qr_base64' o 'qr_url')
            qr_base64 = resp_telemarketer.get("qr_base64") or resp_telemarketer.get("totp_qr", "")
            if qr_base64:
                qr_path = self._guardar_qr_desde_base64(usuario_neo, nombre_apellido, qr_base64)

            # 3. Alta Posición SIP
            await self._crear_posicion_sip(datos)
            logger.info(f"[REAL NEO_SERVICE] Posición SIP creada para '{usuario_neo}'.")

            return {
                "status": "success",
                "mode": "REAL",
                "message": f"Usuario '{usuario_neo}' creado exitosamente en NeoTel.",
                "data": {
                    "usuario":         usuario_neo,
                    "legajo":          datos.get("legajo"),
                    "nombre_apellido": nombre_apellido,
                    "qr_path":         qr_path,
                    "qr_generado":     bool(qr_path),
                }
            }

        except requests.HTTPError as e:
            msg = f"Error HTTP al crear usuario NeoTel '{usuario_neo}': {e}"
            logger.error(f"[REAL NEO_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
        except requests.RequestException as e:
            msg = f"Error de red al conectar con NeoTel API: {e}"
            logger.error(f"[REAL NEO_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
        except Exception as e:
            msg = f"Error inesperado al crear usuario NeoTel '{usuario_neo}': {e}"
            logger.error(f"[REAL NEO_SERVICE] {msg}")
            return {"status": "error", "mode": "REAL", "detail": msg}
