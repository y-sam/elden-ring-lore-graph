from pathlib import Path

from elden_lore_api.audit import audit_dataset
from elden_lore_api.curated import ClaimRecord, load_curated_dataset

DATASET = Path(__file__).parents[1] / "data" / "curated" / "the_shattering.seed.json"


def test_seed_passes_editorial_audit() -> None:
    report = audit_dataset(load_curated_dataset(DATASET))

    assert report.has_errors is False
    assert report.counts["precedence_claims"] >= 10
    assert report.counts["timeline_memberships"] >= 12
    assert report.counts["localized_texts"] == report.counts["evidence"] * 2


def test_audit_detects_timeline_cycle() -> None:
    dataset = load_curated_dataset(DATASET)
    original = next(
        claim for claim in dataset.claims if claim.id == "claim.shattering-event.before-war"
    )
    dataset.claims.append(
        ClaimRecord(
            **{
                **original.model_dump(),
                "id": "claim.shattering-war.before-shattering-event",
                "subject_id": original.object_id,
                "object_id": original.subject_id,
            }
        )
    )

    report = audit_dataset(dataset)

    assert any(issue.code == "timeline_cycle" for issue in report.issues)
