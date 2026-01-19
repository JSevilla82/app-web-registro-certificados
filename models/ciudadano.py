from __future__ import annotations

import uuid
from datetime import datetime

from .db import db


class Ciudadano(db.Model):
    __tablename__ = "ciudadanos"

    id = db.Column(db.Integer, primary_key=True)

    # Identificador aleatorio (compatibilidad/histórico)
    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    nombre_completo = db.Column(db.String(150), nullable=False)
    tipo_documento = db.Column(db.String(10), nullable=False)

    # Index para búsquedas rápidas
    numero_documento = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # Nuevo: fecha de nacimiento para validación adicional
    fecha_nacimiento = db.Column(db.Date, nullable=True)

    # Nuevo: estado del usuario en el censo (activo/inactivo)
    # Por defecto, todo registro existente se considera activo.
    activo = db.Column(db.Boolean, nullable=False, default=True)

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Ciudadano {self.numero_documento} - {self.nombre_completo}>"

    def to_dict(self) -> dict:
        return {
            "public_id": self.public_id,
            "nombre": self.nombre_completo,
            "tipo_doc": self.tipo_documento,
            # Documento enmascarado (evita filtrar dato completo al frontend)
            "num_doc_mask": f"********{self.numero_documento[-3:]}",
            "activo": bool(self.activo),
        }
