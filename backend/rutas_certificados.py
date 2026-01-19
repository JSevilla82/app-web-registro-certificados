from __future__ import annotations

import io
from datetime import datetime

from flask import Blueprint, abort, request, send_file

from backend.pdf import generar_certificado_pdf_bytes
from models import Ciudadano, DocumentoGenerado, db


certificados = Blueprint("certificados", __name__, url_prefix="/certificados")


def _obtener_doc_o_404(codigo: str) -> DocumentoGenerado:
    doc = DocumentoGenerado.query.filter_by(codigo=codigo).first()
    if not doc:
        abort(404)
    return doc


@certificados.get("/descargar/<codigo>")
def descargar_certificado(codigo: str):
    doc = _obtener_doc_o_404(codigo)

    ciudadano = db.session.get(Ciudadano, doc.ciudadano_id)
    if not ciudadano:
        abort(404)

    doc.descargas = (doc.descargas or 0) + 1
    doc.descargado_en = datetime.utcnow()
    db.session.commit()

    verify_url = f"{request.host_url.rstrip('/')}/verificar-certificados?codigo={codigo}"
    pdf_bytes = generar_certificado_pdf_bytes(
        ciudadano=ciudadano,
        codigo=codigo,
        verify_url=verify_url,
        emitido_en_utc=doc.creado_en,
        tipo_documento=getattr(doc, "tipo_documento", "certificado_afiliacion"),
        texto_personalizado=getattr(doc, "texto_personalizado", None),
    )

    filename = f"certificado_{codigo}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
        conditional=True,
    )

@certificados.get("/ver/<codigo>")
def ver_certificado(codigo: str):
    """Abre el certificado en el navegador (nueva pestaña) sin forzar descarga."""
    doc = _obtener_doc_o_404(codigo)

    ciudadano = db.session.get(Ciudadano, doc.ciudadano_id)
    if not ciudadano:
        abort(404)

    verify_url = f"{request.host_url.rstrip('/')}/verificar-certificados?codigo={codigo}"
    pdf_bytes = generar_certificado_pdf_bytes(
        ciudadano=ciudadano,
        codigo=codigo,
        verify_url=verify_url,
        emitido_en_utc=doc.creado_en,
        tipo_documento=getattr(doc, "tipo_documento", "certificado_afiliacion"),
        texto_personalizado=getattr(doc, "texto_personalizado", None),
    )

    filename = f"certificado_{codigo}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=False,
        download_name=filename,
        mimetype="application/pdf",
        conditional=True,
    )
