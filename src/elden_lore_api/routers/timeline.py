from typing import Annotated

from fastapi import APIRouter, Depends, Query

from elden_lore_api.api_models import TimelineResponse
from elden_lore_api.repository import EntityRepository
from elden_lore_api.routers.entities import get_repository, resolve_draft_visibility

router = APIRouter(prefix="/timeline", tags=["timeline"])
Repository = Annotated[EntityRepository, Depends(get_repository)]


@router.get("", response_model=TimelineResponse)
def get_timeline(
    repository: Repository,
    era_id: Annotated[
        str | None,
        Query(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$"),
    ] = None,
    include_drafts: bool = False,
) -> TimelineResponse:
    return repository.get_timeline(
        era_id=era_id,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
