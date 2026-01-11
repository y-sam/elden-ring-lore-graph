// ============================================
// Migration: 004_demigods_claim_great_runes
// Description: Models demigods claiming Great
//              Runes after the Shattering.
// Canonical: true
// Source: opening cinematic
// ============================================



MATCH
  (gr:Artifact {name: "Great Runes"}),
  (m:Character {name: "Malenia"}),
  (r:Character {name: "Radahn"})
CREATE
  (m)-[:CLAIMED {
    source: "opening_cinematic",
    confidence: 0.9,
    canonical: true
  }]->(gr),
  (r)-[:CLAIMED {
    source: "opening_cinematic",
    confidence: 0.9,
    canonical: true
  }]->(gr);
