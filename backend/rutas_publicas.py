from __future__ import annotations

import io
from datetime import datetime, timezone

from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, redirect, render_template, request, send_file, url_for

from backend.pdf import generar_copia_verificacion_pdf_bytes

from models import Ciudadano, DocumentoGenerado, db


publico = Blueprint("publico", __name__)


@publico.get("/validar/<codigo>")
def validar_documento(codigo: str):
    """Compatibilidad para URLs antiguas del QR.

    Ahora la verificación vive en una pestaña dedicada.
    """
    return redirect(url_for("publico.verificar_certificados", codigo=codigo), code=302)


@publico.get("/verificar-certificados")
def verificar_certificados():
    """Página para verificación manual y por enlace/QR."""
    codigo = (request.args.get("codigo") or "").strip()

    if not codigo:
        return render_template(
            "verificar_certificados.html",
            active="verificar",
            codigo="",
            found=None,
            show_loader=False,
        )

    doc = DocumentoGenerado.query.filter_by(codigo=codigo).first()
    if not doc:
        return render_template(
            "verificar_certificados.html",
            active="verificar",
            codigo=codigo,
            found=False,
            show_loader=True,
        ), 404

    ciudadano = db.session.get(Ciudadano, doc.ciudadano_id)
    if not ciudadano:
        return render_template(
            "verificar_certificados.html",
            active="verificar",
            codigo=codigo,
            found=False,
            show_loader=True,
        ), 404

    disponible = True

    tz_name = current_app.config.get("APP_TIMEZONE") or "America/Bogota"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Bogota")
    emitido_local = (doc.creado_en.replace(tzinfo=timezone.utc).astimezone(tz))
    emision_str = emitido_local.strftime('%d/%m/%Y %I:%M %p')

    return render_template(
        "verificar_certificados.html",
        active="verificar",
        codigo=codigo,
        found=True,
        c=ciudadano,
        doc=doc,
        ver_doc_disponible=disponible,
        ver_doc_url=f"/validar/{doc.codigo}/documento" if disponible else None,
        emision_str=emision_str,
        show_loader=True,
    )


@publico.get("/validar/<codigo>/documento")
def ver_documento_verificacion(codigo: str):
    """Retorna una copia del certificado para verificación pública.

    Esta copia se genera al momento de la consulta e incluye marca de verificación.
    El registro se conserva en la base de datos para verificación cuando se requiera.
    """
    doc = DocumentoGenerado.query.filter_by(codigo=codigo).first()
    if not doc:
        return render_template("verificacion_publica.html", found=False), 404

    ciudadano = db.session.get(Ciudadano, doc.ciudadano_id)
    if not ciudadano:
        return render_template("verificacion_publica.html", found=False), 404

    verify_url = f"{request.host_url.rstrip('/')}/verificar-certificados?codigo={codigo}"
    pdf_bytes = generar_copia_verificacion_pdf_bytes(
        ciudadano=ciudadano,
        codigo=codigo,
        verify_url=verify_url,
        consultado_en=datetime.now(),
        emitido_en_utc=doc.creado_en,
        tipo_documento=getattr(doc, "tipo_documento", "certificado_afiliacion"),
        texto_personalizado=getattr(doc, "texto_personalizado", None),
    )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"verificacion_{codigo}.pdf",
        conditional=True,
    )
