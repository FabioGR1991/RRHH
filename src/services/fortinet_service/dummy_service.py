import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DummyFortinetService:
    def __init__(self):
        self.mock_data = {"JuanPerez", "LucianaGutierrez", "PamelaRoig"}

    async def existe_usuario(self, username: str) -> bool:
        return username in self.mock_data

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        identifier = datos.get("username") or datos.get("usuario") or "UsuarioFortinet"
        logger.info(f"[MOCK FORTINET_SERVICE] Creación simulada de VPN Fortinet para: {identifier}")
        return {"status": "success", "mode": "MOCK", "data": identifier}
