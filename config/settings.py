# ===================================================================
# ARCHIVO: config/settings.py
# DESCRIPCIÓN: Configuración global de la aplicación.
# Maneja:
#  - Flag global de simulación para entornos de desarrollo/testing (Mocks).
#  - Definición del dominio corporativo para casillas de correo.
#  - Variables de entorno del sistema.
# ===================================================================

import os

# Flag global para simulaciones (Cambiar a False en Producción con servidores reales)
SIMULATE_INTEGRATIONS: bool = os.getenv("SIMULATE_INTEGRATIONS", "True").lower() == "true"

# Dominio corporativo predeterminado
DOMINIO_EMAIL: str = "tandemtech.com.ar"

