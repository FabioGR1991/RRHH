import re
import unicodedata
import random
import string
import inspect
from typing import Dict, List, Optional, Any, Set

# Dominio corporativo predeterminado
DEFAULT_DOMAIN = "tandemtech.com.ar"


def sanitizar_string(texto: str) -> str:
    """
    Elimina tildes, acentos, caracteres especiales (incluyendo 'ñ') y convierte a minúsculas.
    Ejemplo: "Gómez-Peña" -> "gomezpena"
    """
    if not texto:
        return ""

    # Reemplazar 'ñ' y 'Ñ' explícitamente antes de normalizar
    texto = texto.replace('ñ', 'n').replace('Ñ', 'N')

    # Normalizar caracteres Unicode (NFD separa la letra del acento/tilde)
    texto_norm = unicodedata.normalize('NFD', texto)
    # Filtrar solo caracteres ASCII alfanuméricos
    texto_sin_acentos = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    # Remover cualquier otro carácter que no sea letra o número
    limpio = re.sub(r'[^a-zA-Z0-9]', '', texto_sin_acentos)
    return limpio.lower()


def generar_usernames_candidatos(nombre: str, apellido: str) -> list[str]:
    """
    Genera una lista ordenada de alternativas de username para evitar colisiones.
    Ejemplo para Fabio Gomez:
    1. fgomez (Inicial Nombre + Apellido)
    2. fabiogomez (Primer Nombre + Apellido)
    3. fabiogomez1 ... fabiogomez5 (Contador)
    """
    nom_limpio = sanitizar_string(nombre)
    ape_limpio = sanitizar_string(apellido)

    if not nom_limpio or not ape_limpio:
        return []

    # Extraer primer nombre si tiene nombres compuestos (ej: "Juan Carlos" -> "juan")
    primer_nombre = nom_limpio.split()[0] if " " in nom_limpio else nom_limpio

    candidatos = [
        f"{primer_nombre[0]}{ape_limpio}",  # Opción 1: fgomez
        f"{primer_nombre}{ape_limpio}",     # Opción 2: fabiogomez
    ]

    # Opción 3: Variantes numéricas (fabiogomez1, fabiogomez2...)
    for i in range(1, 6):
        candidatos.append(f"{primer_nombre}{ape_limpio}{i}")

    return candidatos


def transformar_legajo_neotel(legajo: str) -> str:
    """
    Reemplaza el primer dígito del legajo por '3' para el sistema NeoTel/NEO.
    Ejemplo: '1237' -> '3237'
    """
    if not legajo:
        return ""
    legajo_str = str(legajo).strip()
    if legajo_str.startswith("1"):
        return "3" + legajo_str[1:]
    return legajo_str


def generar_password_segura(longitud: int = 10) -> str:
    """
    Genera una contraseña temporal segura que cumpla con políticas estándar de AD.
    (Mayúsculas, minúsculas, números y un carácter especial).
    """
    mayus = string.ascii_uppercase
    minus = string.ascii_lowercase
    numeros = string.digits
    especiales = "!@#$%*"

    password = [
        random.choice(mayus),
        random.choice(minus),
        random.choice(numeros),
        random.choice(especiales)
    ]

    todos = mayus + minus + numeros + especiales
    password.extend(random.choice(todos) for _ in range(longitud - 4))
    random.shuffle(password)
    return "".join(password)


async def _check_existe_usuario(servicio: Any, usuario_o_email: str) -> bool:
    """
    Helper para invocar existe_usuario o usuario_existe sin importar si es async o sync.
    """
    metodo = getattr(servicio, 'existe_usuario', None) or getattr(servicio, 'usuario_existe', None)
    if not metodo:
        return False

    if inspect.iscoroutinefunction(metodo):
        return await metodo(usuario_o_email)
    else:
        return metodo(usuario_o_email)


async def resolver_username_disponible(
    candidatos: List[str], 
    check_services: Optional[Dict[str, Any]] = None,
    reservados_batch: Optional[Set[str]] = None
) -> str:
    """
    Itera sobre la lista de candidatos de username y consulta con los servicios 
    (AD, Google, NeoTel, Fortinet) y la lista de reservados en el lote actual 
    para encontrar el primero que esté 100% libre.
    """
    if reservados_batch is None:
        reservados_batch = set()

    if not candidatos:
        candidato_base = "usuario"
        if candidato_base not in reservados_batch:
            reservados_batch.add(candidato_base)
            return candidato_base
        candidatos = [candidato_base]

    for username in candidatos:
        # Verificar colisión en memoria con el lote/batch procesado previamente
        if username in reservados_batch:
            continue

        colision_detectada = False

        if check_services:
            # 1. Chequear Active Directory
            if 'ad' in check_services and not colision_detectada:
                if await _check_existe_usuario(check_services['ad'], username):
                    colision_detectada = True

            # 2. Chequear Google Workspace
            if 'google' in check_services and not colision_detectada:
                email_candidate = f"{username}@{DEFAULT_DOMAIN}"
                if await _check_existe_usuario(check_services['google'], email_candidate):
                    colision_detectada = True

            # 3. Chequear NeoTel (Telemarketer)
            if 'neotel' in check_services and not colision_detectada:
                if await _check_existe_usuario(check_services['neotel'], username):
                    colision_detectada = True

            # 4. Chequear FortiGate VPN
            if 'fortinet' in check_services and not colision_detectada:
                if await _check_existe_usuario(check_services['fortinet'], username):
                    colision_detectada = True

        # Si ningún sistema ni el batch detectaron colisión, este username está disponible
        if not colision_detectada:
            reservados_batch.add(username)
            return username

    # Fallback si todos los candidatos colisionaron: agregar número correlativo no usado en el batch
    base = candidatos[0]
    i = 1
    while True:
        candidate = f"{base}{i}"
        if candidate not in reservados_batch:
            reservados_batch.add(candidate)
            return candidate
        i += 1


async def generar_preview_credenciales(
    nombre: str,
    apellido: str,
    dni: str,
    legajo: str,
    perfil: str,
    reporta_a: str,
    check_services: Optional[Dict[str, Any]] = None,
    reservados_batch: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Genera el JSON completo de Previsualización de Credenciales
    para que IT lo revise y apruebe en el dashboard antes de la ejecución real.
    """
    candidatos = generar_usernames_candidatos(nombre, apellido)
    username_elegido = await resolver_username_disponible(
        candidatos, 
        check_services=check_services, 
        reservados_batch=reservados_batch
    )

    email = f"{username_elegido}@{DEFAULT_DOMAIN}"
    legajo_neotel = transformar_legajo_neotel(legajo)
    
    # Nueva regla de clave NeoTel: Un 9 precediendo al número de usuario (ej. 3238 -> 93238)
    telemarketer_pass_neotel = f"9{legajo_neotel}" if legajo_neotel else ""

    pass_temp_ad = "T4nd3m**"

    # Formato NombreApellido para la posición de NeoTel (ej. FabioGomez)
    nom_capitalizado = sanitizar_string(nombre).capitalize()
    ape_capitalizado = sanitizar_string(apellido).capitalize()
    nombre_completo_posicion = f"{nom_capitalizado}{ape_capitalizado}"

    return {
        "datos_personales": {
            "nombre": nombre,
            "apellido": apellido,
            "dni": dni,
            "legajo_rrhh": legajo,
            "perfil": perfil,
            "reporta_a": reporta_a
        },
        "propuesta_credenciales": {
            "active_directory": {
                "username": username_elegido,
                "password_temp": pass_temp_ad,
                "ou_destino": f"OU={perfil},OU=Usuarios,DC=tandemtech,DC=com,DC=ar",
                "must_change_pass": True
            },
            "google_workspace": {
                "email": email,
                "password_temp": pass_temp_ad,
                "org_unit": f"/{perfil}"
            },
            "neotel": {
                "telemarketer_user": legajo_neotel,
                "telemarketer_pass": telemarketer_pass_neotel,
                "posicion_user": nombre_completo_posicion,
                "posicion_pass": "Tandem123",
                "protocolo": "SIP",
                "nat": "yes"
            },
            "forticlient": {
                "username": nombre_completo_posicion,
                "password_temp": dni,
                "email_2fa": email,
                "grupo_vpn": "VPN_Usuarios_remotos"
            }
        }
    }


def generar_credenciales_propuestas(
    datos_solicitud: Dict[str, Any], 
    check_services: Optional[Dict[str, Any]] = None,
    reservados_batch: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Wrapper sincrónico / helper utilizado por el Orquestador o procesadores en lote.
    """
    import asyncio
    
    nombre = datos_solicitud.get("nombre", "")
    apellido = datos_solicitud.get("apellido", "")
    dni = str(datos_solicitud.get("dni", ""))
    legajo = str(datos_solicitud.get("legajo", datos_solicitud.get("legajo_rrhh", "")))
    perfil = datos_solicitud.get("perfil", datos_solicitud.get("puesto", ""))
    reporta_a = datos_solicitud.get("reporta_a", "")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si se invoca dentro de un contexto asincrónico activo
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(
                generar_preview_credenciales(
                    nombre, apellido, dni, legajo, perfil, reporta_a, check_services, reservados_batch
                )
            )
        else:
            return loop.run_until_complete(
                generar_preview_credenciales(
                    nombre, apellido, dni, legajo, perfil, reporta_a, check_services, reservados_batch
                )
            )
    except RuntimeError:
        return asyncio.run(
            generar_preview_credenciales(
                nombre, apellido, dni, legajo, perfil, reporta_a, check_services, reservados_batch
            )
        )