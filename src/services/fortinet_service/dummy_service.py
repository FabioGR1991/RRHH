import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DummyFortinetService:
    def __init__(self):
        self.mock_data = {"jperez", "admin", "soporte"}

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        identifier = datos.get("username") or datos.get("email") or datos.get("usuario") or "test_user"
        logger.info(f"[MOCK FORTINET_SERVICE] Operación simulada para: {identifier}")
        return {"status": "success", "mode": "MOCK", "data": identifier}
