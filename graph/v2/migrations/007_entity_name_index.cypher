CREATE INDEX entity_name IF NOT EXISTS
FOR (n:Entity) ON (n.canonical_name)
