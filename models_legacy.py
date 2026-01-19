import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Ciudadano(db.Model):
    __tablename__ = 'ciudadanos'
    
    id = db.Column(db.Integer, primary_key=True)
    # Identificador único aleatorio para la URL pública del certificado y QR
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    nombre_completo = db.Column(db.String(150), nullable=False)
    tipo_documento = db.Column(db.String(10), nullable=False)
    
    # Nota: se indexa para búsquedas rápidas en /api/verificar.
    numero_documento = db.Column(db.String(20), unique=True, nullable=False, index=True)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Ciudadano {self.numero_documento} - {self.nombre_completo}>'

    def to_dict(self):
        return {
            "public_id": self.public_id,
            "nombre": self.nombre_completo,
            "tipo_doc": self.tipo_documento,
            # Mostramos el documento enmascarado por seguridad en la vista previa
            "num_doc_mask": f"********{self.numero_documento[-3:]}"
        }


class DocumentoGenerado(db.Model):
    """Registro (auditoría) de certificados generados.

    Requisitos que cubre:
    - Registrar fecha/hora
    - Registrar quién lo generó (ciudadano)
    - Código único para validación (QR/URL)
    - Marcar cuándo se descargó y cuántas veces
    """

    __tablename__ = "documentos_generados"

    id = db.Column(db.Integer, primary_key=True)

    # Código único (se usa en QR y en la URL pública de verificación)
    codigo = db.Column(db.String(64), unique=True, nullable=False, index=True)

    ciudadano_id = db.Column(db.Integer, db.ForeignKey("ciudadanos.id"), nullable=False, index=True)
    ciudadano = db.relationship("Ciudadano", backref=db.backref("documentos", lazy=True))

    tipo_documento = db.Column(db.String(50), nullable=False, default="certificado_afiliacion")

    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    descargado_en = db.Column(db.DateTime, nullable=True)
    descargas = db.Column(db.Integer, nullable=False, default=0)

    # Metadatos útiles para auditoría
    ip_solicitante = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    # Ruta del archivo generado (relativa o absoluta). No se expone al cliente.
    pdf_path = db.Column(db.String(300), nullable=False)

    def __repr__(self):
        return f"<DocumentoGenerado {self.codigo} ciudadano_id={self.ciudadano_id}>"