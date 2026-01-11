// ============================================
// Migration: 002_marika_and_elden_ring
// Description: Adds the Elden Ring artifact and
//              models Marika's role in the
//              Shattering.
// Canonical: true (with explicit confidence)
// Sources: opening cinematic, item descriptions
// ============================================



// --------------------------------------------
// 1. ARTIFACT: ELDEN RING
// --------------------------------------------

CREATE (:Artifact {
  name: "Elden Ring",
  description: "The metaphysical object embodying the Golden Order.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});



// --------------------------------------------
// 2. MARIKA AS VESSEL
// --------------------------------------------

MATCH
  (m:Character {name: "Marika"}),
  (er:Artifact {name: "Elden Ring"})
CREATE
  (m)-[:VESSEL_OF {
    source: "opening_cinematic",
    confidence: 0.95,
    canonical: true
  }]->(er);



// --------------------------------------------
// 3. SHATTERING RELATIONSHIPS
// --------------------------------------------

MATCH
  (m:Character {name: "Marika"}),
  (e:Event {name: "Shattering of the Elden Ring"}),
  (er:Artifact {name: "Elden Ring"})
CREATE
  (m)-[:RESPONSIBLE_FOR {
    source: "opening_cinematic",
    confidence: 0.85,
    canonical: true
  }]->(e),
  (er)-[:SHATTERED_IN {
    source: "opening_cinematic",
    confidence: 0.95,
    canonical: true
  }]->(e);
