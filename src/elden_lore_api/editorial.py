from typing import Literal

from neo4j import Driver


def _serializable(properties: dict[str, object]) -> dict[str, object]:
    return {
        key: value.iso_format() if hasattr(value, "iso_format") else value
        for key, value in properties.items()
    }


class EditorialRepository:
    LABELS = {
        "claim": "Claim",
        "evidence": "Evidence",
        "localized_text": "LocalizedText",
        "feedback": "Feedback",
    }

    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database

    def dashboard(self) -> dict[str, int]:
        with self.driver.session(database=self.database) as session:
            record = session.run(
                """
                RETURN count { MATCH (:Claim {review_status: 'draft'}) } AS draft_claims,
                       count { MATCH (:Evidence {review_status: 'draft'}) } AS draft_evidence,
                       count {
                           MATCH (:LocalizedText {review_status: 'draft'})
                       } AS draft_localizations,
                       count {
                           MATCH (:Feedback {moderation_status: 'pending'})
                       } AS pending_feedback,
                       count { MATCH (:Evidence {verification_status: 'community_verified'}) }
                           AS community_verified_evidence,
                       count { MATCH (:Evidence {verification_status: 'official_verified'}) }
                           AS official_verified_evidence,
                       count { MATCH (:Evidence {verification_status: 'game_verified'}) }
                           AS game_verified_evidence
                """
            ).single()
        return dict(record)

    def readiness(self) -> dict[str, object]:
        with self.driver.session(database=self.database) as session:
            record = session.run(
                """
                RETURN count {
                    MATCH (evidence:Evidence {review_status: 'draft'})
                    MATCH (source:Source)-[:CONTAINS]->(evidence)
                    WHERE source.authority_tier IN ['P0_GAME', 'P1_OFFICIAL']
                      AND size(evidence.summary_en) >= 40
                      AND size(evidence.locator) >= 10
                } AS evidence_ready,
                count {
                    MATCH (claim:Claim {review_status: 'draft'})
                    WHERE EXISTS { MATCH (claim)-[:SUPPORTED_BY]->(:Evidence) }
                      AND NOT EXISTS {
                        MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
                        WHERE evidence.review_status <> 'reviewed'
                      }
                } AS claims_ready,
                count {
                    MATCH (claim:Claim {review_status: 'draft'})
                    WHERE EXISTS {
                        MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
                        WHERE evidence.review_status <> 'reviewed'
                    }
                } AS claims_blocked
                """
            ).single()
        return {
            **dict(record),
            "policy": [
                "Use community verified when a reputable fan wiki supports the record.",
                "Use official verified for first-party publications.",
                "Reserve game verified, the highest level, for direct in-game comparison.",
                "Confirm the project-authored summary does not overstate the source.",
                "Keep inference and theory below explicit evidence.",
                "Review evidence before approving dependent claims.",
            ],
        }

    def queue(self, kind: str, *, status_value: str, limit: int) -> list[dict[str, object]]:
        label = self.LABELS[kind]
        status_field = "moderation_status" if kind == "feedback" else "review_status"
        with self.driver.session(database=self.database) as session:
            records = session.run(
                f"""
                MATCH (item:{label})
                WHERE item.{status_field} = $status_value
                RETURN properties(item) AS item
                ORDER BY item.created_at, item.id
                LIMIT $limit
                """,
                status_value=status_value,
                limit=limit,
            )
            return [_serializable(dict(record["item"])) for record in records]

    def priority_evidence_queue(self, *, limit: int) -> list[dict[str, object]]:
        """Rank draft evidence by dependent claims and immediate unlocks."""
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (source:Source)-[:CONTAINS]->(evidence:Evidence {review_status: 'draft'})
                OPTIONAL MATCH (claim:Claim {review_status: 'draft'})-[:SUPPORTED_BY]->(evidence)
                OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(dependency:Evidence)
                WITH source, evidence, claim,
                     count(CASE WHEN dependency.review_status <> 'reviewed' THEN 1 END)
                         AS unreviewed_dependencies
                OPTIONAL MATCH (claim)-[:SUBJECT]->(subject:Entity)
                OPTIONAL MATCH (claim)-[:OBJECT]->(object:Entity)
                WITH source, evidence,
                     collect(DISTINCT claim.id) AS claim_ids,
                     collect(DISTINCT subject.canonical_name) +
                         collect(DISTINCT object.canonical_name) AS names,
                     sum(CASE WHEN unreviewed_dependencies = 1 THEN 1 ELSE 0 END)
                         AS unlock_count
                WITH source, evidence, claim_ids, unlock_count,
                     reduce(unique_names = [], name IN names |
                         CASE WHEN name IS NULL OR name IN unique_names
                              THEN unique_names ELSE unique_names + name END
                     ) AS entity_names
                RETURN evidence {
                    .*,
                    source_id: source.id,
                    source_title: source.title,
                    authority_tier: source.authority_tier,
                    affected_claim_ids: claim_ids,
                    impact_count: size(claim_ids),
                    unlock_count: unlock_count,
                    entity_names: entity_names
                } AS item
                ORDER BY unlock_count DESC, size(claim_ids) DESC, evidence.id
                LIMIT $limit
                """,
                limit=limit,
            )
            return [_serializable(dict(record["item"])) for record in records]

    def review(
        self,
        kind: str,
        item_id: str,
        *,
        decision: Literal["reviewed", "disputed", "rejected", "approved"],
        notes: str | None,
        verification_status: str | None = None,
        verification_url: str | None = None,
    ) -> dict[str, object] | None:
        label = self.LABELS[kind]
        allowed_decisions = (
            {"approved", "rejected"}
            if kind == "feedback"
            else {"reviewed", "disputed", "rejected"}
        )
        if decision not in allowed_decisions:
            raise ValueError(f"{decision} is not valid for {kind}")
        if kind == "claim" and decision == "reviewed":
            with self.driver.session(database=self.database) as session:
                blocked = session.run(
                    """
                    MATCH (claim:Claim {id: $item_id})-[:SUPPORTED_BY]->(evidence:Evidence)
                    RETURN count(
                        CASE WHEN evidence.review_status <> 'reviewed' THEN 1 END
                    ) AS blocked
                    """,
                    item_id=item_id,
                ).single()["blocked"]
            if blocked:
                raise ValueError("claim evidence must be reviewed first")
            if verification_status and verification_status != "unverified":
                ranks = {
                    "community_verified": 1,
                    "official_verified": 2,
                    "game_verified": 3,
                }
                allowed = [
                    status for status, rank in ranks.items()
                    if rank >= ranks[verification_status]
                ]
                with self.driver.session(database=self.database) as session:
                    blocked_verification = session.run(
                        """
                        MATCH (claim:Claim {id: $item_id})-[:SUPPORTED_BY]->(evidence:Evidence)
                        RETURN count(CASE WHEN NOT coalesce(evidence.verification_status,
                            'unverified') IN $allowed THEN 1 END) AS blocked
                        """,
                        item_id=item_id,
                        allowed=allowed,
                    ).single()["blocked"]
                if blocked_verification:
                    raise ValueError("claim cannot exceed its supporting evidence verification")
        if verification_status == "community_verified" and not verification_url:
            raise ValueError("community verification requires a source URL")
        if kind not in {"claim", "evidence"} and verification_status is not None:
            raise ValueError(f"verification is not applicable to {kind}")
        field = "moderation_status" if kind == "feedback" else "review_status"
        with self.driver.session(database=self.database) as session:
            record = session.run(
                f"""
                MATCH (item:{label} {{id: $item_id}})
                SET item.{field} = $decision,
                    item.editorial_notes = $notes,
                    item.reviewed_at = datetime(),
                    item.verification_status = CASE WHEN $verification_status IS NULL
                        THEN coalesce(item.verification_status, 'unverified')
                        ELSE $verification_status END,
                    item.verification_url = CASE WHEN $verification_url IS NULL
                        THEN item.verification_url ELSE $verification_url END
                FOREACH (_ IN CASE WHEN 'LocalizedText' IN labels(item)
                                        AND $decision = 'reviewed'
                                   THEN [1] ELSE [] END | SET item.origin = 'human')
                RETURN properties(item) AS item
                """,
                item_id=item_id,
                decision=decision,
                notes=notes,
                verification_status=verification_status,
                verification_url=verification_url,
            ).single()
        return _serializable(dict(record["item"])) if record else None
