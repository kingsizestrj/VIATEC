import os
from datetime import datetime
from flask import Blueprint, jsonify, current_app
from .core import load_caixas, load_config
from .auth import tec_required

bp_api = Blueprint("api", __name__, url_prefix="/tec/api")


@bp_api.route("/caixas")
@tec_required
def caixas():
    cfg = current_app.config
    lista = load_caixas(cfg["CACHE_FILE"], cfg["KML_FILE"])
    conf = load_config(cfg["CONFIG_FILE"], cfg["RAIO_DEFAULT"])
    atualizado = None
    if os.path.exists(cfg["CACHE_FILE"]):
        atualizado = datetime.fromtimestamp(os.path.getmtime(cfg["CACHE_FILE"])).isoformat(timespec="seconds")
    return jsonify({
        "total": len(lista),
        "raio_metros": conf["raio_metros"],
        "atualizado_em": atualizado,
        "caixas": lista,
    })
