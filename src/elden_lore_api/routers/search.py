from typing import Annotated

from fastapi import APIRouter, Depends, Query

from elden_lore_api.api_models import SearchResponse
from elden_lore_api.repository import EntityRepository
from elden_lore_api.routers.entities import get_repository, resolve_draft_visibility

router = APIRouter(prefix="/search", tags=["search"])
Repository = Annotated[EntityRepository, Depends(get_repository)]


@router.get("", response_model=SearchResponse)
def search(
    repository: Repository,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    include_drafts: bool = False,
) -> SearchResponse:
    return repository.search(
        query=q,
        limit=limit,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
