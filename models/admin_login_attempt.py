from __future__ import annotations

"""Estado de intentos de login Admin para usuarios *no existentes*.

Motivo:
- Por seguridad, el UI muestra un mensaje genérico cuando falla el login.
- Antes, el bloqueo progresivo solo aplicaba si el usuario existía en
  `admin_users`. Si el usuario se tecleaba mal, nunca se activaba el bloqueo.

Este modelo guarda un estado por (username_normalizado, ip) para poder aplicar
el mismo esquema de intentos/bloqueo aun cuando el usuario no exista.
"""

from datetime import datetime

from .db import db


class AdminLoginAttempt(db.Model):
    __tablename__ = "admin_login_attempts"

    id = db.Column(db.Integer, primary_key=True)

    # Username normalizado (minúsculas)
    username = db.Column(db.String(80), nullable=False, index=True)

    # IP (remote address) para reducir DoS por usernames arbitrarios
    ip = db.Column(db.String(64), nullable=False, index=True)

    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    lockouts_count = db.Column(db.Integer, nullable=False, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("username", "ip", name="uq_admin_attempts_user_ip"),
    )

    def is_temporarily_locked(self, now_utc: datetime) -> bool:
        return bool(self.lock_until and self.lock_until > now_utc)

    def seconds_until_unlock(self, now_utc: datetime) -> int:
        if not self.lock_until or self.lock_until <= now_utc:
            return 0
        return int((self.lock_until - now_utc).total_seconds())

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
