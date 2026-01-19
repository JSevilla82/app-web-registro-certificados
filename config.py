"""Configuración centralizada.

Se configura vía variables de entorno (.env) para evitar hardcodear secretos.
Incluye control por modo: development / production.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

# Cargar variables desde .env
# lea los valores correctos al ser importado.
from dotenv import load_dotenv

load_dotenv(override=False)


BASE_DIR = Path(__file__).resolve().parent


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _mode() -> str:
    return (os.getenv("APP_MODE") or "development").strip().lower()


APP_MODE = _mode()
IS_PRODUCTION = APP_MODE == "production"


def _modo_flag(nombre: str, default: bool = False) -> bool:
    """Lee flags con prioridad:
    - PROD_<NOMBRE> si producción
    - DEV_<NOMBRE> si desarrollo
    - <NOMBRE> genérico
    - default
    """
    if IS_PRODUCTION:
        if os.getenv(f"PROD_{nombre}") is not None:
            return _as_bool(os.getenv(f"PROD_{nombre}"), default=default)
    else:
        if os.getenv(f"DEV_{nombre}") is not None:
            return _as_bool(os.getenv(f"DEV_{nombre}"), default=default)

    return _as_bool(os.getenv(nombre), default=default)


# --- Base de datos ---
def _resolver_ruta(base: Path, valor: str | None, por_defecto: Path) -> Path:
    """Convierte rutas del .env a absolutas, relativas a BASE_DIR cuando aplique."""
    if not valor:
        return por_defecto.resolve()

    p = Path(valor)
    if p.is_absolute():
        return p.resolve()

    return (base / p).resolve()


DATABASE_DIR = _resolver_ruta(BASE_DIR, os.getenv("DATABASE_DIR"), BASE_DIR / "database")
DATABASE_PATH = _resolver_ruta(BASE_DIR, os.getenv("DATABASE_PATH"), DATABASE_DIR / "cabildo.db")

SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
SQLALCHEMY_TRACK_MODIFICATIONS = False


# --- Seguridad / Flask ---
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), default=IS_PRODUCTION)

# --- Modo / debug ---
DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=(not IS_PRODUCTION))
SEED_ON_START = _as_bool(os.getenv("SEED_ON_START"), default=(not IS_PRODUCTION))

# --- HTTPS / Proxy ---
TRUST_PROXY_HEADERS = _modo_flag("TRUST_PROXY_HEADERS", default=False)

ENABLE_SSL = _modo_flag("ENABLE_SSL", default=False)
FORCE_HTTPS = _modo_flag("FORCE_HTTPS", default=False)

# --- Seguridad adicional ---
ENABLE_CSRF = _modo_flag("ENABLE_CSRF", default=True)
ENABLE_SECURITY_HEADERS = _modo_flag("ENABLE_SECURITY_HEADERS", default=True)

ENABLE_RATELIMIT = _modo_flag("ENABLE_RATELIMIT", default=True)
RATELIMIT_DEFAULTS = os.getenv("RATELIMIT_DEFAULTS", "200 per day;60 per hour").split(";")

# --- Certificados ---
CERTIFICADOS_DIR = Path(os.getenv("CERTIFICADOS_DIR") or (BASE_DIR / "generated"))

# Retención del archivo PDF (descarga para el usuario)
CERT_FILE_RETENTION_HOURS = int(os.getenv("CERT_FILE_RETENTION_HOURS") or "24")

# Retención para la visualización del documento en verificación pública (días)
# Ejemplos: 30, 180 (6 meses aprox.)
VERIFY_DOC_RETENTION_DAYS = int(os.getenv("VERIFY_DOC_RETENTION_DAYS") or "30")

# Token firmado tras verificación (habilita la generación)
VERIFY_TOKEN_MAX_AGE_SECONDS = int(os.getenv("VERIFY_TOKEN_MAX_AGE_SECONDS") or "300")

# --- Firma Capitán Menor (PDF) ---
CAPITAN_MENOR_FIRMA_RUTA = os.getenv("CAPITAN_MENOR_FIRMA_RUTA") or "static/img/Firma_Diomedes.png"
CAPITAN_MENOR_NOMBRE = os.getenv("CAPITAN_MENOR_NOMBRE") or "DIOMEDES FARID MONTES BERTEL"
CAPITAN_MENOR_DOCUMENTO_TIPO = os.getenv("CAPITAN_MENOR_DOCUMENTO_TIPO") or "CC"
CAPITAN_MENOR_DOCUMENTO_NUMERO = os.getenv("CAPITAN_MENOR_DOCUMENTO_NUMERO") or ""

# --- Verificación por fecha de nacimiento ---
BIRTHDATE_CHALLENGE_EXPIRES_MINUTES = int(os.getenv("BIRTHDATE_CHALLENGE_EXPIRES_MINUTES") or "10")
BIRTHDATE_SESSION_MINUTES = int(os.getenv("BIRTHDATE_SESSION_MINUTES") or "30")

BIRTHDATE_LOCK_INITIAL_SECONDS = int(os.getenv("BIRTHDATE_LOCK_INITIAL_SECONDS") or "300")
BIRTHDATE_LOCK_MULTIPLIER = float(os.getenv("BIRTHDATE_LOCK_MULTIPLIER") or "2")

# --- Admin: seguridad de login ---
# Intentos permitidos antes de bloqueo temporal.
ADMIN_LOGIN_MAX_ATTEMPTS = int(os.getenv("ADMIN_LOGIN_MAX_ATTEMPTS") or "3")

# Bloqueo temporal exponencial (segundos): base * (mult ** (bloqueos-1))
ADMIN_LOCK_INITIAL_SECONDS = int(os.getenv("ADMIN_LOCK_INITIAL_SECONDS") or "300")
ADMIN_LOCK_MULTIPLIER = float(os.getenv("ADMIN_LOCK_MULTIPLIER") or "2")

# Tope de bloqueo para evitar tiempos desproporcionados (segundos)
ADMIN_LOCK_MAX_SECONDS = int(os.getenv("ADMIN_LOCK_MAX_SECONDS") or "3600")

# Si el usuario acumula N bloqueos temporales, se bloquea de forma permanente.
ADMIN_MAX_LOCKOUTS_BEFORE_PERMANENT = int(os.getenv("ADMIN_MAX_LOCKOUTS_BEFORE_PERMANENT") or "2")

# Rate limit específico para el endpoint de login admin (además del global)
ADMIN_LOGIN_RATELIMIT = os.getenv("ADMIN_LOGIN_RATELIMIT") or "10 per minute"

# Contrasena temporal (CLI)
ADMIN_TEMP_PASSWORD_LENGTH = int(os.getenv("ADMIN_TEMP_PASSWORD_LENGTH") or "12")

# Politica minima de contrasenas para Admin
ADMIN_PASSWORD_MIN_LENGTH = int(os.getenv("ADMIN_PASSWORD_MIN_LENGTH") or "8")

# --- Límites de payload ---
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH") or str(32 * 1024))

# --- Interfaz / Transiciones ---
UI_MIN_TRANSITION_SECONDS = float(os.getenv("UI_MIN_TRANSITION_SECONDS") or "1")

# --- Zona horaria (para validez diaria y formateo de fechas) ---
APP_TIMEZONE = os.getenv("APP_TIMEZONE") or "America/Bogota"
