import pytest
from flask import Flask
from viabilidade.tec import bp_tec
from viabilidade import auth
from app import create_app


@pytest.fixture(autouse=True)
def _limpa_rate_limit():
    auth._TENTATIVAS.clear()
    yield


@pytest.fixture
def client(tmp_path):
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "t"
    app.config["TESTING"] = True     # evita o time.sleep de atraso nas falhas de login
    uf = str(tmp_path / "tecnicos.json")
    app.config["USERS_FILE"] = uf
    auth.criar_usuario(uf, "joao", "João", "1234", role="tec")
    app.register_blueprint(bp_tec)
    return app.test_client()


def test_tec_index_redireciona_sem_login(client):
    r = client.get("/tec/")
    assert r.status_code == 302
    assert "/tec/login" in r.headers["Location"]


def test_login_valido_entra(client):
    r = client.post("/tec/login", data={"username": "joao", "senha": "1234"})
    assert r.status_code == 302
    assert "/tec" in r.headers["Location"]
    assert client.get("/tec/").status_code == 200


def test_login_invalido_401(client):
    r = client.post("/tec/login", data={"username": "joao", "senha": "x"})
    assert r.status_code == 401


def test_logout_encerra_sessao(client):
    client.post("/tec/login", data={"username": "joao", "senha": "1234"})
    client.get("/tec/logout")
    assert client.get("/tec/").status_code == 302


def test_login_bloqueia_apos_muitas_falhas(client):
    auth._TENTATIVAS.clear()
    for _ in range(auth.MAX_TENTATIVAS):
        client.post("/tec/login", data={"username": "joao", "senha": "errada"})
    # bloqueado agora mesmo com a senha certa
    r = client.post("/tec/login", data={"username": "joao", "senha": "1234"})
    assert r.status_code == 429


def test_login_next_externo_ignorado(client):
    r = client.post("/tec/login?next=https://evil.com", data={"username": "joao", "senha": "1234"})
    assert r.status_code == 302
    assert r.headers["Location"] == "/tec/"
    assert "evil.com" not in r.headers["Location"]


def test_login_next_local_respeitado(client):
    r = client.post("/tec/login?next=/tec/", data={"username": "joao", "senha": "1234"})
    assert r.status_code == 302
    assert r.headers["Location"] == "/tec/"


def test_sw_servido_em_tec_com_escopo_correto(tmp_path):
    # Usa o create_app real (static_folder default = raiz do projeto) para que
    # send_static_file encontre static/tec/sw.js de verdade.
    app = create_app({
        "SECRET_KEY": "t",
        "DATA_DIR": str(tmp_path),
        "TESTING": True,
        "ADMIN_USER": "admin",
        "ADMIN_PASS": "admin1234",
    })
    client = app.test_client()
    r = client.get("/tec/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["Content-Type"]
    assert "vt-shell" in r.get_data(as_text=True)
