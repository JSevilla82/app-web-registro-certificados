from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app

from models import BloqueoVerificacion, db


def clave_bloqueo(tipo_documento: str, numero_documento: str) -> str:
    """Clave estable para aplicar bloqueos por intentos."""
    return f"{tipo_documento}:{numero_documento}"


def obtener_bloqueo(clave: str) -> BloqueoVerificacion:
    bloqueo = BloqueoVerificacion.query.filter_by(clave=clave).first()
    if bloqueo:
        return bloqueo

    bloqueo = BloqueoVerificacion(
        clave=clave,
        intentos_fallidos=0,
        bloqueado_hasta=None,
        actualizado_en=datetime.utcnow(),
    )
    db.session.add(bloqueo)
    db.session.commit()
    return bloqueo


def esta_bloqueado(clave: str) -> tuple[bool, int]:
    ahora = datetime.utcnow()
    bloqueo = obtener_bloqueo(clave)
    if bloqueo.esta_bloqueado(ahora):
        return True, bloqueo.segundos_restantes(ahora)
    return False, 0


def registrar_fallo_y_calcular_bloqueo(clave: str) -> int:
    """Incrementa intentos fallidos y retorna segundos de bloqueo a aplicar."""
    bloqueo = obtener_bloqueo(clave)
    bloqueo.intentos_fallidos = (bloqueo.intentos_fallidos or 0) + 1

    base = int(current_app.config.get("BIRTHDATE_LOCK_INITIAL_SECONDS") or 300)
    mult = float(current_app.config.get("BIRTHDATE_LOCK_MULTIPLIER") or 2)

    segundos = int(base * (mult ** (bloqueo.intentos_fallidos - 1)))

    ahora = datetime.utcnow()
    bloqueo.bloqueado_hasta = ahora + timedelta(seconds=segundos)
    bloqueo.actualizado_en = ahora
    db.session.commit()
    return segundos


def reiniciar_bloqueo(clave: str) -> None:
    bloqueo = obtener_bloqueo(clave)
    bloqueo.intentos_fallidos = 0
    bloqueo.bloqueado_hasta = None
    bloqueo.actualizado_en = datetime.utcnow()
    db.session.commit()
