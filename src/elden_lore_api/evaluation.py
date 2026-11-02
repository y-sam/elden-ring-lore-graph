import json
from dataclasses import dataclass
from pathlib import Path

from elden_lore_api.config import get_settings
from elden_lore_api.curated import CuratedDataset, load_curated_dataset
from elden_lore_api.database import create_driver
from elden_lore_api.repository import EntityRepository

DEFAULT_DATASET = Path(__file__).parents[2] / "data" / "curated" / "the_shattering.seed.json"


@dataclass(frozen=True)
class ReferenceQuestion:
    question: str
    expected_entity_ids: tuple[str, ...]
    expected_claim_ids: tuple[str, ...]
    intent: str


CORNERSTONE_QUESTIONS = (
    ReferenceQuestion(
        "Who is Blaidd?", ("character.blaidd",), ("claim.blaidd-serves-ranni",), "who"
    ),
    ReferenceQuestion(
        "Who is Miquella?",
        ("character.miquella",),
        ("claim.miquella.child-of-marika",),
        "who",
    ),
    ReferenceQuestion(
        "Who is Metyr?", ("character.metyr",), ("claim.metyr-child-greater-will",), "who"
    ),
    ReferenceQuestion(
        "Where is Godwyn?",
        ("character.godwyn",),
        ("claim.godwyn.rests-deeproot",),
        "where",
    ),
    ReferenceQuestion(
        "Where is Nokron?", ("location.nokron",), ("claim.nokron-in-siofra",), "where"
    ),
    ReferenceQuestion(
        "Who serves Ranni?",
        ("character.ranni",),
        ("claim.blaidd-serves-ranni",),
        "who",
    ),
    ReferenceQuestion(
        "What connects Bayle and Placidusax?",
        ("character.bayle", "character.placidusax"),
        ("claim.bayle-fought-placidusax",),
        "relationship",
    ),
    ReferenceQuestion(
        "What connects Mohg and the Formless Mother?",
        ("character.mohg", "outer-god.formless-mother"),
        ("claim.mohg-serves-formless-mother",),
        "relationship",
    ),
    ReferenceQuestion(
        "What connects Miquella and St. Trina?",
        ("character.miquella", "character.st-trina"),
        ("claim.trina-aspect-miquella",),
        "relationship",
    ),
    ReferenceQuestion(
        "Who rules Stormveil Castle?",
        ("location.stormveil-castle",),
        ("claim.godrick-rules-stormveil",),
        "who",
    ),
)


def build_reference_questions(dataset: CuratedDataset, limit: int = 100) -> list[ReferenceQuestion]:
    questions = list(CORNERSTONE_QUESTIONS)
    entities = {entity.id: entity for entity in dataset.entities}
    seen = {question.question for question in questions}
    for claim in sorted(dataset.claims, key=lambda item: item.id):
        if not claim.object_id:
            continue
        subject = entities[claim.subject_id]
        object_ = entities[claim.object_id]
        text = (
            f"What is the relationship between {subject.canonical_name} "
            f"and {object_.canonical_name}?"
        )
        if text in seen:
            continue
        seen.add(text)
        questions.append(
            ReferenceQuestion(
                question=text,
                expected_entity_ids=(subject.id, object_.id),
                expected_claim_ids=(claim.id,),
                intent="relationship",
            )
        )
        if len(questions) >= limit:
            break
    return questions


def validate_reference_questions(
    dataset: CuratedDataset, questions: list[ReferenceQuestion]
) -> list[str]:
    entity_ids = {entity.id for entity in dataset.entities}
    claim_ids = {claim.id for claim in dataset.claims}
    issues: list[str] = []
    if len({question.question for question in questions}) != len(questions):
        issues.append("reference questions must be unique")
    for question in questions:
        unknown_entities = set(question.expected_entity_ids) - entity_ids
        unknown_claims = set(question.expected_claim_ids) - claim_ids
        if unknown_entities:
            issues.append(f"{question.question}: unknown entities {sorted(unknown_entities)}")
        if unknown_claims:
            issues.append(f"{question.question}: unknown claims {sorted(unknown_claims)}")
    return issues


def evaluate_repository(
    repository: EntityRepository, questions: list[ReferenceQuestion]
) -> dict[str, object]:
    failures: list[dict[str, object]] = []
    for reference in questions:
        answer = repository.answer_question(
            question=reference.question, language="en", limit=20, include_drafts=True
        )
        returned_claims = {
            claim.id
            for claim in [
                *answer.explicit_claims,
                *answer.inferred_claims,
                *answer.supporting_claims,
            ]
        }
        returned_entities = {entity.id for entity in answer.matched_entities}
        missing_claims = set(reference.expected_claim_ids) - returned_claims
        missing_entities = set(reference.expected_entity_ids) - returned_entities
        if missing_claims or missing_entities:
            failures.append(
                {
                    "question": reference.question,
                    "missing_claims": sorted(missing_claims),
                    "missing_entities": sorted(missing_entities),
                    "status": answer.status,
                }
            )
    return {
        "total": len(questions),
        "passed": len(questions) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def run() -> None:
    dataset = load_curated_dataset(DEFAULT_DATASET)
    questions = build_reference_questions(dataset)
    settings = get_settings()
    driver = create_driver(settings)
    try:
        report = evaluate_repository(
            EntityRepository(driver, settings.neo4j_database), questions
        )
    finally:
        driver.close()
    print(json.dumps(report, indent=2))
