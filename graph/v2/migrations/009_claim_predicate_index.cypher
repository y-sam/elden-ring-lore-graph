CREATE INDEX claim_predicate IF NOT EXISTS
FOR (n:Claim) ON (n.predicate)
