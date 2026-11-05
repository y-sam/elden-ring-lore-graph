from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from elden_lore_api.api_models import (
    DiscoveryCollection,
    DiscoveryCollectionSummary,
    DiscoveryEntry,
    DiscoveryIndex,
)
from elden_lore_api.discovery import (
    COLLECTION_BY_ID,
    COLLECTIONS,
    SpoilerLevel,
    spoiler_rank,
)
from elden_lore_api.routers.entities import Repository

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("", response_model=DiscoveryIndex)
def list_discovery_collections(
    spoiler_level: Annotated[SpoilerLevel, Query()] = "minimal",
) -> DiscoveryIndex:
    allowed_rank = spoiler_rank(spoiler_level)
    return DiscoveryIndex(
        collections=[
            DiscoveryCollectionSummary(
                id=collection["id"],
                title=collection["title"],
                description=collection["description"],
                spoiler_level=collection["spoiler_level"],
                default_entity_id=collection["default_entity_id"],
                entity_count=len(collection["entries"]),
            )
            for collection in COLLECTIONS
            if spoiler_rank(collection["spoiler_level"]) <= allowed_rank
        ]
    )


@router.get("/{collection_id}", response_model=DiscoveryCollection)
def get_discovery_collection(
    collection_id: str,
    repository: Repository,
    spoiler_level: Annotated[SpoilerLevel, Query()] = "minimal",
) -> DiscoveryCollection:
    collection = COLLECTION_BY_ID.get(collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if spoiler_rank(collection["spoiler_level"]) > spoiler_rank(spoiler_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Journey is hidden by the selected spoiler level",
        )

    entries: list[DiscoveryEntry] = []
    entity_ids = {entry["entity_id"] for entry in collection["entries"]}
    edge_by_id = {}
    for definition in collection["entries"]:
        entity = repository.get_entity(definition["entity_id"], include_drafts=False)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Journey entity unavailable: {definition['entity_id']}",
            )
        entries.append(
            DiscoveryEntry(
                entity=entity,
                introduction=definition["introduction"],
                prompt=definition["prompt"],
                next_entity_ids=definition["next_entity_ids"],
            )
        )
        graph = repository.get_subgraph(
            definition["entity_id"], depth=1, limit=50, include_drafts=False
        )
        if graph:
            for edge in graph.edges:
                if edge.source in entity_ids and edge.target in entity_ids:
                    edge_by_id[edge.id] = edge

    return DiscoveryCollection(
        id=collection["id"],
        title=collection["title"],
        description=collection["description"],
        spoiler_level=collection["spoiler_level"],
        default_entity_id=collection["default_entity_id"],
        entries=entries,
        edges=list(edge_by_id.values()),
        recommended_collection_ids=collection["recommended_collection_ids"],
    )
