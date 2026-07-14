import os
import time
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app)
from .core import parse_kml, save_cache, load_caixas, load_config, save_config
from .auth import (verificar_usuario, login_session, logout_session, criar_usuario,
                   listar_usuarios, set_ativo, remover_usuario, load_users, admin_required,
                   login_bloqueado, registrar_falha, registrar_sucesso, next_seguro)

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


@bp_admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        chave = "admin:" + (request.form.get("username", "").strip().lower() or "?") + "|" + (request.remote_addr or "?")
        if login_bloqueado(chave):
            return render_template("admin_login.html", erro="Muitas tentativas. Aguarde alguns minutos."), 429
        user = verificar_usuario(current_app.config["USERS_FILE"],
                                 request.form.get("username", ""),
                                 request.form.get("senha", ""))
        if user and user["role"] == "admin":
            registrar_sucesso(chave)
            login_session(session, user)
            return redirect(next_seguro(request.args.get("next"), url_for("admin.index")))
        registrar_falha(chave)
        if not current_app.config.get("TESTING"):
            time.sleep(0.5)
        return render_template("admin_login.html", erro="Credenciais inválidas"), 401
    return render_template("admin_login.html", erro=None)


@bp_admin.route("/logout")
@admin_required
def logout():
    logout_session(session)
    return redirect(url_for("admin.login"))


@bp_admin.route("/")
@admin_required
def index():
    cfg = current_app.config
    lista = load_caixas(cfg["CACHE_FILE"], cfg["KML_FILE"])
    conf = load_config(cfg["CONFIG_FILE"], cfg["RAIO_DEFAULT"])
    return render_template("admin.html",
                           total=len(lista),
                           raio=int(conf["raio_metros"]),
                           tem_kml=os.path.exists(cfg["KML_FILE"]),
                           tecnicos=listar_usuarios(cfg["USERS_FILE"], role="tec"))


@bp_admin.route("/upload", methods=["POST"])
@admin_required
def upload():
    f = request.files.get("kml")
    if not f or not f.filename.endswith(".kml"):
        flash("Envie um arquivo .kml", "erro")
        return redirect(url_for("admin.index"))
    f.save(current_app.config["KML_FILE"])
    try:
        caixas = parse_kml(current_app.config["KML_FILE"])
        save_cache(current_app.config["CACHE_FILE"], caixas)
        flash(f"KML carregado: {len(caixas)} caixas.", "ok")
    except Exception as e:
        flash(f"Erro ao processar KML: {e}", "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/raio", methods=["POST"])
@admin_required
def raio():
    try:
        novo = float(request.form["raio"])
        if novo <= 0:
            raise ValueError
        save_config(current_app.config["CONFIG_FILE"], {"raio_metros": novo})
        flash(f"Raio atualizado para {int(novo)}m", "ok")
    except (KeyError, ValueError):
        flash("Valor inválido para o raio", "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos", methods=["POST"])
@admin_required
def tecnicos_criar():
    try:
        criar_usuario(current_app.config["USERS_FILE"],
                      request.form.get("username", ""),
                      request.form.get("nome", ""),
                      request.form.get("senha", ""),
                      role="tec")
        flash("Técnico criado", "ok")
    except ValueError as e:
        flash(str(e), "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos/<username>/toggle", methods=["POST"])
@admin_required
def tecnicos_toggle(username):
    u = load_users(current_app.config["USERS_FILE"]).get(username)
    if u and u["role"] == "tec":
        set_ativo(current_app.config["USERS_FILE"], username, not u.get("ativo", True))
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos/<username>/delete", methods=["POST"])
@admin_required
def tecnicos_delete(username):
    u = load_users(current_app.config["USERS_FILE"]).get(username)
    if u and u["role"] == "tec":
        remover_usuario(current_app.config["USERS_FILE"], username)
    return redirect(url_for("admin.index"))
