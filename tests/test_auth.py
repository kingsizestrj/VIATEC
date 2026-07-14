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
