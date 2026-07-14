import time
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from .auth import (verificar_usuario, login_session, logout_session, tec_required,
                   login_bloqueado, registrar_falha, registrar_sucesso)

bp_tec = Blueprint("tec", __name__, url_prefix="/tec")


@bp_tec.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        chave = (request.form.get("username", "").strip().lower() or "?") + "|" + (request.remote_addr or "?")
        if login_bloqueado(chave):
            return render_template("tec_login.html", erro="Muitas tentativas. Aguarde alguns minutos."), 429
        user = verificar_usuario(
            current_app.config["USERS_FILE"],
            request.form.get("username", ""),
            request.form.get("senha", ""),
        )
        if user:
            registrar_sucesso(chave)
            login_session(session, user)
            return redirect(request.args.get("next") or url_for("tec.index"))
        registrar_falha(chave)
        if not current_app.config.get("TESTING"):
            time.sleep(0.5)
        return render_template("tec_login.html", erro="Usuário ou senha inválidos"), 401
    return render_template("tec_login.html", erro=None)


@bp_tec.route("/logout")
@tec_required
def logout():
    logout_session(session)
    return redirect(url_for("tec.login"))


@bp_tec.route("/")
@tec_required
def index():
    return render_template("tec.html", nome=session.get("nome", ""))


@bp_tec.route("/sw.js")
def service_worker():
    resp = current_app.send_static_file("tec/sw.js")
    resp.headers["Service-Worker-Allowed"] = "/tec/"
    resp.headers["Content-Type"] = "application/javascript"
    return resp
