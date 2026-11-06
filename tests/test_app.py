from fastapi.testclient import TestClient

from elden_lore_api.config import get_settings
from elden_lore_api.main import create_app


def test_health() -> None:
    client = TestClient(create_app(manage_database=False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_ready_without_driver() -> None:
    client = TestClient(create_app(manage_database=False))

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Neo4j driver is not initialized"}


def test_web_app_is_served_at_root() -> None:
    client = TestClient(create_app(manage_database=False))

    response = client.get("/")

    assert response.status_code == 200
    assert "The Lands Between Archive" in response.text


def test_public_policy_pages_are_served() -> None:
    client = TestClient(create_app(manage_database=False))

    assert client.get("/privacy.html").status_code == 200
    assert client.get("/legal.html").status_code == 200


def test_editorial_surface_can_be_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NEO4J_PASSWORD", "n" * 32)
    monkeypatch.setenv("EDITORIAL_TOKEN", "e" * 48)
    monkeypatch.setenv("EDITORIAL_ENABLED", "false")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app(manage_database=False))

        page = client.get("/editorial.html")
        api = client.get("/api/v1/editorial/dashboard")
        discovery = client.get("/api/v1").json()["resources"]

        assert page.status_code == 404
        assert api.status_code == 404
        assert "editorial" not in discovery
    finally:
        get_settings.cache_clear()
