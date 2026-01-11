
// Migration: 008_golden_order_elden_ring

MATCH
  (er:Artifact {name: "Elden Ring"}),
  (go:Concept {name: "Golden Order"})
CREATE
  (er)-[:EMBODIES {
    source: "item_descriptions",
    confidence: 0.95,
    canonical: true
  }]->(go);
