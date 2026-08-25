from config.settings import SIMULATE_INTEGRATIONS

if SIMULATE_INTEGRATIONS:
    from .dummy_service import DummyFortinetService as ServiceClass
else:
    from .real_service import RealFortinetService as ServiceClass

service_instance = ServiceClass()
fortinet_service = service_instance

async def crear_usuario_fortinet(datos: dict) -> dict:
    return await service_instance.crear_usuario(datos)
