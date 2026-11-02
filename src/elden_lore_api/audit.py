import argparse
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from elden_lore_api.curated import CuratedDataset, load_curated_dataset
from elden_lore_api.importer import DEFAULT_DATASET
from elden_lore_api.timeline import topological_layers


class AuditIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    record_id: str | None = None


class AuditReport(BaseModel):
    dataset_id: str
    dataset_version: int
    counts: dict[str, int]
    issues: list[AuditIssue]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def audit_dataset(dataset: CuratedDataset) -> AuditReport:
    issues: list[AuditIssue] = []
    entities = {entity.id: entity for entity in dataset.entities}
    evidence = {item.id: item for item in dataset.evidence}

    for claim in dataset.claims:
        subject = entities[claim.subject_id]
        object_ = entities[claim.object_id] if claim.object_id else None
        if claim.object_id == claim.subject_id:
            issues.append(
                AuditIssue(
                    severity="error",
                    code="self_relation",
                    message="A claim cannot relate an entity to itself",
                    record_id=claim.id,
                )
            )
        if claim.predicate == "BEFORE" and (
            subject.kind != "event" or object_ is None or object_.kind != "event"
        ):
            issues.append(
                AuditIssue(
                    severity="error",
                    code="invalid_before_types",
                    message="BEFORE requires event subjects and objects",
                    record_id=claim.id,
                )
            )
        if claim.predicate == "IN_ERA" and (
            subject.kind != "event" or object_ is None or object_.kind != "era"
        ):
            issues.append(
                AuditIssue(
                    severity="error",
                    code="invalid_in_era_types",
                    message="IN_ERA requires an event subject and era object",
                    record_id=claim.id,
                )
            )
        if claim.review_status == "reviewed":
            draft_evidence = [
                evidence[evidence_id].id
                for evidence_id in claim.evidence_ids
                if evidence[evidence_id].review_status == "draft"
            ]
            if draft_evidence:
                issues.append(
                    AuditIssue(
                        severity="error",
                        code="reviewed_claim_has_draft_evidence",
                        message=f"Reviewed claim relies on draft evidence: {draft_evidence}",
                        record_id=claim.id,
                    )
                )

    event_ids = {entity.id for entity in dataset.entities if entity.kind == "event"}
    precedence = [
        (claim.subject_id, claim.object_id)
        for claim in dataset.claims
        if claim.predicate == "BEFORE" and claim.object_id is not None
    ]
    _, cycle_event_ids = topological_layers(event_ids, precedence)
    if cycle_event_ids:
        issues.append(
            AuditIssue(
                severity="error",
                code="timeline_cycle",
                message=f"Timeline contains a precedence cycle: {cycle_event_ids}",
            )
        )

    predicates = Counter(claim.predicate for claim in dataset.claims)
    counts = {
        "entities": len(dataset.entities),
        "aliases": len(dataset.aliases),
        "sources": len(dataset.sources),
        "evidence": len(dataset.evidence),
        "localized_texts": len(dataset.localized_texts),
        "claims": len(dataset.claims),
        "timeline_memberships": predicates["IN_ERA"],
        "precedence_claims": predicates["BEFORE"],
    }
    return AuditReport(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        counts=counts,
        issues=issues,
    )


def run() -> None:
    parser = argparse.ArgumentParser(description="Audit a curated lore dataset")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    report = audit_dataset(load_curated_dataset(args.path))
    print(report.model_dump_json(indent=2))
    if report.has_errors:
        raise SystemExit(1)
