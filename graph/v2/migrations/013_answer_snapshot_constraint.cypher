CREATE CONSTRAINT answer_snapshot_id_unique IF NOT EXISTS
FOR (n:AnswerSnapshot) REQUIRE n.id IS UNIQUE
