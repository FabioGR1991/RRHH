import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DummyActiveDirectoryService:
    def __init__(self):
        # Quitamos "jperez" para que la sintaxis inicial+apellido quede libre en pruebas
        self.mock_data = {"admin", "lsanchez", "soporte"}

    async def existe_usuario(self, username: str) -> bool:
        return username in self.mock_data

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        identifier = datos.get("username") or datos.get("email") or datos.get("usuario") or "test_user"
        logger.info(f"[MOCK AD_SERVICE] Operación simulada para: {identifier}")
        return {"status": "success", "mode": "MOCK", "data": identifier}
