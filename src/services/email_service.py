"""
===================================================================
ARCHIVO: src/services/email_service.py
DESCRIPCIÓN: Servicio para el envío de notificaciones por correo electrónico.
Se encarga de adjuntar la ficha PDF y notificar al responsable (reporta_a).
===================================================================
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)

# Configuración SMTP por defecto desde entorno
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)


async def enviar_notificacion_alta(
    destinatario_email: str,
    nombre_empleado: str,
    pdf_path: str
) -> bool:
    """
    Envia un correo electrónico al supervisor con el PDF de credenciales adjunto.

    :param destinatario_email: Correo del responsable/supervisor (reporta_a)
    :param nombre_empleado: Nombre completo del nuevo empleado
    :param pdf_path: Ruta del archivo PDF generado
    :return: True si se envió correctamente, False en caso contrario.
    """
    if not destinatario_email or "@" not in destinatario_email:
        logger.warning(f"[EMAIL] Dirección de correo inválida para el destinatario: '{destinatario_email}'. Se omite envío.")
        return False

    if not os.path.exists(pdf_path):
        logger.error(f"[EMAIL] No se encontró el archivo PDF para adjuntar: {pdf_path}")
        return False

    mensaje = MIMEMultipart()
    mensaje["From"] = EMAIL_FROM
    mensaje["To"] = destinatario_email
    mensaje["Subject"] = f"Alta de Usuario Procesada - {nombre_empleado}"

    cuerpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #0284C7;">Notificación de Alta de Usuario</h2>
            <p>Estimado/a,</p>
            <p>Le informamos que el proceso de aprovisionamiento para el empleado <strong>{nombre_empleado}</strong> ha sido ejecutado exitosamente.</p>
            <p>En el archivo PDF adjunto encontrará la ficha completa con las cuentas creadas y sus respectivas credenciales temporales de acceso.</p>
            <br>
            <p style="font-size: 12px; color: #777;">Este es un mensaje automático generado por el sistema de Gestión de Altas IT/RRHH.</p>
        </body>
    </html>
    """

    mensaje.attach(MIMEText(cuerpo_html, "html"))

    # Adjuntar el archivo PDF
    try:
        with open(pdf_path, "rb") as f:
            adjunto = MIMEApplication(f.read(), _subtype="pdf")
            adjunto.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(pdf_path)
            )
            mensaje.attach(adjunto)
    except Exception as e:
        logger.error(f"[EMAIL] Error al adjuntar el PDF {pdf_path}: {e}")
        return False

    # Enviar correo mediante SMTP
    try:
        if not SMTP_USER or not SMTP_PASS:
            logger.info(f"[MOCK EMAIL] Simulación de envío exitosa a '{destinatario_email}'. (Credenciales SMTP no configuradas)")
            return True

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, destinatario_email, mensaje.as_string())
        server.quit()

        logger.info(f"[EMAIL] Correo enviado exitosamente a {destinatario_email}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Fallo al enviar correo SMTP a {destinatario_email}: {e}")
        return False