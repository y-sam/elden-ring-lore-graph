import json
from pathlib import Path

DATASET = Path(__file__).parents[1] / "data" / "curated" / "the_shattering.seed.json"


def test_seed_is_draft_and_contains_no_verbatim_text() -> None:
    content = DATASET.read_text(encoding="utf-8")
    dataset = json.loads(content)

    assert dataset["status"] == "draft"
    assert "verbatim_text" not in content
    reviewed_evidence = {
        evidence["id"]
        for evidence in dataset["evidence"]
        if evidence["review_status"] == "reviewed"
    }
    reviewed_claims = [
        claim for claim in dataset["claims"] if claim["review_status"] == "reviewed"
    ]
    assert reviewed_claims
    assert all(set(claim["evidence_ids"]) <= reviewed_evidence for claim in reviewed_claims)


def test_seed_references_existing_records() -> None:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    entity_ids = {entity["id"] for entity in dataset["entities"]}
    source_ids = {source["id"] for source in dataset["sources"]}
    evidence_ids = {evidence["id"] for evidence in dataset["evidence"]}

    assert all(evidence["source_id"] in source_ids for evidence in dataset["evidence"])
    for claim in dataset["claims"]:
        assert claim["subject_id"] in entity_ids
        assert claim["object_id"] in entity_ids
        assert set(claim["evidence_ids"]) <= evidence_ids
