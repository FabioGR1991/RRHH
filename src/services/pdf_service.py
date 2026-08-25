"""
===================================================================
ARCHIVO: src/services/pdf_service.py
DESCRIPCIÓN: Servicio para la generación de PDFs de credenciales de alta.
Guarda los comprobantes generados en el directorio storage/pdfs/.
===================================================================
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generar_pdf_credenciales(datos_solicitud: dict, credenciales: dict) -> str:
    """
    Genera un archivo PDF con las credenciales creadas para el nuevo empleado.
    
    :param datos_solicitud: Diccionario con datos del empleado (nombre, apellido, dni, legajo, etc.)
    :param credenciales: Diccionario estructurado devuelto por generator.py
    :return: Ruta absoluta del archivo PDF generado.
    """
    # 1. Asegurar que la carpeta de almacenamiento exista
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage/pdfs"))
    os.makedirs(output_dir, exist_ok=True)

    filename = f"Alta_{datos_solicitud['legajo']}_{datos_solicitud['apellido']}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=6
    )

    normal_style = styles['Normal']

    story = []

    # 2. Encabezado
    story.append(Paragraph("Ficha de Alta y Credenciales de Usuario", title_style))
    story.append(Spacer(1, 10))

    # 3. Datos del Empleado (Tabla)
    datos_empleado = [
        [Paragraph("<b>Nombre Completo:</b>", normal_style), f"{datos_solicitud['nombre']} {datos_solicitud['apellido']}"],
        [Paragraph("<b>DNI:</b>", normal_style), str(datos_solicitud['dni'])],
        [Paragraph("<b>Legajo / Usuario:</b>", normal_style), str(datos_solicitud['legajo'])],
        [Paragraph("<b>Perfil AD:</b>", normal_style), datos_solicitud.get('perfil_ad', 'N/A')],
        [Paragraph("<b>Reporta a:</b>", normal_style), datos_solicitud.get('reporta_a', 'N/A')],
    ]

    t_empleado = Table(datos_empleado, colWidths=[150, 380])
    t_empleado.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_empleado)
    story.append(Spacer(1, 15))

    # 4. Detalle de Credenciales por Servicio
    ad_data = credenciales.get("active_directory", {})
    gworkspace_data = credenciales.get("google_workspace", {})
    forti_data = credenciales.get("forticlient", {})
    neo_data = credenciales.get("neotel", {})

    story.append(Paragraph("Credenciales Asignadas", subtitle_style))

    credenciales_tabla = [
        [Paragraph("<b>Servicio</b>", normal_style), Paragraph("<b>Usuario / Email</b>", normal_style), Paragraph("<b>Contraseña Temporal</b>", normal_style)],
        ["Active Directory", ad_data.get("username", "N/A"), ad_data.get("password_temp", "N/A")],
        ["Google Workspace", gworkspace_data.get("email", "N/A"), ad_data.get("password_temp", "N/A")],
        ["FortiClient / VPN", forti_data.get("username", "N/A"), forti_data.get("password_temp", "N/A")],
        ["Neotel (Telemarketer)", neo_data.get("telemarketer_user", "N/A"), neo_data.get("telemarketer_pass", "N/A")],
        ["Neotel (Posición / X-Lite)", neo_data.get("posicion_user", "N/A"), neo_data.get("posicion_pass", "N/A")],
    ]

    t_creds = Table(credenciales_tabla, colWidths=[150, 230, 150])
    t_creds.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')])
    ]))
    story.append(t_creds)
    story.append(Spacer(1, 20))

    # 5. Nota de seguridad final
    nota_seguridad = Paragraph(
        "<i><b>Importante:</b> Las contraseñas asignadas son temporales. Se recomienda al usuario cambiarlas al iniciar sesión por primera vez.</i>",
        normal_style
    )
    story.append(nota_seguridad)

    # 6. Construir PDF
    doc.build(story)
    
    return filepath