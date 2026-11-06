import logging
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from elden_lore_api.api_models import AnswerResponse
from elden_lore_api.config import Settings, get_settings
from elden_lore_api.generation import (
    GeminiAnswerGenerator,
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


@lru_cache(maxsize=4)
def _gemini_service(
    api_key: str,
    model: str,
    timeout_seconds: float,
    max_output_tokens: int,
    cache_ttl_seconds: int,
    cache_max_entries: int,
) -> GroundedAnswerService:
    generator = GeminiAnswerGenerator(
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
    if settings.answer_generator == "deterministic":
        return base
    try:
        if settings.answer_generator == "openai" and settings.openai_api_key:
            service = _openai_service(
                settings.openai_api_key,
                settings.openai_model,
                settings.openai_timeout_seconds,
                settings.openai_max_output_tokens,
                settings.answer_cache_ttl_seconds,
                settings.answer_cache_max_entries,
            )
        elif settings.answer_generator == "gemini" and settings.gemini_api_key:
            service = _gemini_service(
                settings.gemini_api_key,
                settings.gemini_model,
                settings.gemini_timeout_seconds,
                settings.gemini_max_output_tokens,
                settings.answer_cache_ttl_seconds,
                settings.answer_cache_max_entries,
            )
        else:
            return base.model_copy(update={"generation_mode": "fallback"})
        return service.enhance(base)
    except Exception:
        logger.exception("grounded answer generation failed; using deterministic fallback")
        model = (
            settings.openai_model
            if settings.answer_generator == "openai"
            else settings.gemini_model
        )
        return base.model_copy(
            update={
                "generation_mode": "fallback",
                "generator_model": model,
                "limitations": [
                    *base.limitations,
                    "The generative layer was unavailable; this is the deterministic fallback.",
                ],
            }
        )


@router.get("", response_model=AnswerResponse)
def answer_question(
    repository: Repository,
    q: Annotated[str, Query(min_length=3, max_length=300)],
    lang: Literal["en", "es", "pt-BR"] | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 12,
    include_drafts: bool = False,
) -> AnswerResponse:
    settings = get_settings()
    base = repository.answer_question(
        question=q,
        language=lang,
        limit=limit,
        include_drafts=resolve_draft_visibility(include_drafts),
    )
    if base.status == "unknown":
        context = {
            "answer_id": base.answer_id,
            "intent": base.intent,
            "matched_entity_ids": [entity.id for entity in base.matched_entities],
        }
        if settings.log_unknown_questions:
            context["question"] = q
        logger.info("unknown_answer %s", context)
    return _enhance_answer(base, settings)
