from fastapi.testclient import TestClient

from elden_lore_api.api_models import EntityDetail, EntitySubgraph
from elden_lore_api.main import create_app
from elden_lore_api.routers.entities import get_repository


class DiscoveryRepository:
    def get_entity(self, entity_id: str, **_: object) -> EntityDetail:
        return EntityDetail(
            id=entity_id,
            kind=entity_id.split(".", 1)[0],
            canonical_name=entity_id.split(".", 1)[1].replace("-", " ").title(),
            continuity="both",
            claims=[],
        )

    def get_subgraph(self, entity_id: str, **_: object) -> EntitySubgraph:
        return EntitySubgraph(
            root_id=entity_id,
            depth=1,
            nodes=[],
            edges=[],
            truncated=False,
        )


def client() -> TestClient:
    app = create_app(manage_database=False)
    app.dependency_overrides[get_repository] = DiscoveryRepository
    return TestClient(app)


def test_minimal_spoilers_only_return_introductory_collections() -> None:
    response = client().get("/api/v1/discovery?spoiler_level=minimal")

    assert response.status_code == 200
    collection_ids = {item["id"] for item in response.json()["collections"]}
    assert collection_ids == {"start.main-characters", "start.important-locations"}


def test_full_spoilers_include_dlc_collection() -> None:
    response = client().get("/api/v1/discovery?spoiler_level=full")

    assert response.status_code == 200
    collection_ids = {item["id"] for item in response.json()["collections"]}
    assert "start.realm-of-shadow" in collection_ids


def test_journey_contains_exactly_five_starting_points() -> None:
    response = client().get(
        "/api/v1/discovery/start.main-characters?spoiler_level=minimal"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["default_entity_id"] == "character.tarnished"
    assert len(data["entries"]) == 5


def test_spoiler_setting_blocks_hidden_journey() -> None:
    response = client().get(
        "/api/v1/discovery/start.realm-of-shadow?spoiler_level=minimal"
    )

    assert response.status_code == 403
