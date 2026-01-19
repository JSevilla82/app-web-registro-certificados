from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

from models import Ciudadano, db


# Tipos de documento permitidos en el sistema.
# CC: Cédula de ciudadanía
# TI: Tarjeta de identidad
# RC: Registro civil
TIPOS_DOCUMENTO_PERMITIDOS = {"CC", "TI", "RC"}


def normalizar_documento(tipo: str | None, numero: str | None) -> Tuple[str, str]:
    """Valida y normaliza tipo/número."""
    tipo_norm = (tipo or "").strip().upper()
    numero_norm = (numero or "").strip()

    if not tipo_norm:
        raise ValueError("Debe seleccionar el tipo de documento.")
    if tipo_norm not in TIPOS_DOCUMENTO_PERMITIDOS:
        raise ValueError("Tipo de documento no válido.")
    if not numero_norm:
        raise ValueError("Debe ingresar el número de documento.")

    if not numero_norm.isdigit():
        raise ValueError("El número de documento debe contener solo números.")
    if len(numero_norm) < 5 or len(numero_norm) > 20:
        raise ValueError("Longitud del número de documento no válida.")

    return tipo_norm, numero_norm


def buscar_por_documento(tipo: str, numero: str) -> Optional[Ciudadano]:
    """Búsqueda para la app: solo ciudadanos activos.

    Requerimiento: si el ciudadano está inactivo, para la app debe comportarse
    como si no existiera ("no fue encontrado").
    """
    return (
        Ciudadano.query.filter_by(
            tipo_documento=tipo,
            numero_documento=numero,
            activo=True,
        ).first()
    )


def buscar_por_documento_incluyendo_inactivos(tipo: str, numero: str) -> Optional[Ciudadano]:
    """Búsqueda administrativa/consulta: incluye inactivos."""
    return Ciudadano.query.filter_by(tipo_documento=tipo, numero_documento=numero).first()


def seed_si_vacia() -> None:
    """Datos de prueba (solo desarrollo)."""
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
