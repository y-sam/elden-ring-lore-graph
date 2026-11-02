import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from elden_lore_api.curated import CuratedDataset, load_curated_dataset

DATASET = Path(__file__).parents[1] / "data" / "curated" / "the_shattering.seed.json"


def test_seed_validates_as_curated_dataset() -> None:
    dataset = load_curated_dataset(DATASET)

    assert dataset.dataset_id == "dataset.the-shattering.seed"
    assert dataset.dataset_version >= 3
    assert len(dataset.localized_texts) > 0
    assert any(claim.predicate == "SHATTERED_IN" for claim in dataset.claims)
    assert {entity.continuity for entity in dataset.entities} >= {
        "base_game",
        "shadow_of_the_erdtree",
        "both",
    }


def test_unknown_references_are_rejected() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["claims"][0]["object_id"] = "event.missing"

    with pytest.raises(ValidationError, match="unknown object"):
        CuratedDataset.model_validate(payload)


def test_reference_only_source_fails_closed() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["sources"][0]["embedding_allowed"] = True

    with pytest.raises(ValidationError, match="reference-only"):
        CuratedDataset.model_validate(payload)


def test_verbatim_text_is_rejected() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["evidence"][0]["verbatim_text"] = "Protected source text"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CuratedDataset.model_validate(payload)


def test_machine_assisted_localization_cannot_be_reviewed() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["localized_texts"][0]["review_status"] = "reviewed"

    with pytest.raises(ValidationError, match="must remain draft"):
        CuratedDataset.model_validate(payload)


def test_reviewed_primary_records_are_normalized_by_source_tier() -> None:
    dataset = load_curated_dataset(DATASET)
    reviewed_evidence = [
        item for item in dataset.evidence if item.review_status == "reviewed"
    ]

    assert reviewed_evidence
    assert all(
        item.verification_status in {"official_verified", "game_verified"}
        for item in reviewed_evidence
    )
    assert all(
        item.verification_status in {"official_verified", "game_verified"}
        for item in dataset.claims
        if item.review_status == "reviewed"
    )


def test_claim_cannot_outrank_supporting_evidence() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["claims"][0]["verification_status"] = "game_verified"
    evidence_ids = set(payload["claims"][0]["evidence_ids"])
    for evidence in payload["evidence"]:
        if evidence["id"] in evidence_ids:
            evidence["review_status"] = "draft"
            evidence["verification_status"] = "unverified"

    with pytest.raises(ValidationError, match="cannot be game verified"):
        CuratedDataset.model_validate(payload)


def test_manifest_assembles_thematic_fragments(tmp_path: Path) -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    collections = (
        "entities",
        "aliases",
        "sources",
        "evidence",
        "localized_texts",
        "claims",
    )
    fragments = []
    for index, collection in enumerate(collections):
        fragment_name = f"{index:02d}-{collection}.json"
        (tmp_path / fragment_name).write_text(
            json.dumps({collection: payload[collection]}), encoding="utf-8"
        )
        fragments.append(fragment_name)
    manifest = {
        "dataset_id": payload["dataset_id"],
        "dataset_version": payload["dataset_version"],
        "status": payload["status"],
        "fragments": fragments,
    }
    manifest_path = tmp_path / "dataset.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assembled = load_curated_dataset(manifest_path)

    for collection in collections:
        assert len(getattr(assembled, collection)) == len(payload[collection])


def test_manifest_rejects_fragment_outside_its_directory(tmp_path: Path) -> None:
    manifest_path = tmp_path / "dataset.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "dataset.test",
                "dataset_version": 1,
                "status": "draft",
                "fragments": ["../outside.json"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes manifest directory"):
        load_curated_dataset(manifest_path)
