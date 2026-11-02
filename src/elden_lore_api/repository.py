import hashlib
import re
from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from neo4j import Driver

from elden_lore_api.api_models import (
    AnswerResponse,
    ClaimDetail,
    ClaimView,
    EntityDetail,
    EntityPage,
    EntitySubgraph,
    EvidenceView,
    GraphEdge,
    SearchHit,
    SearchResponse,
    TimelineResponse,
    entity_summary,
)
from elden_lore_api.timeline import topological_layers


class EntityRepository:
    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database

    def list_entities(
        self, *, query: str | None, kind: str | None, limit: int, offset: int
    ) -> EntityPage:
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (entity:Entity)
                WHERE ($search IS NULL OR
                       toLower(entity.canonical_name) CONTAINS toLower($search))
                  AND ($kind IS NULL OR entity.kind = $kind)
                RETURN properties(entity) AS entity
                ORDER BY toLower(entity.canonical_name), entity.id
                SKIP $offset LIMIT $limit
                """,
                search=query,
                kind=kind,
                limit=limit,
                offset=offset,
            )
            items = [entity_summary(record["entity"]) for record in records]
        return EntityPage(items=items, limit=limit, offset=offset)

    def get_entity(self, entity_id: str, *, include_drafts: bool) -> EntityDetail | None:
        with self.driver.session(database=self.database) as session:
            entity_record = session.run(
                """
                MATCH (entity:Entity {id: $entity_id})
                RETURN properties(entity) AS entity
                """,
                entity_id=entity_id,
            ).single()
            if entity_record is None:
                return None

            claim_records = list(
                session.run(
                    """
                    MATCH (claim:Claim)-[:SUBJECT]->(subject:Entity)
                    OPTIONAL MATCH (claim)-[:OBJECT]->(object:Entity)
                    WITH claim, subject, object
                    WHERE (subject.id = $entity_id OR object.id = $entity_id)
                      AND ($include_drafts OR
                           claim.review_status IN ['reviewed', 'disputed'])
                    OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
                    OPTIONAL MATCH (source:Source)-[:CONTAINS]->(evidence)
                    OPTIONAL MATCH (evidence)-[:HAS_TEXT]->(localized:LocalizedText)
                    RETURN properties(claim) AS claim,
                           properties(subject) AS subject,
                           properties(object) AS object,
                           properties(evidence) AS evidence,
                           properties(source) AS source,
                           properties(localized) AS localized
                    ORDER BY claim.predicate, claim.id, evidence.id
                    """,
                    entity_id=entity_id,
                    include_drafts=include_drafts,
                )
            )

        claims = _group_claims(claim_records, entity_id=entity_id)
        summary = entity_summary(entity_record["entity"])
        return EntityDetail(**summary.model_dump(), claims=claims)

    def get_claim(self, claim_id: str, *, include_drafts: bool) -> ClaimDetail | None:
        with self.driver.session(database=self.database) as session:
            records = list(
                session.run(
                    """
                    MATCH (claim:Claim {id: $claim_id})-[:SUBJECT]->(subject:Entity)
                    OPTIONAL MATCH (claim)-[:OBJECT]->(object:Entity)
                    WITH claim, subject, object
                    WHERE $include_drafts OR
                          claim.review_status IN ['reviewed', 'disputed']
                    OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
                    OPTIONAL MATCH (source:Source)-[:CONTAINS]->(evidence)
                    OPTIONAL MATCH (evidence)-[:HAS_TEXT]->(localized:LocalizedText)
                    RETURN properties(claim) AS claim,
                           properties(subject) AS subject,
                           properties(object) AS object,
                           properties(evidence) AS evidence,
                           properties(source) AS source,
                           properties(localized) AS localized
                    ORDER BY evidence.id
                    """,
                    claim_id=claim_id,
                    include_drafts=include_drafts,
                )
            )
        if not records:
            return None
        claim = _group_claims(records, entity_id=records[0]["subject"]["id"])[0]
        return ClaimDetail(
            id=claim.id,
            predicate=claim.predicate,
            evidence_level=claim.evidence_level,
            confidence=claim.confidence,
            review_status=claim.review_status,
            verification_status=claim.verification_status,
            continuity=claim.continuity,
            subject=claim.subject,
            object=claim.object,
            evidence=claim.evidence,
        )

    def get_subgraph(
        self, entity_id: str, *, depth: int, limit: int, include_drafts: bool
    ) -> EntitySubgraph | None:
        root = self.get_entity(entity_id, include_drafts=include_drafts)
        if root is None:
            return None

        nodes = {root.id: entity_summary(root.model_dump())}
        edges: dict[str, GraphEdge] = {}
        frontier = {root.id}
        truncated = False

        with self.driver.session(database=self.database) as session:
            for _ in range(depth):
                if not frontier or len(nodes) >= limit:
                    truncated = len(nodes) >= limit
                    break
                records = session.run(
                    """
                    MATCH (claim:Claim)-[:SUBJECT]->(subject:Entity)
                    MATCH (claim)-[:OBJECT]->(object:Entity)
                    WHERE (subject.id IN $frontier OR object.id IN $frontier)
                      AND ($include_drafts OR
                           claim.review_status IN ['reviewed', 'disputed'])
                    RETURN properties(claim) AS claim,
                           properties(subject) AS subject,
                           properties(object) AS object
                    ORDER BY claim.id
                    LIMIT $query_limit
                    """,
                    frontier=sorted(frontier),
                    include_drafts=include_drafts,
                    query_limit=max(100, limit * 4),
                )
                next_frontier: set[str] = set()
                for record in records:
                    subject = entity_summary(record["subject"])
                    object_ = entity_summary(record["object"])
                    new_ids = {
                        node.id for node in (subject, object_) if node.id not in nodes
                    }
                    if len(nodes) + len(new_ids) > limit:
                        truncated = True
                        continue
                    for node in (subject, object_):
                        nodes[node.id] = node
                    next_frontier.update(new_ids)
                    claim = record["claim"]
                    edges[claim["id"]] = GraphEdge(
                        id=claim["id"],
                        source=subject.id,
                        target=object_.id,
                        predicate=claim["predicate"],
                        evidence_level=claim["evidence_level"],
                        confidence=claim["confidence"],
                        review_status=claim["review_status"],
                        verification_status=claim.get(
                            "verification_status", "unverified"
                        ),
                    )
                frontier = next_frontier

        return EntitySubgraph(
            root_id=entity_id,
            depth=depth,
            nodes=sorted(nodes.values(), key=lambda node: (node.canonical_name.lower(), node.id)),
            edges=sorted(edges.values(), key=lambda edge: edge.id),
            truncated=truncated,
        )

    def get_timeline(
        self, *, era_id: str | None, include_drafts: bool
    ) -> TimelineResponse:
        with self.driver.session(database=self.database) as session:
            event_records = list(
                session.run(
                    """
                    MATCH (event:Entity {kind: 'event'})
                    WHERE EXISTS {
                      MATCH (membership:Claim)-[:SUBJECT]->(event)
                      MATCH (membership)-[:OBJECT]->(era:Entity {kind: 'era'})
                      WHERE membership.predicate = 'IN_ERA'
                        AND ($include_drafts OR
                             membership.review_status IN ['reviewed', 'disputed'])
                        AND ($era_id IS NULL OR era.id = $era_id)
                    }
                    RETURN properties(event) AS event
                    ORDER BY toLower(event.canonical_name), event.id
                    """,
                    era_id=era_id,
                    include_drafts=include_drafts,
                )
            )
            events = [entity_summary(record["event"]) for record in event_records]
            event_ids = {event.id for event in events}
            if not event_ids:
                return TimelineResponse(
                    era_id=era_id,
                    events=[],
                    eras=[],
                    memberships=[],
                    precedence=[],
                    layers=[],
                    cycle_event_ids=[],
                    is_partial=False,
                )

            membership_records = list(
                session.run(
                    """
                    MATCH (claim:Claim)-[:SUBJECT]->(event:Entity)
                    MATCH (claim)-[:OBJECT]->(era:Entity {kind: 'era'})
                    WHERE claim.predicate = 'IN_ERA'
                      AND event.id IN $event_ids
                      AND ($include_drafts OR
                           claim.review_status IN ['reviewed', 'disputed'])
                    RETURN properties(claim) AS claim,
                           properties(event) AS subject,
                           properties(era) AS object
                    ORDER BY claim.id
                    """,
                    event_ids=sorted(event_ids),
                    include_drafts=include_drafts,
                )
            )
            precedence_records = list(
                session.run(
                    """
                    MATCH (claim:Claim)-[:SUBJECT]->(before:Entity)
                    MATCH (claim)-[:OBJECT]->(after:Entity)
                    WHERE claim.predicate = 'BEFORE'
                      AND before.id IN $event_ids
                      AND after.id IN $event_ids
                      AND ($include_drafts OR
                           claim.review_status IN ['reviewed', 'disputed'])
                    RETURN properties(claim) AS claim,
                           properties(before) AS subject,
                           properties(after) AS object
                    ORDER BY claim.id
                    """,
                    event_ids=sorted(event_ids),
                    include_drafts=include_drafts,
                )
            )

        memberships = [_graph_edge(record) for record in membership_records]
        precedence = [_graph_edge(record) for record in precedence_records]
        eras_by_id = {
            record["object"]["id"]: entity_summary(record["object"])
            for record in membership_records
        }
        layers, cycle_event_ids = topological_layers(
            event_ids,
            [(edge.source, edge.target) for edge in precedence],
        )
        return TimelineResponse(
            era_id=era_id,
            events=events,
            eras=sorted(
                eras_by_id.values(), key=lambda entity: (entity.canonical_name.lower(), entity.id)
            ),
            memberships=memberships,
            precedence=precedence,
            layers=layers,
            cycle_event_ids=cycle_event_ids,
            is_partial=bool(cycle_event_ids) or any(len(layer) > 1 for layer in layers),
        )

    def search(
        self, *, query: str, limit: int, include_drafts: bool
    ) -> SearchResponse:
        fulltext_query = build_fulltext_query(query)
        if not fulltext_query:
            return SearchResponse(query=query, items=[])

        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                CALL db.index.fulltext.queryNodes(
                  'lore_fulltext',
                  $fulltext_query,
                  {limit: $candidate_limit}
                ) YIELD node, score
                WHERE node:Entity OR
                      (node:Evidence AND
                       ($include_drafts OR
                        node.review_status IN ['reviewed', 'disputed']))
                RETURN labels(node) AS labels, properties(node) AS item, score
                ORDER BY score DESC, item.id
                LIMIT $limit
                """,
                fulltext_query=fulltext_query,
                candidate_limit=max(50, limit * 4),
                include_drafts=include_drafts,
                limit=limit,
            )
            items = [_search_hit(record) for record in records]
            if not items:
                candidates = session.run(
                    """
                    MATCH (entity:Entity)
                    OPTIONAL MATCH (entity)-[:HAS_ALIAS]->(alias:Alias)
                    RETURN properties(entity) AS entity,
                           collect(alias.value) AS aliases
                    """
                )
                ranked = sorted(
                    (
                        (_fuzzy_entity_score(query, record["entity"], record["aliases"]), record)
                        for record in candidates
                    ),
                    key=lambda item: (-item[0], item[1]["entity"]["id"]),
                )
                items = [
                    SearchHit(
                        id=record["entity"]["id"], result_type="entity",
                        title=record["entity"]["canonical_name"], score=score,
                    )
                    for score, record in ranked[:limit]
                    if score >= 0.72
                ]
        return SearchResponse(query=query, items=items)

    def answer_question(
        self, *, question: str, language: str | None, limit: int, include_drafts: bool
    ) -> AnswerResponse:
        answer_language = language or detect_question_language(question)
        intent = detect_question_intent(question)
        entity_query = build_entity_query(question)
        if not entity_query:
            return _unknown_answer(question, language=answer_language, intent=intent)

        with self.driver.session(database=self.database) as session:
            entity_records = list(
                session.run(
                    """
                    CALL db.index.fulltext.queryNodes(
                      'lore_fulltext',
                      $entity_query,
                      {limit: 12}
                    ) YIELD node, score
                    WHERE node:Entity
                    RETURN properties(node) AS entity, score
                    ORDER BY score DESC, node.id
                    LIMIT 4
                    """,
                    entity_query=entity_query,
                )
            )
            question_terms = [
                term.lower() for term in re.findall(r"\w+", question, flags=re.UNICODE)
                if len(term) > 2 and term.lower() not in QUESTION_STOPWORDS
            ]
            alias_records = list(
                session.run(
                    """
                    MATCH (entity:Entity)-[:HAS_ALIAS]->(alias_node:Alias)
                    WHERE any(term IN $terms WHERE toLower(alias_node.value) CONTAINS term)
                    RETURN properties(entity) AS entity, alias_node.value AS matched_alias
                    ORDER BY size(alias_node.value), entity.id
                    LIMIT 4
                    """,
                    terms=question_terms,
                )
            )
            exact_records = list(
                session.run(
                    "MATCH (entity:Entity) RETURN properties(entity) AS entity"
                )
            )
            exact_entity_ids = {
                record["entity"]["id"]
                for record in exact_records
                if _name_phrase_is_named(question, record["entity"]["canonical_name"])
            }
            alias_records.extend(
                {"entity": record["entity"], "matched_alias": None}
                for record in exact_records
                if record["entity"]["id"] in exact_entity_ids
            )
            if not entity_records and not alias_records:
                candidates = list(
                    session.run(
                        """
                        MATCH (entity:Entity)
                        OPTIONAL MATCH (entity)-[:HAS_ALIAS]->(alias:Alias)
                        RETURN properties(entity) AS entity,
                               collect(alias.value) AS aliases
                        """
                    )
                )
                ranked = sorted(
                    (
                        (_fuzzy_entity_score(question, record["entity"], record["aliases"]), record)
                        for record in candidates
                    ),
                    key=lambda item: (-item[0], item[1]["entity"]["id"]),
                )
                alias_records = [
                    {"entity": record["entity"], "matched_alias": None}
                    for score, record in ranked[:1]
                    if score >= 0.78
                ]
            alias_entity_ids = {
                record["entity"]["id"] for record in alias_records
            } | exact_entity_ids
            seen_entity_ids: set[str] = set()
            matched_entities = [
                entity_summary(record["entity"])
                for record in [*alias_records, *entity_records]
                if not (
                    record["entity"]["id"] in seen_entity_ids
                    or seen_entity_ids.add(record["entity"]["id"])
                )
            ]
            named_entities = [
                entity for entity in matched_entities
                if entity.id in alias_entity_ids or _entity_is_named(question, entity.id)
            ]
            matched_entities = named_entities
            if not matched_entities:
                return _unknown_answer(question, language=answer_language, intent=intent)

            entity_ids = [entity.id for entity in matched_entities]
            claim_records = list(
                session.run(
                    """
                    MATCH (anchor:Claim)-[:SUBJECT]->(anchor_subject:Entity)
                    OPTIONAL MATCH (anchor)-[:OBJECT]->(anchor_object:Entity)
                    WITH anchor, anchor_subject, anchor_object
                    WHERE (anchor_subject.id IN $entity_ids OR anchor_object.id IN $entity_ids)
                      AND ($include_drafts OR
                           anchor.review_status IN ['reviewed', 'disputed'])
                    WITH collect(DISTINCT anchor_subject.id) +
                         collect(DISTINCT anchor_object.id) + $entity_ids AS context_ids
                    MATCH (claim:Claim)-[:SUBJECT]->(subject:Entity)
                    OPTIONAL MATCH (claim)-[:OBJECT]->(object:Entity)
                    WITH claim, subject, object, context_ids
                    WHERE (subject.id IN context_ids OR object.id IN context_ids)
                      AND ($include_drafts OR
                           claim.review_status IN ['reviewed', 'disputed'])
                    OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
                    OPTIONAL MATCH (source:Source)-[:CONTAINS]->(evidence)
                    OPTIONAL MATCH (evidence)-[:HAS_TEXT]->(localized:LocalizedText)
                    RETURN properties(claim) AS claim,
                           properties(subject) AS subject,
                           properties(object) AS object,
                           properties(evidence) AS evidence,
                           properties(source) AS source,
                           properties(localized) AS localized
                    ORDER BY claim.id, evidence.id
                    """,
                    entity_ids=entity_ids,
                    include_drafts=include_drafts,
                )
            )

        all_claims = _claim_details(claim_records)
        matched_ids = {entity.id for entity in matched_entities}
        claims = _filter_claims_for_intent(
            all_claims, intent=intent, matched_ids=matched_ids, question=question
        )
        claims.sort(
            key=lambda claim: (
                -sum(
                    entity_id in matched_ids
                    for entity_id in (
                        claim.subject.id,
                        claim.object.id if claim.object else None,
                    )
                ),
                _intent_claim_rank(claim, intent),
                0 if claim.subject.id in matched_ids else 1,
                _claim_rank(claim),
                claim.id,
            )
        )
        claims, supporting_claims = _claims_with_support(
            claims,
            all_claims=all_claims,
            matched_ids=matched_ids,
            intent=intent,
        )
        selected_claims = claims[:limit]
        selected_ids = {claim.id for claim in selected_claims}
        supporting_claims = [
            claim for claim in supporting_claims
            if any(
                _claims_share_entity(claim, selected)
                for selected in selected_claims
                if selected.id in selected_ids
            )
        ]
        return _compose_answer(
            question,
            language=answer_language,
            intent=intent,
            matched_entities=matched_entities,
            claims=selected_claims,
            supporting_claims=supporting_claims,
        )


def _group_claims(records: Iterable[Any], *, entity_id: str) -> list[ClaimView]:
    grouped: dict[str, ClaimView] = {}
    for record in records:
        claim = record["claim"]
        claim_id = claim["id"]
        if claim_id not in grouped:
            subject_properties = record["subject"]
            object_properties = record["object"]
            grouped[claim_id] = ClaimView(
                id=claim_id,
                predicate=claim["predicate"],
                evidence_level=claim["evidence_level"],
                confidence=claim["confidence"],
                review_status=claim["review_status"],
                verification_status=claim.get("verification_status", "unverified"),
                continuity=claim["continuity"],
                direction="outgoing" if subject_properties["id"] == entity_id else "incoming",
                subject=entity_summary(subject_properties),
                object=entity_summary(object_properties) if object_properties else None,
            )
        _merge_evidence(grouped[claim_id].evidence, record)
    return list(grouped.values())


def _graph_edge(record: Any) -> GraphEdge:
    claim = record["claim"]
    return GraphEdge(
        id=claim["id"],
        source=record["subject"]["id"],
        target=record["object"]["id"],
        predicate=claim["predicate"],
        evidence_level=claim["evidence_level"],
        confidence=claim["confidence"],
        review_status=claim["review_status"],
        verification_status=claim.get("verification_status", "unverified"),
    )


def build_fulltext_query(query: str) -> str:
    terms = [term.lower() for term in query.split() if term.isalnum()]
    return " AND ".join(f'"{term}"' for term in terms)


QUESTION_STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "between", "como", "da", "das", "de", "del",
    "did", "do", "does", "dos", "el", "en", "e", "era", "es", "foi", "how", "in",
    "is", "la", "las", "los", "na", "nas", "no", "nos", "o", "of", "os", "por",
    "que", "quem", "se",
    "qual", "relação", "relationship", "sobre", "the", "to", "um", "uma", "what",
    "when", "where", "who", "why", "y",
}


def build_entity_query(question: str) -> str:
    terms = [
        term.lower()
        for term in re.findall(r"\w+", question, flags=re.UNICODE)
        if term.lower() not in QUESTION_STOPWORDS and len(term) > 1
    ]
    return " OR ".join(f'"{term}"' for term in terms[:8])


def _entity_is_named(question: str, entity_id: str) -> bool:
    normalized_question = " ".join(re.findall(r"\w+", question.lower(), flags=re.UNICODE))
    entity_slug = entity_id.split(".", 1)[-1].replace("-", " ")
    distinctive_name = entity_slug.split()[-1]
    generic_event_prefixes = {
        "battle", "death", "defense", "night", "shattering", "stalemate", "union", "war"
    }
    can_use_short_name = entity_slug.split()[0] in generic_event_prefixes
    return entity_slug in normalized_question or (
        can_use_short_name and distinctive_name in normalized_question.split()
    )


def _name_phrase_is_named(question: str, canonical_name: str) -> bool:
    normalized_question = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    normalized_name = " ".join(re.findall(r"[a-z0-9]+", canonical_name.lower()))
    return len(normalized_name) >= 4 and normalized_name in normalized_question


def _claim_details(records: Iterable[Any]) -> list[ClaimDetail]:
    grouped: dict[str, ClaimDetail] = {}
    for record in records:
        claim = record["claim"]
        claim_id = claim["id"]
        if claim_id not in grouped:
            grouped[claim_id] = ClaimDetail(
                id=claim_id,
                predicate=claim["predicate"],
                evidence_level=claim["evidence_level"],
                confidence=claim["confidence"],
                review_status=claim["review_status"],
                verification_status=claim.get("verification_status", "unverified"),
                continuity=claim["continuity"],
                subject=entity_summary(record["subject"]),
                object=entity_summary(record["object"]) if record["object"] else None,
            )
        _merge_evidence(grouped[claim_id].evidence, record)
    return list(grouped.values())


def _merge_evidence(items: list[EvidenceView], record: Any) -> None:
    evidence = record["evidence"]
    source = record["source"]
    if not evidence or not source:
        return
    item = next((candidate for candidate in items if candidate.id == evidence["id"]), None)
    if item is None:
        item = EvidenceView(
            id=evidence["id"],
            locator=evidence["locator"],
            summary_en=evidence["summary_en"],
            review_status=evidence["review_status"],
            verification_status=evidence.get("verification_status", "unverified"),
            verification_url=evidence.get("verification_url"),
            source_id=source["id"],
            source_title=source["title"],
            authority_tier=source["authority_tier"],
        )
        items.append(item)
    localized = record["localized"]
    if localized and localized.get("field") == "summary":
        item.localized_summaries[localized["locale"]] = localized["text"]


def _claim_rank(claim: ClaimDetail) -> tuple[int, int]:
    level_rank = {
        "explicit": 0, "synthesis": 1, "strong_inference": 2,
        "disputed": 3, "weak_inference": 4, "theory": 5, "unknown": 6,
    }
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    return level_rank.get(claim.evidence_level, 7), confidence_rank.get(claim.confidence, 3)


def _intent_claim_rank(claim: ClaimDetail, intent: str) -> int:
    priorities = {
        "who": [
            "SAME_BEING_AS", "CHILD_OF", "TWIN_OF", "CONSORT_OF", "VESSEL_OF",
            "CREATED", "BLADE_OF", "LEADS", "MEMBER_OF", "FOUNDER_OF", "RULED",
            "SERVES", "SERVED", "FOLLOWS", "FOLLOWED", "GUIDED", "SEEKS",
            "PARTICIPANT", "ABANDONED", "AFFLICTED_BY", "ASPECT_OF",
        ],
        "where": [
            "BASED_IN", "LOCATED_IN", "OCCURRED_IN", "INHABITS",
            "RESTS_IN", "FIRST_ARRIVED_IN",
        ],
        "when": ["IN_ERA", "BEFORE"],
        "why": ["CAUSED", "CATALYST_FOR"],
    }
    ordered = priorities.get(intent, [])
    return ordered.index(claim.predicate) if claim.predicate in ordered else len(ordered)


INTENT_PREDICATES = {
    "who": {
        "ABANDONED", "BLADE_OF", "CHILD_OF", "CONSORT_OF", "CREATED", "FOLLOWS",
        "FOUNDER_OF", "LEADS", "MEMBER_OF", "PARTICIPANT", "RULED", "SAME_BEING_AS",
        "SERVED", "SERVES", "FOLLOWED", "GUIDED", "SEEKS", "TWIN_OF", "VESSEL_OF",
    },
    "where": {
        "BASED_IN", "FIRST_ARRIVED_IN", "INHABITS", "LOCATED_IN", "OCCURRED_IN",
        "RESTS_IN",
    },
    "when": {"BEFORE", "IN_ERA"},
    "why": {"CATALYST_FOR", "CAUSED"},
}


def detect_question_language(question: str) -> str:
    text = question.lower()
    if re.search(r"\b(quem|onde|quando|qual|relação|aconteceu|por que|porque|foi|é)\b", text):
        return "pt-BR"
    if re.search(
        r"\b(quién|quien|dónde|donde|cuándo|cuando|relación|qué|que|pasó|por qué)\b",
        text,
    ):
        return "es"
    return "en"


def detect_question_intent(question: str) -> str:
    text = question.lower()
    if re.search(r"\b(relationship|relação|relación)\b", text):
        return "relationship"
    if re.search(r"\b(where|onde|dónde|donde)\b", text):
        return "where"
    if re.search(r"\b(when|quando|cuándo|cuando)\b", text):
        return "when"
    if re.search(r"\b(why|por que|por quê|porque|por qué)\b", text):
        return "why"
    if re.search(r"\b(who|quem|quién|quien)\b", text):
        return "who"
    if re.search(r"\b(happened|aconteceu|ocorreu|pasó|ocurrió)\b", text):
        return "event"
    return "general"


def _filter_claims_for_intent(
    claims: list[ClaimDetail], *, intent: str, matched_ids: set[str], question: str = ""
) -> list[ClaimDetail]:
    if intent == "relationship" and len(matched_ids) > 1:
        return [
            claim for claim in claims
            if claim.object and claim.subject.id in matched_ids and claim.object.id in matched_ids
        ]
    predicates = INTENT_PREDICATES.get(intent)
    if predicates:
        selected = [claim for claim in claims if claim.predicate in predicates]
        if intent != "who":
            return selected
        inverse_predicates = {
            "serves": "SERVES", "served": "SERVED", "follows": "FOLLOWS",
            "followed": "FOLLOWED", "guides": "GUIDED", "rules": "RULED",
        }
        requested_inverse = next(
            (
                predicate
                for word, predicate in inverse_predicates.items()
                if word in question.lower()
            ),
            None,
        )
        if requested_inverse:
            incoming = [
                claim for claim in claims
                if claim.predicate == requested_inverse
                and claim.object and claim.object.id in matched_ids
            ]
            if incoming:
                return incoming
        direct_selected = [
            claim for claim in selected
            if claim.subject.id in matched_ids
            or (claim.object and claim.object.id in matched_ids)
        ]
        if direct_selected:
            return direct_selected
        outgoing = [claim for claim in claims if claim.subject.id in matched_ids]
        if outgoing:
            return outgoing
        return [
            claim for claim in claims
            if claim.object and claim.object.id in matched_ids
        ]
    return claims


def _claims_with_support(
    selected_claims: list[ClaimDetail], *, all_claims: list[ClaimDetail],
    matched_ids: set[str], intent: str,
) -> tuple[list[ClaimDetail], list[ClaimDetail]]:
    direct_claims = [
        claim
        for claim in selected_claims
        if {claim.subject.id, claim.object.id if claim.object else None} & matched_ids
    ]
    if direct_claims:
        return direct_claims, []
    bridge_predicates = {
        "where": {"BASED_IN", "CONTAINS", "CREATED", "LOCATED_IN", "PARTICIPANT"},
        "when": {"CAUSED", "PARTICIPANT"},
    }.get(intent, set())
    valid: list[ClaimDetail] = []
    supporting: dict[str, ClaimDetail] = {}
    for selected in selected_claims:
        selected_ids = {selected.subject.id}
        if selected.object:
            selected_ids.add(selected.object.id)
        if selected_ids & matched_ids:
            valid.append(selected)
            continue
        for candidate in all_claims:
            candidate_ids = {candidate.subject.id}
            if candidate.object:
                candidate_ids.add(candidate.object.id)
            if (
                candidate.predicate in bridge_predicates
                and candidate_ids & matched_ids
                and candidate_ids & selected_ids
            ):
                valid.append(selected)
                supporting[candidate.id] = candidate
                break
    return valid, sorted(
        supporting.values(), key=lambda claim: (_claim_rank(claim), claim.id)
    )


def _claims_share_entity(first: ClaimDetail, second: ClaimDetail) -> bool:
    first_ids = {first.subject.id, first.object.id if first.object else None}
    second_ids = {second.subject.id, second.object.id if second.object else None}
    return bool(first_ids & second_ids)


def _fuzzy_entity_score(
    query: str, entity: dict[str, Any], aliases: list[str] | None = None
) -> float:
    query_tokens = [
        token for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 2 and token not in QUESTION_STOPWORDS
    ]
    candidate_tokens = [
        token
        for value in [entity["canonical_name"], *(aliases or [])]
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
    ]
    if not query_tokens or not candidate_tokens:
        return 0.0
    return max(
        SequenceMatcher(None, query_token, candidate_token).ratio()
        for query_token in query_tokens
        for candidate_token in candidate_tokens
    )


PREDICATE_PHRASES = {
    "en": {
        "ABANDONED": "abandoned", "ABANDONED_ASPECT": "abandoned the aspect",
        "AFFLICTED_BY": "is afflicted by", "ASPECT_OF": "is an aspect of",
        "BASED_IN": "is based in", "BECAME_LORD_OF": "became lord of",
        "BEFORE": "occurred before",
        "BLADE_OF": "is the blade of", "CATALYST_FOR": "was a catalyst for",
        "CAUSED": "caused", "CHILD_OF": "is a child of", "CONSORT_OF": "is consort to",
        "CLAIMED_BY": "was claimed by", "CONTAINS": "contains", "CREATED": "created",
        "DEFENDS": "defends", "DEVASTATED": "devastated", "EMBODIES": "embodies",
        "ENTERED_VIA": "entered via", "FIRST_ARRIVED_IN": "first arrived in",
        "FOLLOWED": "followed", "FOLLOWS": "follows", "FOUGHT": "fought",
        "FOUNDER_OF": "founded", "FRAGMENTS_OF": "are fragments of",
        "GRANTS_POWER_TO": "grants power to", "GUARDED_BY": "is guarded by",
        "GUIDED": "guided", "HELD_TITLE": "held the title tied to",
        "IDENTITY_OF": "is another identity of", "IN_ERA": "belongs to the era",
        "INHABITS": "inhabits", "LEADS": "leads", "LOCATED_IN": "is located in",
        "INTERPRETS": "interprets the will of", "MEMBER_OF": "is a member of",
        "OBSCURED_BY": "is obscured by", "OCCURRED_IN": "occurred in",
        "OPPOSED": "opposed", "ORDER_OF": "belongs to the order of",
        "PARTICIPANT": "involved", "RULED": "ruled", "SAME_BEING_AS": "is the same being as",
        "PROGENITOR_OF": "is the progenitor of", "RESTS_IN": "rests in",
        "SEEKS": "seeks", "SEEKS_TO_END": "seeks to end", "SERVED": "served",
        "SERVES": "serves", "SHATTERED_IN": "was shattered in", "SOURCE_OF": "is the source of",
        "SPREAD_AFTER": "spread after", "STOLE_FRAGMENT_OF": "stole a fragment of",
        "TARGETED": "targeted", "TWIN_OF": "is the twin of", "VESSEL_OF": "is the vessel of",
    },
    "es": {
        "ABANDONED": "abandonó", "ABANDONED_ASPECT": "abandonó el aspecto",
        "AFFLICTED_BY": "padece", "ASPECT_OF": "es un aspecto de",
        "BASED_IN": "tiene su base en", "BECAME_LORD_OF": "se convirtió en señor de",
        "BEFORE": "ocurrió antes de",
        "BLADE_OF": "es la espada de", "CATALYST_FOR": "fue un catalizador de",
        "CAUSED": "causó", "CHILD_OF": "es descendiente de", "CONSORT_OF": "es consorte de",
        "CLAIMED_BY": "fue reclamado por", "CONTAINS": "contiene a", "CREATED": "creó",
        "DEFENDS": "defiende", "DEVASTATED": "devastó", "EMBODIES": "encarna",
        "ENTERED_VIA": "entró a través de", "FIRST_ARRIVED_IN": "llegó primero a",
        "FOLLOWED": "siguió a", "FOLLOWS": "sigue a", "FOUGHT": "combatió contra",
        "FOUNDER_OF": "fundó", "FRAGMENTS_OF": "son fragmentos de",
        "GRANTS_POWER_TO": "otorga poder a", "GUARDED_BY": "es custodiado por",
        "GUIDED": "guio a", "HELD_TITLE": "ostentó el título ligado a",
        "IDENTITY_OF": "es otra identidad de", "IN_ERA": "pertenece a la era",
        "INHABITS": "habita", "LEADS": "lidera", "LOCATED_IN": "está situado en",
        "INTERPRETS": "interpreta la voluntad de", "MEMBER_OF": "es miembro de",
        "OBSCURED_BY": "está oculto por", "OCCURRED_IN": "ocurrió en",
        "OPPOSED": "se opuso a", "ORDER_OF": "pertenece a la orden de",
        "PARTICIPANT": "involucró a", "RULED": "gobernó", "SAME_BEING_AS": "es el mismo ser que",
        "PROGENITOR_OF": "es progenitor de", "RESTS_IN": "reposa en",
        "SEEKS": "busca", "SEEKS_TO_END": "busca acabar con", "SERVED": "sirvió a",
        "SERVES": "sirve a", "SHATTERED_IN": "fue destruido en", "SOURCE_OF": "es la fuente de",
        "SPREAD_AFTER": "se extendió después de", "STOLE_FRAGMENT_OF": "robó un fragmento de",
        "TARGETED": "atacó a", "TWIN_OF": "es gemelo de", "VESSEL_OF": "es el recipiente de",
    },
    "pt-BR": {
        "ABANDONED": "abandonou", "ABANDONED_ASPECT": "abandonou o aspecto",
        "AFFLICTED_BY": "é afligido por", "ASPECT_OF": "é um aspecto de",
        "BASED_IN": "tem sua base em", "BECAME_LORD_OF": "tornou-se lorde de",
        "BEFORE": "ocorreu antes de",
        "BLADE_OF": "é a lâmina de", "CATALYST_FOR": "foi um catalisador de",
        "CAUSED": "causou", "CHILD_OF": "é descendente de", "CONSORT_OF": "é consorte de",
        "CLAIMED_BY": "foi reivindicado por", "CONTAINS": "contém", "CREATED": "criou",
        "DEFENDS": "defende", "DEVASTATED": "devastou", "EMBODIES": "incorpora",
        "ENTERED_VIA": "entrou por meio de", "FIRST_ARRIVED_IN": "chegou primeiro a",
        "FOLLOWED": "seguiu", "FOLLOWS": "segue", "FOUGHT": "lutou contra",
        "FOUNDER_OF": "fundou", "FRAGMENTS_OF": "são fragmentos de",
        "GRANTS_POWER_TO": "concede poder a", "GUARDED_BY": "é guardado por",
        "GUIDED": "guiou", "HELD_TITLE": "ocupou o título ligado a",
        "IDENTITY_OF": "é outra identidade de", "IN_ERA": "pertence à era",
        "INHABITS": "habita", "LEADS": "lidera", "LOCATED_IN": "está localizado em",
        "INTERPRETS": "interpreta a vontade de", "MEMBER_OF": "é membro de",
        "OBSCURED_BY": "é ocultado por", "OCCURRED_IN": "ocorreu em",
        "OPPOSED": "opôs-se a", "ORDER_OF": "pertence à ordem de",
        "PARTICIPANT": "envolveu", "RULED": "governou", "SAME_BEING_AS": "é o mesmo ser que",
        "PROGENITOR_OF": "é progenitor de", "RESTS_IN": "repousa em",
        "SEEKS": "busca", "SEEKS_TO_END": "busca pôr fim a", "SERVED": "serviu a",
        "SERVES": "serve a", "SHATTERED_IN": "foi despedaçado em", "SOURCE_OF": "é a fonte de",
        "SPREAD_AFTER": "espalhou-se depois de", "STOLE_FRAGMENT_OF": "roubou um fragmento de",
        "TARGETED": "teve como alvo", "TWIN_OF": "é gêmeo de", "VESSEL_OF": "é o receptáculo de",
    },
}


ANSWER_TEXT = {
    "en": {
        "supported": "The current evidence supports",
        "inference": "The graph only offers inference",
        "unknown": (
            "The current curated graph does not contain enough evidence "
            "to answer this question."
        ),
        "no_claim": "No supported claim matching the question's intent was found.",
        "inferred": "Some relevant relationships are inference, disputed, theoretical, or unknown.",
        "draft": "This answer includes draft editorial records pending human review.",
    },
    "es": {
        "supported": "La evidencia actual respalda",
        "inference": "El grafo solo ofrece una inferencia",
        "unknown": (
            "El grafo curado actual no contiene evidencia suficiente "
            "para responder esta pregunta."
        ),
        "no_claim": (
            "No se encontró una afirmación respaldada que coincida "
            "con la intención de la pregunta."
        ),
        "inferred": (
            "Algunas relaciones relevantes son inferencias, disputas, "
            "teorías o datos desconocidos."
        ),
        "draft": (
            "Esta respuesta incluye registros editoriales en borrador "
            "pendientes de revisión humana."
        ),
    },
    "pt-BR": {
        "supported": "As evidências atuais sustentam",
        "inference": "O grafo oferece apenas uma inferência",
        "unknown": (
            "O grafo curado atual não contém evidências suficientes "
            "para responder a esta pergunta."
        ),
        "no_claim": "Nenhuma afirmação sustentada corresponde à intenção da pergunta.",
        "inferred": (
            "Algumas relações relevantes são inferências, disputas, "
            "teorias ou dados desconhecidos."
        ),
        "draft": "Esta resposta inclui registros editoriais em rascunho aguardando revisão humana.",
    },
}


def _compose_answer(
    question: str, *, language: str, intent: str,
    matched_entities: list[Any], claims: list[ClaimDetail],
    supporting_claims: list[ClaimDetail]
) -> AnswerResponse:
    if not claims:
        return _unknown_answer(
            question, language=language, intent=intent, matched_entities=matched_entities
        )
    explicit = [claim for claim in claims if claim.evidence_level in {"explicit", "synthesis"}]
    inferred = [claim for claim in claims if claim.evidence_level not in {"explicit", "synthesis"}]
    leading = explicit or inferred
    if len(matched_entities) > 1:
        matched_ids = {entity.id for entity in matched_entities}
        direct = [
            claim
            for claim in leading
            if claim.object
            and claim.subject.id in matched_ids
            and claim.object.id in matched_ids
        ]
        if direct:
            leading = direct
    statements = []
    for claim in leading[:3]:
        relation = PREDICATE_PHRASES[language].get(
            claim.predicate, claim.predicate.lower().replace("_", " ")
        )
        target = claim.object.canonical_name if claim.object else "—"
        statements.append(f"{claim.subject.canonical_name} {relation} {target}")
    text = ANSWER_TEXT[language]
    prefix = text["supported"] if explicit else text["inference"]
    answer = f"{prefix}: " + "; ".join(statements) + "."
    citations_by_id = {
        item.id: item
        for claim in [*claims, *supporting_claims]
        for item in claim.evidence
    }
    limitations = []
    status = "supported" if explicit else "partial"
    if inferred:
        limitations.append(
            text["inferred"]
        )
        if explicit:
            status = "partial"
    if any(claim.review_status == "draft" for claim in claims):
        limitations.append(text["draft"])
    return AnswerResponse(
        answer_id=_answer_id(question, language, claims),
        question=question, language=language, intent=intent, status=status, answer=answer,
        matched_entities=matched_entities, explicit_claims=explicit,
        inferred_claims=inferred, supporting_claims=supporting_claims,
        citations=list(citations_by_id.values()),
        limitations=limitations,
    )


def _unknown_answer(
    question: str, *, language: str, intent: str,
    matched_entities: list[Any] | None = None
) -> AnswerResponse:
    text = ANSWER_TEXT[language]
    return AnswerResponse(
        answer_id=_answer_id(question, language, []),
        question=question,
        language=language,
        intent=intent,
        status="unknown",
        answer=text["unknown"],
        matched_entities=matched_entities or [],
        limitations=[text["no_claim"]],
    )


def _answer_id(question: str, language: str, claims: list[ClaimDetail]) -> str:
    material = "|".join(
        [" ".join(question.lower().split()), language, *sorted(claim.id for claim in claims)]
    )
    return hashlib.sha256(material.encode()).hexdigest()[:32]


def _search_hit(record: Any) -> SearchHit:
    item = record["item"]
    is_entity = "Entity" in record["labels"]
    return SearchHit(
        id=item["id"],
        result_type="entity" if is_entity else "evidence",
        title=item["canonical_name"] if is_entity else item["locator"],
        summary=None if is_entity else item["summary_en"],
        score=record["score"],
    )
