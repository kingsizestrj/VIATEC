# App do Técnico — Viabilidade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um app dedicado (Flask + PWA) que ajuda técnicos em campo a encontrar, pelo GPS do celular, as caixas de fibra mais próximas — com login, navegação até a caixa e funcionamento offline — sem tocar na aplicação em produção.

**Architecture:** Cópia adaptada do `projeto-viabilidade`. Backend Flask organizado em um pacote `viabilidade/` (core de cálculo/KML, auth, e três blueprints: api, tec, admin) montado por uma factory `create_app()`. Tudo atrás de login por sessão; sem superfície pública. O frontend do técnico é uma PWA que baixa a lista de caixas ao logar, guarda em `localStorage` e calcula a caixa mais próxima **no navegador** (haversine em JS), funcionando offline. Deploy próprio via Docker + gunicorn, exposto pelo Nginx Proxy Manager já existente.

**Tech Stack:** Python 3.12, Flask 3, flask-cors, werkzeug (hash de senha), gunicorn, pytest. Frontend: HTML/CSS/JS puro, Leaflet 1.9.4 (vendorizado localmente), Service Worker + Web App Manifest.

## Global Constraints

- Python: **3.12** (imagem `python:3.12-slim`).
- Dependências de runtime: **flask==3.0.3, flask-cors==4.0.1, requests==2.32.3, werkzeug==3.0.3, gunicorn**. **Remover `xmltodict`** (dependência morta). `requests` fica para uso futuro/paridade, mas não é usado no fluxo do técnico.
- Dependência de teste: **pytest**.
- Todos os dados persistem em `DATA_DIR` (default `/app/data`), um volume Docker: `caixas.kml`, `caixas_cache.json`, `tecnicos.json`, `config.json`.
- Senhas **sempre** com hash (`werkzeug.security`), nunca em texto puro.
- **Nenhuma rota** serve dados sem sessão, exceto as telas/POST de login e os estáticos.
- `SECRET_KEY` vem de variável de ambiente; a app **não sobe** sem ela.
- Marca/copy: nome do app "Voltec Técnico". Textos de UI em **pt-BR**.
- N (número de caixas mais próximas exibidas) = **5**, definido como constante `N_CAIXAS = 5` em `static/tec/app.js`.
- Navegação: **Google Maps** via `https://www.google.com/maps/dir/?api=1&destination=LAT,LON`.
- Commits pequenos e frequentes (um por passo de "Commit").

## Interface Catalog (assinaturas canônicas — usar exatamente estes nomes)

`viabilidade/core.py`
```python
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float
def caixas_mais_proximas(caixas: list[dict], lat: float, lon: float, n: int) -> list[dict]
def parse_kml(kml_path: str) -> list[dict]              # [{"nome","descricao","lat","lon"}]
def save_cache(cache_file: str, caixas: list[dict]) -> None
def load_caixas(cache_file: str, kml_file: str) -> list[dict]
def load_config(config_file: str, default_raio: float) -> dict   # {"raio_metros": float}
def save_config(config_file: str, config: dict) -> None
```

`viabilidade/auth.py`
```python
def hash_senha(senha: str) -> str
def verificar_senha(senha_hash: str, senha: str) -> bool
def load_users(users_file: str) -> dict
def save_users(users_file: str, users: dict) -> None
def criar_usuario(users_file: str, username: str, nome: str, senha: str, role: str = "tec") -> None  # ValueError se inválido/duplicado
def verificar_usuario(users_file: str, username: str, senha: str) -> dict | None   # {"username","nome","role","ativo"}
def set_ativo(users_file: str, username: str, ativo: bool) -> None
def remover_usuario(users_file: str, username: str) -> None
def listar_usuarios(users_file: str, role: str = "tec") -> list[dict]   # [{"username","nome","ativo","role"}]
def seed_admin(users_file: str, admin_user: str | None, admin_pass: str | None) -> bool   # RuntimeError se não houver admin e faltar env
def login_session(session, user: dict) -> None
def logout_session(session) -> None
def usuario_atual(session) -> dict | None
def tec_required(f)     # decorator: redireciona /tec/login se sem sessão
def admin_required(f)   # decorator: redireciona /admin/login se não-admin
def login_bloqueado(chave: str) -> bool   # rate-limit: True se excedeu MAX_TENTATIVAS na janela
def registrar_falha(chave: str) -> None   # conta uma tentativa de login falha
def registrar_sucesso(chave: str) -> None # zera as tentativas da chave (login ok)
```

`viabilidade/api.py` → `bp_api` (url_prefix `/tec/api`): `GET /tec/api/caixas` → `{"total","raio_metros","atualizado_em","caixas":[...]}` `@tec_required`

`viabilidade/tec.py` → `bp_tec` (url_prefix `/tec`): endpoints `tec.login`, `tec.logout`, `tec.index`

`viabilidade/admin.py` → `bp_admin` (url_prefix `/admin`): endpoints `admin.login`, `admin.logout`, `admin.index`, `admin.upload`, `admin.raio`, `admin.tecnicos_criar`, `admin.tecnicos_toggle`, `admin.tecnicos_delete`

`app.py`: `def create_app(test_config: dict | None = None) -> Flask`

**Chaves de `app.config`:** `SECRET_KEY, DATA_DIR, RAIO_DEFAULT, CORS_ORIGINS, ADMIN_USER, ADMIN_PASS, KML_FILE, CACHE_FILE, USERS_FILE, CONFIG_FILE`.

## Contrato de DOM (ids/classes usados por `tec.html` + `app.js`)

- `#vt-status` — linha de status (GPS/offline/atualização).
- `#vt-destaque` — card da caixa mais próxima.
- `#vt-lista` — `<ul>` das próximas caixas.
- `#vt-map` — div do mapa Leaflet.
- Navegação: links (`.vt-nav` no destaque e `.mini-nav` na lista) com `href` de deep-link do Google Maps (`https://www.google.com/maps/dir/?api=1&destination=LAT,LON`), abertos em nova aba.

## File Structure

```
projeto-viabilidade-tecnico/
  app.py                      # create_app()
  viabilidade/
    __init__.py
    core.py                   # cálculo + KML + cache + config
    auth.py                   # usuários + sessão + decorators
    api.py                    # bp_api
    tec.py                    # bp_tec
    admin.py                  # bp_admin
  templates/
    tec_login.html
    tec.html                  # shell (lógica em app.js)
    admin_login.html
    admin.html
  static/
    tec/  app.js  tec.css  manifest.webmanifest  sw.js  icons/icon-192.png  icons/icon-512.png
    vendor/leaflet/  leaflet.js  leaflet.css  images/
  tests/
    conftest.py
    test_core.py  test_auth.py  test_api.py  test_tec.py  test_admin.py  test_app.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  .dockerignore
  README.md
  pytest.ini
```

---

## Task 1: Skeleton do projeto + ferramentas de teste

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `viabilidade/__init__.py`, `app.py`, `tests/conftest.py`, `tests/test_app.py`, `.gitignore`

**Interfaces:**
- Produces: `create_app(test_config=None) -> Flask` (stub que já valida `SECRET_KEY`, cria `DATA_DIR`, define as chaves de path em `app.config`, e registra a rota `/` → 200 temporária). Blueprints são registrados nas Tasks 7–10.

- [ ] **Step 1: Criar `requirements.txt`**

```
flask==3.0.3
flask-cors==4.0.1
requests==2.32.3
werkzeug==3.0.3
gunicorn==22.0.0
pytest==8.2.0
```

- [ ] **Step 2: Criar `pytest.ini` e `.gitignore`**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
data/
```

- [ ] **Step 3: Criar `viabilidade/__init__.py` (vazio) e o teste que falha**

`tests/conftest.py`:
```python
import pytest
from app import create_app


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def app(data_dir):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "DATA_DIR": str(data_dir),
        "RAIO_DEFAULT": 200.0,
        "CORS_ORIGINS": "*",
        "ADMIN_USER": "admin",
        "ADMIN_PASS": "admin123",
        "SESSION_COOKIE_SECURE": False,
    })


@pytest.fixture
def client(app):
    return app.test_client()
```

`tests/test_app.py`:
```python
def test_create_app_returns_app_and_sets_paths(app):
    assert app.config["SECRET_KEY"] == "test-secret"
    assert app.config["KML_FILE"].endswith("caixas.kml")
    assert app.config["USERS_FILE"].endswith("tecnicos.json")


def test_missing_secret_key_raises():
    import pytest
    from app import create_app
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": None, "DATA_DIR": "/tmp/vt-test-nokey"})
```

- [ ] **Step 4: Rodar os testes e ver falhar**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL (ImportError: `create_app` — ainda não existe em `app.py`).

- [ ] **Step 5: Implementar o stub de `app.py`**

```python
import os
from flask import Flask, jsonify


def create_app(test_config=None):
    app = Flask(__name__)

    cfg = {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DATA_DIR": os.environ.get("DATA_DIR", "/app/data"),
        "RAIO_DEFAULT": float(os.environ.get("RAIO_METROS", "200")),
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "*"),
        "ADMIN_USER": os.environ.get("ADMIN_USER"),
        "ADMIN_PASS": os.environ.get("ADMIN_PASS"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get("COOKIE_SECURE", "1") == "1",
    }
    if test_config:
        cfg.update(test_config)
    app.config.update(cfg)

    dd = app.config["DATA_DIR"]
    os.makedirs(dd, exist_ok=True)
    app.config["KML_FILE"] = os.path.join(dd, "caixas.kml")
    app.config["CACHE_FILE"] = os.path.join(dd, "caixas_cache.json")
    app.config["USERS_FILE"] = os.path.join(dd, "tecnicos.json")
    app.config["CONFIG_FILE"] = os.path.join(dd, "config.json")

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY não definida — defina a variável de ambiente SECRET_KEY")

    @app.route("/")
    def root():
        return jsonify({"ok": True})  # substituído por redirect na Task 10

    return app
```

- [ ] **Step 6: Rodar os testes e ver passar**

Run: `python -m pytest tests/test_app.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini .gitignore viabilidade/__init__.py app.py tests/
git commit -m "chore: skeleton do app do técnico + harness de testes"
```

---

## Task 2: core — haversine e caixas_mais_proximas

**Files:**
- Create: `viabilidade/core.py`
- Test: `tests/test_core.py`

**Interfaces:**
- Produces: `haversine(...)`, `caixas_mais_proximas(...)` (ver Interface Catalog).

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_core.py`:
```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_core.py -v`
Expected: FAIL (ModuleNotFoundError / AttributeError).

- [ ] **Step 3: Implementar `viabilidade/core.py` (parte 1)**

```python
import math


def haversine(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos (lat/lon)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def caixas_mais_proximas(caixas, lat, lon, n):
    """As n caixas mais próximas de (lat, lon), ordenadas por distância.
    Cada item é uma cópia com a chave extra 'distancia_metros' (arredondada)."""
    enriquecidas = []
    for c in caixas:
        item = dict(c)
        item["distancia_metros"] = round(haversine(lat, lon, c["lat"], c["lon"]), 1)
        enriquecidas.append(item)
    enriquecidas.sort(key=lambda x: x["distancia_metros"])
    return enriquecidas[:n]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_core.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add viabilidade/core.py tests/test_core.py
git commit -m "feat(core): haversine e caixas_mais_proximas com testes"
```

---

## Task 3: core — parse_kml, load_caixas, save_cache

**Files:**
- Modify: `viabilidade/core.py`
- Test: `tests/test_core.py` (adicionar), `tests/fixtures/exemplo.kml` (criar)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `parse_kml`, `save_cache`, `load_caixas` (ver Interface Catalog).

- [ ] **Step 1: Criar a fixture `tests/fixtures/exemplo.kml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>CTO-01</name>
      <description>8 portas livres</description>
      <Point><coordinates>-46.6333,-23.5505,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>CTO-02</name>
      <Point><coordinates>-46.6350,-23.5510</coordinates></Point>
    </Placemark>
  </Document>
</kml>
```

- [ ] **Step 2: Escrever os testes que falham (adicionar ao fim de `tests/test_core.py`)**

```python
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
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_core.py -k "kml or cache" -v`
Expected: FAIL (AttributeError: parse_kml/save_cache/load_caixas).

- [ ] **Step 4: Implementar (adicionar ao `viabilidade/core.py`)**

```python
import json
import os
import xml.etree.ElementTree as ET


def parse_kml(kml_path):
    """Extrai placemarks do KML: [{'nome','descricao','lat','lon'}]."""
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

    caixas = []
    for pm in root.iter(f"{ns}Placemark"):
        name_el = pm.find(f"{ns}name")
        nome = name_el.text.strip() if name_el is not None and name_el.text else "Sem nome"

        desc_el = pm.find(f".//{ns}description")
        descricao = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        coord_el = pm.find(f".//{ns}coordinates")
        if coord_el is None or not coord_el.text:
            continue
        first = coord_el.text.strip().split()[0]
        parts = first.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        caixas.append({"nome": nome, "descricao": descricao, "lat": lat, "lon": lon})
    return caixas


def save_cache(cache_file, caixas):
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(caixas, f, ensure_ascii=False)


def load_caixas(cache_file, kml_file):
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    if os.path.exists(kml_file):
        caixas = parse_kml(kml_file)
        save_cache(cache_file, caixas)
        return caixas
    return []
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_core.py -v`
Expected: PASS (8 passed).

- [ ] **Step 6: Commit**

```bash
git add viabilidade/core.py tests/test_core.py tests/fixtures/exemplo.kml
git commit -m "feat(core): parse_kml, load_caixas e save_cache com testes"
```

---

## Task 4: core — persistência do raio (config)

**Files:**
- Modify: `viabilidade/core.py`
- Test: `tests/test_core.py` (adicionar)

**Interfaces:**
- Produces: `load_config`, `save_config` (ver Interface Catalog).

- [ ] **Step 1: Escrever os testes que falham (adicionar ao fim de `tests/test_core.py`)**

```python
def test_load_config_default_quando_sem_arquivo(tmp_path):
    cfg = core.load_config(str(tmp_path / "config.json"), 200.0)
    assert cfg["raio_metros"] == 200.0


def test_save_e_load_config(tmp_path):
    path = str(tmp_path / "config.json")
    core.save_config(path, {"raio_metros": 350.0})
    assert core.load_config(path, 200.0)["raio_metros"] == 350.0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_core.py -k config -v`
Expected: FAIL (AttributeError).

- [ ] **Step 3: Implementar (adicionar ao `viabilidade/core.py`)**

```python
def load_config(config_file, default_raio):
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"raio_metros": float(data.get("raio_metros", default_raio))}
    return {"raio_metros": float(default_raio)}


def save_config(config_file, config):
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"raio_metros": float(config["raio_metros"])}, f)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_core.py -k config -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add viabilidade/core.py tests/test_core.py
git commit -m "feat(core): persistência do raio (load_config/save_config)"
```

---

## Task 5: auth — hash de senha e store de usuários

**Files:**
- Create: `viabilidade/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces: `hash_senha`, `verificar_senha`, `load_users`, `save_users`, `criar_usuario`, `verificar_usuario`, `set_ativo`, `remover_usuario`, `listar_usuarios`, `seed_admin` (ver Interface Catalog).

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_auth.py`:
```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implementar `viabilidade/auth.py` (parte 1 — store)**

```python
import json
import os
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_auth.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add viabilidade/auth.py tests/test_auth.py
git commit -m "feat(auth): store de usuários com hash de senha e seed de admin"
```

---

## Task 6: auth — sessão e decorators

**Files:**
- Modify: `viabilidade/auth.py`
- Test: `tests/test_auth.py` (adicionar)

**Interfaces:**
- Consumes: `verificar_usuario` (Task 5).
- Produces: `login_session`, `logout_session`, `usuario_atual`, `tec_required`, `admin_required` (ver Interface Catalog).

- [ ] **Step 1: Escrever os testes que falham (adicionar ao fim de `tests/test_auth.py`)**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_auth.py -k "required or sessao or atual or rate_limit" -v`
Expected: FAIL (AttributeError: tec_required / login_bloqueado).

- [ ] **Step 3: Implementar (adicionar ao `viabilidade/auth.py`)**

```python
import time
from functools import wraps
from flask import session as flask_session, redirect, url_for, request


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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_auth.py -v`
Expected: PASS (14 passed).

- [ ] **Step 5: Commit**

```bash
git add viabilidade/auth.py tests/test_auth.py
git commit -m "feat(auth): sessão, decorators e limitador de brute-force no login"
```

---

## Task 7: blueprint do técnico (login + tela)

**Files:**
- Create: `viabilidade/tec.py`, `templates/tec_login.html`, `templates/tec.html`
- Test: `tests/test_tec.py`

**Interfaces:**
- Consumes: `verificar_usuario`, `login_session`, `logout_session`, `tec_required` (auth); `create_app` (Task 1, será estendido na Task 10 para registrar `bp_tec` — nos testes desta task registramos o blueprint manualmente).
- Produces: `bp_tec` com endpoints `tec.login`, `tec.logout`, `tec.index`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_tec.py`:
```python
import pytest
from flask import Flask
from viabilidade.tec import bp_tec
from viabilidade import auth


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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_tec.py -v`
Expected: FAIL (ModuleNotFoundError: viabilidade.tec).

- [ ] **Step 3: Implementar `viabilidade/tec.py`**

```python
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
```

- [ ] **Step 4: Criar `templates/tec_login.html`**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Voltec Técnico — Entrar</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='tec/tec.css') }}"/>
</head>
<body class="vt-login-body">
  <form class="vt-login" method="POST" action="{{ url_for('tec.login') }}">
    <h1>Voltec Técnico</h1>
    {% if erro %}<p class="vt-erro">{{ erro }}</p>{% endif %}
    <input name="username" placeholder="Usuário" autocomplete="username" required/>
    <input name="senha" type="password" placeholder="Senha" autocomplete="current-password" required/>
    <button type="submit">Entrar</button>
  </form>
</body>
</html>
```

- [ ] **Step 5: Criar `templates/tec.html` (shell — a lógica vem na Task 12)**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover"/>
  <title>Voltec Técnico</title>
  <link rel="manifest" href="{{ url_for('static', filename='tec/manifest.webmanifest') }}"/>
  <meta name="theme-color" content="#0a0e1a"/>
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/leaflet/leaflet.css') }}"/>
  <link rel="stylesheet" href="{{ url_for('static', filename='tec/tec.css') }}"/>
</head>
<body class="vt-app">
  <header class="vt-header">
    <span>📡 Voltec Técnico</span>
    <a href="{{ url_for('tec.logout') }}" class="vt-sair">Sair</a>
  </header>
  <div id="vt-status" class="vt-status">Obtendo localização…</div>
  <div id="vt-destaque" class="vt-destaque"></div>
  <div id="vt-map" class="vt-map"></div>
  <ul id="vt-lista" class="vt-lista"></ul>
  <script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>
  <script src="{{ url_for('static', filename='tec/app.js') }}"></script>
</body>
</html>
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_tec.py -v`
Expected: PASS (5 passed). (Os templates renderizam; `tec.css`/`app.js`/leaflet ainda não existem, mas o teste checa apenas status/HTML, não os assets.)

- [ ] **Step 7: Commit**

```bash
git add viabilidade/tec.py templates/tec_login.html templates/tec.html tests/test_tec.py
git commit -m "feat(tec): blueprint de login e shell da tela do técnico"
```

---

## Task 8: blueprint admin (login, painel, upload, raio, técnicos)

**Files:**
- Create: `viabilidade/admin.py`, `templates/admin_login.html`, `templates/admin.html`
- Test: `tests/test_admin.py`

**Interfaces:**
- Consumes: `core.parse_kml/save_cache/load_caixas/load_config/save_config`; `auth.verificar_usuario/login_session/logout_session/criar_usuario/listar_usuarios/set_ativo/remover_usuario/load_users/admin_required`.
- Produces: `bp_admin` com endpoints `admin.login`, `admin.logout`, `admin.index`, `admin.upload`, `admin.raio`, `admin.tecnicos_criar`, `admin.tecnicos_toggle`, `admin.tecnicos_delete`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_admin.py`:
```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_admin.py -v`
Expected: FAIL (ModuleNotFoundError: viabilidade.admin).

- [ ] **Step 3: Implementar `viabilidade/admin.py`**

```python
import os
import time
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app)
from .core import parse_kml, save_cache, load_caixas, load_config, save_config
from .auth import (verificar_usuario, login_session, logout_session, criar_usuario,
                   listar_usuarios, set_ativo, remover_usuario, load_users, admin_required,
                   login_bloqueado, registrar_falha, registrar_sucesso)

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


@bp_admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        chave = "admin:" + (request.form.get("username", "").strip().lower() or "?") + "|" + (request.remote_addr or "?")
        if login_bloqueado(chave):
            return render_template("admin_login.html", erro="Muitas tentativas. Aguarde alguns minutos."), 429
        user = verificar_usuario(current_app.config["USERS_FILE"],
                                 request.form.get("username", ""),
                                 request.form.get("senha", ""))
        if user and user["role"] == "admin":
            registrar_sucesso(chave)
            login_session(session, user)
            return redirect(request.args.get("next") or url_for("admin.index"))
        registrar_falha(chave)
        if not current_app.config.get("TESTING"):
            time.sleep(0.5)
        return render_template("admin_login.html", erro="Credenciais inválidas"), 401
    return render_template("admin_login.html", erro=None)


@bp_admin.route("/logout")
@admin_required
def logout():
    logout_session(session)
    return redirect(url_for("admin.login"))


@bp_admin.route("/")
@admin_required
def index():
    cfg = current_app.config
    lista = load_caixas(cfg["CACHE_FILE"], cfg["KML_FILE"])
    conf = load_config(cfg["CONFIG_FILE"], cfg["RAIO_DEFAULT"])
    return render_template("admin.html",
                           total=len(lista),
                           raio=int(conf["raio_metros"]),
                           tem_kml=os.path.exists(cfg["KML_FILE"]),
                           tecnicos=listar_usuarios(cfg["USERS_FILE"], role="tec"))


@bp_admin.route("/upload", methods=["POST"])
@admin_required
def upload():
    f = request.files.get("kml")
    if not f or not f.filename.endswith(".kml"):
        flash("Envie um arquivo .kml", "erro")
        return redirect(url_for("admin.index"))
    f.save(current_app.config["KML_FILE"])
    try:
        caixas = parse_kml(current_app.config["KML_FILE"])
        save_cache(current_app.config["CACHE_FILE"], caixas)
        flash(f"KML carregado: {len(caixas)} caixas.", "ok")
    except Exception as e:
        flash(f"Erro ao processar KML: {e}", "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/raio", methods=["POST"])
@admin_required
def raio():
    try:
        novo = float(request.form["raio"])
        if novo <= 0:
            raise ValueError
        save_config(current_app.config["CONFIG_FILE"], {"raio_metros": novo})
        flash(f"Raio atualizado para {int(novo)}m", "ok")
    except (KeyError, ValueError):
        flash("Valor inválido para o raio", "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos", methods=["POST"])
@admin_required
def tecnicos_criar():
    try:
        criar_usuario(current_app.config["USERS_FILE"],
                      request.form.get("username", ""),
                      request.form.get("nome", ""),
                      request.form.get("senha", ""),
                      role="tec")
        flash("Técnico criado", "ok")
    except ValueError as e:
        flash(str(e), "erro")
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos/<username>/toggle", methods=["POST"])
@admin_required
def tecnicos_toggle(username):
    u = load_users(current_app.config["USERS_FILE"]).get(username)
    if u and u["role"] == "tec":
        set_ativo(current_app.config["USERS_FILE"], username, not u.get("ativo", True))
    return redirect(url_for("admin.index"))


@bp_admin.route("/tecnicos/<username>/delete", methods=["POST"])
@admin_required
def tecnicos_delete(username):
    u = load_users(current_app.config["USERS_FILE"]).get(username)
    if u and u["role"] == "tec":
        remover_usuario(current_app.config["USERS_FILE"], username)
    return redirect(url_for("admin.index"))
```

- [ ] **Step 4: Criar `templates/admin_login.html`**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Admin — Entrar</title>
  <style>
    body{background:#0a0e1a;color:#e8edf5;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
    form{background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:28px;width:300px;display:flex;flex-direction:column;gap:12px}
    h1{font-size:1.1rem;margin:0 0 8px}
    input{padding:10px;border-radius:8px;border:1px solid #1e2d45;background:#0a0e1a;color:#e8edf5}
    button{padding:10px;border:0;border-radius:8px;background:#00d4ff;color:#0a0e1a;font-weight:700;cursor:pointer}
    .erro{color:#ff4560;font-size:.85rem;margin:0}
  </style>
</head>
<body>
  <form method="POST" action="{{ url_for('admin.login') }}">
    <h1>Painel Admin</h1>
    {% if erro %}<p class="erro">{{ erro }}</p>{% endif %}
    <input name="username" placeholder="Usuário" required/>
    <input name="senha" type="password" placeholder="Senha" required/>
    <button type="submit">Entrar</button>
  </form>
</body>
</html>
```

- [ ] **Step 5: Criar `templates/admin.html`**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Viabilidade — Painel Admin</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/leaflet/leaflet.css') }}"/>
  <style>
    :root{--bg:#0a0e1a;--surface:#111827;--surface2:#1a2236;--border:#1e2d45;--accent:#00d4ff;--accent2:#00ff88;--danger:#ff4560;--text:#e8edf5;--muted:#6b7e99}
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif}
    header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;gap:12px;align-items:center}
    header a{margin-left:auto;color:var(--muted);text-decoration:none}
    .layout{display:grid;grid-template-columns:380px 1fr;height:calc(100vh - 57px)}
    .sidebar{padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;background:var(--surface)}
    .card{background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px}
    .card h2{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:12px}
    input,button{font:inherit}
    input[type=file],input[type=number],input[type=text],input[type=password]{width:100%;padding:9px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);margin-bottom:8px}
    button{padding:9px 12px;border:0;border-radius:8px;background:var(--accent);color:var(--bg);font-weight:700;cursor:pointer}
    button.danger{background:var(--danger);color:#fff}
    .stats{display:flex;gap:12px}
    .stat{flex:1;background:var(--bg);border-radius:8px;padding:12px;text-align:center}
    .stat b{font-size:1.6rem;color:var(--accent)}
    .flash{border-radius:8px;padding:10px 12px;font-size:.85rem}
    .flash.ok{background:rgba(0,255,136,.1);border:1px solid var(--accent2);color:var(--accent2)}
    .flash.erro{background:rgba(255,69,96,.1);border:1px solid var(--danger);color:var(--danger)}
    table{width:100%;border-collapse:collapse;font-size:.85rem}
    td,th{text-align:left;padding:6px 4px;border-bottom:1px solid var(--border)}
    .inline{display:inline}
    #map{width:100%;height:100%}
    @media(max-width:768px){.layout{grid-template-columns:1fr;grid-template-rows:auto 360px;height:auto}}
  </style>
</head>
<body>
  <header>
    <span>📡 Viabilidade — Admin</span>
    {% if tem_kml %}<span style="color:var(--accent2)">● KML ativo</span>{% endif %}
    <a href="{{ url_for('admin.logout') }}">Sair</a>
  </header>
  <div class="layout">
    <aside class="sidebar">
      {% with msgs = get_flashed_messages(with_categories=true) %}
        {% for cat, msg in msgs %}<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}
      {% endwith %}

      <div class="card">
        <h2>Resumo</h2>
        <div class="stats">
          <div class="stat"><b>{{ total }}</b><div>caixas</div></div>
          <div class="stat"><b>{{ raio }}m</b><div>raio</div></div>
        </div>
      </div>

      <div class="card">
        <h2>Carregar KML</h2>
        <form action="{{ url_for('admin.upload') }}" method="POST" enctype="multipart/form-data">
          <input type="file" name="kml" accept=".kml" required/>
          <button type="submit">Enviar e processar</button>
        </form>
      </div>

      <div class="card">
        <h2>Raio de atendimento</h2>
        <form action="{{ url_for('admin.raio') }}" method="POST">
          <input type="number" name="raio" value="{{ raio }}" min="10" max="5000" step="10"/>
          <button type="submit">Salvar</button>
        </form>
      </div>

      <div class="card">
        <h2>Técnicos</h2>
        <form action="{{ url_for('admin.tecnicos_criar') }}" method="POST">
          <input type="text" name="username" placeholder="Usuário" required/>
          <input type="text" name="nome" placeholder="Nome"/>
          <input type="password" name="senha" placeholder="Senha" required/>
          <button type="submit">Adicionar técnico</button>
        </form>
        <table>
          <tr><th>Usuário</th><th>Nome</th><th></th></tr>
          {% for t in tecnicos %}
          <tr>
            <td>{{ t.username }}{% if not t.ativo %} <small>(inativo)</small>{% endif %}</td>
            <td>{{ t.nome }}</td>
            <td>
              <form class="inline" method="POST" action="{{ url_for('admin.tecnicos_toggle', username=t.username) }}">
                <button type="submit">{{ 'Desativar' if t.ativo else 'Ativar' }}</button>
              </form>
              <form class="inline" method="POST" action="{{ url_for('admin.tecnicos_delete', username=t.username) }}">
                <button class="danger" type="submit">Remover</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </table>
      </div>
    </aside>
    <main><div id="map"></div></main>
  </div>

  <script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>
  <script>
    const map = L.map('map').setView([-15.78, -47.93], 4);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {subdomains:'abcd', maxZoom:19, attribution:'© OSM © CARTO'}).addTo(map);
    fetch("/tec/api/caixas", {credentials: "same-origin"}).then(r => r.json()).then(d => {
      const pts = [];
      (d.caixas || []).forEach(c => {
        L.marker([c.lat, c.lon]).addTo(map).bindPopup('<b>' + c.nome + '</b><br>' + (c.descricao || ''));
        pts.push([c.lat, c.lon]);
      });
      if (pts.length) map.fitBounds(pts, {padding: [40, 40]});
    });
  </script>
</body>
</html>
```

Nota: o mapa do admin faz `fetch("/tec/api/caixas")` (caminho literal, não `url_for`) — assim o template renderiza mesmo nos testes desta task, onde `bp_api` não está registrado. Nos testes o mapa não é exercitado (checam status/CRUD, não JS).

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_admin.py -v`
Expected: PASS (6 passed).

- [ ] **Step 7: Commit**

```bash
git add viabilidade/admin.py templates/admin_login.html templates/admin.html tests/test_admin.py
git commit -m "feat(admin): painel com login, upload KML, raio e CRUD de técnicos"
```

---

## Task 9: blueprint da API de dados (`/tec/api/caixas`)

**Files:**
- Create: `viabilidade/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `core.load_caixas/load_config`; `auth.tec_required/criar_usuario`.
- Produces: `bp_api` com endpoint `api.caixas` → `GET /tec/api/caixas`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_api.py`:
```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL (ModuleNotFoundError: viabilidade.api).

- [ ] **Step 3: Implementar `viabilidade/api.py`**

```python
import os
from datetime import datetime
from flask import Blueprint, jsonify, current_app
from .core import load_caixas, load_config
from .auth import tec_required

bp_api = Blueprint("api", __name__, url_prefix="/tec/api")


@bp_api.route("/caixas")
@tec_required
def caixas():
    cfg = current_app.config
    lista = load_caixas(cfg["CACHE_FILE"], cfg["KML_FILE"])
    conf = load_config(cfg["CONFIG_FILE"], cfg["RAIO_DEFAULT"])
    atualizado = None
    if os.path.exists(cfg["CACHE_FILE"]):
        atualizado = datetime.fromtimestamp(os.path.getmtime(cfg["CACHE_FILE"])).isoformat(timespec="seconds")
    return jsonify({
        "total": len(lista),
        "raio_metros": conf["raio_metros"],
        "atualizado_em": atualizado,
        "caixas": lista,
    })
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_api.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add viabilidade/api.py tests/test_api.py
git commit -m "feat(api): endpoint autenticado /tec/api/caixas"
```

---

## Task 10: Montagem final da factory (create_app)

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py` (adicionar)

**Interfaces:**
- Consumes: `bp_api`, `bp_tec`, `bp_admin`, `auth.seed_admin`.
- Produces: `create_app` completo — registra os 3 blueprints, aplica CORS em `/tec/api/*`, `/` → redirect para `tec.index`, e semeia o admin.

- [ ] **Step 1: Escrever os testes que falham (adicionar ao fim de `tests/test_app.py`)**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL (`/` retorna 200 do stub, não 302; sem blueprints registrados).

- [ ] **Step 3: Reescrever `app.py` com a factory completa**

```python
import os
from flask import Flask, redirect, url_for
from flask_cors import CORS


def create_app(test_config=None):
    app = Flask(__name__)

    cfg = {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DATA_DIR": os.environ.get("DATA_DIR", "/app/data"),
        "RAIO_DEFAULT": float(os.environ.get("RAIO_METROS", "200")),
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "*"),
        "ADMIN_USER": os.environ.get("ADMIN_USER"),
        "ADMIN_PASS": os.environ.get("ADMIN_PASS"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get("COOKIE_SECURE", "1") == "1",
    }
    if test_config:
        cfg.update(test_config)
    app.config.update(cfg)

    dd = app.config["DATA_DIR"]
    os.makedirs(dd, exist_ok=True)
    app.config["KML_FILE"] = os.path.join(dd, "caixas.kml")
    app.config["CACHE_FILE"] = os.path.join(dd, "caixas_cache.json")
    app.config["USERS_FILE"] = os.path.join(dd, "tecnicos.json")
    app.config["CONFIG_FILE"] = os.path.join(dd, "config.json")

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY não definida — defina a variável de ambiente SECRET_KEY")

    origins = app.config["CORS_ORIGINS"]
    origins_val = "*" if origins.strip() == "*" else [o.strip() for o in origins.split(",") if o.strip()]
    # supports_credentials só quando há origens explícitas (cookies de sessão exigem
    # origem específica; com "*" o navegador proíbe credenciais mesmo).
    CORS(app, resources={r"/tec/api/*": {"origins": origins_val}},
         supports_credentials=(origins_val != "*"))

    from viabilidade.api import bp_api
    from viabilidade.tec import bp_tec
    from viabilidade.admin import bp_admin
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_tec)
    app.register_blueprint(bp_admin)

    @app.route("/")
    def root():
        return redirect(url_for("tec.index"))

    from viabilidade.auth import seed_admin
    seed_admin(app.config["USERS_FILE"], app.config["ADMIN_USER"], app.config["ADMIN_PASS"])

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=False)
```

- [ ] **Step 4: Rodar toda a suíte e ver passar**

Run: `python -m pytest -v`
Expected: PASS (todos os testes das Tasks 1–10).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat(app): factory registra blueprints, CORS na API, root->/tec e seed do admin"
```

---

## Task 11: Vendorizar o Leaflet localmente

**Files:**
- Create: `static/vendor/leaflet/leaflet.js`, `static/vendor/leaflet/leaflet.css`, `static/vendor/leaflet/images/*`

**Interfaces:**
- Consumes: nada. Produces: assets locais do Leaflet usados por `admin.html` e `tec.html`.

- [ ] **Step 1: Baixar o Leaflet 1.9.4 para `static/vendor/leaflet/`**

```bash
mkdir -p static/vendor/leaflet/images
curl -fsSL https://unpkg.com/leaflet@1.9.4/dist/leaflet.js  -o static/vendor/leaflet/leaflet.js
curl -fsSL https://unpkg.com/leaflet@1.9.4/dist/leaflet.css -o static/vendor/leaflet/leaflet.css
for img in marker-icon.png marker-icon-2x.png marker-shadow.png layers.png layers-2x.png; do
  curl -fsSL "https://unpkg.com/leaflet@1.9.4/dist/images/$img" -o "static/vendor/leaflet/images/$img"
done
```

- [ ] **Step 2: Verificar que os arquivos existem e não estão vazios**

Run: `ls -l static/vendor/leaflet/leaflet.js static/vendor/leaflet/leaflet.css && test -s static/vendor/leaflet/leaflet.js && echo OK`
Expected: `OK` e tamanhos > 0. (Se offline, obter os arquivos do Leaflet 1.9.4 por outro meio e colocá-los nesses caminhos.)

- [ ] **Step 3: Commit**

```bash
git add static/vendor/leaflet
git commit -m "chore: vendoriza Leaflet 1.9.4 (sem CDN)"
```

---

## Task 12: Frontend do técnico (app.js + tec.css)

**Files:**
- Create: `static/tec/app.js`, `static/tec/tec.css`

**Interfaces:**
- Consumes: `GET /tec/api/caixas` (Task 9); contrato de DOM (`#vt-status`, `#vt-destaque`, `#vt-lista`, `#vt-map`; navegação por `href`/deep-link); Leaflet global `L` (Task 11).
- Produces: comportamento da tela do técnico. A lógica pura em JS (`haversine`/`maisProximas`) é um espelho fiel de `core.haversine`/`caixas_mais_proximas`, já cobertos por testes unitários na Task 2; a verificação de ponta a ponta é **manual** no navegador/celular (Step 3 abaixo e Task 14).

- [ ] **Step 1: Criar `static/tec/tec.css`**

```css
:root{--bg:#0a0e1a;--surface:#111827;--border:#1e2d45;--accent:#00d4ff;--accent2:#00ff88;--danger:#ff4560;--text:#e8edf5;--muted:#6b7e99}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,sans-serif}
.vt-login-body{display:flex;min-height:100vh;align-items:center;justify-content:center}
.vt-login{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:28px;width:300px;display:flex;flex-direction:column;gap:12px}
.vt-login h1{font-size:1.1rem}
.vt-login input{padding:11px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text)}
.vt-login button{padding:11px;border:0;border-radius:8px;background:var(--accent);color:var(--bg);font-weight:700}
.vt-erro{color:var(--danger);font-size:.85rem}
.vt-app{display:flex;flex-direction:column;min-height:100vh}
.vt-header{display:flex;align-items:center;gap:8px;padding:14px 16px;background:var(--surface);border-bottom:1px solid var(--border);font-weight:600}
.vt-sair{margin-left:auto;color:var(--muted);text-decoration:none;font-size:.85rem}
.vt-status{padding:8px 16px;font-size:.8rem;color:var(--muted);background:var(--surface)}
.vt-status.offline{color:var(--danger)}
.vt-destaque{margin:12px 16px;padding:16px;border-radius:12px;background:var(--surface);border:1px solid var(--border);border-left:4px solid var(--accent2)}
.vt-destaque h2{font-size:1.1rem;color:var(--accent2)}
.vt-destaque .dist{font-size:2rem;font-weight:700}
.vt-destaque .desc{color:var(--muted);font-size:.85rem;margin-top:4px}
.vt-nav{display:inline-block;margin-top:10px;padding:10px 16px;background:var(--accent);color:var(--bg);border:0;border-radius:8px;font-weight:700;text-decoration:none;cursor:pointer}
.vt-map{height:38vh;margin:0 16px;border-radius:12px;overflow:hidden}
.vt-lista{list-style:none;margin:12px 16px 32px}
.vt-lista li{display:flex;align-items:center;gap:10px;padding:12px;border-bottom:1px solid var(--border)}
.vt-lista .nome{font-weight:600}
.vt-lista .m{margin-left:auto;color:var(--accent);font-variant-numeric:tabular-nums}
.vt-lista .mini-nav{padding:6px 10px;border-radius:6px;background:var(--surface);border:1px solid var(--border);color:var(--text);text-decoration:none;font-size:.8rem}
```

- [ ] **Step 2: Criar `static/tec/app.js`**

```javascript
(function () {
  "use strict";
  const N_CAIXAS = 5;
  const CACHE_KEY = "vt_caixas";
  const CACHE_TS = "vt_caixas_ts";

  let caixas = [];
  let pos = null;
  let map = null, meMarker = null, boxLayer = null;

  const $ = (id) => document.getElementById(id);

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000, rad = Math.PI / 180;
    const dphi = (lat2 - lat1) * rad, dl = (lon2 - lon1) * rad;
    const a = Math.sin(dphi / 2) ** 2 +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function maisProximas(lista, lat, lon, n) {
    return lista
      .map((c) => Object.assign({}, c, { d: haversine(lat, lon, c.lat, c.lon) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, n);
  }

  function fmt(m) { return m >= 1000 ? (m / 1000).toFixed(2) + " km" : Math.round(m) + " m"; }
  function navUrl(lat, lon) { return "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lon; }

  async function carregarCaixas() {
    try {
      const r = await fetch("/tec/api/caixas", { credentials: "same-origin" });
      if (r.status === 401 || r.status === 302 || r.redirected) { location.href = "/tec/login"; return; }
      const data = await r.json();
      caixas = data.caixas || [];
      localStorage.setItem(CACHE_KEY, JSON.stringify(caixas));
      localStorage.setItem(CACHE_TS, new Date().toISOString());
      status("Caixas atualizadas agora (" + caixas.length + ")");
    } catch (e) {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        caixas = JSON.parse(cached);
        const ts = localStorage.getItem(CACHE_TS);
        status("Offline — dados de " + (ts ? new Date(ts).toLocaleString("pt-BR") : "?"), true);
      } else {
        status("Sem conexão e sem dados salvos. Conecte-se uma vez para baixar as caixas.", true);
      }
    }
    render();
  }

  function status(msg, off) {
    const el = $("vt-status");
    el.textContent = msg;
    el.classList.toggle("offline", !!off);
  }

  function initMap() {
    if (map || !window.L) return;
    map = L.map("vt-map").setView([-15.78, -47.93], 4);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { subdomains: "abcd", maxZoom: 19, attribution: "© OSM © CARTO" }).addTo(map);
    boxLayer = L.layerGroup().addTo(map);
  }

  function render() {
    if (!pos) return;
    const perto = maisProximas(caixas, pos.lat, pos.lon, N_CAIXAS);
    const dest = $("vt-destaque");
    if (!perto.length) {
      dest.innerHTML = "<p>Nenhuma caixa cadastrada.</p>";
    } else {
      const c = perto[0];
      dest.innerHTML =
        '<h2>' + c.nome + '</h2>' +
        '<div class="dist">' + fmt(c.d) + '</div>' +
        (c.descricao ? '<div class="desc">' + c.descricao + '</div>' : '') +
        '<a class="vt-nav" href="' + navUrl(c.lat, c.lon) + '" target="_blank" rel="noopener">Navegar ▸</a>';
    }
    const ul = $("vt-lista");
    ul.innerHTML = perto.slice(1).map((c) =>
      '<li><span class="nome">' + c.nome + '</span><span class="m">' + fmt(c.d) + '</span>' +
      '<a class="mini-nav" href="' + navUrl(c.lat, c.lon) + '" target="_blank" rel="noopener">Ir</a></li>'
    ).join("");

    initMap();
    if (map) {
      if (!meMarker) meMarker = L.circleMarker([pos.lat, pos.lon], { radius: 8, color: "#00d4ff" }).addTo(map);
      else meMarker.setLatLng([pos.lat, pos.lon]);
      boxLayer.clearLayers();
      const pts = [[pos.lat, pos.lon]];
      perto.forEach((c) => {
        L.marker([c.lat, c.lon]).addTo(boxLayer).bindPopup("<b>" + c.nome + "</b><br>" + fmt(c.d));
        pts.push([c.lat, c.lon]);
      });
      map.fitBounds(pts, { padding: [40, 40], maxZoom: 17 });
    }
  }

  function iniciarGPS() {
    if (!navigator.geolocation) { status("GPS indisponível neste dispositivo", true); return; }
    navigator.geolocation.watchPosition(
      (p) => { pos = { lat: p.coords.latitude, lon: p.coords.longitude }; render(); },
      () => status("Não foi possível obter o GPS. Verifique a permissão de localização.", true),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    );
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/tec/sw.js").catch(() => {});
  }
  carregarCaixas();
  iniciarGPS();
})();
```

- [ ] **Step 3: Verificação manual rápida no navegador**

Run: `SECRET_KEY=dev ADMIN_USER=admin ADMIN_PASS=admin123 DATA_DIR=./data COOKIE_SECURE=0 python app.py`
Abra `http://localhost:5000/tec`, faça login (`admin`/`admin123` só existe como admin — crie um técnico pelo `/admin` antes, ou use o admin como técnico não funciona: admin não é `tec`). Passo prático: entre em `/admin/login`, crie um técnico, depois faça login em `/tec/login`. Permita o GPS. Confirme: status atualiza, card de destaque aparece, lista e mapa renderizam, botão "Navegar" abre o Google Maps.
Expected: tela funcional (com o KML carregado no admin).

- [ ] **Step 4: Commit**

```bash
git add static/tec/app.js static/tec/tec.css
git commit -m "feat(tec): tela do técnico — GPS ao vivo, N mais próximas, mapa e navegar"
```

---

## Task 13: PWA — manifest, service worker e ícones

**Files:**
- Create: `static/tec/manifest.webmanifest`, `static/tec/sw.js`, `static/tec/icons/icon-192.png`, `static/tec/icons/icon-512.png`

**Interfaces:**
- Consumes: assets de `static/tec/` e `static/vendor/leaflet/`.
- Produces: instalabilidade ("adicionar à tela inicial") e casca offline.

- [ ] **Step 1: Criar `static/tec/manifest.webmanifest`**

```json
{
  "name": "Voltec Técnico",
  "short_name": "Voltec Téc",
  "start_url": "/tec/",
  "scope": "/tec/",
  "display": "standalone",
  "background_color": "#0a0e1a",
  "theme_color": "#0a0e1a",
  "icons": [
    { "src": "/static/tec/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/tec/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: Criar `static/tec/sw.js`**

```javascript
const CACHE = "vt-shell-v1";
const SHELL = [
  "/tec/",
  "/static/tec/app.js",
  "/static/tec/tec.css",
  "/static/vendor/leaflet/leaflet.js",
  "/static/vendor/leaflet/leaflet.css",
  "/static/tec/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/tec/api/")) return; // dados: sempre rede (o app.js trata o cache em localStorage)

  const ehHTML = e.request.mode === "navigation" || url.pathname === "/tec/" || url.pathname === "/tec";
  if (ehHTML) {
    // network-first para o HTML: pega da rede e atualiza o cache; cai no cache se offline
    e.respondWith(
      fetch(e.request)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put("/tec/", copia));
          return resp;
        })
        .catch(() => caches.match(e.request).then((hit) => hit || caches.match("/tec/")))
    );
    return;
  }

  // cache-first para estáticos
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
```

- [ ] **Step 3: Gerar os ícones PNG (192 e 512)**

```bash
python - <<'PY'
import struct, zlib
def png(path, size, rgb=(10,14,26)):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = b""
    row = bytes(rgb) * size
    for _ in range(size):
        raw += b"\x00" + row
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
png("static/tec/icons/icon-192.png", 192)
png("static/tec/icons/icon-512.png", 512)
print("ok")
PY
```

(Placeholder sólido na cor de tema; substituível depois pela logo real.)

- [ ] **Step 4: Verificar manifest e SW no navegador**

Run: reinicie `python app.py`, abra `/tec` no Chrome, DevTools → Application → Manifest (sem erros) e Service Workers (ativado). Ligue "Offline" e recarregue: a casca do app carrega e a lista usa o cache do `localStorage`.
Expected: instalável; casca funciona offline.

- [ ] **Step 5: Commit**

```bash
git add static/tec/manifest.webmanifest static/tec/sw.js static/tec/icons
git commit -m "feat(pwa): manifest, service worker e ícones do app do técnico"
```

---

## Task 14: Deploy — Docker, gunicorn e README

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `README.md`

**Interfaces:**
- Consumes: `create_app` (gunicorn chama a factory).
- Produces: imagem executável e instruções de deploy/NPM.

- [ ] **Step 1: Criar `.dockerignore`**

```
__pycache__/
*.pyc
.venv/
data/
tests/
docs/
.git/
```

- [ ] **Step 2: Criar `Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY viabilidade/ viabilidade/
COPY templates/ templates/
COPY static/ static/

VOLUME ["/app/data"]
ENV RAIO_METROS=200
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/tec/login || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
```

- [ ] **Step 3: Criar `docker-compose.yml`**

```yaml
services:
  viabilidade-tecnico:
    build: .
    container_name: viabilidade-tecnico
    restart: unless-stopped
    ports:
      - "5001:5000"           # host:container — 5001 no host p/ não colidir com a app de produção
    volumes:
      - tecnico_data:/app/data
    environment:
      - SECRET_KEY=${SECRET_KEY:?defina SECRET_KEY}
      - ADMIN_USER=${ADMIN_USER:-admin}
      - ADMIN_PASS=${ADMIN_PASS:?defina ADMIN_PASS}
      - RAIO_METROS=200
      - CORS_ORIGINS=*
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/tec/login"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  tecnico_data:
    driver: local
```

- [ ] **Step 4: Criar `README.md`**

````markdown
# Viabilidade — App do Técnico

App dedicado que ajuda técnicos em campo a achar, pelo GPS, as caixas de fibra
mais próximas. Deploy independente da aplicação de produção do widget do cliente.

## Rodar local

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
SECRET_KEY=dev ADMIN_USER=admin ADMIN_PASS=admin123 DATA_DIR=./data COOKIE_SECURE=0 python app.py
```

- Admin: http://localhost:5000/admin/login  (suba o KML, defina o raio, crie técnicos)
- Técnico: http://localhost:5000/tec/login

## Testes

```bash
python -m pytest -v
```

## Deploy (Docker + Nginx Proxy Manager)

```bash
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
export ADMIN_USER=admin
export ADMIN_PASS='uma-senha-forte'
docker compose up -d --build
```

No **Nginx Proxy Manager** (já existente em produção): crie um **Proxy Host**
apontando `tecnico.voltecautomacao.com.br` → `IP_DO_HOST:5001`, ative **SSL**
(Let's Encrypt) e **Block Common Exploits**. Não é necessário nenhum bloqueio de
`text/html` — o login já protege tudo.

## Variáveis de ambiente

| Var | Obrigatória | Default | Descrição |
|---|---|---|---|
| `SECRET_KEY` | sim | — | Chave de sessão do Flask |
| `ADMIN_USER` / `ADMIN_PASS` | 1º boot | — | Cria o admin inicial |
| `RAIO_METROS` | não | 200 | Raio default (ajustável no admin) |
| `CORS_ORIGINS` | não | `*` | Origens permitidas na API (`/tec/api/*`) |
| `DATA_DIR` | não | `/app/data` | Pasta de dados persistentes |

## Uso pelo técnico

1. Abrir a URL no celular e fazer login.
2. "Adicionar à tela inicial" (instala como app).
3. Permitir a localização. A tela mostra a caixa mais próxima, a lista das
   próximas e um mapa; "Navegar" abre o Google Maps.
4. Funciona offline após o primeiro acesso (as caixas ficam salvas no aparelho).
````

- [ ] **Step 5: Testar a imagem Docker**

```bash
export SECRET_KEY=teste ADMIN_USER=admin ADMIN_PASS=admin123
docker compose up -d --build
sleep 8
curl -fsS http://localhost:5001/tec/login | grep -q "Voltec Técnico" && echo "SUBIU OK"
docker compose down
```
Expected: `SUBIU OK`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore README.md
git commit -m "chore: deploy com gunicorn, Docker e instruções de NPM"
```

---

## Notas de execução

- Ao começar, copie do `projeto-viabilidade` original **apenas** o que ajudar de
  referência; este plano recria os módulos do zero via TDD (não copie `app.py`,
  o widget do cliente, nem o arquivo `data` de 0 byte).
- Rode `python -m pytest -v` ao final de cada task de backend; a suíte deve ficar
  sempre verde.
- Tasks 12 e 13 (frontend/PWA) são verificadas manualmente no celular, conforme a
  seção de testes do spec.
