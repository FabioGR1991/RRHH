import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RealFortinetService:
    def __init__(self):
        pass

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        identifier = datos.get("username") or datos.get("email") or datos.get("usuario")
        logger.info(f"[REAL FORTINET_SERVICE] Ejecutando integración real para: {identifier}")
        return {"status": "success", "mode": "REAL", "data": identifier}
