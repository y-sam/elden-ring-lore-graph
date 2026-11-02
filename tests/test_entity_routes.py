from fastapi.testclient import TestClient

from elden_lore_api.api_models import (
    AnswerResponse,
    ClaimDetail,
    EntityDetail,
    EntityPage,
    EntitySubgraph,
    EntitySummary,
    SearchHit,
    SearchResponse,
    TimelineResponse,
)
from elden_lore_api.main import create_app
from elden_lore_api.routers.entities import get_repository

ENTITY = EntitySummary(
    id="artifact.elden-ring",
    kind="artifact",
    canonical_name="Elden Ring",
    continuity="both",
)


class FakeRepository:
    def list_entities(self, **_: object) -> EntityPage:
        return EntityPage(items=[ENTITY], limit=25, offset=0)

    def get_entity(self, entity_id: str, **_: object) -> EntityDetail | None:
        if entity_id == ENTITY.id:
            return EntityDetail(**ENTITY.model_dump(), claims=[])
        return None

    def get_subgraph(self, entity_id: str, **_: object) -> EntitySubgraph | None:
        if entity_id == ENTITY.id:
            return EntitySubgraph(
                root_id=ENTITY.id,
                depth=1,
                nodes=[ENTITY],
                edges=[],
                truncated=False,
            )
        return None

    def get_claim(self, claim_id: str, **_: object) -> ClaimDetail | None:
        if claim_id == "claim.ring-created":
            return ClaimDetail(
                id=claim_id,
                predicate="CREATED",
                evidence_level="explicit",
                confidence="high",
                review_status="reviewed",
                continuity="both",
                subject=ENTITY,
                object=None,
                evidence=[],
            )
        return None

    def get_timeline(self, **_: object) -> TimelineResponse:
        return TimelineResponse(
            era_id="era.the-shattering",
            events=[ENTITY],
            eras=[],
            memberships=[],
            precedence=[],
            layers=[[ENTITY.id]],
            cycle_event_ids=[],
            is_partial=False,
        )

    def search(self, *, query: str, **_: object) -> SearchResponse:
        return SearchResponse(
            query=query,
            items=[
                SearchHit(
                    id=ENTITY.id,
                    result_type="entity",
                    title=ENTITY.canonical_name,
                    score=1.0,
                )
            ],
        )

    def answer_question(self, *, question: str, **_: object) -> AnswerResponse:
        return AnswerResponse(
            answer_id="0" * 32,
            question=question,
            language="en",
            intent="general",
            status="unknown",
            answer=(
                "The current curated graph does not contain enough evidence "
                "to answer this question."
            ),
            limitations=["No supported claim matching the question was found."],
        )


def client() -> TestClient:
    app = create_app(manage_database=False)
    app.dependency_overrides[get_repository] = FakeRepository
    return TestClient(app)


def test_list_entities() -> None:
    response = client().get("/api/v1/entities?q=ring&kind=artifact")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == ENTITY.id


def test_get_entity_and_subgraph() -> None:
    entity_response = client().get(f"/api/v1/entities/{ENTITY.id}")
    graph_response = client().get(f"/api/v1/entities/{ENTITY.id}/subgraph")

    assert entity_response.status_code == 200
    assert graph_response.status_code == 200
    assert graph_response.json()["root_id"] == ENTITY.id


def test_missing_entity_returns_404() -> None:
    response = client().get("/api/v1/entities/missing.entity")

    assert response.status_code == 404
    assert response.json() == {"detail": "Entity not found"}


def test_get_claim_and_missing_claim() -> None:
    response = client().get("/api/v1/claims/claim.ring-created")
    missing = client().get("/api/v1/claims/missing.claim")

    assert response.status_code == 200
    assert response.json()["predicate"] == "CREATED"
    assert missing.status_code == 404


def test_timeline_route() -> None:
    response = client().get("/api/v1/timeline?era_id=era.the-shattering")

    assert response.status_code == 200
    assert response.json()["layers"] == [[ENTITY.id]]


def test_search_route() -> None:
    response = client().get("/api/v1/search?q=elden")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == ENTITY.id


def test_answer_route() -> None:
    response = client().get("/api/v1/answers?q=Who+is+Miquella")

    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
