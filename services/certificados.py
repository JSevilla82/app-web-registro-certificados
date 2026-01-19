"""Servicios para generación y validación de certificados.

Incluye:
- Tokens temporales (firmados) para separar el paso de verificación del paso de generación.
- Generación de PDF 100% del lado del servidor.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import current_app, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import Ciudadano, DocumentoGenerado, db
from services.pdf_generator import generar_certificado_pdf


TOKEN_SALT = "cabildo-verification-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def generar_token_verificacion(ciudadano_id: int) -> str:
    """Crea un token firmado que expira (max_age) y habilita la generación."""
    return _serializer().dumps({"ciudadano_id": ciudadano_id})


def validar_token_verificacion(token: str, max_age_seconds: int) -> int:
    """Valida token y retorna ciudadano_id. Lanza ValueError si es inválido."""
    try:
        data = _serializer().loads(token, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise ValueError("La verificación expiró. Por favor, realice la consulta nuevamente.") from e
    except BadSignature as e:
        raise ValueError("Token de verificación inválido.") from e

    ciudadano_id = data.get("ciudadano_id")
    if not isinstance(ciudadano_id, int):
        raise ValueError("Token de verificación inválido.")
    return ciudadano_id


def _nuevo_codigo_unico() -> str:
    for _ in range(5):
        code = secrets.token_urlsafe(16)
        if not DocumentoGenerado.query.filter_by(codigo=code).first():
            return code
    return secrets.token_urlsafe(24)


def generar_certificado_para_ciudadano(
    ciudadano: Ciudadano,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> DocumentoGenerado:
    """Genera el PDF y crea el registro en la base de datos."""
    certificados_dir = Path(current_app.config.get("CERTIFICADOS_DIR") or "generated")
    certificados_dir.mkdir(parents=True, exist_ok=True)

    codigo = _nuevo_codigo_unico()
    # URL pública que irá en el QR y también impresa debajo (clickeable)
    verify_url = url_for("validar_documento", codigo=codigo, _external=True)
    filename = f"certificado_{codigo}.pdf"
    pdf_path = str((certificados_dir / filename).resolve())

    # 1) Registrar en DB (estado: creado) para auditoría
    doc = DocumentoGenerado(
        codigo=codigo,
        ciudadano_id=ciudadano.id,
        ip_solicitante=ip,
        user_agent=(user_agent[:255] if user_agent else None),
        pdf_path=pdf_path,
        creado_en=datetime.utcnow(),
    )
    db.session.add(doc)
    db.session.commit()

    # 2) Generar PDF en el servidor
    #    Nota: si falla, eliminamos el registro.
    try:
        generar_certificado_pdf(ciudadano=ciudadano, codigo=doc.codigo, verify_url=verify_url, out_path=pdf_path)
    except Exception:
        db.session.delete(doc)
        db.session.commit()
        # Intento de limpieza del archivo si alcanzó a crearse
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
        raise

    return doc
