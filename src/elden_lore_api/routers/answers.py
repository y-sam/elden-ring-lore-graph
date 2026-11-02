import logging
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from elden_lore_api.api_models import AnswerResponse
from elden_lore_api.config import Settings, get_settings
from elden_lore_api.generation import (
    GroundedAnswerCache,
    GroundedAnswerService,
    OpenAIAnswerGenerator,
)
from elden_lore_api.routers.entities import Repository, resolve_draft_visibility

router = APIRouter(prefix="/answers", tags=["answers"])
logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _openai_service(
    api_key: str,
    model: str,
    timeout_seconds: float,
    max_output_tokens: int,
    cache_ttl_seconds: int,
    cache_max_entries: int,
) -> GroundedAnswerService:
    generator = OpenAIAnswerGenerator(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
    )
    cache = GroundedAnswerCache(
        ttl_seconds=cache_ttl_seconds,
        max_entries=cache_max_entries,
    )
    return GroundedAnswerService(generator, cache)


def _enhance_answer(base: AnswerResponse, settings: Settings) -> AnswerResponse:
    if settings.answer_generator != "openai" or not settings.openai_api_key:
        return base
    try:
        return _openai_service(
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_timeout_seconds,
            settings.openai_max_output_tokens,
            settings.answer_cache_ttl_seconds,
            settings.answer_cache_max_entries,
        ).enhance(base)
    except Exception:
        logger.exception("grounded answer generation failed; using deterministic fallback")
        return base


@router.get("", response_model=AnswerResponse)
def answer_question(
    repository: Repository,
    q: Annotated[str, Query(min_length=3, max_length=300)],
    lang: Literal["en", "es", "pt-BR"] | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 12,
    include_drafts: bool = False,
) -> AnswerResponse:
    base = repository.answer_question(
        question=q,
        language=lang,
        limit=limit,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    return _enhance_answer(base, get_settings())
