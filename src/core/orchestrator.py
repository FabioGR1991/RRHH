# ===================================================================
# ARCHIVO: src/core/orchestrator.py
# DESCRIPCIÓN: Motor principal de aprovisionamiento de altas.
#              Ejecuta la secuencia completa de creación de cuentas:
#              AD → Gmail → NeoTel (Telemarketer + Posición) → FortiClient VPN
#
#              Conmutación transparente DUMMY/REAL via SIMULATE_INTEGRATIONS
#              en config/settings.py o variable de entorno DUMMY_MODE.
#
#              Manejo de errores por módulo: si falla una plataforma,
#              actualiza el estado de la solicitud a ERROR_PARCIAL
#              registrando el detalle del error, sin abortar el resto.
# ===================================================================

import json
import logging
from typing import Dict, Any, Optional, Set

from src.core.generator import generar_credenciales_propuestas
from src.services.ad_service import ad_service, crear_usuario_ad
from src.services.gadmin_service import gadmin_service, crear_casilla_google
from src.services.neo_service import neo_service, crear_usuario_neotel
from src.services.fortinet_service import fortinet_service, crear_usuario_fortinet
from config.settings import SIMULATE_INTEGRATIONS

logger = logging.getLogger(__name__)


def obtener_usuario_neotel_desde_legajo(legajo: str) -> str:
    """
    Regla de Negocio NeoTel:
    Transforma el Legajo reemplazando el primer caracter '1' por '3'.
    Ejemplo: '1005' -> '3005'. Si no empieza con '1', antepone '3'.
    """
    legajo_str = str(legajo).strip()
    if not legajo_str:
        return ""
    if legajo_str.startswith("1"):
        return "3" + legajo_str[1:]
    return "3" + legajo_str


class Orchestrator:
    """
    Orquestador principal de aprovisionamiento de altas IT.

    Responsabilidades:
    1. Prevalidar disponibilidades cruzadas (AD, Gmail, NeoTel, FortiGate).
    2. Ejecutar secuencialmente la creación de cuentas en cada plataforma.
    3. Registrar el resultado por módulo (éxito o error granular).
    4. Retornar el estado final: COMPLETADO si todos OK, ERROR_PARCIAL si alguno falló.
    """

    def __init__(self):
        self.ad_service       = ad_service
        self.gadmin_service   = gadmin_service
        self.neo_service      = neo_service
        self.fortinet_service = fortinet_service

    def _obtener_mapa_check_services(self) -> Dict[str, Any]:
        """Retorna el mapa de servicios para crosscheck de disponibilidad."""
        return {
            "ad":       self.ad_service,
            "google":   self.gadmin_service,
            "neotel":   self.neo_service,
            "fortinet": self.fortinet_service,
        }

    async def prevalidar_solicitud(
        self,
        datos_solicitud: Dict[str, Any],
        check_services: Optional[Dict[str, Any]] = None,
        reservados_batch: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Fase de Pre-Validación (Dry-Run / Preview).
        Genera la propuesta de credenciales y valida disponibilidad cruzada en NeoTel.

        Args:
            datos_solicitud:  Datos del formulario del empleado.
            check_services:   Mapa de servicios para crosscheck (default: todos los servicios).
            reservados_batch: Set de usernames ya reservados en lote actual.

        Returns:
            Dict con valido (bool), propuesta (credenciales), usuario_neo y conflictos.
        """
        if check_services is None:
            check_services = self._obtener_mapa_check_services()

        # 1. Generar la propuesta de credenciales
        propuesta = generar_credenciales_propuestas(
            datos_solicitud,
            check_services=check_services,
            reservados_batch=reservados_batch
        )

        # 2. Obtener el Legajo de la solicitud
        legajo_raw = (
            datos_solicitud.get("legajo")
            or datos_solicitud.get("legajo_original")
            or propuesta.get("legajo")
        )

        # 3. Calcular el usuario NeoTel asignado (3xxx)
        usuario_neo = (
            propuesta.get("propuesta_credenciales", {}).get("neotel", {}).get("telemarketer_user")
            or propuesta.get("neotel", {}).get("usuario")
            or propuesta.get("legajo_neo")
            or obtener_usuario_neotel_desde_legajo(legajo_raw)
        )

        logger.info(
            f"[ORCHESTRATOR] Crosscheck disponibilidad — "
            f"Legajo: {legajo_raw} | Usuario NeoTel: {usuario_neo}"
        )

        conflictos = []

        # 4. Crosscheck NeoTel
        if not usuario_neo:
            conflictos.append({
                "plataforma": "NeoTel",
                "campo":      "Usuario / Legajo Neo",
                "valor":      "-",
                "motivo":     "No se pudo determinar el Legajo o Usuario NeoTel de la solicitud."
            })
        else:
            neotel_check_svc = check_services.get("neotel", self.neo_service)
            metodo_existe = getattr(neotel_check_svc, "usuario_existe", None)
            ya_existe = metodo_existe(usuario_neo) if metodo_existe else False
            if ya_existe:
                conflictos.append({
                    "plataforma": "NeoTel",
                    "campo":      "Usuario / Legajo Neo",
                    "valor":      usuario_neo,
                    "motivo":     f"El usuario NeoTel '{usuario_neo}' ya se encuentra ocupado."
                })

        es_valido = len(conflictos) == 0

        return {
            "valido":      es_valido,
            "propuesta":   propuesta,
            "usuario_neo": usuario_neo,
            "conflictos":  conflictos
        }

    async def ejecutar_alta_confirmada(
        self,
        datos_solicitud: Dict[str, Any],
        check_services: Optional[Dict[str, Any]] = None,
        reservados_batch: Optional[Set[str]] = None,
        es_fuera_de_nomina: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecución real / Simulación de la creación de cuentas al 'Confirmar y Ejecutar Alta'.

        Secuencia:
          1. AD (Active Directory) — solo si no es Fuera de Nómina
          2. Gmail (Google Workspace) — solo si no es Fuera de Nómina
          3. NeoTel (Telemarketer + Posición SIP) — siempre
          4. FortiClient (VPN) — solo si no es Fuera de Nómina

        Cada paso tiene try/except individual. Los errores NO interrumpen la secuencia;
        se acumulan en resultados_modulos y determinan el estado final.

        Args:
            datos_solicitud:    Datos del empleado.
            check_services:     Mapa de servicios para crosscheck.
            reservados_batch:   Set de usernames ya reservados en lote.
            es_fuera_de_nomina: Si True, omite AD, Gmail y FortiClient.

        Returns:
            Dict con exito (bool), estado_final, detalles por módulo y credenciales_finales.
        """
        if check_services is None:
            check_services = self._obtener_mapa_check_services()

        # ── PASO 0: Pre-validación ──────────────────────────────────────────
        pre_check = await self.prevalidar_solicitud(
            datos_solicitud,
            check_services=check_services,
            reservados_batch=reservados_batch
        )
        if not pre_check["valido"]:
            logger.warning(
                f"[ORCHESTRATOR] Alta rechazada por conflictos: {pre_check['conflictos']}"
            )
            return {
                "exito":             False,
                "estado_final":      "RECHAZADO",
                "mensaje":           "No se puede ejecutar el alta debido a conflictos de duplicidad.",
                "errores":           pre_check["conflictos"],
                "detalles":          {},
                "credenciales_finales": pre_check["propuesta"]
            }

        propuesta     = pre_check["propuesta"]
        usuario_neo   = pre_check["usuario_neo"]
        creds         = propuesta.get("propuesta_credenciales", {})
        datos_personales = propuesta.get("datos_personales", {})

        nombre   = datos_solicitud.get("nombre", datos_personales.get("nombre", ""))
        apellido = datos_solicitud.get("apellido", datos_personales.get("apellido", ""))
        dni      = datos_solicitud.get("dni", datos_personales.get("dni", ""))

        resultados_modulos: Dict[str, Dict[str, Any]] = {}
        modulos_fallidos: list[str] = []

        modo = "MOCK" if SIMULATE_INTEGRATIONS else "REAL"
        logger.info(
            f"[ORCHESTRATOR] Iniciando aprovisionamiento en modo {modo} para "
            f"'{nombre} {apellido}' (Legajo: {datos_solicitud.get('legajo', '-')})"
        )

        # ── PASO 1: Active Directory ────────────────────────────────────────
        if not es_fuera_de_nomina:
            ad_payload = {
                **creds.get("active_directory", {}),
                "nombre":   nombre,
                "apellido": apellido,
                "email":    creds.get("google_workspace", {}).get("email", ""),
                "perfil":   datos_solicitud.get("perfil_ad", datos_solicitud.get("perfil", "")),
            }
            try:
                res_ad = await crear_usuario_ad(ad_payload)
                resultados_modulos["active_directory"] = res_ad
                if res_ad.get("status") == "success":
                    logger.info(f"[ORCHESTRATOR] ✅ AD: Usuario '{ad_payload.get('username')}' creado.")
                else:
                    modulos_fallidos.append("active_directory")
                    logger.warning(f"[ORCHESTRATOR] ⚠️ AD: {res_ad.get('detail', 'Error desconocido')}")
            except Exception as e:
                msg = f"Excepción no controlada en AD: {str(e)}"
                logger.error(f"[ORCHESTRATOR] ❌ {msg}")
                resultados_modulos["active_directory"] = {"status": "error", "detail": msg}
                modulos_fallidos.append("active_directory")

        # ── PASO 2: Google Workspace ────────────────────────────────────────
        if not es_fuera_de_nomina:
            gmail_payload = {
                **creds.get("google_workspace", {}),
                "nombre":   nombre,
                "apellido": apellido,
                "username": creds.get("active_directory", {}).get("username", ""),
            }
            try:
                res_gmail = await crear_casilla_google(gmail_payload)
                resultados_modulos["google_workspace"] = res_gmail
                if res_gmail.get("status") == "success":
                    logger.info(f"[ORCHESTRATOR] ✅ Gmail: Casilla '{gmail_payload.get('email')}' creada.")
                else:
                    modulos_fallidos.append("google_workspace")
                    logger.warning(f"[ORCHESTRATOR] ⚠️ Gmail: {res_gmail.get('detail', 'Error desconocido')}")
            except Exception as e:
                msg = f"Excepción no controlada en Gmail: {str(e)}"
                logger.error(f"[ORCHESTRATOR] ❌ {msg}")
                resultados_modulos["google_workspace"] = {"status": "error", "detail": msg}
                modulos_fallidos.append("google_workspace")

        # ── PASO 3: NeoTel ──────────────────────────────────────────────────
        neo_payload = {
            "usuario":         usuario_neo,
            "legajo_neo":      usuario_neo,
            "legajo":          datos_solicitud.get("legajo", ""),
            "dni":             dni,
            "nombre":          nombre,
            "apellido":        apellido,
            "nombre_apellido": f"{nombre} {apellido}".strip(),
            "posicion_user":   creds.get("neotel", {}).get("posicion_user", ""),
        }
        try:
            res_neo = await crear_usuario_neotel(neo_payload)
            resultados_modulos["neotel"] = res_neo
            if res_neo.get("status") == "success":
                logger.info(f"[ORCHESTRATOR] ✅ NeoTel: Usuario '{usuario_neo}' creado.")
            else:
                modulos_fallidos.append("neotel")
                logger.warning(f"[ORCHESTRATOR] ⚠️ NeoTel: {res_neo.get('detail', 'Error desconocido')}")
        except Exception as e:
            msg = f"Excepción no controlada en NeoTel: {str(e)}"
            logger.error(f"[ORCHESTRATOR] ❌ {msg}")
            resultados_modulos["neotel"] = {"status": "error", "detail": msg}
            modulos_fallidos.append("neotel")

        # ── PASO 4: FortiClient VPN ─────────────────────────────────────────
        if not es_fuera_de_nomina:
            forti_payload = {
                **creds.get("forticlient", {}),
                "nombre":   nombre,
                "apellido": apellido,
                "dni":      dni,
                "perfil":   datos_solicitud.get("perfil_ad", datos_solicitud.get("perfil", "")),
            }
            try:
                res_forti = await crear_usuario_fortinet(forti_payload)
                resultados_modulos["forticlient"] = res_forti
                if res_forti.get("status") == "success":
                    logger.info(
                        f"[ORCHESTRATOR] ✅ FortiGate: Usuario VPN "
                        f"'{forti_payload.get('username')}' creado."
                    )
                else:
                    modulos_fallidos.append("forticlient")
                    logger.warning(f"[ORCHESTRATOR] ⚠️ FortiGate: {res_forti.get('detail', 'Error desconocido')}")
            except Exception as e:
                msg = f"Excepción no controlada en FortiGate: {str(e)}"
                logger.error(f"[ORCHESTRATOR] ❌ {msg}")
                resultados_modulos["forticlient"] = {"status": "error", "detail": msg}
                modulos_fallidos.append("forticlient")

        # ── DETERMINACIÓN DEL ESTADO FINAL ──────────────────────────────────
        exito_global = len(modulos_fallidos) == 0
        estado_final = "COMPLETADO" if exito_global else "ERROR_PARCIAL"

        if exito_global:
            logger.info(
                f"[ORCHESTRATOR] 🎉 Alta COMPLETADA para '{nombre} {apellido}'. "
                f"Modo: {modo}"
            )
        else:
            logger.warning(
                f"[ORCHESTRATOR] ⚠️ Alta con ERROR_PARCIAL para '{nombre} {apellido}'. "
                f"Módulos fallidos: {modulos_fallidos}"
            )

        # Enriquecer credenciales finales con el qr_path de NeoTel si se generó
        qr_path = (
            resultados_modulos.get("neotel", {})
            .get("data", {})
            .get("qr_path", "")
        )
        if qr_path:
            creds["neotel"]["qr_path"] = qr_path

        # ── PASO 5: Generación Automática del PDF de Bienvenida ───────────────
        pdf_path = None
        if exito_global or estado_final in ("COMPLETADO", "ERROR_PARCIAL"):
            try:
                from src.services.pdf_service import generar_pdf_bienvenida
                solicitud_id = datos_solicitud.get("id") or datos_solicitud.get("solicitud_id", 0)
                datos_para_pdf = {
                    **propuesta,
                    "datos_personales": {
                        "nombre": nombre,
                        "apellido": apellido,
                        "dni": dni,
                        "legajo": datos_solicitud.get("legajo", ""),
                        "perfil": datos_solicitud.get("perfil_ad", datos_solicitud.get("perfil", "")),
                        "reporta_a": datos_solicitud.get("reporta_a", ""),
                    },
                    "propuesta_credenciales": creds,
                    "es_fuera_de_nomina": es_fuera_de_nomina,
                    "qr_path": qr_path,
                }
                pdf_path = generar_pdf_bienvenida(solicitud_id=solicitud_id, credenciales=datos_para_pdf)
                logger.info(f"[ORCHESTRATOR] 📄 PDF de bienvenida generado exitosamente: {pdf_path}")
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] ⚠️ Error al generar PDF de bienvenida: {e}")

        return {
            "exito":              exito_global,
            "estado_final":       estado_final,
            "mensaje":            (
                "Alta orquestada completada exitosamente."
                if exito_global else
                f"Alta procesada con errores parciales en: {', '.join(modulos_fallidos)}."
            ),
            "modulos_fallidos":   modulos_fallidos,
            "detalles":           resultados_modulos,
            "credenciales_finales": propuesta,
            "pdf_path":           pdf_path or "",
            "log_errores":        json.dumps(
                {k: v for k, v in resultados_modulos.items() if v.get("status") == "error"},
                ensure_ascii=False
            ) if modulos_fallidos else None
        }


# Instancia global del orquestador
orchestrator = Orchestrator()