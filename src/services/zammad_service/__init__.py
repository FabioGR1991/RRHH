import os
from .dummy_service import crear_ticket_zammad as crear_ticket_dummy
from .real_service import crear_ticket_zammad as crear_ticket_real

# Lee la variable de entorno (por defecto True para entorno seguro/pruebas)
USE_DUMMY_ZAMMAD = os.getenv("USE_DUMMY_ZAMMAD", "True").lower() in ("true", "1", "yes")

if USE_DUMMY_ZAMMAD:
    crear_ticket_zammad = crear_ticket_dummy
    zammad_service = "DUMMY"
else:
    crear_ticket_zammad = crear_ticket_real
    zammad_service = "REAL"
