CREATE CONSTRAINT localized_text_id_unique IF NOT EXISTS
FOR (n:LocalizedText) REQUIRE n.id IS UNIQUE
