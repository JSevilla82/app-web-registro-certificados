from __future__ import annotations

import os
from datetime import datetime, timedelta

from flask import current_app

from models import DocumentoGenerado, db


def limpiar_pdfs_expirados() -> int:
    """Elimina archivos PDF de certificados cuya ventana de retención ya venció.

    Mantiene el registro en la base de datos para verificación histórica.
    Retorna cantidad de archivos eliminados.
    """
    horas = int(current_app.config.get("CERT_FILE_RETENTION_HOURS") or 24)
    ventana = datetime.utcnow() - timedelta(hours=horas)

    eliminados = 0
    docs = DocumentoGenerado.query.filter(DocumentoGenerado.creado_en < ventana).all()
    for doc in docs:
        try:
            if doc.pdf_path and os.path.exists(doc.pdf_path):
                os.remove(doc.pdf_path)
                eliminados += 1
        except Exception:
            pass

    if eliminados:
        db.session.commit()

    return eliminados
