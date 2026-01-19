"""Generación de PDF del certificado.

Este módulo NO depende del frontend. Genera un PDF desde el servidor usando ReportLab.

Requisitos solicitados por el usuario:
- El documento no se muestra en línea (se descarga como PDF).
- El QR va un poco más a la izquierda.
- Debajo del QR se imprime la URL y es clickeable.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import qrcode
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def _qr_as_reportlab_image(data: str, size_px: int = 260) -> Image:
    """Genera un QR y lo devuelve como Flowable Image."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size_px, size_px))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=110, height=110, hAlign="LEFT")


def generar_certificado_pdf(*, ciudadano, codigo: str, verify_url: str, out_path: str) -> None:
    """Crea un PDF en out_path."""
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Fecha/hora de emisión visible en el documento
    now = datetime.now()

    # Styles
    styles = getSampleStyleSheet()
    base = styles["Normal"]
    base.fontName = "Helvetica"
    base.fontSize = 11
    base.leading = 16

    header_style = ParagraphStyle(
        "header",
        parent=base,
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
    )

    title_style = ParagraphStyle(
        "title",
        parent=base,
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceBefore=18,
        spaceAfter=18,
    )
    title_style.fontName = "Helvetica-Bold"

    body_style = ParagraphStyle(
        "body",
        parent=base,
        alignment=TA_JUSTIFY,
    )

    body_bold_style = ParagraphStyle(
        "body_bold",
        parent=body_style,
    )
    body_bold_style.fontName = "Helvetica-Bold"

    small_style = ParagraphStyle(
        "small",
        parent=base,
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
    )

    link_style = ParagraphStyle(
        "link",
        parent=base,
        fontSize=7.2,
        leading=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0f3a5f"),
    )

    footer_style = ParagraphStyle(
        "footer",
        parent=base,
        fontSize=7.5,
        leading=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"),
    )
    footer_style.fontName = "Helvetica-Bold"

    # Documento
    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=A4,
        leftMargin=52,
        rightMargin=52,
        topMargin=52,
        bottomMargin=52,
        title="Certificado Cabildo Indígena de la Peñata",
        author="Cabildo Indígena de la Peñata",
    )

    story = []

    header_lines = [
        "RESGUARDO INDIGENA ZENU SAN ANDRES DE SOTAVENTO",
        "CORDOBA – SUCRE",
        "CABILDO MENOR INDIGENA DE LA PEÑATA – TERRITORIO – SINCELEJO",
        "NIT. 823.003.642-8",
        "RESOLUCION N° 0022 DEL 26 DE OCTUBRE DEL 2011",
    ]
    for line in header_lines:
        story.append(Paragraph(f"<b>{line}</b>", header_style))
    story.append(Spacer(1, 22))

    # Texto legal
    story.append(
        Paragraph(
            "El Capitán Menor Indígena de la Peñata, en uso de sus facultades legales Ley 21 1991, "
            "Leyes complementarias y Decretos Complementarios, uso de costumbres propias del pueblo Zenú, "
            "y en cumplimiento de su función de representación y organización comunitaria.",
            body_style,
        )
    )
    story.append(Paragraph("CERTIFICA QUE", title_style))

    story.append(
        Paragraph(
            f"<b>{ciudadano.nombre_completo}</b> identificado(a) con {ciudadano.tipo_documento} No. "
            f"<b>{ciudadano.numero_documento}</b> se encuentra debidamente afiliado(a) al Cabildo Menor Indígena "
            "de la Peñata, perteneciente al Resguardo Indígena Zenú de San Andrés de Sotavento, Córdoba - Sucre, "
            "y registrado en la base de datos del ministerio del interior, formando parte activa de nuestra comunidad "
            "respetando los principios de identidad, unidad, territorio y cultura ancestral del pueblo Zenú.",
            body_style,
        )
    )

    mes = MESES_ES.get(now.month, str(now.month))
    hora = now.strftime("%I:%M %p")
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "La presente certificación se expide a solicitud del interesado (a), en la ciudad de "
            f"<b>Sincelejo, Sucre</b>, a los <b>{now.day:02d}</b> días del mes de <b>{mes}</b> del año "
            f"<b>{now.year}</b>, siendo las <b>{hora}</b>.",
            body_style,
        )
    )

    story.append(Spacer(1, 28))

    # --- Bloque inferior: firma + QR ---
    # Firma
    signature_flowables = []
    signature_path = Path(current_app.root_path) / "static" / "img" / "Firma_Diomedes.png"
    if signature_path.exists():
        signature_flowables.append(Image(str(signature_path), width=180, height=80, hAlign="LEFT"))
        signature_flowables.append(Spacer(1, 2))
    signature_flowables.append(HRFlowable(width=250, thickness=1.2, color=colors.black))
    signature_flowables.append(Spacer(1, 4))
    signature_flowables.append(Paragraph("DIOMEDES FARID MONTES BERTEL", ParagraphStyle(
        "sig_name", parent=base, fontName="Helvetica-Bold", fontSize=9.5, leading=11, alignment=TA_LEFT
    )))
    signature_flowables.append(Paragraph("Capitán Menor Indígena", ParagraphStyle(
        "sig_role", parent=base, fontSize=8.8, leading=10, alignment=TA_LEFT
    )))

    # QR + URL
    qr_img = _qr_as_reportlab_image(verify_url)

    # QR
    qr_block = [
        qr_img,
        Spacer(1, 4),
        Paragraph("Valide este documento escaneando el código QR", ParagraphStyle(
            "qr_text", parent=small_style, alignment=TA_LEFT
        )),
        Spacer(1, 3),
        Paragraph(f"<link href='{verify_url}'>{verify_url}</link>", link_style),
    ]
    table = Table(
        [[signature_flowables, qr_block]],
        colWidths=[doc.width * 0.58, doc.width * 0.42],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Los Cabildos Menores son considerados Entidades territoriales Indígenas de carácter especial, Decreto "
            "1386, por ende, puede Ejercer todas las funciones de las entidades territorial",
            footer_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph(f"Código de verificación: <b>{codigo}</b>", ParagraphStyle(
        "code", parent=base, fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.HexColor("#444444")
    )))

    doc.build(story)
