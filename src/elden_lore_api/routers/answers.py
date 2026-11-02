from typing import Annotated, Literal

from fastapi import APIRouter, Query

from elden_lore_api.api_models import AnswerResponse
from elden_lore_api.routers.entities import Repository, resolve_draft_visibility

router = APIRouter(prefix="/answers", tags=["answers"])


@router.get("", response_model=AnswerResponse)
def answer_question(
    repository: Repository,
    q: Annotated[str, Query(min_length=3, max_length=300)],
    lang: Literal["en", "es", "pt-BR"] | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 12,
    include_drafts: bool = False,
) -> AnswerResponse:
    return repository.answer_question(
        question=q,
        language=lang,
        limit=limit,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
