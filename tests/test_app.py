def test_create_app_returns_app_and_sets_paths(app):
    assert app.config["SECRET_KEY"] == "test-secret"
    assert app.config["KML_FILE"].endswith("caixas.kml")
    assert app.config["USERS_FILE"].endswith("tecnicos.json")


def test_missing_secret_key_raises():
    import pytest
    from app import create_app
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": None, "DATA_DIR": "/tmp/vt-test-nokey"})
