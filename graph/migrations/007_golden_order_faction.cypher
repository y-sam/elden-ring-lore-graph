// ============================================
// Migration: 007_golden_order_faction
// ============================================



CREATE (:Faction {
  name: "Golden Order",
  description: "The religious and political institution enforcing the Golden Order.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});
