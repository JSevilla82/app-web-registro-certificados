from __future__ import annotations

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .db import db


class AdminUser(db.Model):
    """Usuario para el panel Admin.

    Guardamos la contrasena como hash (nunca en texto plano).

    Incluye:
    - bloqueo por intentos fallidos
    - contrasena temporal (requiere cambio al primer inicio de sesion)
    """

    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), nullable=False)

    # Usuario de login (normalizado a minusculas)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Ultimo inicio de sesion (UTC)
    ultimo_inicio_sesion = db.Column(db.DateTime, nullable=True)

    # --- Contrasena temporal / cambio obligatorio ---
    # Si es True, al iniciar sesion se fuerza al usuario a cambiar su contrasena.
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)

    # Cuando se genero/emitio la contrasena temporal (UTC)
    temp_password_issued_at = db.Column(db.DateTime, nullable=True)

    # Cuando se establecio la contrasena final (UTC)
    password_changed_at = db.Column(db.DateTime, nullable=True)

    # --- Seguridad login ---
    # Intentos fallidos acumulados (se reinician al bloquear o al login exitoso)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)

    # Cantidad de bloqueos temporales aplicados (para incrementar tiempos)
    lockouts_count = db.Column(db.Integer, nullable=False, default=0)

    # Bloqueado hasta (UTC). Si esta en el futuro, no se permite iniciar sesion.
    lock_until = db.Column(db.DateTime, nullable=True)

    # Bloqueo permanente (requiere desbloqueo via CLI)
    permanently_locked = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, raw_password: str) -> None:
        raw_password = (raw_password or "").strip()
        if not raw_password:
            raise ValueError("La contrasena no puede estar vacia")
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not raw_password:
            return False
        return check_password_hash(self.password_hash, raw_password)

    @staticmethod
    def normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    # Helpers de bloqueo
    def is_temporarily_locked(self, now_utc: datetime) -> bool:
        return bool(self.lock_until and self.lock_until > now_utc)

    def seconds_until_unlock(self, now_utc: datetime) -> int:
        if not self.lock_until or self.lock_until <= now_utc:
            return 0
        return int((self.lock_until - now_utc).total_seconds())

    def __repr__(self) -> str:
        return f"<AdminUser {self.username}>"
