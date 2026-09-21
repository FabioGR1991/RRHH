"""
===================================================================
ARCHIVO: src/services/pdf_service.py
DESCRIPCIÓN: Servicio para la generación de PDFs de Bienvenida institucional.
             Basado en el documento modelo AdrianaMartinez.pdf (4 páginas).
             Destaca las credenciales en rojo, inserta QR dinámico 2FA
             y guarda los documentos en storage/pdfs/.
===================================================================
"""

import os
import io
import re
import base64
import logging
from typing import Dict, Any, Optional

import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

# Directorios de almacenamiento
BASE_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage"))
PDF_OUTPUT_DIR   = os.path.join(BASE_STORAGE_DIR, "pdfs")
ASSETS_DIR       = os.path.join(BASE_STORAGE_DIR, "assets")

# Paleta y estilos corporativos alineados con AdrianaMartinez.pdf
COLOR_NAVY           = colors.HexColor("#0B2238")
COLOR_RED            = colors.HexColor("#D32F2F")  # Credenciales en rojo
COLOR_BLUE_TEXT      = colors.HexColor("#0284C7")
COLOR_BORDER         = colors.HexColor("#CBD5E1")
COLOR_CALLOUT_BLUE_BG = colors.HexColor("#EBF3FB")
COLOR_CALLOUT_BLUE_BD = colors.HexColor("#0284C7")
COLOR_CALLOUT_YEL_BG = colors.HexColor("#FFFBEB")
COLOR_CALLOUT_YEL_BD = colors.HexColor("#F59E0B")


def _asegurar_directorios():
    """Crea los directorios necesarios si no existen."""
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)


def _asegurar_activos_visuales():
    """
    Verifica que las imágenes y códigos QR base existan en storage/assets/.
    Si faltan, intenta extraerlos del PDF modelo o generarlos automáticamente.
    """
    _asegurar_directorios()

    # 1. Ticketera QR
    ticket_path = os.path.join(ASSETS_DIR, "ticketera_qr.png")
    if not os.path.exists(ticket_path):
        try:
            img = qrcode.make("https://soporte.tandemtech.com.ar")
            img.save(ticket_path)
        except Exception as e:
            logger.warning(f"[PDF_SERVICE] Error generando QR de Ticketera: {e}")

    # 2. NeoTel Default QR
    neo_default_path = os.path.join(ASSETS_DIR, "neotel_default_qr.png")
    if not os.path.exists(neo_default_path):
        try:
            img = qrcode.make("http://192.168.1.233/ecrm/")
            img.save(neo_default_path)
        except Exception as e:
            logger.warning(f"[PDF_SERVICE] Error generando QR de NeoTel default: {e}")

    # 3. Intentar extraer capturas de AdrianaMartinez.pdf si no existen
    archivos_capturas = ["chrome_2fa_qr.png", "xlite_dialer.png", "xlite_properties.png", "forticlient_screen.png"]
    faltan_capturas = any(not os.path.exists(os.path.join(ASSETS_DIR, f)) for f in archivos_capturas)
    modelo_pdf = os.path.join(BASE_STORAGE_DIR, "AdrianaMartinez.pdf")

    if faltan_capturas and os.path.exists(modelo_pdf):
        try:
            import pypdf
            reader = pypdf.PdfReader(modelo_pdf)
            # Extracción selectiva de imágenes de las páginas
            for idx, page in enumerate(reader.pages):
                for img in page.images:
                    # Mapeo según dimensiones y nombres
                    if "X15" in img.name and idx == 0:
                        with open(os.path.join(ASSETS_DIR, "chrome_2fa_qr.png"), "wb") as f:
                            f.write(img.data)
                    elif "X13" in img.name and idx == 1:
                        with open(os.path.join(ASSETS_DIR, "xlite_dialer.png"), "wb") as f:
                            f.write(img.data)
                    elif "X14" in img.name and idx == 1:
                        with open(os.path.join(ASSETS_DIR, "xlite_properties.png"), "wb") as f:
                            f.write(img.data)
                    elif "X11" in img.name and idx == 2:
                        with open(os.path.join(ASSETS_DIR, "forticlient_screen.png"), "wb") as f:
                            f.write(img.data)
        except Exception as e:
            logger.warning(f"[PDF_SERVICE] Nota al extraer capturas del modelo PDF: {e}")


def _procesar_qr_dinamico(qr_input: Any, temp_filename: str) -> Optional[str]:
    """
    Procesa la imagen o token QR dinámico de 2FA de NeoTel.
    Soporta:
    - Ruta a archivo existente (.png/.jpg)
    - Cadena Base64 (data:image/png;base64,... o texto base64 plano)
    - Token o URL TOTP para generar imagen QR sobre la marcha.
    """
    if not qr_input:
        return None

    # Caso 1: Ruta de archivo existente
    if isinstance(qr_input, str) and os.path.exists(qr_input):
        return qr_input

    # Caso 2: Cadena Base64
    if isinstance(qr_input, str) and ("base64," in qr_input or len(qr_input) > 200):
        try:
            data_str = qr_input.split("base64,")[-1] if "base64," in qr_input else qr_input
            decoded = base64.b64decode(data_str)
            target_path = os.path.join(ASSETS_DIR, temp_filename)
            with open(target_path, "wb") as f:
                f.write(decoded)
            return target_path
        except Exception as e:
            logger.warning(f"[PDF_SERVICE] Error decodificando Base64 de QR: {e}")

    # Caso 3: Es un token de texto o URL otpauth -> generar imagen QR
    if isinstance(qr_input, str) and len(qr_input) > 5:
        try:
            img = qrcode.make(qr_input)
            target_path = os.path.join(ASSETS_DIR, temp_filename)
            img.save(target_path)
            return target_path
        except Exception as e:
            logger.warning(f"[PDF_SERVICE] Error generando QR desde token: {e}")

    return None


def _dibujar_encabezado_pie(canvas, doc):
    """
    Dibuja el encabezado azul institucional y el pie de página
    en cada una de las páginas del documento.
    """
    canvas.saveState()

    # ── Encabezado Superior (Banda Navy) ──────────────────────────
    canvas.setFillColor(COLOR_NAVY)
    canvas.rect(0, 792 - 68, 612, 68, fill=True, stroke=False)

    # Título Principal
    canvas.setFont("Helvetica-Bold", 14.5)
    canvas.setFillColor(colors.white)
    canvas.drawString(36, 792 - 34, "MANUAL DE INGRESO Y CONFIGURACIÓN")

    # Subtítulo
    canvas.setFont("Helvetica", 8.8)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.drawString(36, 792 - 48, "TandemTechnology—Guía de Accesos, Red, Telefonía y Seguridad")

    # ── Pie de Página ─────────────────────────────────────────────
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.75)
    canvas.line(36, 36, 612 - 36, 36)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(36, 24, "Tandem Technology © 2026 — Documentación Interna de Operaciones")

    canvas.drawRightString(612 - 36, 24, f"Página {doc.page}")

    canvas.restoreState()


def generar_pdf_bienvenida(solicitud_id: int, credenciales: dict) -> str:
    """
    Genera el Manual de Bienvenida y Credenciales en formato PDF (4 páginas),
    idéntico en diseño y estructura a storage/AdrianaMartinez.pdf.

    Parámetros:
        solicitud_id: ID de la solicitud en base de datos.
        credenciales: Diccionario completo de credenciales y datos del colaborador
                      (generado por orchestrator / generator).

    Retorna:
        Ruta absoluta al archivo PDF generado en storage/pdfs/.
    """
    _asegurar_activos_visuales()

    # ── 1. Extracción y Normalización de Variables ─────────────────────────
    # Aceptar formatos anidados o planos
    datos_personales = credenciales.get("datos_personales", {})
    propuesta_creds  = credenciales.get("propuesta_credenciales", credenciales)

    ad_creds    = propuesta_creds.get("active_directory", {})
    g_creds     = propuesta_creds.get("google_workspace", {})
    neo_creds   = propuesta_creds.get("neotel", {})
    forti_creds = propuesta_creds.get("forticlient", {})

    nombre = (
        datos_personales.get("nombre")
        or credenciales.get("nombre")
        or "Colaborador"
    ).strip().title()

    apellido = (
        datos_personales.get("apellido")
        or credenciales.get("apellido")
        or "Tandem"
    ).strip().title()

    dni = str(
        datos_personales.get("dni")
        or credenciales.get("dni")
        or ""
    ).strip()

    legajo = str(
        datos_personales.get("legajo")
        or datos_personales.get("legajo_rrhh")
        or credenciales.get("legajo")
        or "0000"
    ).strip()

    es_fuera_de_nomina = bool(
        credenciales.get("es_fuera_de_nomina")
        or datos_personales.get("es_fuera_de_nomina")
    )

    # Variables dinámicas de acceso (destacadas en rojo en el PDF)
    usuario_ad = (
        ad_creds.get("username")
        or credenciales.get("usuario_ad")
        or f"{nombre[:1].lower()}{apellido.lower()}"
    )

    email = (
        g_creds.get("email")
        or credenciales.get("email")
        or f"{usuario_ad}@tandemtech.com.ar"
    )

    clave_ad_mail = (
        ad_creds.get("password_temp")
        or credenciales.get("clave_ad_mail")
        or "T4nd3m**"
    )

    usuario_neo = str(
        neo_creds.get("telemarketer_user")
        or credenciales.get("usuario_neo")
        or (f"3{legajo[1:]}" if legajo.startswith("1") else f"3{legajo}")
    )

    clave_neo = str(
        neo_creds.get("telemarketer_pass")
        or credenciales.get("clave_neo")
        or f"9{usuario_neo}"
    )

    # Formato NombreApellido sin espacios para X-Lite y FortiClient
    nombre_sin_espacios = re.sub(r"[^a-zA-Z0-9]", "", f"{nombre}{apellido}")
    posicion_user = (
        neo_creds.get("posicion_user")
        or credenciales.get("posicion_xlite")
        or nombre_sin_espacios
    )

    posicion_pass = (
        neo_creds.get("posicion_pass")
        or credenciales.get("clave_xlite")
        or "Tandem123"
    )

    usuario_fortinet = (
        forti_creds.get("username")
        or credenciales.get("usuario_fortinet")
        or posicion_user
    )

    clave_fortinet = str(
        forti_creds.get("password_temp")
        or credenciales.get("clave_fortinet")
        or dni
    )

    # Ruta de destino del PDF
    apellido_sanitizado = re.sub(r"[^a-zA-Z0-9]", "", apellido) or "Colaborador"
    pdf_filename = f"Manual_Bienvenida_{legajo}_{apellido_sanitizado}.pdf"
    pdf_filepath = os.path.join(PDF_OUTPUT_DIR, pdf_filename)

    # ── 2. Configuración del Documento ReportLab ──────────────────────────
    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=76,
        bottomMargin=46,
    )

    # ── 3. Estilos Tipográficos ───────────────────────────────────────────
    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    style_sec_hdr = ParagraphStyle(
        "SecHdr",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=colors.white,
    )

    style_sub_title = ParagraphStyle(
        "SubTitle",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=9.2,
        textColor=COLOR_BLUE_TEXT,
        spaceBefore=3,
        spaceAfter=3,
    )

    style_th = ParagraphStyle(
        "TH",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.white,
    )

    style_td = ParagraphStyle(
        "TD",
        parent=normal,
        fontName="Helvetica",
        fontSize=7.8,
        textColor=colors.HexColor("#1E293B"),
        leading=10,
    )

    style_callout_blue = ParagraphStyle(
        "CalloutBlue",
        parent=normal,
        fontName="Helvetica",
        fontSize=7.5,
        textColor=colors.HexColor("#0F172A"),
        leading=10,
    )

    style_callout_yellow = ParagraphStyle(
        "CalloutYellow",
        parent=normal,
        fontName="Helvetica",
        fontSize=7.5,
        textColor=colors.HexColor("#78350F"),
        leading=10,
    )

    style_instruction = ParagraphStyle(
        "Inst",
        parent=normal,
        fontName="Helvetica",
        fontSize=7.8,
        textColor=colors.HexColor("#334155"),
        leading=10.5,
    )

    # Funciones generadoras de bloques visuales
    def sec_hdr(txt: str) -> Table:
        p = Paragraph(f"<b>{txt}</b>", style_sec_hdr)
        t = Table([[p]], colWidths=[540])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_NAVY),
            ("PADDING",    (0, 0), (-1, -1), 4),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def blue_callout(txt: str) -> Table:
        p = Paragraph(txt, style_callout_blue)
        t = Table([[p]], colWidths=[540])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_CALLOUT_BLUE_BG),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#BAE6FD")),
            ("LINELEFT",   (0, 0), (0, -1),  3,   COLOR_CALLOUT_BLUE_BD),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        return t

    def yellow_callout(txt: str) -> Table:
        p = Paragraph(txt, style_callout_yellow)
        t = Table([[p]], colWidths=[540])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_CALLOUT_YEL_BG),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
            ("LINELEFT",   (0, 0), (0, -1),  3,   COLOR_CALLOUT_YEL_BD),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        return t

    story = []

    # =========================================================================
    # PÁGINA 1: WINDOWS & NEOTEL (Credenciales y Doble Factor 2FA)
    # =========================================================================
    story.append(sec_hdr("1. WINDOWS"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("■■ <b>Credenciales Iniciales de Usuario</b>", style_sub_title))

    if es_fuera_de_nomina:
        t1_data = [
            [Paragraph("<b>Servicio / Recurso</b>", style_th), Paragraph("<b>Usuario</b>", style_th), Paragraph("<b>Contraseña / Clave</b>", style_th), Paragraph("<b>Observaciones</b>", style_th)],
            [Paragraph("Windows", style_td), Paragraph("<i>N/A (Fuera de Nómina)</i>", style_td), Paragraph("-", style_td), Paragraph("Personal contractor sin acceso a dominio local.", style_td)],
            [Paragraph("Mail Corporativo", style_td), Paragraph("<i>N/A (Fuera de Nómina)</i>", style_td), Paragraph("-", style_td), Paragraph("No se aprovisiona cuenta corporativa Gmail.", style_td)],
        ]
    else:
        t1_data = [
            [Paragraph("<b>Servicio / Recurso</b>", style_th), Paragraph("<b>Usuario</b>", style_th), Paragraph("<b>Contraseña / Clave</b>", style_th), Paragraph("<b>Observaciones</b>", style_th)],
            [Paragraph("Windows", style_td), Paragraph(f'<b><font color="#D32F2F">TT\\{usuario_ad}</font></b>', style_td), Paragraph(f"<b>{clave_ad_mail}</b>", style_td), Paragraph("Clave temporal. Exige cambio obligatorio en el primer logueo.", style_td)],
            [Paragraph("Mail Corporativo", style_td), Paragraph(f'<b><font color="#D32F2F">{email}</font></b>', style_td), Paragraph(f"<b>{clave_ad_mail}</b>", style_td), Paragraph("Cuenta oficial de Gmail corporativo.", style_td)],
        ]

    t1 = Table(t1_data, colWidths=[100, 150, 110, 180])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),  COLOR_NAVY),
        ("GRID",       (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING",    (0, 0), (-1, -1), 4),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t1)
    story.append(Spacer(1, 4))
    story.append(blue_callout("■ <b>Callout de Dominio:</b> Al ingresar tus credenciales de Windows, recordá anteponer el prefijo de dominio <b>tt\\</b> antes de tu nombre de usuario (ejemplo: tt\\malmada)."))
    story.append(Spacer(1, 6))

    # ── Sección NeoTel ──
    story.append(sec_hdr("2. NEOTEL"))
    story.append(Spacer(1, 4))

    p_neo_left  = Paragraph("■■ <b>Portal de Gestión NeoTel (eCRM)</b>", style_sub_title)
    p_neo_right = Paragraph("<b>Islas NEOTEL</b>", ParagraphStyle("Islas", parent=style_sub_title, alignment=2))
    t_neo_sub   = Table([[p_neo_left, p_neo_right]], colWidths=[270, 270])
    t_neo_sub.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 0)]))
    story.append(t_neo_sub)

    t2_data = [
        [Paragraph("<b>Credenciales</b>", style_th), Paragraph("<b>Enlaces directos por Isla</b>", style_th)],
        [Paragraph(f'Usuario NeoTel: <b><font color="#D32F2F">{usuario_neo}</font></b>', style_td), Paragraph('Isla 1 (Arg): <font color="#0284C7">http://192.168.1.233/ecrm/</font>', style_td)],
        [Paragraph(f'Contraseña: <b><font color="#D32F2F">{clave_neo}</font></b>', style_td), Paragraph('Isla 2 (Int): <font color="#0284C7">http://192.168.1.72/ecrm/</font>', style_td)],
    ]
    t2 = Table(t2_data, colWidths=[240, 300])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),  COLOR_NAVY),
        ("GRID",       (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING",    (0, 0), (-1, -1), 4),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t2)
    story.append(Spacer(1, 4))

    story.append(Paragraph("■ <b>Autenticación de Doble Factor (2FA) e Instrucciones QR</b>", style_sub_title))
    story.append(Paragraph("El acceso a NeoTel requiere el uso de doble factor de autenticación mediante código QR. Podés vincularlo utilizando cualquiera de las dos alternativas siguientes:", style_instruction))
    story.append(Spacer(1, 4))

    # Box Opción A / B con QR de Chrome Extension
    opt_text = Paragraph("""
    <b>Opción A: Dispositivo Móvil (Smartphone)</b><br/>
    1. Descargá e instalá la app Google Authenticator desde la tienda de aplicaciones.<br/>
    2. Escaneá el código QR proporcionado en la plataforma NeoTel de tu isla al ingresar por primera vez.<br/><br/>
    <b>Opción B: Extensión para Google Chrome</b><br/>
    1. Instalá la extensión oficial de <font color="#0284C7"><u>2FA Authenticator</u></font> en tu navegador.<br/>
    2. Escaneá o cargá la imagen del QR para guardar y sincronizar tus llaves dinámicas.
    """, style_instruction)

    chrome_qr_path = os.path.join(ASSETS_DIR, "chrome_2fa_qr.png")
    if os.path.exists(chrome_qr_path):
        img_chrome = Image(chrome_qr_path, width=58, height=58)
    else:
        # Fallback generado con qrcode
        img_chrome = Image(os.path.join(ASSETS_DIR, "ticketera_qr.png"), width=58, height=58)

    cap_chrome = Paragraph("Escaneá para instalar la<br/>extensión 2FA en Chrome", ParagraphStyle("Cap", parent=normal, fontSize=6.5, alignment=1, textColor=colors.HexColor("#64748B"), leading=8))
    col_chrome = Table([[img_chrome], [cap_chrome]], colWidths=[120])
    col_chrome.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 0)]))

    t_box_opts = Table([[opt_text, col_chrome]], colWidths=[420, 120])
    t_box_opts.setStyle(TableStyle([
        ("BOX",     (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_box_opts)
    story.append(Spacer(1, 4))

    # Box NeoTel QR Dinámico
    qr_raw_input = neo_creds.get("qr_path") or credenciales.get("qr_path") or credenciales.get("neotel_qr")
    temp_qr_filename = f"qr_neo_{legajo}.png"
    dynamic_qr_path = _procesar_qr_dinamico(qr_raw_input, temp_qr_filename)

    if not dynamic_qr_path or not os.path.exists(dynamic_qr_path):
        dynamic_qr_path = os.path.join(ASSETS_DIR, "neotel_default_qr.png")

    qr_neo_text = Paragraph("""
    <b>Codigo QR para acceso a NeoTel:</b><br/><br/>
    1. Escaneá con la app Google Authenticator para obtener el Token<br/><br/>
    2. Escaneá/Cargá el código QR con la Extension Authenticator de Google Chrome
    """, style_instruction)

    img_neo = Image(dynamic_qr_path, width=58, height=58)
    cap_neo = Paragraph("Escaneá para NEO ISLA 1", ParagraphStyle("CapN", parent=normal, fontSize=6.5, alignment=1, textColor=colors.HexColor("#64748B"), leading=8))
    col_neo = Table([[img_neo], [cap_neo]], colWidths=[120])
    col_neo.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 0)]))

    t_box_neo = Table([[qr_neo_text, col_neo]], colWidths=[420, 120])
    t_box_neo.setStyle(TableStyle([
        ("BOX",     (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_box_neo)

    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: TELEFONÍA XLITE - POSICION (Servidores y Softphone)
    # =========================================================================
    story.append(sec_hdr("3. TELEFONÍA XLITE - POSICION"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("■■ <b>Servidores VoIP / Domain</b>", style_sub_title))

    t_voip_data = [
        [Paragraph("<b>Isla Operativa</b>", style_th), Paragraph("<b>Destino / País de Gestión</b>", style_th), Paragraph("<b>IP Servidor (Domain)</b>", style_th)],
        [Paragraph("Isla 1", style_td), Paragraph("Argentina", style_td), Paragraph("192.168.1.234", style_td)],
        [Paragraph("Isla 2", style_td), Paragraph("Internacional (Chile / Otros países)", style_td), Paragraph("192.168.1.73", style_td)],
    ]
    t_voip = Table(t_voip_data, colWidths=[130, 250, 160])
    t_voip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),  COLOR_NAVY),
        ("GRID",       (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING",    (0, 0), (-1, -1), 4),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_voip)
    story.append(Spacer(1, 4))

    story.append(Paragraph("■■ <b>Paso a Paso: Configuración de Cuenta en X-Lite</b>", style_sub_title))
    story.append(Paragraph("Al abrir X-Lite, accedé a las propiedades de la cuenta (<b>SIP Account Settings</b>) y completá los campos con la siguiente estructura:", style_instruction))
    story.append(Spacer(1, 3))

    xlite_bullets = Paragraph(f"""
    • <b>Display Name:</b> Ingresá <b><font color="#D32F2F">{posicion_user}</font></b> (sin espacios, respetando mayúsculas).<br/>
    • <b>User Name:</b> Escribí <b><font color="#D32F2F">{posicion_user}</font></b><br/>
    • <b>Password:</b> Ingresá la contraseña fija <b><font color="#D32F2F">{posicion_pass}</font></b>.<br/>
    • <b>Authorization Name:</b> Repetí exactamente <b><font color="#D32F2F">{posicion_user}</font></b>.<br/>
    • <b>Domain:</b> Colocá la IP del servidor según la isla asignada (<b><font color="#D32F2F">192.168.1.234</font></b> para Argentina o <b><font color="#D32F2F">192.168.1.73</font></b> para Internacional).
    """, style_instruction)
    story.append(xlite_bullets)
    story.append(Spacer(1, 4))

    story.append(blue_callout("■ <b>Validación de Sintaxis:</b> Asegurate de no dejar espacios en blanco antes ni después de cada campo y de mantener la combinación exacta de mayúsculas y minúsculas."))
    story.append(Spacer(1, 6))

    dialer_path = os.path.join(ASSETS_DIR, "xlite_dialer.png")
    props_path  = os.path.join(ASSETS_DIR, "xlite_properties.png")

    elementos_xlite = []
    if os.path.exists(dialer_path) and os.path.exists(props_path):
        img_dialer = Image(dialer_path, width=135, height=155)
        img_props  = Image(props_path,  width=190, height=155)
        t_xlite_imgs = Table([[img_dialer, img_props]], colWidths=[200, 340])
        t_xlite_imgs.setStyle(TableStyle([
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t_xlite_imgs)

    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 3: CONECTIVIDAD VPN (FortiClient)
    # =========================================================================
    story.append(sec_hdr("4. CONECTIVIDAD VPN"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("■ <b>Paso a Paso: Conexión Remota con FortiClient VPN</b>", style_sub_title))

    if es_fuera_de_nomina:
        vpn_steps = Paragraph("""
        1. <b>Personal Fuera de Nómina:</b> Esta solicitud no tiene habilitado perfil de VPN Fortinet.<br/>
        2. Toda la gestión operativa se realiza exclusivamente mediante la plataforma web de NeoTel eCRM.
        """, style_instruction)
    else:
        vpn_steps = Paragraph(f"""
        1. Abrí la aplicación <b>FortiClient VPN</b> en tu PC/Notebook.<br/>
        2. En la lista desplegable de conexiones, seleccioná el perfil <b>Tandem Technology</b>.<br/>
        3. Ingresá tus credenciales de acceso remoto:<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Usuario:</b> <b><font color="#D32F2F">{usuario_fortinet}</font></b> &nbsp;&nbsp;&nbsp;&nbsp; <b>Contraseña:</b> <b><font color="#D32F2F">{clave_fortinet}</font></b><br/>
        4. Hacé clic en <b>Connect</b> para establecer la conexión cifrada a la red interna.<br/>
        5. Se habilita un campo donde debés ingresar un <b>Token</b> que llega a tu mail corporativo.
        """, style_instruction)

    story.append(vpn_steps)
    story.append(Spacer(1, 5))

    story.append(yellow_callout("■■ <b>Llamado de Atención — Operativa Especial Movistar T3:</b> Si te asignan operaciones para <b>Movistar T3</b>, no debés utilizar el perfil estándar de VPN. En su lugar, solicitá la habilitación de la conexión especial enviando un ticket al área de soporte."))
    story.append(Spacer(1, 8))

    forti_img_path = os.path.join(ASSETS_DIR, "forticlient_screen.png")
    if os.path.exists(forti_img_path):
        img_forti = Image(forti_img_path, width=360, height=285)
        t_forti_img = Table([[img_forti]], colWidths=[540])
        t_forti_img.setStyle(TableStyle([
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t_forti_img)

    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 4: TICKETERA Y SOPORTE OFICIAL
    # =========================================================================
    story.append(sec_hdr("5. TICKETERA"))
    story.append(Spacer(1, 6))
    story.append(Paragraph("■ <b>Mesa de Ayuda y Ticketera de Soporte Oficial</b>", style_sub_title))
    story.append(Spacer(1, 4))

    tick_text = Paragraph("""
    Para reportar incidentes técnicos, solicitar accesos especiales (como la conectividad para Movistar T3) o resolver dudas operativas, utilizá la ticketera unificada de Tandem Technology.<br/><br/>
    • <b>Portal Web:</b> <font color="#0284C7"><u>https://soporte.tandemtech.com.ar</u></font><br/>
    • <b>Método de Ingreso:</b> Iniciá sesión directamente con tu cuenta corporativa de Google tras loguearte en el navegador Google Chrome.
    """, style_instruction)

    tick_qr_path = os.path.join(ASSETS_DIR, "ticketera_qr.png")
    if not os.path.exists(tick_qr_path):
        _asegurar_activos_visuales()

    img_tick = Image(tick_qr_path, width=65, height=65)
    cap_tick = Paragraph("Escaneá para ingresar a la<br/>Ticketera", ParagraphStyle("CapT", parent=normal, fontSize=6.5, alignment=1, textColor=colors.HexColor("#64748B"), leading=8))
    col_tick = Table([[img_tick], [cap_tick]], colWidths=[120])
    col_tick.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 0)]))

    t_box_tick = Table([[tick_text, col_tick]], colWidths=[420, 120])
    t_box_tick.setStyle(TableStyle([
        ("BOX",     (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_box_tick)
    story.append(Spacer(1, 8))

    story.append(blue_callout("■ <b>Atención y Consultas:</b> Si presentás cualquier inconveniente durante el proceso de instalación o validación de accesos, podés comunicarte inmediatamente con el equipo de soporte técnico a través del portal."))

    # ── 4. Construcción del Documento ─────────────────────────────────────
    try:
        doc.build(story, onFirstPage=_dibujar_encabezado_pie, onLaterPages=_dibujar_encabezado_pie)
        logger.info(f"[PDF_SERVICE] ✅ Manual de bienvenida generado con éxito: {pdf_filepath}")
        return pdf_filepath
    except Exception as e:
        logger.error(f"[PDF_SERVICE] ❌ Error construyendo el PDF '{pdf_filepath}': {e}")
        raise


def generar_pdf_credenciales(datos_solicitud: dict, credenciales: dict) -> str:
    """
    Función de retrocompatibilidad. Delega la creación en generar_pdf_bienvenida.
    """
    solicitud_id = datos_solicitud.get("id") or datos_solicitud.get("solicitud_id", 0)
    payload = {
        "datos_personales": datos_solicitud,
        "propuesta_credenciales": credenciales,
        "es_fuera_de_nomina": datos_solicitud.get("es_fuera_de_nomina", False),
    }
    return generar_pdf_bienvenida(solicitud_id=solicitud_id, credenciales=payload)