# ===================================================================
# ARCHIVO: src/services/ad_service.py
# DESCRIPCIÓN: Servicio para integración con Active Directory (LDAP).
# ===================================================================

import logging
from typing import Dict, Any
from config.settings import SIMULATE_INTEGRATIONS

logger = logging.getLogger(__name__)

class ActiveDirectoryService:
    def __init__(self):
        self.mock_mode = SIMULATE_INTEGRATIONS
        self.mock_users = {"jperez", "admin", "lsanchez", "soporte"}

    async def verificar_usuario_existe(self, username: str) -> bool:
        if self.mock_mode:
            existe = username.lower() in self.mock_users
            logger.info(f"[MOCK AD] Verificando usuario {username}: {'EXISTE' if existe else 'DISPONIBLE'}")
            return existe
        
        # TODO: Lógica LDAP real
        return False

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        username = datos.get("usuario_ad")
        if self.mock_mode:
            self.mock_users.add(username)
            logger.info(f"[MOCK AD] Usuario {username} creado exitosamente.")
            return {"status": "success", "mode": "MOCK", "username": username}

        # TODO: Lógica creación LDAP real
        return {"status": "success", "mode": "REAL", "username": username}

ad_service = ActiveDirectoryService()