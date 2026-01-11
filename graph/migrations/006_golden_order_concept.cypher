// ============================================
// Migration: 006_golden_order_concept
// ============================================


CREATE (:Concept {
  name: "Golden Order",
  description: "The metaphysical laws governing the Lands Between, embodied by the Elden Ring.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});
