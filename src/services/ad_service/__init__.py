from config.settings import SIMULATE_INTEGRATIONS

if SIMULATE_INTEGRATIONS:
    from .dummy_service import DummyActiveDirectoryService as ServiceClass
else:
    from .real_service import RealActiveDirectoryService as ServiceClass

service_instance = ServiceClass()
ad_service = service_instance

async def crear_usuario_ad(datos: dict) -> dict:
    return await service_instance.crear_usuario(datos)
