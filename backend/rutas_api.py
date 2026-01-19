from __future__ import annotations

from flask import Blueprint, jsonify, request, session

import config
from backend.ciudadanos import buscar_por_documento, normalizar_documento
from backend.certificados import (
    generar_certificado_especial,
    generar_o_reutilizar_certificado,
    generar_token_verificacion,
    normalizar_texto_especial,
    validar_token_verificacion,
)
from backend.verificacion_fecha_nacimiento import (
    clave_bloqueo,
    esta_bloqueado,
    registrar_fallo_y_calcular_bloqueo,
    reiniciar_bloqueo,
)
from models import Ciudadano, db


api = Blueprint("api", __name__, url_prefix="/api")


def _json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@api.post("/verificar")
def api_verificar_ciudadano():
    data = _json()
    try:
        tipo, numero = normalizar_documento(data.get("tipo"), data.get("numero"))
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    ciudadano = buscar_por_documento(tipo, numero)
    if not ciudadano:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404

    # Si existe fecha de nacimiento, requerimos validación adicional (ingreso directo de la fecha)
    if ciudadano.fecha_nacimiento:
        clave = clave_bloqueo(tipo, numero)
        bloqueado, segundos = esta_bloqueado(clave)
        if bloqueado:
            return (
                jsonify(
                    {
                        "success": False,
                        "locked": True,
                        "retry_after_seconds": segundos,
                        "message": "Por seguridad, debe esperar antes de intentar nuevamente.",
                    }
                ),
                429,
            )

        return jsonify(
            {
                "success": True,
                "requires_birthdate": True,
                "data": ciudadano.to_dict(),
            }
        )

    token = generar_token_verificacion(ciudadano.id)
    return jsonify(
        {
            "success": True,
            "data": ciudadano.to_dict(),
            "token": token,
            "token_expires_in": config.VERIFY_TOKEN_MAX_AGE_SECONDS,
        }
    )


@api.post("/verificar/fecha-nacimiento")
def api_verificar_fecha_nacimiento():
    data = _json()
    fecha_iso = (data.get("birthdate") or "").strip()
    try:
        tipo, numero = normalizar_documento(data.get("tipo"), data.get("numero"))
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    if not fecha_iso:
        return jsonify({"success": False, "message": "Debe ingresar la fecha de nacimiento."}), 400

    ciudadano = buscar_por_documento(tipo, numero)
    if not ciudadano:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404

    clave = clave_bloqueo(tipo, numero)
    bloqueado, segundos_bloqueo = esta_bloqueado(clave)
    if bloqueado:
        return (
            jsonify(
                {
                    "success": False,
                    "locked": True,
                    "retry_after_seconds": segundos_bloqueo,
                    "message": "Por seguridad, debe esperar antes de intentar nuevamente.",
                }
            ),
            429,
        )

    correcto = bool(ciudadano.fecha_nacimiento and ciudadano.fecha_nacimiento.isoformat() == fecha_iso)
    if not correcto:
        segundos = registrar_fallo_y_calcular_bloqueo(clave)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "La fecha ingresada no coincide. Por seguridad, debe esperar antes de reintentar.",
                    "retry_after_seconds": segundos,
                }
            ),
            403,
        )

    reiniciar_bloqueo(clave)

    token = generar_token_verificacion(ciudadano.id)
    return jsonify(
        {
            "success": True,
            "data": ciudadano.to_dict(),
            "token": token,
            "token_expires_in": config.VERIFY_TOKEN_MAX_AGE_SECONDS,
        }
    )


@api.post("/certificados/generar")
def api_generar_certificado():
    data = _json()
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify({"success": False, "message": "Falta token de verificación."}), 400

    try:
        ciudadano_id = validar_token_verificacion(token, config.VERIFY_TOKEN_MAX_AGE_SECONDS)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    ciudadano = db.session.get(Ciudadano, ciudadano_id)
    if not ciudadano or not getattr(ciudadano, "activo", True):
        # Requerimiento: si está inactivo, la app lo trata como "no encontrado"
        return jsonify({"success": False, "message": "Ciudadano no encontrado."}), 404

    try:
        doc, reutilizado = generar_o_reutilizar_certificado(
            ciudadano=ciudadano,
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            tipo_documento="certificado_afiliacion",
        )
    except Exception:
        return jsonify({"success": False, "message": "No se pudo generar el certificado."}), 500

    return jsonify(
        {
            "success": True,
            "codigo": doc.codigo,
            "recently_generated": reutilizado,
            "download_url": f"/certificados/descargar/{doc.codigo}",
            "view_url": f"/certificados/ver/{doc.codigo}",
            "verify_url": f"/verificar-certificados?codigo={doc.codigo}",
        }
    )


@api.post("/admin/certificados/generar")
def api_admin_generar_certificado():
    """Genera certificado como administrador (sin validar fecha de nacimiento).

    Requiere sesión admin activa.
    Entrada JSON: {"numero": "..."} (solo dígitos).
    """
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "No autorizado."}), 401
    if session.get("admin_force_password_change"):
        return jsonify({"success": False, "message": "Debe cambiar la contraseña antes de continuar."}), 403

    data = _json()
    raw_numero = (data.get("numero") or "").strip()
    numero = "".join([c for c in raw_numero if c.isdigit()])

    if not numero:
        return jsonify({"success": False, "message": "Debe ingresar el número de documento."}), 400
    if len(numero) < 5 or len(numero) > 20:
        return jsonify({"success": False, "message": "Longitud del número de documento no válida."}), 400

    # Búsqueda por número sin exigir tipo (admin)
    ciudadanos = Ciudadano.query.filter_by(numero_documento=numero, activo=True).all()
    if not ciudadanos:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404
    if len(ciudadanos) > 1:
        return jsonify(
            {
                "success": False,
                "message": "Se encontraron múltiples registros con ese número. Contacte al Cabildo para asistencia.",
            }
        ), 409

    ciudadano = ciudadanos[0]

    try:
        doc, reutilizado = generar_o_reutilizar_certificado(
            ciudadano=ciudadano,
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            generado_por="admin",
            tipo_documento="certificado_afiliacion",
        )
    except Exception:
        return jsonify({"success": False, "message": "No se pudo generar el certificado."}), 500

    return jsonify(
        {
            "success": True,
            "codigo": doc.codigo,
            "recently_generated": reutilizado,
            "data": ciudadano.to_dict(),
            "download_url": f"/certificados/descargar/{doc.codigo}",
            "view_url": f"/certificados/ver/{doc.codigo}",
            "verify_url": f"/verificar-certificados?codigo={doc.codigo}",
        }
    )


@api.post("/admin/certificados/validar")
def api_admin_validar_ciudadano_para_certificado():
    """Valida existencia/afiliación para generar certificado (Admin).

    Entrada JSON: {"numero": "..."}
    """
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "No autorizado."}), 401
    if session.get("admin_force_password_change"):
        return jsonify({"success": False, "message": "Debe cambiar la contraseña antes de continuar."}), 403

    data = _json()
    raw_numero = (data.get("numero") or "").strip()
    numero = "".join([c for c in raw_numero if c.isdigit()])

    if not numero:
        return jsonify({"success": False, "message": "Debe ingresar el número de documento."}), 400
    if len(numero) < 5 or len(numero) > 20:
        return jsonify({"success": False, "message": "Longitud del número de documento no válida."}), 400

    ciudadanos = Ciudadano.query.filter_by(numero_documento=numero, activo=True).all()
    if not ciudadanos:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404
    if len(ciudadanos) > 1:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Se encontraron múltiples registros con ese número. Contacte al Cabildo para asistencia.",
                }
            ),
            409,
        )

    return jsonify({"success": True, "data": ciudadanos[0].to_dict()})


@api.post("/admin/certificados/especial/validar")
def api_admin_validar_ciudadano_para_especial():
    """Valida existencia/afiliación para certificado especial (Admin).

    Entrada JSON: {"numero": "..."}
    """
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "No autorizado."}), 401
    if session.get("admin_force_password_change"):
        return jsonify({"success": False, "message": "Debe cambiar la contraseña antes de continuar."}), 403

    data = _json()
    raw_numero = (data.get("numero") or "").strip()
    numero = "".join([c for c in raw_numero if c.isdigit()])

    if not numero:
        return jsonify({"success": False, "message": "Debe ingresar el número de documento."}), 400
    if len(numero) < 5 or len(numero) > 20:
        return jsonify({"success": False, "message": "Longitud del número de documento no válida."}), 400

    ciudadanos = Ciudadano.query.filter_by(numero_documento=numero, activo=True).all()
    if not ciudadanos:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404
    if len(ciudadanos) > 1:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Se encontraron múltiples registros con ese número. Contacte al Cabildo para asistencia.",
                }
            ),
            409,
        )

    return jsonify({"success": True, "data": ciudadanos[0].to_dict()})


@api.post("/admin/certificados/especial/generar")
def api_admin_generar_certificado_especial():
    """Genera un certificado especial (Admin) con texto personalizado.

    Entrada JSON: {"numero": "...", "texto": "..."}
    """
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "No autorizado."}), 401
    if session.get("admin_force_password_change"):
        return jsonify({"success": False, "message": "Debe cambiar la contraseña antes de continuar."}), 403

    data = _json()
    raw_numero = (data.get("numero") or "").strip()
    numero = "".join([c for c in raw_numero if c.isdigit()])
    texto_raw = (data.get("texto") or "").strip()

    if not numero:
        return jsonify({"success": False, "message": "Debe ingresar el número de documento."}), 400
    if len(numero) < 5 or len(numero) > 20:
        return jsonify({"success": False, "message": "Longitud del número de documento no válida."}), 400

    texto = normalizar_texto_especial(texto_raw)
    if not texto:
        return jsonify({"success": False, "message": "Debe ingresar el texto personalizado del certificado."}), 400
    if len(texto) > 1200:
        return jsonify({"success": False, "message": "El texto es demasiado largo. Redúzcalo e intente de nuevo."}), 400

    ciudadanos = Ciudadano.query.filter_by(numero_documento=numero, activo=True).all()
    if not ciudadanos:
        return jsonify({"success": False, "message": "Ciudadano no encontrado en el censo."}), 404
    if len(ciudadanos) > 1:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Se encontraron múltiples registros con ese número. Contacte al Cabildo para asistencia.",
                }
            ),
            409,
        )

    ciudadano = ciudadanos[0]

    try:
        doc = generar_certificado_especial(
            ciudadano=ciudadano,
            texto_personalizado=texto,
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            generado_por="admin",
        )
    except Exception:
        return jsonify({"success": False, "message": "No se pudo generar el certificado."}), 500

    return jsonify(
        {
            "success": True,
            "codigo": doc.codigo,
            "data": ciudadano.to_dict(),
            "tipo": "especial",
            "download_url": f"/certificados/descargar/{doc.codigo}",
            "view_url": f"/certificados/ver/{doc.codigo}",
            "verify_url": f"/verificar-certificados?codigo={doc.codigo}",
        }
    )
