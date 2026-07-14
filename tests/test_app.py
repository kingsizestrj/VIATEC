def test_create_app_returns_app_and_sets_paths(app):
    assert app.config["SECRET_KEY"] == "test-secret"
    assert app.config["KML_FILE"].endswith("caixas.kml")
    assert app.config["USERS_FILE"].endswith("tecnicos.json")


def test_missing_secret_key_raises():
    import pytest
    from app import create_app
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": None, "DATA_DIR": "/tmp/vt-test-nokey"})


def test_root_redireciona_para_tec(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/tec" in r.headers["Location"]


def test_admin_semeado_no_boot(app):
    from viabilidade import auth
    u = auth.verificar_usuario(app.config["USERS_FILE"], "admin", "admin123")
    assert u is not None and u["role"] == "admin"


def test_cors_header_na_api(client):
    # Sem login a rota redireciona, mas o cabeçalho CORS é aplicado pela extensão.
    r = client.get("/tec/api/caixas", headers={"Origin": "https://exemplo.com"})
    assert r.headers.get("Access-Control-Allow-Origin") is not None


def test_login_tecnico_ponta_a_ponta(app, client):
    from viabilidade import auth
    auth.criar_usuario(app.config["USERS_FILE"], "joao", "João", "1234", role="tec")
    assert client.get("/tec/api/caixas").status_code == 302
    client.post("/tec/login", data={"username": "joao", "senha": "1234"})
    assert client.get("/tec/api/caixas").status_code == 200
