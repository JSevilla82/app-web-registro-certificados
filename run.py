from __future__ import annotations

import os

from app import crear_app
import config


def _ssl_context():
    if not config.ENABLE_SSL:
        return None

    cert = os.getenv("SSL_CERT_PATH")
    key = os.getenv("SSL_KEY_PATH")
    if cert and key:
        return (cert, key)

    # certificado temporal para desarrollo.
    if os.getenv("SSL_ADHOC", "").strip().lower() in {"1", "true", "yes", "y", "on"}:
        return "adhoc"

    return None


app = crear_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=config.DEBUG,
        ssl_context=_ssl_context(),
    )
