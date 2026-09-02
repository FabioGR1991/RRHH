"""
===================================================================
ARCHIVO: src/services/reportantes_service.py
DESCRIPCIÓN: Filtrado local sobre la lista estática de supervisores/reportantes.
===================================================================
"""

from typing import List, Dict
from config.settings import SUPERVISORES_HABILITADOS

def buscar_reportantes_estaticos(query: str) -> List[Dict[str, str]]:
    """Filtra la lista fija de supervisores comparando nombre, email o rol."""
    if not query or len(query.strip()) < 1:
        return []

    q = query.strip().lower()
    coincidencias = []

    for sup in SUPERVISORES_HABILITADOS:
        # Coincidencia por Nombre, Email o Rol
        if (q in sup["email"].lower() or 
            q in sup["nombre"].lower() or 
            q in sup["rol"].lower()):
            
            coincidencias.append({
                "email": sup["email"],
                "label": f"{sup['nombre']} - {sup['rol']} ({sup['email']})"
            })

    return coincidencias[:10]