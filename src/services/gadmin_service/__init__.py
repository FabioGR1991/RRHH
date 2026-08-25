from config.settings import SIMULATE_INTEGRATIONS

if SIMULATE_INTEGRATIONS:
    from .dummy_service import DummyGAdminService as ServiceClass
else:
    from .real_service import RealGAdminService as ServiceClass

service_instance = ServiceClass()
gadmin_service = service_instance

async def crear_casilla_google(datos: dict) -> dict:
    return await service_instance.crear_casilla(datos)
