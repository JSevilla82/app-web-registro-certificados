from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from html import escape as html_escape
from zoneinfo import ZoneInfo
from pathlib import Path

import qrcode
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Flowable,
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



class LinkNoWrap(Flowable):
    """Enlace sin salto de línea para ubicarlo debajo del QR."""

    def __init__(
        self,
        text: str,
        url: str,
        *,
        width: float,
        font_name: str = "Helvetica",
        font_size: float = 7.2,
        color=colors.HexColor("#0f3a5f"),
        min_font_size: float = 5.8,
    ) -> None:
        super().__init__()
        self.text = text
        self.url = url
        self.width = float(width)
        self.font_name = font_name
        self.font_size = float(font_size)
        self.min_font_size = float(min_font_size)
        self.color = color
        self.height = self.font_size + 4

    def wrap(self, availWidth, availHeight):  # noqa: N802
        return self.width, self.height

    def draw(self):  # noqa: N802
        c = self.canv
        size = self.font_size
        while pdfmetrics.stringWidth(self.text, self.font_name, size) > self.width and size > self.min_font_size:
            size -= 0.2

        c.saveState()
        c.setFont(self.font_name, size)
        c.setFillColor(self.color)

        text_width = pdfmetrics.stringWidth(self.text, self.font_name, size)
        x = max(0, (self.width - text_width) / 2)
        y = 0
        c.drawString(x, y, self.text)

        c.linkURL(self.url, (x, y, x + text_width, y + size + 2), relative=0)
        c.restoreState()

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


def _resolver_ruta_firma(ruta: str | None) -> Path | None:
    if not ruta:
        return None
    ruta = ruta.strip()
    if not ruta:
        return None
    p = Path(ruta)
    if not p.is_absolute():
        p = Path(current_app.root_path) / ruta
    return p


def _tz() -> ZoneInfo:
    tz_name = current_app.config.get("APP_TIMEZONE") or "America/Bogota"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("America/Bogota")


def _to_local(dt_utc_naive: datetime) -> datetime:
    """Convierte un datetime naive en UTC a datetime aware en zona local."""
    tz = _tz()
    if dt_utc_naive.tzinfo is None:
        dt_utc = dt_utc_naive.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt_utc_naive.astimezone(timezone.utc)
    return dt_utc.astimezone(tz)


def _parrafo_principal_certificado(*, ciudadano, tipo_documento: str, texto_personalizado: str | None) -> str:
    """Construye el párrafo principal del certificado.

    - Afiliación: texto estándar.
    - Especial: mantiene solo la frase de identificación + texto personalizado.

    Nota: texto_personalizado se escapa para evitar que rompa el markup de ReportLab.
    """

    if (tipo_documento or "").strip() == "certificado_especial":
        intro = (
            f"<b>{ciudadano.nombre_completo}</b> identificado(a) con {ciudadano.tipo_documento} No. "
            f"<b>{ciudadano.numero_documento}</b>."
        )
        t = (texto_personalizado or "").strip()
        if t:
            t = t[0].upper() + t[1:]
            t = html_escape(t).replace("\n", "<br/>")
            return f"{intro} {t}"
        return intro

    return (
        f"<b>{ciudadano.nombre_completo}</b> identificado(a) con {ciudadano.tipo_documento} No. "
        f"<b>{ciudadano.numero_documento}</b> se encuentra debidamente afiliado(a) al Cabildo Menor Indígena "
        "de la Peñata, perteneciente al Resguardo Indígena Zenú de San Andrés de Sotavento, Córdoba - Sucre, "
        "y registrado en la base de datos del ministerio del interior, formando parte activa de nuestra comunidad "
        "respetando los principios de identidad, unidad, territorio y cultura ancestral del pueblo Zenú."
    )


def generar_certificado_pdf_bytes(
    *,
    ciudadano,
    codigo: str,
    verify_url: str,
    emitido_en_utc: datetime,
    tipo_documento: str = "certificado_afiliacion",
    texto_personalizado: str | None = None,
) -> bytes:
    """Genera el certificado en bytes.

    Cambios solicitados:
    - No depende de un archivo guardado en disco.
    - La fecha/hora de emisión debe corresponder al momento en que el usuario lo generó
      (emitido_en_utc), no al momento en que se abre/descarga.
    """
    buf = io.BytesIO()

    emitido_local = _to_local(emitido_en_utc)

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
        spaceBefore=30,
        spaceAfter=30,
    )
    title_style.fontName = "Helvetica-Bold"

    body_style = ParagraphStyle(
        "body",
        parent=base,
        alignment=TA_JUSTIFY,
    )

    small_left = ParagraphStyle(
        "small_left",
        parent=base,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#444444"),
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

    # Ajustes de layout solicitados (copia de verificación):
    ID_Y_OFFSET = 55
    FOOTER_Y = 80
    TOP_MARGIN = 90
    SIGNATURE_TOP_SPACER = 60  # espacio antes de firma/QR 
    ID_Y_OFFSET = 55
    FOOTER_Y = 80
    TOP_MARGIN = 90

    ID_Y_OFFSET = 55  # px aprox desde el borde superior
    FOOTER_Y = 80     # px aprox desde el borde inferior
    TOP_MARGIN = 90
    SIGNATURE_TOP_SPACER = 60  # espacio antes de firma/QR 
    def _dibujar_id_documento(canvas, doc):  # noqa: N803
        """Elementos fijos de la hoja.

        - ID arriba a la izquierda (arriba del todo)
        - Leyenda legal siempre al final de la hoja
        """
        canvas.saveState()

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#444444"))
        texto_id = f"ID: {codigo}"
        x_id = doc.leftMargin
        y_id = doc.pagesize[1] - ID_Y_OFFSET 
        canvas.drawString(x_id, y_id, texto_id)

        footer_text = (
            "Los Cabildos Menores son considerados Entidades territoriales Indígenas de carácter especial, Decreto "
            "1386, por ende, puede Ejercer todas las funciones de las entidades territorial"
        )
        para = Paragraph(footer_text, footer_style)
        w, h = para.wrap(doc.width, doc.bottomMargin)
        para.drawOn(canvas, doc.leftMargin, FOOTER_Y)

        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=TOP_MARGIN,
        bottomMargin=50,
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
    story.append(Spacer(1, 16))

    story.append(
        Paragraph(
            "El Capitán Menor Indígena de la Peñata, en uso de sus facultades legales Ley 21 1991, "
            "Leyes complementarias y Decretos Complementarios, uso de costumbres propias del pueblo Zenú, "
            "y en cumplimiento de su función de representación y organización comunitaria.",
            body_style,
        )
    )
    story.append(Paragraph("CERTIFICA QUE", title_style))

    story.append(Paragraph(_parrafo_principal_certificado(ciudadano=ciudadano, tipo_documento=tipo_documento, texto_personalizado=texto_personalizado), body_style))

    mes = MESES_ES.get(emitido_local.month, str(emitido_local.month))
    hora = emitido_local.strftime("%I:%M %p")

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "La presente certificación se expide a solicitud del interesado (a), en la ciudad de "
            f"<b>Sincelejo, Sucre</b>, a los <b>{emitido_local.day:02d}</b> días del mes de <b>{mes}</b> del año "
            f"<b>{emitido_local.year}</b>, siendo las <b>{hora}</b>.",
            body_style,
        )
    )

    story.append(Spacer(1, SIGNATURE_TOP_SPACER))

    firma_ruta = current_app.config.get("CAPITAN_MENOR_FIRMA_RUTA")
    nombre_firma = current_app.config.get("CAPITAN_MENOR_NOMBRE") or "CAPITÁN MENOR"
    doc_tipo = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_TIPO") or ""
    doc_num = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_NUMERO") or ""

    signature_flowables = []
    firma_path = _resolver_ruta_firma(firma_ruta) or (Path(current_app.root_path) / "static" / "img" / "Firma_Diomedes.png")

    if firma_path.exists():
        signature_flowables.append(Image(str(firma_path), width=180, height=80, hAlign="LEFT"))
        signature_flowables.append(Spacer(1, 1))

    signature_flowables.append(HRFlowable(width=250, thickness=1.2, color=colors.black))
    signature_flowables.append(Spacer(1, 4))

    nombre_con_doc = nombre_firma
    if doc_tipo or doc_num:
        nombre_con_doc = f"{nombre_firma}<br/>{doc_tipo} {doc_num}".strip()    

    signature_flowables.append(
        Paragraph(
            nombre_con_doc,
            ParagraphStyle(
                "sig_name",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=9.5,
                leading=11,
                alignment=TA_LEFT,
            ),
        )
    )

    signature_flowables.append(
        Paragraph(
            "Capitán Menor Indígena",
            ParagraphStyle("sig_role", parent=base, fontSize=8.8, leading=10, alignment=TA_LEFT),
        )
    )

    qr_img = _qr_as_reportlab_image(verify_url)
    qr_block = [
        qr_img,
        Spacer(1, 4),
        LinkNoWrap(verify_url, verify_url, width=110, font_name="Helvetica", font_size=7.2),
        Spacer(1, 6),
        Paragraph(
            "Escanee el QR o haga clic en el enlace para validar la autenticidad y el estado de afiliación.",
            small_left,
        ),
    ]

    table = Table(
        [[signature_flowables, qr_block]],
        colWidths=[doc.width * 0.60, doc.width * 0.40],
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

    # La leyenda legal e ID se pintan por canvas (footer fijo + ID arriba)
    doc.build(story, onFirstPage=_dibujar_id_documento, onLaterPages=_dibujar_id_documento)
    buf.seek(0)
    return buf.getvalue()


def generar_certificado_pdf(*, ciudadano, codigo: str, verify_url: str, out_path: str, emitido_en_utc: datetime | None = None) -> None:
    """Crea un PDF (tamaño carta) en out_path.

    Nota: el proyecto ya no guarda PDFs por defecto, pero mantenemos esta función
    por compatibilidad.
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if emitido_en_utc is None:
        emitido_en_utc = datetime.utcnow()

    pdf_bytes = generar_certificado_pdf_bytes(
        ciudadano=ciudadano,
        codigo=codigo,
        verify_url=verify_url,
        emitido_en_utc=emitido_en_utc,
    )
    out_file.write_bytes(pdf_bytes)
    return

    ahora = datetime.now()

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
        spaceBefore=30,
        spaceAfter=30,
    )
    title_style.fontName = "Helvetica-Bold"

    body_style = ParagraphStyle(
        "body",
        parent=base,
        alignment=TA_JUSTIFY,
    )

    small_left = ParagraphStyle(
        "small_left",
        parent=base,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
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

    ID_Y_OFFSET = 55
    FOOTER_Y = 80
    TOP_MARGIN = 90

    def _dibujar_id_documento(canvas, doc):
        """Elementos fijos de la hoja.

        - ID arriba a la izquierda (arriba del todo)
        - Leyenda legal siempre al final de la hoja
        """
        canvas.saveState()

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#444444"))
        texto_id = f"ID: {codigo}"
        canvas.drawString(doc.leftMargin, doc.pagesize[1] - ID_Y_OFFSET, texto_id)

        footer_text = (
            "Los Cabildos Menores son considerados Entidades territoriales Indígenas de carácter especial, Decreto "
            "1386, por ende, puede Ejercer todas las funciones de las entidades territorial"
        )
        para = Paragraph(footer_text, footer_style)
        para.wrap(doc.width, doc.bottomMargin)
        para.drawOn(canvas, doc.leftMargin, FOOTER_Y)

        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=TOP_MARGIN,
        bottomMargin=50,
        title="Certificado Cabildo Indígena de la Peñata",
        author="Cabildo Indígena de la Peñata",
    )

    story = []

    # Encabezado
    header_lines = [
        "RESGUARDO INDIGENA ZENU SAN ANDRES DE SOTAVENTO",
        "CORDOBA – SUCRE",
        "CABILDO MENOR INDIGENA DE LA PEÑATA – TERRITORIO – SINCELEJO",
        "NIT. 823.003.642-8",
        "RESOLUCION N° 0022 DEL 26 DE OCTUBRE DEL 2011",
    ]
    for line in header_lines:
        story.append(Paragraph(f"<b>{line}</b>", header_style))
    story.append(Spacer(1, 16))

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
            _parrafo_principal_certificado(
                ciudadano=ciudadano,
                tipo_documento=tipo_documento,
                texto_personalizado=texto_personalizado,
            ),
            body_style,
        )
    )

    mes = MESES_ES.get(ahora.month, str(ahora.month))
    hora = ahora.strftime("%I:%M %p")

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "La presente certificación se expide a solicitud del interesado (a), en la ciudad de "
            f"<b>Sincelejo, Sucre</b>, a los <b>{ahora.day:02d}</b> días del mes de <b>{mes}</b> del año "
            f"<b>{ahora.year}</b>, siendo las <b>{hora}</b>.",
            body_style,
        )
    )

    story.append(Spacer(1, SIGNATURE_TOP_SPACER))

    # Firma (parametrizable por .env)
    firma_ruta = current_app.config.get("CAPITAN_MENOR_FIRMA_RUTA")
    nombre_firma = current_app.config.get("CAPITAN_MENOR_NOMBRE") or "CAPITÁN MENOR"
    doc_tipo = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_TIPO") or ""
    doc_num = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_NUMERO") or ""

    signature_flowables = []
    firma_path = _resolver_ruta_firma(firma_ruta) or (Path(current_app.root_path) / "static" / "img" / "Firma_Diomedes.png")

    if firma_path.exists():
        signature_flowables.append(Image(str(firma_path), width=180, height=80, hAlign="LEFT"))
        signature_flowables.append(Spacer(1, 1))

    signature_flowables.append(HRFlowable(width=250, thickness=1.2, color=colors.black))
    signature_flowables.append(Spacer(1, 4))
    sufijo_doc = ""
    if doc_tipo or doc_num:
        sufijo_doc = f" - {doc_tipo} {doc_num}".strip()

    signature_flowables.append(
        Paragraph(
            f"{nombre_firma}{sufijo_doc}",
            ParagraphStyle(
                "sig_name",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=9.5,
                leading=11,
                alignment=TA_LEFT,
            ),
        )
    )

    signature_flowables.append(
        Paragraph(
            "Capitán Menor Indígena",
            ParagraphStyle("sig_role", parent=base, fontSize=8.8, leading=10, alignment=TA_LEFT),
        )
    )

    # QR + enlace + texto
    qr_img = _qr_as_reportlab_image(verify_url)

    qr_block = [
        qr_img,
        Spacer(1, 4),
        LinkNoWrap(verify_url, verify_url, width=110, font_name="Helvetica", font_size=7.2),
        Spacer(1, 6),
        Paragraph(
            "Escanee el QR o haga clic en el enlace para validar la autenticidad y el estado de afiliación.",
            small_left,
        ),
    ]

    table = Table(
        [[signature_flowables, qr_block]],
        colWidths=[doc.width * 0.60, doc.width * 0.40],
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

    story.append(Spacer(1, 10))

    doc.build(story, onFirstPage=_dibujar_id_documento, onLaterPages=_dibujar_id_documento)


def generar_copia_verificacion_pdf_bytes(
    *,
    ciudadano,
    codigo: str,
    verify_url: str,
    consultado_en: datetime,
    emitido_en_utc: datetime,
    tipo_documento: str = "certificado_afiliacion",
    texto_personalizado: str | None = None,
) -> bytes:
    """Genera una copia del certificado para fines de verificación pública.

    - No modifica ni depende del archivo original
    - Incluye marca/leyenda indicando que es una copia
    - Incluye fecha y hora de la consulta

    Retorna el PDF en bytes (para abrirse en el navegador).
    """
    buf = io.BytesIO()

    styles = getSampleStyleSheet()
    base = styles["Normal"]
    base.fontName = "Helvetica"
    base.fontSize = 11
    base.leading = 16

    aviso_style = ParagraphStyle(
        "aviso",
        parent=base,
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
    )
    aviso_style.fontName = "Helvetica-Bold"

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
        spaceBefore=30,
        spaceAfter=30,
    )
    title_style.fontName = "Helvetica-Bold"

    body_style = ParagraphStyle(
        "body",
        parent=base,
        alignment=TA_JUSTIFY,
    )

    small_left = ParagraphStyle(
        "small_left",
        parent=base,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
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

    ID_Y_OFFSET = 55
    FOOTER_Y = 80
    TOP_MARGIN = 90
    SIGNATURE_TOP_SPACER = 60 
    def _dibujar_id_documento(canvas, doc):  # noqa: N803
        """Elementos fijos de la hoja.

        - ID arriba a la izquierda (arriba del todo)
        - Leyenda legal siempre al final de la hoja
        """
        canvas.saveState()

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#444444"))
        texto_id = f"ID: {codigo}"
        canvas.drawString(doc.leftMargin, doc.pagesize[1] - ID_Y_OFFSET, texto_id)

        footer_text = (
            "Los Cabildos Menores son considerados Entidades territoriales Indígenas de carácter especial, Decreto "
            "1386, por ende, puede Ejercer todas las funciones de las entidades territorial"
        )
        para = Paragraph(footer_text, footer_style)
        para.wrap(doc.width, doc.bottomMargin)
        para.drawOn(canvas, doc.leftMargin, FOOTER_Y)

        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=TOP_MARGIN,
        bottomMargin=50,
        title="Copia para verificación - Certificado Cabildo",
        author="Cabildo Indígena de la Peñata",
    )

    story = []

    # Aviso de copia (servidor central)
    consulta_txt = consultado_en.strftime("%d/%m/%Y %I:%M %p")
    story.append(Paragraph("COPIA PARA VERIFICACIÓN (SERVIDOR CENTRAL)", aviso_style))
    story.append(Paragraph(f"Consulta realizada: {consulta_txt}", ParagraphStyle("aviso2", parent=aviso_style, fontName="Helvetica", fontSize=8.2)))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#DDDDDD")))
    story.append(Spacer(1, 10))

    header_lines = [
        "RESGUARDO INDIGENA ZENU SAN ANDRES DE SOTAVENTO",
        "CORDOBA – SUCRE",
        "CABILDO MENOR INDIGENA DE LA PEÑATA – TERRITORIO – SINCELEJO",
        "NIT. 823.003.642-8",
        "RESOLUCION N° 0022 DEL 26 DE OCTUBRE DEL 2011",
    ]
    for line in header_lines:
        story.append(Paragraph(f"<b>{line}</b>", header_style))
    story.append(Spacer(1, 16))

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
            _parrafo_principal_certificado(
                ciudadano=ciudadano,
                tipo_documento=tipo_documento,
                texto_personalizado=texto_personalizado,
            ),
            body_style,
        )
    )

    emitido_local = _to_local(emitido_en_utc)
    mes = MESES_ES.get(emitido_local.month, str(emitido_local.month))
    hora = emitido_local.strftime("%I:%M %p")

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "La presente certificación se expide a solicitud del interesado (a), en la ciudad de "
            f"<b>Sincelejo, Sucre</b>, a los <b>{emitido_local.day:02d}</b> días del mes de <b>{mes}</b> del año "
            f"<b>{emitido_local.year}</b>, siendo las <b>{hora}</b>.",
            body_style,
        )
    )

    story.append(Spacer(1, SIGNATURE_TOP_SPACER))

    firma_ruta = current_app.config.get("CAPITAN_MENOR_FIRMA_RUTA")
    nombre_firma = current_app.config.get("CAPITAN_MENOR_NOMBRE") or "CAPITÁN MENOR"
    doc_tipo = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_TIPO") or ""
    doc_num = current_app.config.get("CAPITAN_MENOR_DOCUMENTO_NUMERO") or ""

    signature_flowables = []
    firma_path = _resolver_ruta_firma(firma_ruta) or (Path(current_app.root_path) / "static" / "img" / "Firma_Diomedes.png")

    if firma_path.exists():
        signature_flowables.append(Image(str(firma_path), width=180, height=80, hAlign="LEFT"))
        signature_flowables.append(Spacer(1, 1))

    signature_flowables.append(HRFlowable(width=250, thickness=1.2, color=colors.black))
    signature_flowables.append(Spacer(1, 4))

    nombre_con_doc = nombre_firma
    if doc_tipo or doc_num:
        nombre_con_doc = f"{nombre_firma}<br/>{doc_tipo} {doc_num}".strip()

    signature_flowables.append(
        Paragraph(
            nombre_con_doc,
            ParagraphStyle(
                "sig_name",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=9.5,
                leading=11,
                alignment=TA_LEFT,
            ),
        )
    )

    signature_flowables.append(
        Paragraph(
            "Capitán Menor Indígena",
            ParagraphStyle("sig_role", parent=base, fontSize=8.8, leading=10, alignment=TA_LEFT),
        )
    )

    qr_img = _qr_as_reportlab_image(verify_url)
    qr_block = [
        qr_img,
        Spacer(1, 4),
        LinkNoWrap(verify_url, verify_url, width=110, font_name="Helvetica", font_size=7.2),
        Spacer(1, 6),
        Paragraph(
            "Escanee el QR o haga clic en el enlace para validar la autenticidad y el estado de afiliación.",
            small_left,
        ),
    ]

    table = Table(
        [[signature_flowables, qr_block]],
        colWidths=[doc.width * 0.60, doc.width * 0.40],
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

    doc.build(story, onFirstPage=_dibujar_id_documento, onLaterPages=_dibujar_id_documento)
    buf.seek(0)
    return buf.getvalue()
