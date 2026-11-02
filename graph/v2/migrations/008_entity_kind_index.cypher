CREATE INDEX entity_kind IF NOT EXISTS
FOR (n:Entity) ON (n.kind)
