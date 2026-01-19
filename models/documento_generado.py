from __future__ import annotations

from datetime import datetime

from .db import db


class DocumentoGenerado(db.Model):
    """Registro (auditoría) de certificados generados.

    - Registrar fecha/hora
    - Registrar ciudadano
    - Código único para validación (QR/URL)
    - Marcar descargas
    - Guardar ruta del PDF (solo por retención temporal)
    """

    __tablename__ = "documentos_generados"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(64), unique=True, nullable=False, index=True)

    ciudadano_id = db.Column(db.Integer, db.ForeignKey("ciudadanos.id"), nullable=False, index=True)

    tipo_documento = db.Column(db.String(50), nullable=False, default="certificado_afiliacion")

    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    descargado_en = db.Column(db.DateTime, nullable=True)
    descargas = db.Column(db.Integer, nullable=False, default=0)

    # Metadatos útiles para auditoría
    ip_solicitante = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)


    # Origen de la generación: "usuario" (público) o "admin"
    generado_por = db.Column(db.String(20), nullable=False, default="usuario")

    # Para certificados especiales (Admin): texto personalizado que acompaña el certificado.
    # Se almacena como texto plano (sin HTML). El PDF se encarga de escaparlo.
    texto_personalizado = db.Column(db.Text, nullable=True)

    # Ruta del archivo generado (absoluta). No se expone al cliente.
    pdf_path = db.Column(db.String(300), nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentoGenerado {self.codigo} ciudadano_id={self.ciudadano_id}>"
