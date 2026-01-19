from __future__ import annotations

from sqlalchemy import text

from .db import db


def asegurar_columna_fecha_nacimiento() -> None:
    """Agrega la columna fecha_nacimiento si la BD ya existía y no la tiene."""
    engine = db.engine
    with engine.begin() as conn:
        info = conn.execute(text("PRAGMA table_info(ciudadanos)")).fetchall()
        columnas = {row[1] for row in info}  # row[1] = name
        if "fecha_nacimiento" not in columnas:
            conn.execute(text("ALTER TABLE ciudadanos ADD COLUMN fecha_nacimiento DATE"))


def asegurar_columna_activo() -> None:
    """Agrega la columna activo si la BD ya existía y no la tiene.

    En SQLite, BOOLEAN se almacena como INTEGER (0/1). Dejamos DEFAULT 1 para
    que cualquier registro histórico quede como activo.
    """
    engine = db.engine
    with engine.begin() as conn:
        info = conn.execute(text("PRAGMA table_info(ciudadanos)")).fetchall()
        columnas = {row[1] for row in info}
        if "activo" not in columnas:
            conn.execute(text("ALTER TABLE ciudadanos ADD COLUMN activo BOOLEAN NOT NULL DEFAULT 1"))


def asegurar_columnas_admin_users() -> None:
    """Agrega columnas de seguridad a la tabla admin_users si no existen.

    Compatible con SQLite (ALTER TABLE ADD COLUMN).
    """
    engine = db.engine
    with engine.begin() as conn:
        info = conn.execute(text("PRAGMA table_info(admin_users)")).fetchall()
        columnas = {row[1] for row in info}

        if "must_change_password" not in columnas:
            # SQLite guarda BOOLEAN como INTEGER (0/1)
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"))
        if "temp_password_issued_at" not in columnas:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN temp_password_issued_at DATETIME"))
        if "password_changed_at" not in columnas:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN password_changed_at DATETIME"))

        if "failed_attempts" not in columnas:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"))
        if "lockouts_count" not in columnas:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN lockouts_count INTEGER NOT NULL DEFAULT 0"))
        if "lock_until" not in columnas:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN lock_until DATETIME"))
        if "permanently_locked" not in columnas:
            # SQLite guarda BOOLEAN como INTEGER (0/1)
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN permanently_locked BOOLEAN NOT NULL DEFAULT 0"))



def asegurar_columna_generado_por_documentos() -> None:
    """Agrega la columna generado_por a documentos_generados si la BD ya existía y no la tiene.

    En SQLite, TEXT con DEFAULT permite backfill automático.
    """
    engine = db.engine
    with engine.begin() as conn:
        info = conn.execute(text("PRAGMA table_info(documentos_generados)")).fetchall()
        columnas = {row[1] for row in info}
        if "generado_por" not in columnas:
            conn.execute(text("ALTER TABLE documentos_generados ADD COLUMN generado_por TEXT NOT NULL DEFAULT 'usuario'"))


def asegurar_columnas_certificados_especiales() -> None:
    """Agrega columnas necesarias para certificados especiales en documentos_generados.

    - tipo_documento: para diferenciar afiliación vs especial
    - texto_personalizado: para almacenar el texto del certificado especial
    """
    engine = db.engine
    with engine.begin() as conn:
        info = conn.execute(text("PRAGMA table_info(documentos_generados)")).fetchall()
        columnas = {row[1] for row in info}

        if "tipo_documento" not in columnas:
            conn.execute(text("ALTER TABLE documentos_generados ADD COLUMN tipo_documento TEXT NOT NULL DEFAULT 'certificado_afiliacion'"))

        if "texto_personalizado" not in columnas:
            conn.execute(text("ALTER TABLE documentos_generados ADD COLUMN texto_personalizado TEXT"))

def asegurar_tablas() -> None:
    """Crea tablas y aplica migraciones ligeras compatibles con SQLite."""
    db.create_all()
    # El reto por opciones de fecha de nacimiento fue removido. Si existía una tabla
    # antigua, la eliminamos para evitar residuos y crecimiento innecesario.
    engine = db.engine
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS retos_fecha_nacimiento"))
    asegurar_columna_fecha_nacimiento()
    asegurar_columna_activo()
    asegurar_columnas_admin_users()
    asegurar_columna_generado_por_documentos()
    asegurar_columnas_certificados_especiales()
