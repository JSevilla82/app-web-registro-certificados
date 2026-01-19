from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from zoneinfo import ZoneInfo

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import Ciudadano, DocumentoGenerado, db
 


TOKEN_SALT = "cabildo-verification-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def generar_token_verificacion(ciudadano_id: int) -> str:
    return _serializer().dumps({"ciudadano_id": ciudadano_id})


def validar_token_verificacion(token: str, max_age_seconds: int) -> int:
    try:
        data = _serializer().loads(token, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise ValueError("La verificación expiró. Por favor, realice la consulta nuevamente.") from e
    except BadSignature as e:
        raise ValueError("Token de verificación inválido.") from e

    ciudadano_id = data.get("ciudadano_id")
    if not isinstance(ciudadano_id, int):
        raise ValueError("Token de verificación inválido.")
    return ciudadano_id


def _nuevo_codigo_unico() -> str:
    """Genera un código fácil de transcribir y prácticamente no repetible.

    Formato: CIP + YYYYMMDD + HHMMSS + 4 dígitos aleatorios
    Ejemplo: CIP202601111530451234

    Se valida contra la BD para evitar colisiones.
    """
    for _ in range(20):
        ahora = datetime.utcnow()
        codigo = f"CIP{ahora.strftime('%Y%m%d')}{ahora.strftime('%H%M%S')}{secrets.randbelow(10000):04d}"
        if not DocumentoGenerado.query.filter_by(codigo=codigo).first():
            return codigo

    # Fallback extremadamente improbable
    ahora = datetime.utcnow()
    return f"CIP{ahora.strftime('%Y%m%d')}{ahora.strftime('%H%M%S')}{secrets.randbelow(1000000):06d}"



def _tz() -> ZoneInfo:
    tz_name = current_app.config.get("APP_TIMEZONE") or "America/Bogota"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("America/Bogota")


def _hoy_utc_rango() -> tuple[datetime, datetime]:
    """Rango [inicio, fin) del día local, convertido a UTC naive.

    Guardamos en BD con datetime naive en UTC. Para agrupar por día local,
    calculamos el inicio/fin del día en la zona horaria del proyecto.
    """
    tz = _tz()
    ahora_local = datetime.now(tz)
    inicio_local = ahora_local.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_local = inicio_local + timedelta(days=1)
    inicio_utc = inicio_local.astimezone(timezone.utc).replace(tzinfo=None)
    fin_utc = fin_local.astimezone(timezone.utc).replace(tzinfo=None)
    return inicio_utc, fin_utc


def obtener_certificado_del_dia(
    ciudadano_id: int,
    generado_por: Optional[str] = None,
    tipo_documento: Optional[str] = None,
) -> Optional[DocumentoGenerado]:
    """Retorna el certificado del día (según zona horaria del proyecto) si existe.

    Si se especifica `generado_por`, el certificado del día se calcula por (ciudadano, día, origen).
    """
    inicio_utc, fin_utc = _hoy_utc_rango()

    q = (
        DocumentoGenerado.query
        .filter(DocumentoGenerado.ciudadano_id == ciudadano_id)
        .filter(DocumentoGenerado.creado_en >= inicio_utc)
        .filter(DocumentoGenerado.creado_en < fin_utc)
    )

    if generado_por:
        q = q.filter(DocumentoGenerado.generado_por == generado_por)

    if tipo_documento:
        q = q.filter(DocumentoGenerado.tipo_documento == tipo_documento)

    return q.order_by(DocumentoGenerado.creado_en.desc()).first()



def generar_o_reutilizar_certificado(
    ciudadano: Ciudadano,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    generado_por: str = "usuario",
    tipo_documento: str = "certificado_afiliacion",
    texto_personalizado: Optional[str] = None,
    allow_reuse: bool = True,
) -> Tuple[DocumentoGenerado, bool]:
    """Crea (una vez por día) el registro del certificado o reutiliza el del día.

    Cambios solicitados:
    - Ya NO se guarda el PDF en disco.
    - El certificado se reutiliza durante el día en curso (zona horaria del proyecto).
    - Al cambiar de fecha, se genera uno nuevo (nuevo código).
    """
    if allow_reuse:
        del_dia = obtener_certificado_del_dia(ciudadano.id, generado_por=generado_por, tipo_documento=tipo_documento)
        if del_dia:
            return del_dia, True

    codigo = _nuevo_codigo_unico()

    doc = DocumentoGenerado(
        codigo=codigo,
        ciudadano_id=ciudadano.id,
        generado_por=generado_por,
        tipo_documento=tipo_documento,
        texto_personalizado=texto_personalizado,
        ip_solicitante=ip,
        user_agent=(user_agent[:255] if user_agent else None),
        # Mantener columna existente (SQLite) sin guardar archivo real.
        pdf_path="",
        creado_en=datetime.utcnow(),
    )
    db.session.add(doc)
    db.session.commit()

    return doc, False


def normalizar_texto_especial(texto: str) -> str:
    """Normaliza el texto de un certificado especial.

    - Trim
    - Quita espacios repetidos
    - Primera letra en mayúscula
    """
    t = (texto or "").strip()
    # Colapsar espacios, manteniendo saltos de línea como espacios
    t = " ".join(t.split())
    if t:
        t = t[0].upper() + t[1:]
    return t


def generar_certificado_especial(
    ciudadano: Ciudadano,
    texto_personalizado: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    generado_por: str = "admin",
) -> DocumentoGenerado:
    """Crea un certificado especial (sin reutilizar por día).

    Estos certificados incluyen un texto personalizado y se registran con:
    tipo_documento='certificado_especial'.
    """

    codigo = _nuevo_codigo_unico()
    t = normalizar_texto_especial(texto_personalizado)

    doc = DocumentoGenerado(
        codigo=codigo,
        ciudadano_id=ciudadano.id,
        generado_por=generado_por,
        tipo_documento="certificado_especial",
        texto_personalizado=t,
        ip_solicitante=ip,
        user_agent=(user_agent[:255] if user_agent else None),
        pdf_path="",
        creado_en=datetime.utcnow(),
    )
    db.session.add(doc)
    db.session.commit()
    return doc
