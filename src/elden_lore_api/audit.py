import argparse
from collections import Counter, defaultdict
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
    coverage: dict[str, object]
    issues: list[AuditIssue]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def audit_dataset(dataset: CuratedDataset) -> AuditReport:
    issues: list[AuditIssue] = []
    entities = {entity.id: entity for entity in dataset.entities}
    evidence = {item.id: item for item in dataset.evidence}

    entity_names: dict[tuple[str, str], list[str]] = defaultdict(list)
    for entity in dataset.entities:
        entity_names[(entity.kind, _normalized(entity.canonical_name))].append(entity.id)
    for record_ids in entity_names.values():
        if len(record_ids) > 1:
            issues.append(
                AuditIssue(
                    severity="warning",
                    code="possible_duplicate_entity",
                    message=f"Entities share a kind and normalized name: {record_ids}",
                )
            )

    alias_keys: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for alias in dataset.aliases:
        alias_keys[(alias.entity_id, alias.locale, _normalized(alias.value))].append(alias.id)
    for record_ids in alias_keys.values():
        if len(record_ids) > 1:
            issues.append(
                AuditIssue(
                    severity="error",
                    code="duplicate_alias_value",
                    message=f"Aliases repeat the same entity, locale and value: {record_ids}",
                )
            )

    evidence_keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in dataset.evidence:
        evidence_keys[(item.source_id, _normalized(item.locator))].append(item.id)
    for record_ids in evidence_keys.values():
        if len(record_ids) > 1:
            issues.append(
                AuditIssue(
                    severity="warning",
                    code="possible_duplicate_evidence",
                    message=f"Evidence shares a source and normalized locator: {record_ids}",
                )
            )

    claim_keys: dict[tuple[str, str, str | None, str], list[str]] = defaultdict(list)
    for claim in dataset.claims:
        claim_keys[
            (claim.subject_id, claim.predicate, claim.object_id, claim.continuity)
        ].append(claim.id)
    for record_ids in claim_keys.values():
        if len(record_ids) > 1:
            issues.append(
                AuditIssue(
                    severity="warning",
                    code="possible_duplicate_claim",
                    message=f"Claims share subject, predicate, object and continuity: {record_ids}",
                )
            )

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
    connected_entity_ids = {
        entity_id
        for claim in dataset.claims
        for entity_id in (claim.subject_id, claim.object_id)
        if entity_id is not None
    }
    isolated_entity_ids = sorted(set(entities) - connected_entity_ids)
    for entity_id in isolated_entity_ids:
        issues.append(
            AuditIssue(
                severity="warning",
                code="isolated_entity",
                message="Entity is not referenced by any claim",
                record_id=entity_id,
            )
        )
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
    reviewed_claims = sum(claim.review_status == "reviewed" for claim in dataset.claims)
    reviewed_evidence = sum(item.review_status == "reviewed" for item in dataset.evidence)
    coverage: dict[str, object] = {
        "entities_by_kind": dict(sorted(Counter(e.kind for e in dataset.entities).items())),
        "entities_by_continuity": dict(
            sorted(Counter(e.continuity.value for e in dataset.entities).items())
        ),
        "claims_by_predicate": dict(sorted(predicates.items())),
        "claims_by_evidence_level": dict(
            sorted(Counter(c.evidence_level.value for c in dataset.claims).items())
        ),
        "claims_by_verification": dict(
            sorted(Counter(c.verification_status.value for c in dataset.claims).items())
        ),
        "evidence_by_verification": dict(
            sorted(Counter(e.verification_status.value for e in dataset.evidence).items())
        ),
        "reviewed_claim_percentage": _percentage(reviewed_claims, len(dataset.claims)),
        "reviewed_evidence_percentage": _percentage(reviewed_evidence, len(dataset.evidence)),
        "connected_entity_percentage": _percentage(
            len(connected_entity_ids), len(dataset.entities)
        ),
        "isolated_entity_ids": isolated_entity_ids,
    }
    return AuditReport(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        counts=counts,
        coverage=coverage,
        issues=issues,
    )


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _percentage(part: int, total: int) -> float:
    return round(part * 100 / total, 1) if total else 100.0


def run() -> None:
    parser = argparse.ArgumentParser(description="Audit a curated lore dataset")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    report = audit_dataset(load_curated_dataset(args.path))
    print(report.model_dump_json(indent=2))
    if report.has_errors:
        raise SystemExit(1)
