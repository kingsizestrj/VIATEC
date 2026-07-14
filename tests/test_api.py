import pytest
from flask import Flask
from viabilidade.api import bp_api
from viabilidade.tec import bp_tec
from viabilidade import auth, core


@pytest.fixture
def client(tmp_path):
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "t"
    app.config.update(
        USERS_FILE=str(tmp_path / "tecnicos.json"),
        KML_FILE=str(tmp_path / "caixas.kml"),
        CACHE_FILE=str(tmp_path / "cache.json"),
        CONFIG_FILE=str(tmp_path / "config.json"),
        RAIO_DEFAULT=200.0,
    )
    auth.criar_usuario(app.config["USERS_FILE"], "joao", "João", "1234", role="tec")
    core.save_cache(app.config["CACHE_FILE"], [{"nome": "C1", "descricao": "d", "lat": -23.5, "lon": -46.6}])
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_tec)
    return app.test_client()


def test_caixas_exige_login(client):
    r = client.get("/tec/api/caixas")
    assert r.status_code == 302  # redireciona para /tec/login


def test_caixas_com_login_retorna_json(client):
    client.post("/tec/login", data={"username": "joao", "senha": "1234"})
    r = client.get("/tec/api/caixas")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["raio_metros"] == 200.0
    assert data["caixas"][0]["nome"] == "C1"
    assert "atualizado_em" in data
