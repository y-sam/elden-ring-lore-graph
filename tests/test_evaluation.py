from pathlib import Path

from elden_lore_api.curated import load_curated_dataset
from elden_lore_api.evaluation import build_reference_questions, validate_reference_questions

DATASET = Path("data/curated/the_shattering.seed.json")


def test_reference_suite_contains_one_hundred_valid_english_questions() -> None:
    dataset = load_curated_dataset(DATASET)
    questions = build_reference_questions(dataset)

    assert len(questions) == 100
    assert validate_reference_questions(dataset, questions) == []
    assert all(question.question.endswith("?") for question in questions)
    assert any(question.question == "Who is Blaidd?" for question in questions)
