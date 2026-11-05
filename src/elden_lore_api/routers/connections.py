from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from elden_lore_api.api_models import ConnectionResponse
from elden_lore_api.routers.entities import Repository, resolve_draft_visibility

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=ConnectionResponse)
def find_connections(
    repository: Repository,
    from_id: Annotated[str, Query(min_length=3, max_length=120)],
    to_id: Annotated[str, Query(min_length=3, max_length=120)],
    max_depth: Annotated[int, Query(ge=1, le=4)] = 3,
    limit: Annotated[int, Query(ge=1, le=5)] = 3,
    evidence_level: Annotated[
        Literal["explicit", "synthesis", "strong_inference", "inference", "theory"] | None,
        Query(),
    ] = None,
    verification_status: Annotated[
        Literal[
            "game_verified", "official_verified", "community_verified", "unverified"
        ]
        | None,
        Query(),
    ] = None,
    include_drafts: bool = False,
) -> ConnectionResponse:
    if from_id == to_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose two different entities",
        )
    result = repository.find_connections(
        from_id,
        to_id,
        max_depth=max_depth,
        limit=limit,
        evidence_level=evidence_level,
        verification_status=verification_status,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both entities were not found",
        )
    return result
