import pytest
from viabilidade import core


def test_haversine_mesmo_ponto_zero():
    assert core.haversine(-23.55, -46.63, -23.55, -46.63) == pytest.approx(0.0, abs=1e-6)


def test_haversine_um_grau_de_latitude():
    # 1 grau de latitude ~ 111.19 km
    assert core.haversine(0.0, 0.0, 1.0, 0.0) == pytest.approx(111195, rel=1e-3)


def test_caixas_mais_proximas_ordena_e_limita():
    caixas = [
        {"nome": "A", "descricao": "", "lat": 0.0, "lon": 0.0},
        {"nome": "B", "descricao": "", "lat": 0.01, "lon": 0.0},   # ~1.1 km
        {"nome": "C", "descricao": "", "lat": 0.05, "lon": 0.0},   # ~5.5 km
    ]
    r = core.caixas_mais_proximas(caixas, 0.0, 0.0, 2)
    assert [c["nome"] for c in r] == ["A", "B"]
    assert r[0]["distancia_metros"] == pytest.approx(0.0, abs=0.1)
    assert "distancia_metros" in r[1]


def test_caixas_mais_proximas_nao_muta_original():
    caixas = [{"nome": "A", "descricao": "", "lat": 0.0, "lon": 0.0}]
    core.caixas_mais_proximas(caixas, 1.0, 1.0, 5)
    assert "distancia_metros" not in caixas[0]


import os
import json

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "exemplo.kml")


def test_parse_kml_extrai_placemarks():
    caixas = core.parse_kml(FIXTURE)
    assert len(caixas) == 2
    a = caixas[0]
    assert a["nome"] == "CTO-01"
    assert a["descricao"] == "8 portas livres"
    assert a["lon"] == pytest.approx(-46.6333)
    assert a["lat"] == pytest.approx(-23.5505)
    assert caixas[1]["descricao"] == ""


def test_save_e_load_cache(tmp_path):
    cache = str(tmp_path / "cache.json")
    kml = str(tmp_path / "nao_existe.kml")
    core.save_cache(cache, [{"nome": "X", "descricao": "", "lat": 1.0, "lon": 2.0}])
    assert core.load_caixas(cache, kml)[0]["nome"] == "X"


def test_load_caixas_parseia_kml_quando_sem_cache(tmp_path):
    cache = str(tmp_path / "cache.json")
    caixas = core.load_caixas(cache, FIXTURE)
    assert len(caixas) == 2
    assert os.path.exists(cache)  # cache gerado a partir do KML


def test_load_caixas_vazio_sem_kml_sem_cache(tmp_path):
    assert core.load_caixas(str(tmp_path / "c.json"), str(tmp_path / "k.kml")) == []


def test_load_config_default_quando_sem_arquivo(tmp_path):
    cfg = core.load_config(str(tmp_path / "config.json"), 200.0)
    assert cfg["raio_metros"] == 200.0


def test_save_e_load_config(tmp_path):
    path = str(tmp_path / "config.json")
    core.save_config(path, {"raio_metros": 350.0})
    assert core.load_config(path, 200.0)["raio_metros"] == 350.0
