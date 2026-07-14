import io
import pytest
from flask import Flask
from viabilidade.admin import bp_admin
from viabilidade import auth, core


@pytest.fixture
def ctx(tmp_path):
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "t"
    app.config.update(
        USERS_FILE=str(tmp_path / "tecnicos.json"),
        KML_FILE=str(tmp_path / "caixas.kml"),
        CACHE_FILE=str(tmp_path / "cache.json"),
        CONFIG_FILE=str(tmp_path / "config.json"),
        RAIO_DEFAULT=200.0,
        TESTING=True,
    )
    auth.criar_usuario(app.config["USERS_FILE"], "admin", "Admin", "adm", role="admin")
    app.register_blueprint(bp_admin)
    return app, app.test_client()


def login_admin(client):
    return client.post("/admin/login", data={"username": "admin", "senha": "adm"})


def test_admin_index_protegido(ctx):
    _, client = ctx
    assert client.get("/admin/").status_code == 302


def test_admin_login_e_painel(ctx):
    _, client = ctx
    assert login_admin(client).status_code == 302
    assert client.get("/admin/").status_code == 200


def test_upload_kml_popula_cache(ctx):
    app, client = ctx
    login_admin(client)
    kml = b'<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><name>C1</name><Point><coordinates>-46.6,-23.5</coordinates></Point></Placemark></kml>'
    client.post("/admin/upload", data={"kml": (io.BytesIO(kml), "rede.kml")},
                content_type="multipart/form-data")
    assert len(core.load_caixas(app.config["CACHE_FILE"], app.config["KML_FILE"])) == 1


def test_raio_persiste(ctx):
    app, client = ctx
    login_admin(client)
    client.post("/admin/raio", data={"raio": "300"})
    assert core.load_config(app.config["CONFIG_FILE"], 200.0)["raio_metros"] == 300.0


def test_crud_tecnicos(ctx):
    app, client = ctx
    login_admin(client)
    client.post("/admin/tecnicos", data={"username": "joao", "nome": "João", "senha": "1"})
    assert [u["username"] for u in auth.listar_usuarios(app.config["USERS_FILE"])] == ["joao"]
    client.post("/admin/tecnicos/joao/toggle")
    assert auth.listar_usuarios(app.config["USERS_FILE"])[0]["ativo"] is False
    client.post("/admin/tecnicos/joao/delete")
    assert auth.listar_usuarios(app.config["USERS_FILE"]) == []
