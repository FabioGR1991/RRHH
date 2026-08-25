# ===================================================================
# ARCHIVO: src/services/neo_service.py
# DESCRIPCIÓN: Servicio para integración con Telefonía / Sistema NEO.
# ===================================================================

import logging
from typing import Dict, Any
from config.settings import SIMULATE_INTEGRATIONS

logger = logging.getLogger(__name__)

class NeoService:
    def __init__(self):
        self.mock_mode = SIMULATE_INTEGRATIONS
        self.mock_neo_users = {"jperez", "admin"}

    async def verificar_usuario_existe(self, username: str) -> bool:
        if self.mock_mode:
            existe = username.lower() in self.mock_neo_users
            logger.info(f"[MOCK NEO] Verificando usuario {username}: {'EXISTE' if existe else 'DISPONIBLE'}")
            return existe
        
        return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        username = datos.get("usuario_neo")
        if self.mock_mode:
            self.mock_neo_users.add(username)
            logger.info(f"[MOCK NEO] Usuario {username} creado en NEO.")
            return {"status": "success", "mode": "MOCK", "username": username}

        return {"status": "success", "mode": "REAL", "username": username}

neo_service = NeoService()