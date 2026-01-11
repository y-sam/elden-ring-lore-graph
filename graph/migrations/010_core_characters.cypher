
// Migration: 010_core_characters
// Canonical: true


CREATE (:Character:Demigod {
  name: "Godrick the Grafted",
  description: "A demigod obsessed with grafting, ruler of Stormveil.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});

CREATE (:Character:Demigod {
  name: "Radagon",
  description: "Second Elden Lord and other half of Queen Marika.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});

CREATE (:Character:Demigod {
  name: "Rennala",
  description: "Queen of the Full Moon and head of the Carian royal family.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});

CREATE (:Character:Demigod {
  name: "Rykard",
  description: "Lord of Blasphemy, who rejected the Golden Order.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});
