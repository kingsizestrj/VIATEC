import json
import os
import time
from functools import wraps
from flask import session as flask_session, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash


def hash_senha(senha):
    return generate_password_hash(senha)


def verificar_senha(senha_hash, senha):
    return check_password_hash(senha_hash, senha)


def load_users(users_file):
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users_file, users):
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def criar_usuario(users_file, username, nome, senha, role="tec"):
    username = (username or "").strip().lower()
    if not username or not senha:
        raise ValueError("Usuário e senha são obrigatórios")
    users = load_users(users_file)
    if username in users:
        raise ValueError("Usuário já existe")
    users[username] = {
        "nome": (nome or username).strip(),
        "senha_hash": hash_senha(senha),
        "role": role,
        "ativo": True,
    }
    save_users(users_file, users)


def verificar_usuario(users_file, username, senha):
    username = (username or "").strip().lower()
    u = load_users(users_file).get(username)
    if not u or not u.get("ativo", True):
        return None
    if not verificar_senha(u["senha_hash"], senha or ""):
        return None
    return {"username": username, "nome": u["nome"], "role": u["role"], "ativo": u["ativo"]}


def set_ativo(users_file, username, ativo):
    users = load_users(users_file)
    if username in users:
        users[username]["ativo"] = bool(ativo)
        save_users(users_file, users)


def remover_usuario(users_file, username):
    users = load_users(users_file)
    if username in users:
        del users[username]
        save_users(users_file, users)


def listar_usuarios(users_file, role="tec"):
    users = load_users(users_file)
    return [
        {"username": k, "nome": v["nome"], "ativo": v.get("ativo", True), "role": v["role"]}
        for k, v in sorted(users.items())
        if v["role"] == role
    ]


def seed_admin(users_file, admin_user, admin_pass):
    users = load_users(users_file)
    if any(u.get("role") == "admin" for u in users.values()):
        return False
    if not admin_user or not admin_pass:
        raise RuntimeError("Nenhum admin cadastrado e ADMIN_USER/ADMIN_PASS não definidos")
    criar_usuario(users_file, admin_user, "Administrador", admin_pass, role="admin")
    return True


def login_session(session, user):
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["nome"] = user.get("nome", "")


def logout_session(session):
    session.clear()


def usuario_atual(session):
    if session.get("username"):
        return {"username": session["username"], "role": session.get("role"), "nome": session.get("nome", "")}
    return None


def tec_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not flask_session.get("username"):
            return redirect(url_for("tec.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if flask_session.get("role") != "admin":
            return redirect(url_for("admin.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


# ── Proteção leve contra brute-force (em memória, por worker) ──
_TENTATIVAS = {}          # chave -> lista de timestamps de falhas recentes
MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 300


def _falhas_recentes(chave, agora):
    recentes = [t for t in _TENTATIVAS.get(chave, []) if agora - t < JANELA_SEGUNDOS]
    if recentes:
        _TENTATIVAS[chave] = recentes
    else:
        _TENTATIVAS.pop(chave, None)
    return recentes


def login_bloqueado(chave):
    return len(_falhas_recentes(chave, time.time())) >= MAX_TENTATIVAS


def registrar_falha(chave):
    agora = time.time()
    _falhas_recentes(chave, agora)
    _TENTATIVAS.setdefault(chave, []).append(agora)


def registrar_sucesso(chave):
    _TENTATIVAS.pop(chave, None)
