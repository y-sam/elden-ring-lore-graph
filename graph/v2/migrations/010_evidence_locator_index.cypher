CREATE INDEX evidence_locator IF NOT EXISTS
FOR (n:Evidence) ON (n.locator)
