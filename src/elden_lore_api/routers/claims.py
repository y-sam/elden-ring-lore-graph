from fastapi import APIRouter, HTTPException, status

from elden_lore_api.api_models import ClaimDetail
from elden_lore_api.routers.entities import Repository, resolve_draft_visibility

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(
    claim_id: str,
    repository: Repository,
    include_drafts: bool = False,
) -> ClaimDetail:
    claim = repository.get_claim(
        claim_id,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim
