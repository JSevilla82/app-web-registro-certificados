"""Aplicación Flask — Cabildo Indígena de la Peñata.

app.py mantiene lo esencial:
- Crear la app
- Cargar configuración
- Inicializar extensiones
- Registrar blueprints
- Rutas de templates
"""

from __future__ import annotations

import os
import math
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from backend import api as api_bp
from backend import certificados as certificados_bp
from backend import publico as publico_bp
from backend.ciudadanos import seed_si_vacia
from models import init_db
from models import AdminUser, AdminLoginAttempt, Ciudadano, DocumentoGenerado, db
from models.migraciones import asegurar_tablas


def crear_app() -> Flask:
    load_dotenv(override=False)

    app = Flask(__name__)
    app.config.from_object(config)

    # Directorios
    os.makedirs(str(config.DATABASE_DIR), exist_ok=True)
    os.makedirs(str(config.CERTIFICADOS_DIR), exist_ok=True)

    # BD
    init_db(app)

    # ProxyFix (si está detrás de un proxy)
    if config.TRUST_PROXY_HEADERS:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # CSRF (configurable desde .env)
    if config.ENABLE_CSRF:
        csrf = CSRFProtect()
        csrf.init_app(app)

        @app.errorhandler(CSRFError)
        def handle_csrf_error(e):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Token CSRF inválido. Recargue la página e intente de nuevo."}), 400
            return render_template("index.html"), 400

    # Rate limiting (configurable desde .env)
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=config.RATELIMIT_DEFAULTS,
        storage_uri=os.getenv("RATELIMIT_STORAGE_URL", "memory://"),
        enabled=config.ENABLE_RATELIMIT,
    )

    # Headers de seguridad (configurable desde .env)
    if config.ENABLE_SECURITY_HEADERS:
        Talisman(
            app,
            force_https=config.FORCE_HTTPS,
            strict_transport_security=config.FORCE_HTTPS,
            content_security_policy=None,
        )

    @app.context_processor
    def inject_now():
        return {
            "now": datetime.now(),
            "ui_min_transition_seconds": getattr(config, "UI_MIN_TRANSITION_SECONDS", 2),
        }

    with app.app_context():
        asegurar_tablas()
        if config.SEED_ON_START:
            seed_si_vacia()
        # Ya no se eliminan certificados por retención: se mantienen en BD y se regeneran en el momento.

    # Blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(certificados_bp)
    app.register_blueprint(publico_bp)

    # Páginas (templates)
    @app.get("/")
    def home():
        return render_template("index.html", active="inicio")

    @app.get("/certificado")
    def certificado():
        return render_template("certificado.html", active="certificado")

    # --- Admin (UI placeholder) ---
    def _require_admin():
        """Protege rutas admin.
        - Requiere sesión admin.
        - Si hay cambio de contraseña pendiente, fuerza el flujo.
        """

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        if session.get("admin_force_password_change"):
            return redirect(url_for("admin_change_password"))

        return None

    def _set_admin_flash(kind: str, text: str) -> None:
        session["admin_flash"] = {"kind": kind, "text": text}

    def _pop_admin_flash():
        return session.pop("admin_flash", None)

    @app.get("/admin")
    def admin_root():
        return redirect(url_for("admin_login"))

    @app.get("/admin/login")
    def admin_login():
        # Si ya esta logueado, enviar al panel (o forzar cambio de contrasena)
        if session.get("admin_logged_in"):
            if session.get("admin_force_password_change"):
                return redirect(url_for("admin_change_password"))
            return redirect(url_for("admin_panel"))
        return render_template("admin_login.html", active="admin")

    @app.post("/admin/login")
    @limiter.limit(getattr(config, "ADMIN_LOGIN_RATELIMIT", "10 per minute"))
    def admin_login_post():
        raw_username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        username = AdminUser.normalize_username(raw_username)

        if not username or not password:
            return (
                render_template(
                    "admin_login.html",
                    active="admin",
                    error="Debe ingresar usuario y contraseña.",
                    username=raw_username,
                ),
                400,
            )

        user = AdminUser.query.filter_by(username=username).first()
        ip = get_remote_address() or "unknown"

        # --- Seguridad de login ---
        ahora = datetime.utcnow()
        # Si el usuario NO existe, también aplicamos bloqueo progresivo (por username+IP)
        # para evitar que un simple typo deje la protección "inactiva".
        if not user:
            attempt = AdminLoginAttempt.query.filter_by(username=username, ip=ip).first()
            if not attempt:
                attempt = AdminLoginAttempt(username=username, ip=ip)
                db.session.add(attempt)
                db.session.commit()

            # Bloqueo temporal (para usuario inexistente)
            if attempt.is_temporarily_locked(ahora):
                secs = attempt.seconds_until_unlock(ahora)
                mins = max(1, int(math.ceil(secs / 60)))
                attempt.touch()
                db.session.commit()
                return (
                    render_template(
                        "admin_login.html",
                        active="admin",
                        error=(
                            f"Demasiados intentos fallidos. Por seguridad, este usuario está bloqueado temporalmente. "
                            f"Intente nuevamente en {mins} min."
                        ),
                        username=raw_username,
                        attempt_info=f"Tiempo restante de bloqueo: {mins} min.",
                    ),
                    429,
                )

            # Fallo genérico: contamos intentos aun sin usuario real
            error_msg = "No pudimos iniciar sesión. Verifique su usuario y contraseña e intente de nuevo."

            max_attempts = int(app.config.get("ADMIN_LOGIN_MAX_ATTEMPTS") or 3)
            base = int(app.config.get("ADMIN_LOCK_INITIAL_SECONDS") or 300)
            mult = float(app.config.get("ADMIN_LOCK_MULTIPLIER") or 2)
            max_lock = int(app.config.get("ADMIN_LOCK_MAX_SECONDS") or 3600)

            attempt.failed_attempts = int(getattr(attempt, "failed_attempts", 0) or 0) + 1
            attempt.touch()

            remaining = max(0, max_attempts - attempt.failed_attempts)
            if remaining > 0:
                db.session.commit()
                attempt_info = (
                    f"Intentos fallidos: {attempt.failed_attempts} de {max_attempts}. "
                    f"Le quedan {remaining}."
                )
                return (
                    render_template(
                        "admin_login.html",
                        active="admin",
                        error=error_msg,
                        username=raw_username,
                        attempt_info=attempt_info,
                    ),
                    401,
                )

            # Se agotaron intentos -> bloqueo temporal
            attempt.failed_attempts = 0
            attempt.lockouts_count = int(getattr(attempt, "lockouts_count", 0) or 0) + 1
            seconds = int(base * (mult ** (attempt.lockouts_count - 1)))
            seconds = min(seconds, max_lock)
            attempt.lock_until = ahora + timedelta(seconds=seconds)
            attempt.touch()
            db.session.commit()

            mins = max(1, int(math.ceil(seconds / 60)))
            return (
                render_template(
                    "admin_login.html",
                    active="admin",
                    error=(
                        f"Demasiados intentos fallidos. Se aplicó un bloqueo temporal de {mins} min. "
                        "El tiempo aumentará si continúa equivocándose."
                    ),
                    username=raw_username,
                    attempt_info=f"Bloqueo #{attempt.lockouts_count}. Tiempo: {mins} min.",
                ),
                429,
            )

        # Si existe, evaluar bloqueo antes de validar contraseña
        if user:
            if getattr(user, "permanently_locked", False):
                return (
                    render_template(
                        "admin_login.html",
                        active="admin",
                        error=(
                            "Este usuario está bloqueado por seguridad. "
                            "Para habilitarlo, restablezca la contraseña o desbloquéelo desde el administrador de usuarios."
                        ),
                        username=raw_username,
                        attempt_info="Bloqueo permanente activado.",
                    ),
                    403,
                )

            if user.is_temporarily_locked(ahora):
                secs = user.seconds_until_unlock(ahora)
                mins = max(1, int(math.ceil(secs / 60)))
                return (
                    render_template(
                        "admin_login.html",
                        active="admin",
                        error=(
                            f"Demasiados intentos fallidos. Por seguridad, este usuario está bloqueado temporalmente. "
                            f"Intente nuevamente en {mins} min."
                        ),
                        username=raw_username,
                        attempt_info=f"Tiempo restante de bloqueo: {mins} min.",
                    ),
                    429,
                )

        # Validación de credenciales
        if (not user) or (not user.check_password(password)):
            # Respuesta genérica para no filtrar si el usuario existe.
            error_msg = "No pudimos iniciar sesión. Verifique su usuario y contraseña e intente de nuevo."

            attempt_info = None

            if user:
                max_attempts = int(app.config.get("ADMIN_LOGIN_MAX_ATTEMPTS") or 3)
                base = int(app.config.get("ADMIN_LOCK_INITIAL_SECONDS") or 300)
                mult = float(app.config.get("ADMIN_LOCK_MULTIPLIER") or 2)
                max_lock = int(app.config.get("ADMIN_LOCK_MAX_SECONDS") or 3600)
                perma_after = int(app.config.get("ADMIN_MAX_LOCKOUTS_BEFORE_PERMANENT") or 2)

                user.failed_attempts = int(getattr(user, "failed_attempts", 0) or 0) + 1

                remaining = max(0, max_attempts - user.failed_attempts)

                # Aún quedan intentos
                if remaining > 0:
                    db.session.commit()
                    attempt_info = f"Intentos fallidos: {user.failed_attempts} de {max_attempts}. Le quedan {remaining}."
                    return (
                        render_template(
                            "admin_login.html",
                            active="admin",
                            error=error_msg,
                            username=raw_username,
                            attempt_info=attempt_info,
                        ),
                        401,
                    )

                # Se agotaron intentos -> bloqueo temporal (o permanente)
                user.failed_attempts = 0
                user.lockouts_count = int(getattr(user, "lockouts_count", 0) or 0) + 1

                # Bloqueo permanente si excede umbral
                if user.lockouts_count >= perma_after:
                    user.permanently_locked = True
                    user.lock_until = None
                    db.session.commit()
                    return (
                        render_template(
                            "admin_login.html",
                            active="admin",
                            error=(
                                "Por seguridad, este usuario quedó bloqueado. "
                                "Para volver a ingresar debe restablecer la contraseña desde el administrador de usuarios."
                            ),
                            username=raw_username,
                            attempt_info="Bloqueo permanente (requiere restablecer contraseña o desbloquear).",
                        ),
                        403,
                    )

                seconds = int(base * (mult ** (user.lockouts_count - 1)))
                seconds = min(seconds, max_lock)
                user.lock_until = ahora + timedelta(seconds=seconds)
                db.session.commit()

                mins = max(1, int(math.ceil(seconds / 60)))
                return (
                    render_template(
                        "admin_login.html",
                        active="admin",
                        error=(
                            f"Demasiados intentos fallidos. Se aplicó un bloqueo temporal de {mins} min. "
                            "El tiempo aumentará si continúa equivocándose."
                        ),
                        username=raw_username,
                        attempt_info=f"Bloqueo #{user.lockouts_count}. Tiempo: {mins} min.",
                    ),
                    429,
                )

            # Nota: el caso "usuario no existe" se maneja arriba con AdminLoginAttempt.
            return (
                render_template(
                    "admin_login.html",
                    active="admin",
                    error=error_msg,
                    username=raw_username,
                ),
                401,
            )

        # Login OK: registrar último inicio de sesión y reiniciar bloqueos
        user.ultimo_inicio_sesion = datetime.utcnow()
        user.failed_attempts = 0
        user.lockouts_count = 0
        user.lock_until = None
        # Nota: si el usuario estaba bloqueado permanente, no llegaría aquí.
        db.session.commit()

        # Limpieza: si existía un estado de intentos por typo (username+ip), lo reseteamos.
        attempt = AdminLoginAttempt.query.filter_by(username=username, ip=ip).first()
        if attempt:
            attempt.failed_attempts = 0
            attempt.lockouts_count = 0
            attempt.lock_until = None
            attempt.touch()
            db.session.commit()

        session["admin_logged_in"] = True
        session["admin_user_id"] = user.id
        session["admin_username"] = user.username
        session["admin_nombre"] = user.nombre

        # Si tiene contrasena temporal (o se marco como obligatoria), forzamos el cambio.
        session["admin_force_password_change"] = bool(getattr(user, "must_change_password", False))
        if session.get("admin_force_password_change"):
            return redirect(url_for("admin_change_password"))

        return redirect(url_for("admin_panel"))

    @app.get("/admin/panel")
    def admin_panel():
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        # Si esta pendiente el cambio de contrasena, no permitir entrar al panel
        if session.get("admin_force_password_change"):
            return redirect(url_for("admin_change_password"))

        admin_nombre = session.get("admin_nombre")
        admin_username = session.get("admin_username")
        return render_template(
            "admin_panel.html",
            active="admin",
            admin_nombre=admin_nombre,
            admin_username=admin_username,
        )

    
    @app.get("/admin/certificados")
    def admin_certificado():
        """Generador de certificados como administrador (sin reto de fecha de nacimiento).

        Requiere sesión admin y que el cambio de contraseña esté completado.
        """
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        if session.get("admin_force_password_change"):
            return redirect(url_for("admin_change_password"))

        admin_nombre = session.get("admin_nombre")
        admin_username = session.get("admin_username")
        return render_template("admin_certificado.html", active="admin", admin_nombre=admin_nombre, admin_username=admin_username)


    @app.get("/admin/certificados/especial")
    def admin_certificado_especial():
        """Generador de certificados especiales (Admin) con texto personalizado."""
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        if session.get("admin_force_password_change"):
            return redirect(url_for("admin_change_password"))

        return render_template(
            "admin_certificado_especial.html",
            active="admin",
            admin_nombre=session.get("admin_nombre"),
            admin_username=session.get("admin_username"),
            ui_min_transition_seconds=config.UI_MIN_TRANSITION_SECONDS,
        )


    @app.get("/admin/certificados/registros")
    def admin_registros_certificados():
        """Listado de todos los certificados generados (usuario y admin).

        Incluye botón para ir a la verificación pública (igual al QR/link).
        """
        gate = _require_admin()
        if gate:
            return gate

        q_raw = (request.args.get("q") or "").strip()
        origen = (request.args.get("origen") or "todos").strip().lower()
        page = request.args.get("page") or "1"
        try:
            page_i = max(1, int(page))
        except Exception:
            page_i = 1

        # Paginación: máximo 10 registros por página (carga desde BD por página)
        per_page = 10

        # Join DocumentoGenerado + Ciudadano para mostrar datos del titular
        query = (
            db.session.query(DocumentoGenerado, Ciudadano)
            .join(Ciudadano, DocumentoGenerado.ciudadano_id == Ciudadano.id)
        )

        if q_raw:
            s = f"%{q_raw}%"
            query = query.filter(
                (DocumentoGenerado.codigo.ilike(s))
                | (Ciudadano.numero_documento.ilike(s))
                | (Ciudadano.nombre_completo.ilike(s))
            )

        if origen in {"usuario", "admin"}:
            query = query.filter(DocumentoGenerado.generado_por == origen)
        else:
            origen = "todos"

        total = query.count()
        pages = max(1, int(math.ceil(total / per_page))) if total else 1
        page_i = min(page_i, pages)

        pairs = (
            query.order_by(DocumentoGenerado.id.desc())
            .offset((page_i - 1) * per_page)
            .limit(per_page)
            .all()
        )

        tz_name = config.APP_TIMEZONE or "America/Bogota"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("America/Bogota")

        rows = []
        for doc, c in pairs:
            # doc.creado_en se guarda en UTC. Lo mostramos en zona local.
            try:
                emitido_local = doc.creado_en.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
                emision_str = emitido_local.strftime("%d/%m/%Y %I:%M %p")
            except Exception:
                emision_str = doc.creado_en.strftime("%d/%m/%Y %H:%M")

            rows.append(
                {
                    "id": doc.id,
                    "codigo": doc.codigo,
                    "generado_por": (doc.generado_por or "usuario"),
                    "tipo_documento": getattr(doc, "tipo_documento", "certificado_afiliacion"),
                    "tipo_label": "Especial" if getattr(doc, "tipo_documento", "") == "certificado_especial" else "Afiliación",
                    "emision_str": emision_str,
                    "nombre": c.nombre_completo,
                    "tipo_doc": c.tipo_documento,
                    "num_doc": c.numero_documento,
                    "activo": bool(c.activo),
                    "verify_link": f"/verificar-certificados?codigo={doc.codigo}",
                }
            )

        def _page_url(p: int):
            args = {"q": q_raw, "origen": origen, "page": p}
            args = {k: v for k, v in args.items() if v and v != "todos"}
            return url_for("admin_registros_certificados", **args)

        return render_template(
            "admin_registros_certificados.html",
            active="admin",
            admin_nombre=session.get("admin_nombre"),
            admin_username=session.get("admin_username"),
            q=q_raw,
            origen=origen,
            rows=rows,
            total=total,
            page=page_i,
            pages=pages,
            prev_url=_page_url(page_i - 1) if page_i > 1 else None,
            next_url=_page_url(page_i + 1) if page_i < pages else None,
        )


    # --- Admin: Gestión de ciudadanos ---

    def _parse_birthdate(value: str | None):
        v = (value or "").strip()
        if not v:
            return None
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except Exception:
            return None

    @app.get("/admin/ciudadanos")
    def admin_ciudadanos():
        gate = _require_admin()
        if gate:
            return gate

        q_raw = (request.args.get("q") or "").strip()
        estado = (request.args.get("estado") or "activos").strip().lower()
        page = request.args.get("page") or "1"
        try:
            page_i = max(1, int(page))
        except Exception:
            page_i = 1

        # Paginación: máximo 10 registros por página (carga desde BD por página)
        per_page = 10

        query = Ciudadano.query
        if q_raw:
            s = f"%{q_raw}%"
            query = query.filter(
                (Ciudadano.nombre_completo.ilike(s))
                | (Ciudadano.numero_documento.ilike(s))
                | (Ciudadano.tipo_documento.ilike(s))
            )

        if estado == "inactivos":
            query = query.filter(Ciudadano.activo.is_(False))
        elif estado == "todos":
            pass
        else:
            # activos por defecto
            estado = "activos"
            query = query.filter(Ciudadano.activo.is_(True))

        total = query.count()
        pages = max(1, int(math.ceil(total / per_page))) if total else 1
        page_i = min(page_i, pages)

        rows = (
            query.order_by(Ciudadano.id.desc())
            .offset((page_i - 1) * per_page)
            .limit(per_page)
            .all()
        )

        def _page_url(p: int):
            args = {"q": q_raw, "estado": estado, "page": p}
            # limpiar args vacíos
            args = {k: v for k, v in args.items() if v}
            return url_for("admin_ciudadanos", **args)

        return render_template(
            "admin_ciudadanos.html",
            active="admin",
            admin_nombre=session.get("admin_nombre"),
            admin_username=session.get("admin_username"),
            flash=_pop_admin_flash(),
            q=q_raw,
            estado=estado,
            rows=rows,
            total=total,
            page=page_i,
            pages=pages,
            prev_url=_page_url(page_i - 1) if page_i > 1 else None,
            next_url=_page_url(page_i + 1) if page_i < pages else None,
        )

    @app.get("/admin/ciudadanos/nuevo")
    def admin_ciudadanos_nuevo():
        gate = _require_admin()
        if gate:
            return gate

        return render_template(
            "admin_ciudadano_form.html",
            active="admin",
            flash=_pop_admin_flash(),
            mode="nuevo",
            values={"activo": True},
        )

    @app.post("/admin/ciudadanos/nuevo")
    def admin_ciudadanos_nuevo_post():
        gate = _require_admin()
        if gate:
            return gate

        nombre = (request.form.get("nombre") or "").strip()
        tipo = (request.form.get("tipo") or "").strip()
        numero = (request.form.get("numero") or "").strip()
        nacimiento_raw = (request.form.get("nacimiento") or "").strip()
        nacimiento = _parse_birthdate(nacimiento_raw)
        activo = (request.form.get("activo") or "").strip().lower() in {"1", "true", "on", "yes"}

        # Validación reutilizando reglas actuales
        try:
            from backend.ciudadanos import normalizar_documento  # type: ignore

            tipo_norm, numero_norm = normalizar_documento(tipo, numero)
        except Exception as e:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="nuevo",
                    error=str(e),
                    values={
                        "nombre": nombre,
                        "tipo": tipo,
                        "numero": numero,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if not nacimiento_raw:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="nuevo",
                    error="La fecha de nacimiento es obligatoria.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if nacimiento is None:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="nuevo",
                    error="La fecha de nacimiento no es válida.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if not nombre:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="nuevo",
                    error="El nombre es obligatorio.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        exists = Ciudadano.query.filter_by(tipo_documento=tipo_norm, numero_documento=numero_norm).first()
        if exists:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="nuevo",
                    error="Ya existe un ciudadano con ese documento.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                409,
            )

        r = Ciudadano(
            nombre_completo=nombre,
            tipo_documento=tipo_norm,
            numero_documento=numero_norm,
            fecha_nacimiento=nacimiento,
            activo=bool(activo),
        )
        db.session.add(r)
        db.session.commit()

        _set_admin_flash("success", f"Usuario \"{nombre}\" ha sido creado.")
        return redirect(url_for("admin_ciudadanos", estado="todos", q=numero_norm))

    @app.get("/admin/ciudadanos/<int:cid>/editar")
    def admin_ciudadanos_editar(cid: int):
        gate = _require_admin()
        if gate:
            return gate

        r = db.session.get(Ciudadano, cid)
        if not r:
            _set_admin_flash("error", "No encontramos ese ciudadano.")
            return redirect(url_for("admin_ciudadanos"))

        values = {
            "nombre": r.nombre_completo,
            "tipo": r.tipo_documento,
            "numero": r.numero_documento,
            "nacimiento": r.fecha_nacimiento.isoformat() if r.fecha_nacimiento else "",
            "activo": bool(r.activo),
        }

        return render_template(
            "admin_ciudadano_form.html",
            active="admin",
            flash=_pop_admin_flash(),
            mode="editar",
            ciudadano=r,
            values=values,
        )

    @app.post("/admin/ciudadanos/<int:cid>/editar")
    def admin_ciudadanos_editar_post(cid: int):
        gate = _require_admin()
        if gate:
            return gate

        r = db.session.get(Ciudadano, cid)
        if not r:
            _set_admin_flash("error", "No encontramos ese ciudadano.")
            return redirect(url_for("admin_ciudadanos"))

        nombre = (request.form.get("nombre") or "").strip()
        tipo = (request.form.get("tipo") or "").strip()
        numero = (request.form.get("numero") or "").strip()
        nacimiento_raw = (request.form.get("nacimiento") or "").strip()
        nacimiento = _parse_birthdate(nacimiento_raw)
        activo = (request.form.get("activo") or "").strip().lower() in {"1", "true", "on", "yes"}

        try:
            from backend.ciudadanos import normalizar_documento  # type: ignore

            tipo_norm, numero_norm = normalizar_documento(tipo, numero)
        except Exception as e:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="editar",
                    ciudadano=r,
                    error=str(e),
                    values={
                        "nombre": nombre,
                        "tipo": tipo,
                        "numero": numero,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if not nacimiento_raw:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="editar",
                    ciudadano=r,
                    error="La fecha de nacimiento es obligatoria.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if nacimiento is None:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="editar",
                    ciudadano=r,
                    error="La fecha de nacimiento no es válida.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        if not nombre:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="editar",
                    ciudadano=r,
                    error="El nombre es obligatorio.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                400,
            )

        # Evitar duplicados si cambia documento
        other = Ciudadano.query.filter_by(tipo_documento=tipo_norm, numero_documento=numero_norm).first()
        if other and other.id != r.id:
            return (
                render_template(
                    "admin_ciudadano_form.html",
                    active="admin",
                    mode="editar",
                    ciudadano=r,
                    error="Ya existe otro ciudadano con ese documento.",
                    values={
                        "nombre": nombre,
                        "tipo": tipo_norm,
                        "numero": numero_norm,
                        "nacimiento": nacimiento_raw,
                        "activo": activo,
                    },
                ),
                409,
            )

        r.nombre_completo = nombre
        r.tipo_documento = tipo_norm
        r.numero_documento = numero_norm
        r.fecha_nacimiento = nacimiento
        r.activo = bool(activo)
        db.session.commit()

        _set_admin_flash("success", f"Usuario \"{r.nombre_completo}\" ha sido actualizado.")
        return redirect(url_for("admin_ciudadanos", estado="todos", q=numero_norm))

    @app.post("/admin/ciudadanos/<int:cid>/toggle")
    def admin_ciudadanos_toggle(cid: int):
        gate = _require_admin()
        if gate:
            return gate

        r = db.session.get(Ciudadano, cid)
        if not r:
            _set_admin_flash("error", "No encontramos ese ciudadano.")
            return redirect(url_for("admin_ciudadanos"))

        r.activo = not bool(r.activo)
        db.session.commit()

        _set_admin_flash(
            "success",
            f"Usuario \"{r.nombre_completo}\" ha sido {'activado' if r.activo else 'desactivado'}.",
        )

        next_url = (request.form.get("next") or "").strip()
        return redirect(next_url or url_for("admin_ciudadanos"))

    @app.post("/admin/ciudadanos/<int:cid>/eliminar")
    def admin_ciudadanos_eliminar(cid: int):
        gate = _require_admin()
        if gate:
            return gate

        r = db.session.get(Ciudadano, cid)
        if not r:
            _set_admin_flash("error", "No encontramos ese ciudadano.")
            return redirect(url_for("admin_ciudadanos"))

        # Seguridad: si tiene certificados, no se elimina (se recomienda desactivar)
        has_docs = DocumentoGenerado.query.filter_by(ciudadano_id=r.id).first() is not None
        if has_docs:
            _set_admin_flash(
                "warning",
                f"No se puede eliminar al usuario \"{r.nombre_completo}\" porque tiene certificados generados. "
                "Recomendación: desactive la afiliación.",
            )
            next_url = (request.form.get("next") or "").strip()
            return redirect(next_url or url_for("admin_ciudadanos"))

        db.session.delete(r)
        db.session.commit()

        _set_admin_flash("success", f"Usuario \"{r.nombre_completo}\" ha sido eliminado.")
        next_url = (request.form.get("next") or "").strip()
        return redirect(next_url or url_for("admin_ciudadanos"))

    @app.get("/admin/change-password")
    def admin_change_password():
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        if not session.get("admin_force_password_change"):
            return redirect(url_for("admin_panel"))

        admin_username = session.get("admin_username")
        return render_template(
            "admin_change_password.html",
            active="admin",
            admin_username=admin_username,
        )

    @app.post("/admin/change-password")
    def admin_change_password_post():
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        if not session.get("admin_force_password_change"):
            return redirect(url_for("admin_panel"))

        new_password = (request.form.get("new_password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        def validate(pwd: str) -> str | None:
            min_len = int(app.config.get("ADMIN_PASSWORD_MIN_LENGTH") or 8)
            if len(pwd) < min_len:
                return f"La contrasena debe tener minimo {min_len} caracteres."
            if any(ch.isspace() for ch in pwd):
                return "La contrasena no debe contener espacios."
            if not any(ch.isalpha() for ch in pwd) or not any(ch.isdigit() for ch in pwd):
                return "La contrasena debe incluir al menos una letra y un numero."
            return None

        if not new_password or not confirm_password:
            return (
                render_template(
                    "admin_change_password.html",
                    active="admin",
                    admin_username=session.get("admin_username"),
                    error="Debe completar los campos de contrasena.",
                ),
                400,
            )

        if new_password != confirm_password:
            return (
                render_template(
                    "admin_change_password.html",
                    active="admin",
                    admin_username=session.get("admin_username"),
                    error="Las contrasenas no coinciden.",
                ),
                400,
            )

        err = validate(new_password)
        if err:
            return (
                render_template(
                    "admin_change_password.html",
                    active="admin",
                    admin_username=session.get("admin_username"),
                    error=err,
                ),
                400,
            )

        # Actualizar en BD
        user_id = session.get("admin_user_id")
        user = AdminUser.query.get(user_id) if user_id else None
        if not user:
            # Sesion inconsistente
            session.pop("admin_logged_in", None)
            session.pop("admin_user_id", None)
            session.pop("admin_username", None)
            session.pop("admin_nombre", None)
            session.pop("admin_force_password_change", None)
            return redirect(url_for("admin_login"))

        user.set_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.utcnow()
        user.failed_attempts = 0
        user.lockouts_count = 0
        user.lock_until = None
        user.permanently_locked = False
        db.session.commit()

        session["admin_force_password_change"] = False
        return redirect(url_for("admin_panel"))

    @app.get("/admin/logout")
    def admin_logout():
        session.pop("admin_logged_in", None)
        session.pop("admin_user_id", None)
        session.pop("admin_username", None)
        session.pop("admin_nombre", None)
        session.pop("admin_force_password_change", None)
        return redirect(url_for("admin_login"))

    return app


app = crear_app()
