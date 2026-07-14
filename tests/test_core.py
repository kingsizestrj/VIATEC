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
