import uuid

from neo4j import Driver

from elden_lore_api.api_models import (
    FeedbackCreate,
    FeedbackReceipt,
    FeedbackSummary,
)


class FeedbackRepository:
    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database

    def create(self, payload: FeedbackCreate) -> FeedbackReceipt:
        feedback_id = f"feedback.{uuid.uuid4().hex}"
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MERGE (answer:AnswerSnapshot {id: $answer_id})
                ON CREATE SET answer.question = $question,
                              answer.language = $language,
                              answer.created_at = datetime()
                CREATE (feedback:Feedback {
                  id: $feedback_id,
                  rating: $rating,
                  reason: $reason,
                  comment: $comment,
                  moderation_status: 'pending',
                  created_at: datetime()
                })
                MERGE (feedback)-[:ABOUT]->(answer)
                WITH feedback
                UNWIND $claim_ids AS claim_id
                MATCH (claim:Claim {id: claim_id})
                MERGE (feedback)-[:REFERENCES]->(claim)
                """,
                answer_id=payload.answer_id,
                question=payload.question,
                language=payload.language,
                feedback_id=feedback_id,
                rating=payload.rating,
                reason=payload.reason,
                comment=payload.comment.strip() if payload.comment else None,
                claim_ids=payload.claim_ids,
            ).consume()
        return FeedbackReceipt(id=feedback_id)

    def summary(self, answer_id: str) -> FeedbackSummary:
        with self.driver.session(database=self.database) as session:
            record = session.run(
                """
                OPTIONAL MATCH (feedback:Feedback)-[:ABOUT]->(
                    :AnswerSnapshot {id: $answer_id}
                )
                RETURN count(
                    CASE WHEN feedback.moderation_status = 'approved' THEN 1 END
                ) AS total,
                count(CASE WHEN feedback.moderation_status = 'pending' THEN 1 END) AS pending,
                count(CASE WHEN feedback.moderation_status = 'approved'
                      AND feedback.rating = 'helpful' THEN 1 END) AS helpful,
                count(CASE WHEN feedback.moderation_status = 'approved'
                      AND feedback.rating = 'mixed' THEN 1 END) AS mixed,
                count(CASE WHEN feedback.moderation_status = 'approved'
                      AND feedback.rating = 'not_helpful' THEN 1 END) AS not_helpful
                """,
                answer_id=answer_id,
            ).single()
        values = dict(record)
        total = values["total"]
        if total < 3:
            signal = "insufficient"
        elif values["helpful"] / total >= 0.7:
            signal = "positive"
        elif values["not_helpful"] / total >= 0.5:
            signal = "negative"
        else:
            signal = "mixed"
        return FeedbackSummary(answer_id=answer_id, community_signal=signal, **values)
