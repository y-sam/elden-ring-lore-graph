from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from neo4j import Driver

from elden_lore_api.api_models import (
    EntityDetail,
    EntityPage,
    EntitySubgraph,
    SuggestedQuestionResponse,
)
from elden_lore_api.config import get_settings
from elden_lore_api.repository import EntityRepository
from elden_lore_api.suggestions import build_suggested_questions

router = APIRouter(prefix="/entities", tags=["entities"])


def get_repository(request: Request) -> EntityRepository:
    driver: Driver | None = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j driver is not initialized",
        )
    return EntityRepository(driver, get_settings().neo4j_database)


Repository = Annotated[EntityRepository, Depends(get_repository)]


def resolve_draft_visibility(include_drafts: bool) -> bool:
    if include_drafts and get_settings().app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Draft content is not available in production",
        )
    return include_drafts


@router.get("", response_model=EntityPage)
def list_entities(
    repository: Repository,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    kind: Annotated[str | None, Query(pattern=r"^[a-z][a-z0-9_]*$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EntityPage:
    return repository.list_entities(query=q, kind=kind, limit=limit, offset=offset)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(
    entity_id: str,
    repository: Repository,
    include_drafts: bool = False,
) -> EntityDetail:
    entity = repository.get_entity(
        entity_id,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


@router.get("/{entity_id}/questions", response_model=SuggestedQuestionResponse)
def get_suggested_questions(
    entity_id: str,
    repository: Repository,
    include_drafts: bool = False,
) -> SuggestedQuestionResponse:
    entity = repository.get_entity(
        entity_id,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return SuggestedQuestionResponse(
        entity_id=entity.id,
        items=build_suggested_questions(entity),
    )


@router.get("/{entity_id}/subgraph", response_model=EntitySubgraph)
def get_subgraph(
    entity_id: str,
    repository: Repository,
    depth: Annotated[int, Query(ge=1, le=3)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    include_drafts: bool = False,
) -> EntitySubgraph:
    graph = repository.get_subgraph(
        entity_id,
        depth=depth,
        limit=limit,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if graph is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return graph
