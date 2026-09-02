# ===================================================================
# ARCHIVO: config/settings.py
# DESCRIPCIÓN: Configuración global de la aplicación.
# Maneja:
#  - Flag global de simulación para entornos de desarrollo/testing (Mocks).
#  - Ruta base del proyecto y rutas a archivos CSV dummy para crosscheck.
#  - Definición del dominio corporativo para casillas de correo.
#  - Variables de entorno del sistema.
#  - Listado estático de supervisores / reportantes habilitados.
# ===================================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env si existe
load_dotenv()

# Ruta base del proyecto (Directorio raíz RRHH)
BASE_DIR = Path(__file__).resolve().parent.parent

# Flag global para simulaciones (Cambiar a False en Producción con servidores reales)
SIMULATE_INTEGRATIONS: bool = os.getenv("SIMULATE_INTEGRATIONS", "True").lower() == "true"
DUMMY_MODE: bool = os.getenv("DUMMY_MODE", str(SIMULATE_INTEGRATIONS)).lower() == "true"

# Dominio corporativo predeterminado
DOMINIO_EMAIL: str = os.getenv("DOMINIO_EMAIL", "tandemtech.com.ar")

# ===================================================================
# RUTAS A BASE DE DATOS DUMMY (ARCHIVOS CSV)
# ===================================================================
DUMMY_DB_DIR = os.path.join(BASE_DIR, "storage", "dummy_db")

# NeoTel (Crosscheck & Persistencia)
NEOTEL_CSV_PATH: str = os.getenv(
    "NEOTEL_CSV_PATH", 
    os.path.join(DUMMY_DB_DIR, "neotel_usuarios.csv")
)

# Integraciones adicionales en CSV (Google Admin, AD, FortiClient, Posiciones)
GADMIN_CSV_PATH: str = os.getenv(
    "GADMIN_CSV_PATH", 
    os.path.join(DUMMY_DB_DIR, "gadmin_usuarios.csv")
)
AD_CSV_PATH: str = os.getenv(
    "AD_CSV_PATH", 
    os.path.join(DUMMY_DB_DIR, "ad_usuarios.csv")
)
FORTINET_CSV_PATH: str = os.getenv(
    "FORTINET_CSV_PATH", 
    os.path.join(DUMMY_DB_DIR, "fortinet_usuarios.csv")
)

# ===================================================================
# LISTADO DE SUPERVISORES / REPORTANTES HABILITADOS
# ===================================================================
SUPERVISORES_HABILITADOS = [
    {"nombre": "Juan Pérez", "email": "juan.perez@tandemtech.com.ar", "rol": "Gerente de Operaciones"},
    {"nombre": "María González", "email": "maria.gonzalez@tandemtech.com.ar", "rol": "Team Leader Contact Center"},
    {"nombre": "Carlos Rodríguez", "email": "carlos.rodriguez@tandemtech.com.ar", "rol": "Planificador WFM"},
    {"nombre": "Ana Martínez", "email": "ana.martinez@tandemtech.com.ar", "rol": "Supervisora Turno Mañana"},
    {"nombre": "Lucas Gómez", "email": "lucas.gomez@tandemtech.com.ar", "rol": "Jefe de Sistemas"},
]