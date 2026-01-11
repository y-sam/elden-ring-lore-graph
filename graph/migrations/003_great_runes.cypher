// ============================================
// Migration: 003_great_runes
// Description: Introduces Great Runes as
//              fragments of the Elden Ring.
// Canonical: true
// Sources: opening cinematic, item descriptions
// ============================================



// --------------------------------------------
// 1. GREAT RUNES (ABSTRACT SET)
// --------------------------------------------

CREATE (:Artifact {
  name: "Great Runes",
  description: "Fragments of the Elden Ring claimed by the demigods.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});



// --------------------------------------------
// 2. GREAT RUNES ORIGIN
// --------------------------------------------

MATCH
  (er:Artifact {name: "Elden Ring"}),
  (gr:Artifact {name: "Great Runes"})
CREATE
  (gr)-[:SHATTERED_FROM {
    source: "opening_cinematic",
    confidence: 0.95,
    canonical: true
  }]->(er);
