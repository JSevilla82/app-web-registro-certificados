from __future__ import annotations

from datetime import datetime

from .db import db


class BloqueoVerificacion(db.Model):
    """Control de intentos para la verificación de fecha de nacimiento.

    - Se bloquea por un tiempo si el usuario falla el reto.
    - El tiempo de bloqueo crece exponencialmente según configuración.
    """

    __tablename__ = "bloqueos_verificacion"

    id = db.Column(db.Integer, primary_key=True)

    # Clave estable: tipo:num
    clave = db.Column(db.String(64), unique=True, nullable=False, index=True)

    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0)

    bloqueado_hasta = db.Column(db.DateTime, nullable=True)

    actualizado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def esta_bloqueado(self, ahora: datetime) -> bool:
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > ahora)

    def segundos_restantes(self, ahora: datetime) -> int:
        if not self.bloqueado_hasta or self.bloqueado_hasta <= ahora:
            return 0
        return int((self.bloqueado_hasta - ahora).total_seconds())
