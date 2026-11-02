import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from neo4j import Driver
from pydantic import BaseModel, Field

from elden_lore_api.config import get_settings
from elden_lore_api.editorial import EditorialRepository

router = APIRouter(prefix="/editorial", tags=["editorial"])


class ReviewRequest(BaseModel):
    decision: Literal["reviewed", "disputed", "rejected", "approved"]
    verification_status: Literal[
        "unverified", "community_verified", "official_verified", "game_verified"
    ] | None = None
    verification_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class BatchReviewRequest(ReviewRequest):
    item_ids: list[str] = Field(min_length=1, max_length=100)


def require_editorial_token(x_editorial_token: Annotated[str, Header()]) -> None:
    settings = get_settings()
    if settings.app_env == "production" and settings.editorial_token == "local-development-only":
        raise HTTPException(status_code=503, detail="Editorial access is not configured")
    if not secrets.compare_digest(x_editorial_token, settings.editorial_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_editorial_repository(request: Request) -> EditorialRepository:
    driver: Driver | None = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="Neo4j driver is not initialized")
    return EditorialRepository(driver, get_settings().neo4j_database)


Repository = Annotated[EditorialRepository, Depends(get_editorial_repository)]
Authorized = Annotated[None, Depends(require_editorial_token)]


@router.get("/dashboard")
def dashboard(_: Authorized, repository: Repository) -> dict[str, int]:
    return repository.dashboard()


@router.get("/readiness")
def readiness(_: Authorized, repository: Repository) -> dict[str, object]:
    return repository.readiness()


@router.get("/queue")
def queue(
    _: Authorized,
    repository: Repository,
    kind: Literal["claim", "evidence", "localized_text", "feedback"],
    status_value: str = "draft",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, object]]:
    return repository.queue(kind, status_value=status_value, limit=limit)


@router.get("/priority-evidence")
def priority_evidence(
    _: Authorized,
    repository: Repository,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    return repository.priority_evidence_queue(limit=limit)


@router.patch("/{kind}/{item_id}")
def review(
    kind: Literal["claim", "evidence", "localized_text", "feedback"],
    item_id: str,
    payload: ReviewRequest,
    _: Authorized,
    repository: Repository,
) -> dict[str, object]:
    try:
        item = repository.review(
            kind, item_id, decision=payload.decision, notes=payload.notes,
            verification_status=payload.verification_status,
            verification_url=payload.verification_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Editorial item not found")
    return item


@router.post("/{kind}/batch")
def batch_review(
    kind: Literal["claim", "evidence", "localized_text", "feedback"],
    payload: BatchReviewRequest,
    _: Authorized,
    repository: Repository,
) -> dict[str, object]:
    reviewed: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for item_id in payload.item_ids:
        try:
            item = repository.review(
                kind, item_id, decision=payload.decision, notes=payload.notes
                , verification_status=payload.verification_status,
                verification_url=payload.verification_url
            )
            if item is None:
                errors.append({"id": item_id, "detail": "not found"})
            else:
                reviewed.append(item)
        except ValueError as exc:
            errors.append({"id": item_id, "detail": str(exc)})
    return {"reviewed": reviewed, "errors": errors}
