import os
from config.settings import SIMULATE_INTEGRATIONS
from .dummy_service import crear_ticket_zammad as crear_ticket_dummy
from .real_service import crear_ticket_zammad as crear_ticket_real

# Usa la configuración global SIMULATE_INTEGRATIONS o el override específico
USE_DUMMY_ZAMMAD = os.getenv("USE_DUMMY_ZAMMAD", str(SIMULATE_INTEGRATIONS)).lower() in ("true", "1", "yes")

if USE_DUMMY_ZAMMAD:
    crear_ticket_zammad = crear_ticket_dummy
    zammad_service = "DUMMY"
else:
    crear_ticket_zammad = crear_ticket_real
    zammad_service = "REAL"