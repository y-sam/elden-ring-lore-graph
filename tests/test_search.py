from elden_lore_api.api_models import ClaimDetail, EntitySummary
from elden_lore_api.repository import (
    INTENT_PREDICATES,
    _alias_is_named,
    _entity_is_named,
    _fuzzy_entity_score,
    _why_explanation_claims,
    build_entity_query,
    build_fulltext_query,
    detect_question_intent,
    detect_question_language,
)


def _claim(claim_id: str, predicate: str, subject_id: str, object_id: str) -> ClaimDetail:
    def entity(entity_id: str) -> EntitySummary:
        return EntitySummary(
            id=entity_id,
            kind=entity_id.split(".", 1)[0],
            canonical_name=entity_id.split(".", 1)[1].replace("-", " ").title(),
            continuity="both",
        )

    return ClaimDetail(
        id=claim_id,
        predicate=predicate,
        evidence_level="explicit",
        confidence="high",
        review_status="reviewed",
        verification_status="game_verified",
        continuity="both",
        subject=entity(subject_id),
        object=entity(object_id),
    )


def test_fulltext_query_uses_only_safe_alphanumeric_terms() -> None:
    assert build_fulltext_query("Elden Ring") == '"elden" AND "ring"'
    assert build_fulltext_query("Radahn +(Caelid):*") == '"radahn"'


def test_fulltext_query_can_be_empty_after_sanitizing() -> None:
    assert build_fulltext_query("+ - : *") == ""


def test_entity_query_ignores_question_words_and_punctuation() -> None:
    assert build_entity_query("Quem é Marika?") == '"marika"'
    assert build_entity_query("What is the relationship between Radagon and Marika?") == (
        '"radagon" OR "marika"'
    )


def test_entity_name_must_appear_as_a_phrase() -> None:
    assert _entity_is_named("What happened at the Battle of Aeonia?", "event.battle-of-aeonia")
    assert _entity_is_named("¿Dónde ocurrió Aeonia?", "event.battle-of-aeonia")
    assert not _entity_is_named("Who is Radagon?", "event.radagon-becomes-elden-lord")
    assert not _entity_is_named("Who is Miquella?", "event.mohg-takes-miquella")


def test_generic_title_does_not_match_an_unmentioned_alias() -> None:
    question = "Who is the Gloam-Eyed Queen?"

    assert not _alias_is_named(question, "Queen Marika the Eternal")
    assert _alias_is_named("Who is Marika?", "Queen Marika the Eternal")


def test_question_language_detection() -> None:
    assert detect_question_language("Who is Miquella?") == "en"
    assert detect_question_language("¿Dónde ocurrió Aeonia?") == "es"
    assert detect_question_language("Quem é Miquella?") == "pt-BR"


def test_question_intent_detection() -> None:
    assert detect_question_intent("Who is Miquella?") == "who"
    assert detect_question_intent("What did Miquella abandon?") == "what"
    assert detect_question_intent("Onde ocorreu a Batalha de Aeonia?") == "where"
    assert detect_question_intent("¿Cuándo ocurrió Aeonia?") == "when"
    assert detect_question_intent("Why did the Shattering happen?") == "why"
    assert detect_question_intent("Qual a relação entre Marika e Radagon?") == "relationship"


def test_who_intent_accepts_character_service_relationships() -> None:
    assert {"SERVES", "FOLLOWS", "FOLLOWED"} <= INTENT_PREDICATES["who"]
    assert "SERVED" not in INTENT_PREDICATES["who"]


def test_fuzzy_entity_score_recovers_small_name_typos() -> None:
    entity = {"canonical_name": "Blaidd the Half-Wolf"}
    assert _fuzzy_entity_score("Who is Blaid?", entity) >= 0.8
    assert _fuzzy_entity_score("Who is Malenia?", entity) < 0.72


def test_why_explanation_keeps_paths_and_focus_support_only() -> None:
    claims = [
        _claim("opposes", "OPPOSED", "character.ansbach", "character.miquella"),
        _claim("served", "SERVES", "character.ansbach", "character.mohg"),
        _claim("unrelated", "FOLLOWS", "character.freyja", "character.miquella"),
    ]

    selected = _why_explanation_claims(
        claims,
        matched_ids={"character.ansbach", "character.miquella"},
        question="Why does Ansbach oppose Miquella?",
    )

    assert {claim.id for claim in selected} == {"opposes", "served"}
