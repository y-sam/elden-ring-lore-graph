import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"


class Continuity(StrEnum):
    BASE_GAME = "base_game"
    SHADOW_OF_THE_ERDTREE = "shadow_of_the_erdtree"
    BOTH = "both"


class RightsStatus(StrEnum):
    ORIGINAL = "original"
    PUBLIC_DOMAIN = "public_domain"
    PERMISSIVE_LICENSE = "permissive_license"
    REFERENCE_ONLY = "reference_only"
    PERMISSION_GRANTED = "permission_granted"
    UNKNOWN = "unknown"


class EvidenceLevel(StrEnum):
    EXPLICIT = "explicit"
    SYNTHESIS = "synthesis"
    STRONG_INFERENCE = "strong_inference"
    WEAK_INFERENCE = "weak_inference"
    THEORY = "theory"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    COMMUNITY_VERIFIED = "community_verified"
    OFFICIAL_VERIFIED = "official_verified"
    GAME_VERIFIED = "game_verified"


class EntityRecord(StrictModel):
    id: Identifier
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    canonical_name: Annotated[str, Field(min_length=1, max_length=200)]
    continuity: Continuity


class AliasRecord(StrictModel):
    id: Identifier
    entity_id: Identifier
    value: Annotated[str, Field(min_length=1, max_length=200)]
    locale: Literal["en", "es", "pt-BR"]
    review_status: ReviewStatus


class SourceRecord(StrictModel):
    id: Identifier
    title: Annotated[str, Field(min_length=1, max_length=300)]
    authority_tier: Literal[
        "P0_GAME", "P1_OFFICIAL", "P2_CREATOR", "S1_SECONDARY", "T_COMMUNITY"
    ]
    rights_status: RightsStatus
    ingestion_allowed: bool
    public_display_allowed: bool
    embedding_allowed: bool
    license: str | None = None
    attribution: str | None = None
    source_url: str | None = None
    terms_url: str | None = None
    retrieved_at: str | None = None

    @model_validator(mode="after")
    def fail_closed_for_unknown_rights(self) -> "SourceRecord":
        if self.rights_status in {
            RightsStatus.UNKNOWN,
            RightsStatus.REFERENCE_ONLY,
        } and (self.ingestion_allowed or self.public_display_allowed or self.embedding_allowed):
            raise ValueError(
                "unknown and reference-only sources cannot allow ingestion, "
                "display, or embedding"
            )
        return self


class EvidenceRecord(StrictModel):
    id: Identifier
    source_id: Identifier
    locator: Annotated[str, Field(min_length=1, max_length=500)]
    summary_en: Annotated[str, Field(min_length=1, max_length=1000)]
    summary_rights_status: Literal["original"]
    review_status: ReviewStatus
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_url: str | None = None


class LocalizedEvidenceTextRecord(StrictModel):
    id: Identifier
    evidence_id: Identifier
    locale: Literal["es", "pt-BR"]
    field: Literal["summary"] = "summary"
    text: Annotated[str, Field(min_length=1, max_length=1000)]
    origin: Literal["machine_assisted", "human"]
    review_status: ReviewStatus

    @model_validator(mode="after")
    def machine_text_must_remain_draft(self) -> "LocalizedEvidenceTextRecord":
        if self.origin == "machine_assisted" and self.review_status != ReviewStatus.DRAFT:
            raise ValueError("machine-assisted localized text must remain draft")
        return self


class ClaimRecord(StrictModel):
    id: Identifier
    subject_id: Identifier
    predicate: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$")]
    object_id: Identifier | None = None
    evidence_ids: Annotated[list[Identifier], Field(min_length=1)]
    evidence_level: EvidenceLevel
    confidence: Confidence
    review_status: ReviewStatus
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    continuity: Continuity


class CuratedDataset(StrictModel):
    dataset_id: Identifier
    dataset_version: Annotated[int, Field(ge=1)]
    status: DatasetStatus
    entities: list[EntityRecord]
    aliases: list[AliasRecord] = Field(default_factory=list)
    sources: list[SourceRecord]
    evidence: list[EvidenceRecord]
    localized_texts: list[LocalizedEvidenceTextRecord] = Field(default_factory=list)
    claims: list[ClaimRecord]

    @model_validator(mode="after")
    def references_must_resolve(self) -> "CuratedDataset":
        entity_ids = _unique_ids(self.entities, "entity")
        _unique_ids(self.aliases, "alias")
        source_ids = _unique_ids(self.sources, "source")
        sources = {item.id: item for item in self.sources}
        evidence_ids = _unique_ids(self.evidence, "evidence")
        _unique_ids(self.localized_texts, "localized text")
        _unique_ids(self.claims, "claim")

        for item in self.evidence:
            if item.source_id not in source_ids:
                raise ValueError(f"evidence {item.id} references unknown source {item.source_id}")
            if (
                item.review_status == ReviewStatus.REVIEWED
                and item.verification_status == VerificationStatus.UNVERIFIED
                and sources[item.source_id].authority_tier in {"P0_GAME", "P1_OFFICIAL"}
            ):
                item.verification_status = (
                    VerificationStatus.GAME_VERIFIED
                    if sources[item.source_id].authority_tier == "P0_GAME"
                    else VerificationStatus.OFFICIAL_VERIFIED
                )
                item.verification_url = sources[item.source_id].source_url
        for alias in self.aliases:
            if alias.entity_id not in entity_ids:
                raise ValueError(f"alias {alias.id} references unknown entity {alias.entity_id}")
        for claim in self.claims:
            if claim.subject_id not in entity_ids:
                raise ValueError(f"claim {claim.id} references unknown subject {claim.subject_id}")
            if claim.object_id is not None and claim.object_id not in entity_ids:
                raise ValueError(f"claim {claim.id} references unknown object {claim.object_id}")
            unknown_evidence = set(claim.evidence_ids) - evidence_ids
            if unknown_evidence:
                raise ValueError(
                    f"claim {claim.id} references unknown evidence {sorted(unknown_evidence)}"
                )
            supporting = [item for item in self.evidence if item.id in claim.evidence_ids]
            if (
                claim.review_status == ReviewStatus.REVIEWED
                and claim.verification_status == VerificationStatus.UNVERIFIED
                and all(
                    item.verification_status == VerificationStatus.GAME_VERIFIED
                    for item in supporting
                )
            ):
                claim.verification_status = VerificationStatus.GAME_VERIFIED
            elif (
                claim.review_status == ReviewStatus.REVIEWED
                and claim.verification_status == VerificationStatus.UNVERIFIED
                and all(
                    item.verification_status in {
                        VerificationStatus.OFFICIAL_VERIFIED,
                        VerificationStatus.GAME_VERIFIED,
                    }
                    for item in supporting
                )
            ):
                claim.verification_status = VerificationStatus.OFFICIAL_VERIFIED
            if claim.verification_status == VerificationStatus.GAME_VERIFIED and any(
                item.verification_status != VerificationStatus.GAME_VERIFIED
                for item in supporting
            ):
                raise ValueError(
                    f"claim {claim.id} cannot be game verified before all evidence"
                )
            ranks = {
                VerificationStatus.UNVERIFIED: 0,
                VerificationStatus.COMMUNITY_VERIFIED: 1,
                VerificationStatus.OFFICIAL_VERIFIED: 2,
                VerificationStatus.GAME_VERIFIED: 3,
            }
            if any(
                ranks[item.verification_status] < ranks[claim.verification_status]
                for item in supporting
            ):
                raise ValueError(
                    f"claim {claim.id} cannot outrank its supporting evidence"
                )
        for text in self.localized_texts:
            if text.evidence_id not in evidence_ids:
                raise ValueError(
                    f"localized text {text.id} references unknown evidence {text.evidence_id}"
                )
        return self


def _unique_ids(records: list[StrictModel], record_type: str) -> set[str]:
    ids = [str(record.id) for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate {record_type} id")
    return set(ids)


def load_curated_dataset(path: Path) -> CuratedDataset:
    return CuratedDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))
