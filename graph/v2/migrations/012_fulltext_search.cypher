CREATE FULLTEXT INDEX lore_fulltext IF NOT EXISTS
FOR (n:Entity|Evidence) ON EACH [n.canonical_name, n.locator, n.summary_en]
