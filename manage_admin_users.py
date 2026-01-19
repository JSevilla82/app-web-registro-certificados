"""CREADO PARA USARSE DURANTE EL DESARROLLO DE LA APLICACIÓN

CLI para administrar usuarios Admin (login /admin) en la BD.

Este script gestiona la tabla `admin_users` (los que pueden iniciar sesion en /admin).

COMO FUNCIONA (contrasena temporal):
- `add` crea el usuario con una contrasena TEMPORAL y obliga a cambiarla al iniciar sesion.
- `reset-password` emite una nueva contrasena TEMPORAL, desbloquea y obliga a cambiarla.
- `set-password` establece la contrasena FINAL (ya no pide cambio) y habilita el usuario.

ELEGIR LA CONTRASENA TEMPORAL:
- Puedes definirla tu mismo con `--temp-pass "..."`.
- O usar `--temp-pass` SIN valor para que el script te la pida oculta por consola.
- Si no indicas `--temp-pass`, se genera automaticamente.

EJEMPLOS RAPIDOS:
  python manage_admin_users.py add --nombre "Juan Perez" --user 1102858449
  python manage_admin_users.py add --nombre "Juan Perez" --user 1102858449 --temp-pass "Temporal123+"
  python manage_admin_users.py reset-password --user 1102858449
  python manage_admin_users.py reset-password --user 1102858449 --temp-pass
  python manage_admin_users.py set-password --user 1102858449
  python manage_admin_users.py unlock --user 1102858449
  python manage_admin_users.py list --search "mendez"

NOTAS:
- Las contrasenas se guardan como HASH (nunca texto plano).
- Los comandos imprimen en consola la contrasena temporal (si aplica).
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from datetime import datetime
from getpass import getpass

from dotenv import load_dotenv


def _bootstrap_app():
    """Carga .env e inicializa la app/DB con el mismo stack del proyecto."""
    load_dotenv(override=False)
    from app import crear_app  # type: ignore

    app = crear_app()
    return app


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _prompt_password(label: str = "Contrasena") -> str:
    p1 = getpass(f"{label}: ")
    p2 = getpass("Confirmar contrasena: ")
    if p1 != p2:
        raise ValueError("Las contrasenas no coinciden")
    return p1


def _generate_temp_password(length: int = 12) -> str:
    """Genera una contrasena temporal (segura y facil de copiar).

    - Garantiza al menos 1 mayuscula, 1 minuscula, 1 digito, 1 simbolo.
    - Usa `secrets` para aleatoriedad criptograficamente segura.
    """
    if length < 10:
        length = 10

    upp = secrets.choice(string.ascii_uppercase)
    low = secrets.choice(string.ascii_lowercase)
    dig = secrets.choice(string.digits)
    sym_pool = "!@#$%^&*+-_?"
    sym = secrets.choice(sym_pool)

    pool = string.ascii_letters + string.digits + sym_pool
    rest = "".join(secrets.choice(pool) for _ in range(length - 4))

    pwd_list = list(upp + low + dig + sym + rest)
    # Shuffle seguro
    secrets.SystemRandom().shuffle(pwd_list)
    return "".join(pwd_list)


def _reset_lock_state(user) -> None:
    # Reinicia estados de bloqueo (si existen)
    if hasattr(user, "failed_attempts"):
        user.failed_attempts = 0
    if hasattr(user, "lockouts_count"):
        user.lockouts_count = 0
    if hasattr(user, "lock_until"):
        user.lock_until = None
    if hasattr(user, "permanently_locked"):
        user.permanently_locked = False


def cmd_list(app, limit: int, search: str | None) -> int:
    from models import AdminUser  # type: ignore

    with app.app_context():
        q = AdminUser.query
        if search:
            s = f"%{search.strip()}%"
            q = q.filter((AdminUser.nombre.ilike(s)) | (AdminUser.username.ilike(s)))

        rows = q.order_by(AdminUser.id.desc()).limit(limit).all()
        if not rows:
            print("(sin resultados)")
            return 0

        for r in rows:
            locked = "perma" if getattr(r, "permanently_locked", False) else ("temp" if getattr(r, "lock_until", None) else "")
            must = "si" if getattr(r, "must_change_password", False) else "no"
            print(
                f"{r.username}\t{r.nombre}\t"
                f"registro:{_fmt_dt(r.fecha_registro)}\t"
                f"ultimo_login:{_fmt_dt(r.ultimo_inicio_sesion)}\t"
                f"cambio_pwd:{must}\t"
                f"lock:{locked}"
            )

    return 0


def cmd_show(app, username: str) -> int:
    from models import AdminUser  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        print(f"ID interno: {r.id}")
        print(f"Nombre: {r.nombre}")
        print(f"Usuario: {r.username}")
        print(f"Fecha de registro (UTC): {_fmt_dt(r.fecha_registro)}")
        print(f"Ultimo inicio de sesion (UTC): {_fmt_dt(r.ultimo_inicio_sesion)}")

        # Contrasena temporal
        print(f"Requiere cambio de contrasena: {'si' if getattr(r, 'must_change_password', False) else 'no'}")
        print(f"Temporal emitida (UTC): {_fmt_dt(getattr(r, 'temp_password_issued_at', None))}")
        print(f"Contrasena cambiada (UTC): {_fmt_dt(getattr(r, 'password_changed_at', None))}")

        # Seguridad
        print(f"Intentos fallidos: {getattr(r, 'failed_attempts', 0) or 0}")
        print(f"Bloqueos temporales acumulados: {getattr(r, 'lockouts_count', 0) or 0}")
        print(f"Bloqueado hasta (UTC): {_fmt_dt(getattr(r, 'lock_until', None))}")
        print(f"Bloqueo permanente: {'si' if getattr(r, 'permanently_locked', False) else 'no'}")

    return 0


def cmd_add(app, nombre: str, username: str, temp_password: str | None) -> int:
    from models import AdminUser, db  # type: ignore

    nombre = (nombre or "").strip()
    if not nombre:
        print("El nombre es obligatorio.")
        return 2

    u = AdminUser.normalize_username(username)
    if not u:
        print("El usuario es obligatorio.")
        return 2

    # Por defecto generamos contrasena temporal
    if temp_password == "__PROMPT__":
        pwd = _prompt_password("Contrasena temporal")
    else:
        pwd = (temp_password or "").strip()
    if not pwd:
        length = int(os.getenv("ADMIN_TEMP_PASSWORD_LENGTH") or "12")
        pwd = _generate_temp_password(length=length)

    with app.app_context():
        exists = AdminUser.query.filter_by(username=u).first()
        if exists:
            print("Ya existe. Use update o reset-password.")
            return 1

        r = AdminUser(nombre=nombre, username=u)
        r.set_password(pwd)
        r.must_change_password = True
        r.temp_password_issued_at = datetime.utcnow()
        r.password_changed_at = None

        db.session.add(r)
        db.session.commit()

        print("Creado:", r.username)
        print("Contrasena temporal:", pwd)
        print("Nota: Al iniciar sesion, el sistema obligara a cambiarla.")

    return 0


def cmd_update(app, username: str, nombre: str | None, new_user: str | None) -> int:
    from models import AdminUser, db  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        changed = False

        if nombre is not None:
            n = nombre.strip()
            if not n:
                print("Nombre invalido (vacio).")
                return 2
            r.nombre = n
            changed = True

        if new_user is not None:
            nu = AdminUser.normalize_username(new_user)
            if not nu:
                print("Nuevo usuario invalido.")
                return 2
            if nu != r.username and AdminUser.query.filter_by(username=nu).first():
                print("Ya existe otro usuario con ese username.")
                return 1
            r.username = nu
            changed = True

        if not changed:
            print("Nada que actualizar.")
            return 0

        db.session.commit()
        print("Actualizado.")

    return 0


def cmd_set_password(app, username: str, password: str | None) -> int:
    """Establece contrasena final (no temporal)."""
    from models import AdminUser, db  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    try:
        pwd = (password or "").strip() if password is not None else ""
        if not pwd:
            pwd = _prompt_password("Contrasena nueva")
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}")
        return 2

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        r.set_password(pwd)
        r.must_change_password = False
        r.password_changed_at = datetime.utcnow()
        _reset_lock_state(r)
        db.session.commit()
        print("Contrasena actualizada (final) y usuario habilitado.")

    return 0


def cmd_reset_password(app, username: str, temp_password: str | None) -> int:
    """Emite contrasena temporal y desbloquea."""
    from models import AdminUser, db  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    if temp_password == "__PROMPT__":
        pwd = _prompt_password("Contrasena temporal")
    else:
        pwd = (temp_password or "").strip()
    if not pwd:
        length = int(os.getenv("ADMIN_TEMP_PASSWORD_LENGTH") or "12")
        pwd = _generate_temp_password(length=length)

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        r.set_password(pwd)
        r.must_change_password = True
        r.temp_password_issued_at = datetime.utcnow()
        r.password_changed_at = None
        _reset_lock_state(r)
        db.session.commit()

        print("Contrasena temporal reiniciada para:", r.username)
        print("Contrasena temporal:", pwd)
        print("Nota: Al iniciar sesion, el sistema obligara a cambiarla.")

    return 0


def cmd_unlock(app, username: str) -> int:
    """Desbloquea un usuario admin (temporal o permanente) sin cambiar contrasena."""
    from models import AdminUser, db  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        _reset_lock_state(r)
        db.session.commit()
        print("Usuario desbloqueado.")

    return 0


def cmd_delete(app, username: str) -> int:
    from models import AdminUser, db  # type: ignore

    u = AdminUser.normalize_username(username)
    if not u:
        print("Usuario invalido.")
        return 2

    with app.app_context():
        r = AdminUser.query.filter_by(username=u).first()
        if not r:
            print("No existe.")
            return 1

        db.session.delete(r)
        db.session.commit()
        print("Eliminado.")

    return 0


EPILOG = """USO:
  python manage_admin_users.py <comando> [opciones]

COMANDOS:
  list
    - Lista usuarios Admin.
    - Opcional: --limit N, --search "texto"

  show
    - Muestra el detalle de un usuario.
    - Requiere: --user <username>

  add
    - Crea un usuario con contrasena TEMPORAL (obliga a cambiar al iniciar sesion).
    - Requiere: --nombre "..." --user <username>
    - Opcional: --temp-pass "..."  (o --temp-pass para pedirla oculta)

  update
    - Actualiza nombre y/o username.
    - Requiere: --user <username>

  set-password
    - Establece la contrasena FINAL (quita el cambio obligatorio) y habilita.
    - Requiere: --user <username>
    - Opcional: --pass "..." (si no se pasa, la pide oculta)

  reset-password
    - Emite una nueva contrasena TEMPORAL, desbloquea y obliga a cambiar.
    - Requiere: --user <username>
    - Opcional: --temp-pass "..." (o --temp-pass para pedirla oculta)

  unlock
    - Desbloquea (reinicia intentos/bloqueos) sin cambiar contrasena.
    - Requiere: --user <username>

  delete
    - Elimina el usuario Admin.
    - Requiere: --user <username>
"""

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manage_admin_users.py",
        description="CLI para administrar usuarios Admin (login /admin) en la BD.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=EPILOG,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Listar usuarios admin")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--search", type=str, default=None)

    p_show = sub.add_parser("show", help="Ver un usuario")
    p_show.add_argument("--user", required=True)

    p_add = sub.add_parser("add", help="Crear usuario con contrasena temporal")
    p_add.add_argument("--nombre", required=True)
    p_add.add_argument("--user", required=True)
    p_add.add_argument(
        "--temp-pass",
        dest="temp_password",
        nargs="?",
        const="__PROMPT__",
        default=None,
        help="Contrasena temporal. Si se omite, se genera automaticamente. Si se usa sin valor, se pedira oculta por consola.",
    )
    # Alias por compatibilidad: --pass (igual que --temp-pass)
    p_add.add_argument(
        "--pass",
        dest="temp_password",
        nargs="?",
        const="__PROMPT__",
        help="Alias de --temp-pass.",
    )

    p_up = sub.add_parser("update", help="Actualizar usuario")
    p_up.add_argument("--user", required=True)
    p_up.add_argument("--nombre", default=None)
    p_up.add_argument("--new-user", default=None)

    p_sp = sub.add_parser("set-password", help="Establecer contrasena final")
    p_sp.add_argument("--user", required=True)
    p_sp.add_argument("--pass", dest="password", default=None)

    p_rp = sub.add_parser("reset-password", help="Reiniciar contrasena (temporal) y desbloquear")
    p_rp.add_argument("--user", required=True)
    p_rp.add_argument(
        "--temp-pass",
        dest="temp_password",
        nargs="?",
        const="__PROMPT__",
        default=None,
        help="Contrasena temporal. Si se omite, se genera automaticamente. Si se usa sin valor, se pedira oculta por consola.",
    )
    # Alias por compatibilidad: --pass (igual que --temp-pass)
    p_rp.add_argument(
        "--pass",
        dest="temp_password",
        nargs="?",
        const="__PROMPT__",
        help="Alias de --temp-pass.",
    )

    p_un = sub.add_parser("unlock", help="Desbloquear usuario (reinicia intentos/bloqueos)")
    p_un.add_argument("--user", required=True)

    p_del = sub.add_parser("delete", help="Eliminar usuario")
    p_del.add_argument("--user", required=True)

    return p


def main(argv: list[str]) -> int:
    os.environ.setdefault("APP_MODE", os.getenv("APP_MODE", "development"))

    parser = build_parser()
    args = parser.parse_args(argv)

    app = _bootstrap_app()

    if args.cmd == "list":
        return cmd_list(app, limit=args.limit, search=args.search)
    if args.cmd == "show":
        return cmd_show(app, username=args.user)
    if args.cmd == "add":
        return cmd_add(app, nombre=args.nombre, username=args.user, temp_password=args.temp_password)
    if args.cmd == "update":
        return cmd_update(app, username=args.user, nombre=args.nombre, new_user=args.new_user)
    if args.cmd == "set-password":
        return cmd_set_password(app, username=args.user, password=args.password)
    if args.cmd == "reset-password":
        return cmd_reset_password(app, username=args.user, temp_password=args.temp_password)
    if args.cmd == "unlock":
        return cmd_unlock(app, username=args.user)
    if args.cmd == "delete":
        return cmd_delete(app, username=args.user)

    print("Comando no reconocido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
