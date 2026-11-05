from fastapi.testclient import TestClient

from elden_lore_api.api_models import (
    ClaimDetail,
    ConnectionPath,
    ConnectionResponse,
    EntitySummary,
    GraphEdge,
)
from elden_lore_api.main import create_app
from elden_lore_api.repository import _find_ranked_paths
from elden_lore_api.routers.entities import get_repository

RANNI = EntitySummary(
    id="character.ranni", kind="character", canonical_name="Ranni", continuity="base_game"
)
BLAIDD = EntitySummary(
    id="character.blaidd", kind="character", canonical_name="Blaidd", continuity="base_game"
)


def edge(
    edge_id: str,
    source: str,
    target: str,
    *,
    evidence_level: str = "explicit",
    verification_status: str = "game_verified",
) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        predicate="CONNECTED_TO",
        evidence_level=evidence_level,
        confidence="high",
        review_status="reviewed",
        verification_status=verification_status,
    )


def test_connection_paths_prefer_shorter_routes() -> None:
    paths, truncated = _find_ranked_paths(
        "a",
        "d",
        [edge("direct", "a", "d"), edge("ab", "a", "b"), edge("bd", "b", "d")],
        max_depth=3,
        limit=3,
    )

    assert paths[0] == (["a", "d"], ["direct"])
    assert truncated is False


def test_connection_paths_rank_stronger_evidence_first() -> None:
    paths, _ = _find_ranked_paths(
        "a",
        "d",
        [
            edge("weak-a", "a", "b", evidence_level="theory"),
            edge("weak-b", "b", "d", evidence_level="theory"),
            edge("strong-a", "a", "c"),
            edge("strong-b", "c", "d"),
        ],
        max_depth=2,
        limit=2,
    )

    assert paths[0][1] == ["strong-a", "strong-b"]


class ConnectionRepository:
    def find_connections(self, source_id: str, target_id: str, **_: object):
        if "missing" in {source_id, target_id}:
            return None
        claim = ClaimDetail(
            id="claim.blaidd-serves-ranni",
            predicate="SERVES",
            evidence_level="explicit",
            confidence="high",
            review_status="reviewed",
            verification_status="game_verified",
            continuity="base_game",
            subject=BLAIDD,
            object=RANNI,
            evidence=[],
        )
        return ConnectionResponse(
            source=RANNI,
            target=BLAIDD,
            paths=[
                ConnectionPath(
                    nodes=[RANNI, BLAIDD],
                    claims=[claim],
                    length=1,
                    minimum_confidence="high",
                )
            ],
            max_depth=3,
            truncated=False,
        )


def client() -> TestClient:
    app = create_app(manage_database=False)
    app.dependency_overrides[get_repository] = ConnectionRepository
    return TestClient(app)


def test_connection_endpoint() -> None:
    response = client().get(
        "/api/v1/connections?from_id=character.ranni&to_id=character.blaidd"
    )

    assert response.status_code == 200
    assert response.json()["paths"][0]["claims"][0]["predicate"] == "SERVES"


def test_connection_endpoint_rejects_same_entity() -> None:
    response = client().get(
        "/api/v1/connections?from_id=character.ranni&to_id=character.ranni"
    )

    assert response.status_code == 422
