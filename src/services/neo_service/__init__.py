from config.settings import SIMULATE_INTEGRATIONS

if SIMULATE_INTEGRATIONS:
    from .dummy_service import DummyNeoService as ServiceClass
else:
    from .real_service import RealNeoService as ServiceClass

service_instance = ServiceClass()
neo_service = service_instance

async def crear_usuario_neotel(datos: dict) -> dict:
    return await service_instance.crear_usuario(datos)
