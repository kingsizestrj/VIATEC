import os
from flask import Flask, redirect, url_for
from flask_cors import CORS


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

    origins = app.config["CORS_ORIGINS"]
    origins_val = "*" if origins.strip() == "*" else [o.strip() for o in origins.split(",") if o.strip()]
    # supports_credentials só quando há origens explícitas (cookies de sessão exigem
    # origem específica; com "*" o navegador proíbe credenciais mesmo).
    CORS(app, resources={r"/tec/api/*": {"origins": origins_val}},
         supports_credentials=(origins_val != "*"))

    from viabilidade.api import bp_api
    from viabilidade.tec import bp_tec
    from viabilidade.admin import bp_admin
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_tec)
    app.register_blueprint(bp_admin)

    @app.route("/")
    def root():
        return redirect(url_for("tec.index"))

    from viabilidade.auth import seed_admin
    seed_admin(app.config["USERS_FILE"], app.config["ADMIN_USER"], app.config["ADMIN_PASS"])

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=False)
