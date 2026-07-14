import os
from flask import Flask, jsonify


def create_app(test_config=None):
    app = Flask(__name__)

    cfg = {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DATA_DIR": os.environ.get("DATA_DIR", "/app/data"),
        "RAIO_DEFAULT": float(os.environ.get("RAIO_METROS", "200")),
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "*"),
        "ADMIN_USER": os.environ.get("ADMIN_USER"),
        "ADMIN_PASS": os.environ.get("ADMIN_PASS"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get("COOKIE_SECURE", "1") == "1",
    }
    if test_config:
        cfg.update(test_config)
    app.config.update(cfg)

    dd = app.config["DATA_DIR"]
    os.makedirs(dd, exist_ok=True)
    app.config["KML_FILE"] = os.path.join(dd, "caixas.kml")
    app.config["CACHE_FILE"] = os.path.join(dd, "caixas_cache.json")
    app.config["USERS_FILE"] = os.path.join(dd, "tecnicos.json")
    app.config["CONFIG_FILE"] = os.path.join(dd, "config.json")

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY não definida — defina a variável de ambiente SECRET_KEY")

    @app.route("/")
    def root():
        return jsonify({"ok": True})  # substituído por redirect na Task 10

    return app
