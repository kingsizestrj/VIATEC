import pytest
from viabilidade import auth


def users_file(tmp_path):
    return str(tmp_path / "tecnicos.json")


def test_hash_e_verifica_senha():
    h = auth.hash_senha("segredo")
    assert h != "segredo"
    assert auth.verificar_senha(h, "segredo") is True
    assert auth.verificar_senha(h, "errada") is False


def test_criar_e_verificar_usuario(tmp_path):
    uf = users_file(tmp_path)
    auth.criar_usuario(uf, "Joao", "João Silva", "1234", role="tec")
    u = auth.verificar_usuario(uf, "joao", "1234")   # username normalizado p/ minúsculo
    assert u["username"] == "joao"
    assert u["role"] == "tec"
    assert auth.verificar_usuario(uf, "joao", "xxxx") is None


def test_criar_usuario_duplicado_erro(tmp_path):
    uf = users_file(tmp_path)
    auth.criar_usuario(uf, "joao", "J", "1")
    with pytest.raises(ValueError):
        auth.criar_usuario(uf, "joao", "J", "1")


def test_usuario_inativo_nao_autentica(tmp_path):
    uf = users_file(tmp_path)
    auth.criar_usuario(uf, "joao", "J", "1")
    auth.set_ativo(uf, "joao", False)
    assert auth.verificar_usuario(uf, "joao", "1") is None


def test_listar_e_remover(tmp_path):
    uf = users_file(tmp_path)
    auth.criar_usuario(uf, "joao", "J", "1")
    auth.criar_usuario(uf, "maria", "M", "1")
    assert {u["username"] for u in auth.listar_usuarios(uf)} == {"joao", "maria"}
    auth.remover_usuario(uf, "joao")
    assert {u["username"] for u in auth.listar_usuarios(uf)} == {"maria"}


def test_seed_admin_cria_uma_vez(tmp_path):
    uf = users_file(tmp_path)
    assert auth.seed_admin(uf, "admin", "senha") is True
    assert auth.seed_admin(uf, "admin", "senha") is False   # já existe admin
    assert auth.verificar_usuario(uf, "admin", "senha")["role"] == "admin"


def test_seed_admin_sem_env_e_sem_admin_erro(tmp_path):
    with pytest.raises(RuntimeError):
        auth.seed_admin(users_file(tmp_path), None, None)


from flask import Flask, session, jsonify


def make_app():
    app = Flask(__name__)
    app.secret_key = "t"

    @app.route("/set/<role>")
    def do_set(role):
        auth.login_session(session, {"username": "u", "nome": "U", "role": role})
        return "ok"

    @app.route("/atual")
    def atual():
        return jsonify(auth.usuario_atual(session) or {})

    @app.route("/protegida-tec")
    @auth.tec_required
    def protegida_tec():
        return "tec-ok"

    @app.route("/protegida-admin")
    @auth.admin_required
    def protegida_admin():
        return "admin-ok"

    # blueprints reais definem tec.login e admin.login; aqui criamos stubs com esses endpoints
    @app.route("/tec/login", endpoint="tec.login")
    def tec_login():
        return "tec-login"

    @app.route("/admin/login", endpoint="admin.login")
    def admin_login():
        return "admin-login"

    return app


def test_tec_required_redireciona_sem_sessao():
    c = make_app().test_client()
    r = c.get("/protegida-tec")
    assert r.status_code == 302
    assert "/tec/login" in r.headers["Location"]


def test_tec_required_permite_com_sessao():
    c = make_app().test_client()
    c.get("/set/tec")
    assert c.get("/protegida-tec").data == b"tec-ok"


def test_admin_required_bloqueia_tec():
    c = make_app().test_client()
    c.get("/set/tec")
    r = c.get("/protegida-admin")
    assert r.status_code == 302
    assert "/admin/login" in r.headers["Location"]


def test_admin_required_permite_admin():
    c = make_app().test_client()
    c.get("/set/admin")
    assert c.get("/protegida-admin").data == b"admin-ok"


def test_rate_limit_bloqueia_apos_max_tentativas():
    auth._TENTATIVAS.clear()
    chave = "joao|1.2.3.4"
    for _ in range(auth.MAX_TENTATIVAS):
        assert auth.login_bloqueado(chave) is False
        auth.registrar_falha(chave)
    assert auth.login_bloqueado(chave) is True


def test_rate_limit_sucesso_zera():
    auth._TENTATIVAS.clear()
    chave = "joao|1.2.3.4"
    for _ in range(auth.MAX_TENTATIVAS):
        auth.registrar_falha(chave)
    auth.registrar_sucesso(chave)
    assert auth.login_bloqueado(chave) is False
