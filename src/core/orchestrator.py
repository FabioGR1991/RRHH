# ===================================================================
# ARCHIVO: src/core/orchestrator.py
# ===================================================================

import logging
from typing import Dict, Any, Optional, Set

from src.core.generator import generar_credenciales_propuestas
from src.services.neo_service.dummy_service import DummyNeoService

logger = logging.getLogger(__name__)

def obtener_usuario_neotel_desde_legajo(legajo: str) -> str:
    """
    Regla de Negocio NeoTel:
    Transforma el Legajo reemplazando el primer caracter '1' por '3'.
    Ejemplo: '1005' -> '3005'. Si no empieza con '1', antepone '3'.
    """
    legajo_str = str(legajo).strip()
    if not legajo_str:
        return ""
    if legajo_str.startswith("1"):
        return "3" + legajo_str[1:]
    return "3" + legajo_str

class Orchestrator:
    def __init__(self):
        self.neo_service = DummyNeoService()

    async def prevalidar_solicitud(
        self, 
        datos_solicitud: Dict[str, Any], 
        check_services: Optional[Dict[str, Any]] = None,
        reservados_batch: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Fase de Pre-Validación (Re-verificar disponibilidad / Preview).
        Consulta la disponibilidad cruzada en los servicios reales/mocks y en NeoTel.
        """
        # 1. Generar la propuesta de credenciales conservando el estado del lote
        propuesta = generar_credenciales_propuestas(
            datos_solicitud, 
            check_services=check_services, 
            reservados_batch=reservados_batch
        )
        
        # 2. Obtener el Legajo de la solicitud
        legajo_raw = (
            datos_solicitud.get("legajo") 
            or datos_solicitud.get("legajo_original") 
            or propuesta.get("legajo")
        )
        
        # 3. Calcular el usuario NeoTel asignado (3xxx)
        usuario_neo = (
            propuesta.get("neotel", {}).get("usuario") 
            or propuesta.get("legajo_neo") 
            or obtener_usuario_neotel_desde_legajo(legajo_raw)
        )

        logger.info(f"[ORCHESTRATOR] Crosscheck disponibilidad para Legajo Raw: {legajo_raw} -> Usuario Neo: {usuario_neo}")

        conflictos = []

        # 4. Crosscheck contra el CSV de NeoTel
        if not usuario_neo:
            conflictos.append({
                "plataforma": "NeoTel",
                "campo": "Usuario / Legajo Neo",
                "valor": "-",
                "motivo": "No se pudo determinar el Legajo o Usuario NeoTel de la solicitud."
            })
        elif self.neo_service.usuario_existe(usuario_neo):
            conflictos.append({
                "plataforma": "NeoTel",
                "campo": "Usuario / Legajo Neo",
                "valor": usuario_neo,
                "motivo": f"El usuario NeoTel '{usuario_neo}' ya se encuentra ocupado en la base de datos CSV."
            })

        es_valido = len(conflictos) == 0

        return {
            "valido": es_valido,
            "propuesta": propuesta,
            "usuario_neo": usuario_neo,
            "conflictos": conflictos
        }

    async def ejecutar_alta_confirmada(
        self, 
        datos_solicitud: Dict[str, Any], 
        check_services: Optional[Dict[str, Any]] = None,
        reservados_batch: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Ejecución real / Simulación de la creación de cuentas al 'Confirmar y Ejecutar Alta'.
        """
        # 1. Prevalidar disponibilidades pasando servicios de verificación y el lote reservado
        pre_check = await self.prevalidar_solicitud(
            datos_solicitud, 
            check_services=check_services, 
            reservados_batch=reservados_batch
        )
        if not pre_check["valido"]:
            logger.warning(f"[ORCHESTRATOR] Intento de alta rechazado por conflictos: {pre_check['conflictos']}")
            return {
                "exito": False,
                "mensaje": "No se puede ejecutar el alta debido a conflictos de duplicidad.",
                "errores": pre_check["conflictos"]
            }

        propuesta = pre_check["propuesta"]
        usuario_neo = pre_check["usuario_neo"]
        resultados_ejecucion = {}

        # 2. Construir payload con claves explícitas para DummyNeoService
        nombre = datos_solicitud.get("nombre", "")
        apellido = datos_solicitud.get("apellido", "")
        
        datos_neo = {
            "usuario": usuario_neo,
            "legajo_neo": usuario_neo,
            "legajo": datos_solicitud.get("legajo"),
            "nombre": nombre,
            "apellido": apellido,
            "nombre_apellido": f"{nombre} {apellido}".strip()
        }
        
        # 3. Escribir en la BD Dummy (CSV)
        res_neo = await self.neo_service.crear_usuario(datos_neo)
        resultados_ejecucion["neotel"] = res_neo

        exito_global = res_neo.get("status") == "success"

        return {
            "exito": exito_global,
            "mensaje": "Alta orquestada procesada correctamente." if exito_global else "Fallo en aprovisionamiento de servicios.",
            "detalles": resultados_ejecucion,
            "credenciales_finales": propuesta
        }

# Instancia global del orquestador
orchestrator = Orchestrator()