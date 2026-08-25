from config.settings import SIMULATE_INTEGRATIONS

if SIMULATE_INTEGRATIONS:
    from .dummy_service import DummyXLiteService as ServiceClass
else:
    from .real_service import RealXLiteService as ServiceClass

service_instance = ServiceClass()
xlite_service = service_instance

async def crear_usuario_xlite(datos: dict) -> dict:
    return await service_instance.crear_usuario(datos)
