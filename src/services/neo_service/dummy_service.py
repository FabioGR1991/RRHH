import os
import logging
import pandas as pd
import qrcode
from typing import Dict, Any
from config.settings import NEOTEL_CSV_PATH, BASE_DIR

logger = logging.getLogger(__name__)

# Directorio de almacenamiento de imágenes QR
QR_DIR = os.path.join(BASE_DIR, "storage", "qrs")


class DummyNeoService:
    def __init__(self, csv_path: str = NEOTEL_CSV_PATH):
        self.csv_path = csv_path
        self._asegurar_csv_existe()
        os.makedirs(QR_DIR, exist_ok=True)

    def _asegurar_csv_existe(self) -> None:
        """Crea la estructura del CSV con columnas completas si no existe."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=["Usuario", "Legajo", "DNI", "Nombre_Apellido"])
            df.to_csv(self.csv_path, index=False, sep=";", encoding="latin-1")
            logger.info(f"[MOCK NEO_SERVICE] Creado CSV inicial en: {self.csv_path}")

    def _leer_csv_seguro(self) -> pd.DataFrame:
        """Lee el CSV soportando utf-8 y latin-1 sin fallar por caracteres especiales o filas malformadas."""
        if not os.path.exists(self.csv_path):
            return pd.DataFrame(columns=["Usuario", "Legajo", "DNI", "Nombre_Apellido"])
        try:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="utf-8", on_bad_lines="skip").fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(self.csv_path, sep=";", dtype=str, encoding="latin-1", on_bad_lines="skip").fillna("")

    def usuario_existe(self, usuario_neo: str) -> bool:
        """Verifica si un usuario NeoTel (código 3xxx) ya existe en el CSV."""
        try:
            df = self._leer_csv_seguro()
            if df.empty or "Usuario" not in df.columns:
                return False
            usuarios = df["Usuario"].astype(str).str.strip().values
            return usuario_neo.strip() in usuarios
        except Exception as e:
            logger.error(f"[MOCK NEO_SERVICE] Error al verificar usuario '{usuario_neo}': {e}")
            return False

    def legajo_o_dni_existe(self, legajo: str, dni: str) -> Dict[str, bool]:
        """Verifica la existencia de Legajo/Usuario Neo y DNI.
        Ignora celdas de DNI vacías en la base histórica.
        """
        resultado = {"existe_legajo": False, "existe_dni": False}

        try:
            df = self._leer_csv_seguro()
            if df.empty:
                return resultado

            legajo_target = str(legajo).strip()
            dni_target = str(dni).strip()

            # 1. Chequeo de Legajo / Usuario
            if "Legajo" in df.columns:
                legajos = df["Legajo"].astype(str).str.strip().values
                if legajo_target in legajos:
                    resultado["existe_legajo"] = True

            if "Usuario" in df.columns:
                usuario_neo_target = "3" + legajo_target[1:] if legajo_target.startswith("1") else "3" + legajo_target
                usuarios = df["Usuario"].astype(str).str.strip().values
                if usuario_neo_target in usuarios:
                    resultado["existe_legajo"] = True

            # 2. Chequeo de DNI (solo evalúa filas donde el DNI NO esté vacío)
            if "DNI" in df.columns and dni_target:
                dnis_existentes = df[df["DNI"].astype(str).str.strip() != ""]["DNI"].astype(str).str.strip().values
                if dni_target in dnis_existentes:
                    resultado["existe_dni"] = True

            return resultado

        except Exception as e:
            logger.error(f"[MOCK NEO_SERVICE] Error evaluando duplicados: {str(e)}")
            return resultado

    def _generar_qr_dummy(self, usuario_neo: str, nombre_apellido: str) -> str:
        """
        Genera una imagen QR dummy que simula el token 2FA de NeoTel.
        El contenido codificado es una URI TOTP estándar.

        Args:
            usuario_neo: Código de usuario NeoTel (ej. '3005')
            nombre_apellido: Nombre completo del empleado

        Returns:
            Ruta absoluta del archivo PNG generado.
        """
        # URI TOTP estándar (RFC 6238) — compatible con Google Authenticator
        secret_dummy = "JBSWY3DPEHPK3PXP"  # Base32 dummy para pruebas
        totp_uri = (
            f"otpauth://totp/NeoTel:{usuario_neo}"
            f"?secret={secret_dummy}"
            f"&issuer=NeoTel+Tandem"
            f"&algorithm=SHA1&digits=6&period=30"
        )

        nombre_safe = "".join(c for c in nombre_apellido if c.isalnum() or c in "-_")
        filename = f"qr_neo_{usuario_neo}_{nombre_safe}.png"
        filepath = os.path.join(QR_DIR, filename)

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(totp_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filepath)
            logger.info(f"[MOCK NEO_SERVICE] QR dummy generado en: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[MOCK NEO_SERVICE] Error al generar QR para '{usuario_neo}': {e}")
            return ""

    async def crear_usuario(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        usuario_neo = str(datos.get("usuario") or datos.get("legajo_neo") or "").strip()
        legajo = str(datos.get("legajo") or "").strip()
        dni = str(datos.get("dni") or "").strip()

        nombre = datos.get("nombre", "").strip()
        apellido = datos.get("apellido", "").strip()
        nombre_apellido = datos.get("nombre_apellido") or f"{nombre} {apellido}".strip()

        if not usuario_neo:
            raise ValueError("[MOCK NEO_SERVICE] El identificador de usuario NeoTel es obligatorio.")

        # Validación contra la base CSV
        check = self.legajo_o_dni_existe(legajo, dni)
        if check["existe_legajo"] or check["existe_dni"]:
            motivo = "Legajo/Usuario Neo" if check["existe_legajo"] else "DNI"
            msg_error = f"El {motivo} ingresado ya existe en la base de datos de NeoTel."
            logger.warning(f"[MOCK NEO_SERVICE] {msg_error}")
            return {
                "status": "error",
                "mode": "MOCK",
                "detail": msg_error,
                "usuario": usuario_neo
            }

        try:
            nuevo_registro = pd.DataFrame([{
                "Usuario": usuario_neo,
                "Legajo": legajo,
                "DNI": dni,
                "Nombre_Apellido": nombre_apellido
            }])

            nuevo_registro.to_csv(
                self.csv_path,
                mode='a',
                header=False,
                index=False,
                sep=";",
                encoding="latin-1"
            )

            logger.info(f"[MOCK NEO_SERVICE] Telemarketer '{usuario_neo}' (Legajo: {legajo}) creado en CSV.")

            # Generar QR del token 2FA dummy
            qr_path = self._generar_qr_dummy(usuario_neo, nombre_apellido)

            return {
                "status": "success",
                "mode": "MOCK",
                "message": f"Usuario {usuario_neo} registrado exitosamente en NeoTel.",
                "data": {
                    "usuario": usuario_neo,
                    "legajo": legajo,
                    "dni": dni,
                    "nombre_apellido": nombre_apellido,
                    "qr_path": qr_path,
                    "qr_generado": bool(qr_path),
                }
            }
        except Exception as e:
            msg_exc = f"Error al escribir en el CSV de NeoTel: {str(e)}"
            logger.error(f"[MOCK NEO_SERVICE] {msg_exc}")
            return {"status": "error", "mode": "MOCK", "detail": msg_exc}