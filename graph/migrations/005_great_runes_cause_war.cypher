// ============================================
// Migration: 005_great_runes_cause_war
// Description: Models the Great Runes as the
//              cause of the War of the Shattering.
// Canonical: true
// Source: opening cinematic
// ============================================



MATCH
  (war:Event {name: "War of the Shattering"}),
  (gr:Artifact {name: "Great Runes"})
CREATE
  (war)-[:CAUSED_BY {
    source: "opening_cinematic",
    confidence: 0.9,
    canonical: true
  }]->(gr);
