from types import SimpleNamespace

import pytest

from elden_lore_api.api_models import (
    AnswerResponse,
    ClaimDetail,
    EntitySummary,
    EvidenceView,
)
from elden_lore_api.generation import (
    GeneratedAnswer,
    GroundedAnswerCache,
    GroundedAnswerService,
    OpenAIAnswerGenerator,
    build_grounding_context,
)


class FakeResponses:
    def __init__(self, generated: GeneratedAnswer) -> None:
        self.generated = generated
        self.calls = 0
        self.kwargs = None

    def parse(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.generated)


def _base_answer() -> AnswerResponse:
    subject = EntitySummary(
        id="character.ranni",
        kind="character",
        canonical_name="Ranni the Witch",
        continuity="base_game",
    )
    object_ = EntitySummary(
        id="concept.empyrean",
        kind="concept",
        canonical_name="Empyrean",
        continuity="both",
    )
    evidence = EvidenceView(
        id="evidence.base.ranni-retinue",
        locator="Ranni quest dialogue",
        summary_en="Ranni identifies herself as an Empyrean.",
        review_status="draft",
        source_id="game.base.boss-and-quest-scenes",
        source_title="Elden Ring base game boss and quest scenes",
        authority_tier="P0_GAME",
    )
    claim = ClaimDetail(
        id="claim.ranni-is-empyrean",
        predicate="HELD_TITLE",
        evidence_level="explicit",
        confidence="high",
        review_status="draft",
        continuity="base_game",
        subject=subject,
        object=object_,
        evidence=[evidence],
    )
    return AnswerResponse(
        answer_id="a" * 32,
        question="Is Ranni an Empyrean?",
        language="en",
        intent="general",
        status="supported",
        answer="The current evidence supports: Ranni is an Empyrean.",
        matched_entities=[subject],
        explicit_claims=[claim],
        citations=[evidence],
    )


def _service(generated: GeneratedAnswer):
    responses = FakeResponses(generated)
    client = SimpleNamespace(responses=responses)
    generator = OpenAIAnswerGenerator(
        api_key="test",
        model="test-model",
        timeout_seconds=1,
        max_output_tokens=300,
        client=client,
    )
    return GroundedAnswerService(
        generator, GroundedAnswerCache(ttl_seconds=60, max_entries=10)
    ), responses


def test_grounded_generator_uses_structured_output_and_cache() -> None:
    service, responses = _service(
        GeneratedAnswer(
            answer="Ranni is explicitly identified as an Empyrean.",
            cited_claim_ids=["claim.ranni-is-empyrean"],
            cited_evidence_ids=["evidence.base.ranni-retinue"],
        )
    )

    first = service.enhance(_base_answer())
    second = service.enhance(_base_answer())

    assert first.generator == "openai"
    assert first.generator_model == "test-model"
    assert first.generated_claim_ids == ["claim.ranni-is-empyrean"]
    assert second.answer == first.answer
    assert responses.calls == 1
    assert responses.kwargs["text_format"] is GeneratedAnswer
    assert responses.kwargs["max_output_tokens"] == 300


def test_generated_answer_cannot_cite_unknown_records() -> None:
    service, _ = _service(
        GeneratedAnswer(
            answer="Unsupported.",
            cited_claim_ids=["claim.invented"],
            cited_evidence_ids=["evidence.base.ranni-retinue"],
        )
    )

    with pytest.raises(ValueError, match="unknown claim"):
        service.enhance(_base_answer())


def test_unknown_answer_never_calls_model() -> None:
    service, responses = _service(
        GeneratedAnswer(
            answer="Unused",
            cited_claim_ids=["claim.ranni-is-empyrean"],
            cited_evidence_ids=["evidence.base.ranni-retinue"],
        )
    )
    base = _base_answer().model_copy(
        update={"status": "unknown", "citations": [], "explicit_claims": []}
    )

    assert service.enhance(base) == base
    assert responses.calls == 0


def test_grounding_context_contains_only_bounded_graph_records() -> None:
    context = build_grounding_context(_base_answer())

    assert context["question"] == "Is Ranni an Empyrean?"
    assert context["claims"][0]["id"] == "claim.ranni-is-empyrean"
    assert context["evidence"][0]["id"] == "evidence.base.ranni-retinue"
