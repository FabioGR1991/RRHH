import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DummyGAdminService:
    def __init__(self):
        self.mock_data = {"jperez@tuempresa.com", "admin@tuempresa.com", "soporte@tuempresa.com"}

    async def crear_casilla(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        identifier = datos.get("email") or datos.get("username") or datos.get("usuario") or "test@tuempresa.com"
        logger.info(f"[MOCK GADMIN_SERVICE] Operación simulada para: {identifier}")
        return {"status": "success", "mode": "MOCK", "data": identifier}
