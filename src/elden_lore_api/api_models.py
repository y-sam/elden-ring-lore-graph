from typing import Any, Literal

from pydantic import BaseModel, Field


class EntitySummary(BaseModel):
    id: str
    kind: str
    canonical_name: str
    continuity: str


class EvidenceView(BaseModel):
    id: str
    locator: str
    summary_en: str
    review_status: str
    verification_status: str = "unverified"
    verification_url: str | None = None
    source_id: str
    source_title: str
    authority_tier: str
    localized_summaries: dict[str, str] = Field(default_factory=dict)


class ClaimView(BaseModel):
    id: str
    predicate: str
    evidence_level: str
    confidence: str
    review_status: str
    verification_status: str = "unverified"
    continuity: str
    direction: Literal["outgoing", "incoming"]
    subject: EntitySummary
    object: EntitySummary | None = None
    evidence: list[EvidenceView] = Field(default_factory=list)


class ClaimDetail(BaseModel):
    id: str
    predicate: str
    evidence_level: str
    confidence: str
    review_status: str
    verification_status: str = "unverified"
    continuity: str
    subject: EntitySummary
    object: EntitySummary | None = None
    evidence: list[EvidenceView] = Field(default_factory=list)


class EntityDetail(EntitySummary):
    claims: list[ClaimView] = Field(default_factory=list)


class EntityPage(BaseModel):
    items: list[EntitySummary]
    limit: int
    offset: int


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    predicate: str
    evidence_level: str
    confidence: str
    review_status: str
    verification_status: str = "unverified"


class EntitySubgraph(BaseModel):
    root_id: str
    depth: int
    nodes: list[EntitySummary]
    edges: list[GraphEdge]
    truncated: bool


class TimelineResponse(BaseModel):
    era_id: str | None
    events: list[EntitySummary]
    eras: list[EntitySummary]
    memberships: list[GraphEdge]
    precedence: list[GraphEdge]
    layers: list[list[str]]
    cycle_event_ids: list[str]
    is_partial: bool


class SearchHit(BaseModel):
    id: str
    result_type: Literal["entity", "evidence"]
    title: str
    summary: str | None = None
    score: float


class SearchResponse(BaseModel):
    query: str
    items: list[SearchHit]


class AnswerResponse(BaseModel):
    answer_id: str
    question: str
    language: Literal["en", "es", "pt-BR"]
    intent: Literal["who", "where", "when", "why", "relationship", "event", "general"]
    status: Literal["supported", "partial", "unknown"]
    answer: str
    matched_entities: list[EntitySummary] = Field(default_factory=list)
    explicit_claims: list[ClaimDetail] = Field(default_factory=list)
    inferred_claims: list[ClaimDetail] = Field(default_factory=list)
    supporting_claims: list[ClaimDetail] = Field(default_factory=list)
    citations: list[EvidenceView] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generator: Literal["deterministic", "openai", "gemini"] = "deterministic"
    generator_model: str | None = None
    generated_claim_ids: list[str] = Field(default_factory=list)
    generated_evidence_ids: list[str] = Field(default_factory=list)


class FeedbackCreate(BaseModel):
    answer_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    question: str = Field(min_length=3, max_length=300)
    language: Literal["en", "es", "pt-BR"]
    rating: Literal["helpful", "mixed", "not_helpful"]
    reason: Literal[
        "accurate", "clear", "missing_context", "wrong_fact", "weak_evidence",
        "translation", "other",
    ] | None = None
    comment: str | None = Field(default=None, max_length=1000)
    claim_ids: list[str] = Field(default_factory=list, max_length=20)


class FeedbackReceipt(BaseModel):
    id: str
    moderation_status: Literal["pending"] = "pending"


class FeedbackSummary(BaseModel):
    answer_id: str
    helpful: int = 0
    mixed: int = 0
    not_helpful: int = 0
    total: int = 0
    pending: int = 0
    community_signal: Literal["insufficient", "positive", "mixed", "negative"]


def entity_summary(properties: dict[str, Any]) -> EntitySummary:
    return EntitySummary(
        id=properties["id"],
        kind=properties["kind"],
        canonical_name=properties["canonical_name"],
        continuity=properties["continuity"],
    )
