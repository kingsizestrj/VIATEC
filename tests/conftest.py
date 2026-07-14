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
