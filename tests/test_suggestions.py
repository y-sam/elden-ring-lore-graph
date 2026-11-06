from elden_lore_api.api_models import ClaimView, EntityDetail, EntitySummary
from elden_lore_api.suggestions import build_suggested_questions


def test_suggestions_use_visible_grounded_relationships() -> None:
    ranni = EntitySummary(
        id="character.ranni", kind="character",
        canonical_name="Ranni the Witch", continuity="base_game",
    )
    blaidd = EntitySummary(
        id="character.blaidd", kind="character",
        canonical_name="Blaidd the Half-Wolf", continuity="base_game",
    )
    entity = EntityDetail(
        **ranni.model_dump(),
        claims=[
            ClaimView(
                id="claim.blaidd-serves-ranni", predicate="SERVES",
                evidence_level="explicit", confidence="high",
                review_status="reviewed", continuity="base_game",
                direction="incoming", subject=blaidd, object=ranni,
            )
        ],
    )

    suggestions = build_suggested_questions(entity)
    questions = {item.question for item in suggestions}

    assert "Who is Ranni the Witch?" in questions
    assert "Who serves Ranni the Witch?" in questions
    assert (
        "What is the relationship between Ranni the Witch and Blaidd the Half-Wolf?"
        in questions
    )
