"""
===================================================================
ARCHIVO: crear_modulos.py
DESCRIPCIÓN: Script para crear la estructura de módulos para la 
             refactorización de solicitudes_controller.py
===================================================================
"""

from pathlib import Path

# Directorio donde se ubican los controladores
BASE_DIR = Path("src/controllers")

ARCHIVOS_A_CREAR = {
    BASE_DIR
    / "solicitudes_helpers.py": (
        '"""\n'
        "===================================================================\n"
        "ARCHIVO: src/controllers/solicitudes_helpers.py\n"
        "DESCRIPCIÓN: Funciones auxiliares y reglas de negocio para solicitudes.\n"
        "===================================================================\n"
        '"""\n\n'
    ),
    BASE_DIR
    / "solicitudes_export_service.py": (
        '"""\n'
        "===================================================================\n"
        "ARCHIVO: src/controllers/solicitudes_export_service.py\n"
        "DESCRIPCIÓN: Servicio para generación y formateo de reportes Excel.\n"
        "===================================================================\n"
        '"""\n\n'
    ),
}


def crear_archivos():
    # Asegurar que la carpeta exista
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    for ruta_archivo, plantilla in ARCHIVOS_A_CREAR.items():
        if ruta_archivo.exists():
            print(f"[Omitido] El archivo ya existe: {ruta_archivo}")
        else:
            ruta_archivo.write_text(plantilla, encoding="utf-8")
            print(f"[Creado] Archivo generado con éxito: {ruta_archivo}")


if __name__ == "__main__":
    crear_archivos()