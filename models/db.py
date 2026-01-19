from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def init_db(app) -> None:
    """Inicializa SQLAlchemy con la app."""
    db.init_app(app)
