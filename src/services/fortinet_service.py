# ===================================================================
# ARCHIVO: src/services/fortinet_service.py
# DESCRIPCIÓN: Servicio para integración con Fortigate 100F (VPN).
# ===================================================================

import logging
from typing import Dict, Any
from config.settings import SIMULATE_INTEGRATIONS

logger = logging.getLogger(__name__)

class FortinetService:
    def __init__(self):
        self.mock_mode = SIMULATE_INTEGRATIONS
        self.mock_vpn_users = {"jperez", "admin"}

    async def verificar_usuario_existe(self, username: str) -> bool:
        if self.mock_mode:
            existe = username.lower() in self.mock_vpn_users
            logger.info(f"[MOCK Fortinet] Verificando VPN {username}: {'EXISTE' if existe else 'DISPONIBLE'}")
            return existe
        
        return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        username = datos.get("usuario_fortinet")
        if self.mock_mode:
            self.mock_vpn_users.add(username)
            logger.info(f"[MOCK Fortinet] Cuenta VPN {username} creada exitosamente.")
            return {"status": "success", "mode": "MOCK", "username": username}

        return {"status": "success", "mode": "REAL", "username": username}

fortinet_service = FortinetService()