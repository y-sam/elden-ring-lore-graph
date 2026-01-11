
// Migration: 009_marika_and_golden_order

// Canonical: true

MATCH
  (m:Character {name: "Marika"}),
  (goConcept:Concept {name: "Golden Order"}),
  (goFaction:Faction {name: "Golden Order"})
CREATE
  (m)-[:VESSEL_OF {
    source: "item_descriptions",
    confidence: 0.9,
    canonical: true
  }]->(goConcept),
  (m)-[:LEADS {
    source: "opening_cinematic",
    confidence: 0.95,
    canonical: true
  }]->(goFaction);
