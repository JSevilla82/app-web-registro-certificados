"""Lógica de negocio / procesamiento de datos.

La idea es mantener app.py delgado: rutas + renderizado.
Aquí dejamos las consultas, validaciones y (opcional) seed de desarrollo.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

from models import db, Ciudadano


DOC_TYPES_PERMITIDOS = {"CC", "TI"}


def normalizar_documento(tipo: str | None, numero: str | None) -> Tuple[str, str]:
    """Valida y normaliza inputs.

    - tipo: se recorta y se pasa a mayúsculas
    - numero: se recorta; se deja tal cual para no perder ceros, etc.
    """
    tipo = (tipo or "").strip().upper()
    numero = (numero or "").strip()

    if not tipo:
        raise ValueError("Debe seleccionar el tipo de documento.")
    if tipo not in DOC_TYPES_PERMITIDOS:
        raise ValueError("Tipo de documento no válido.")
    if not numero:
        raise ValueError("Debe ingresar el número de documento.")

    if not numero.isdigit():
        raise ValueError("El número de documento debe contener solo números.")
    if len(numero) < 5 or len(numero) > 20:
        raise ValueError("Longitud del número de documento no válida.")

    return tipo, numero


def buscar_por_documento(tipo: str, numero: str) -> Optional[Ciudadano]:
    """Busca ciudadano en base al tipo y número."""
    return Ciudadano.query.filter_by(tipo_documento=tipo, numero_documento=numero).first()


def seed_si_vacia() -> None:
    """Crea datos mínimos de prueba si no hay registros.

    Útil para desarrollo/demos. En producción, normalmente se desactiva.
    """
    if Ciudadano.query.first():
        return

    test_user = Ciudadano(
        nombre_completo="Juan Pérez García",
        fecha_nacimiento=date(1990, 5, 15),
        tipo_documento="CC",
        numero_documento="12345678",
    )
    db.session.add(test_user)
    db.session.commit()
