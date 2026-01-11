// ============================================
// Migration: 001_shattering_era
// Description: Introduces The Shattering era,
//              its core events, participants,
//              and causal relationships.
// Canonical: true
// Sources: opening cinematic, item descriptions
// ============================================



// --------------------------------------------
// 1. ERAS
// --------------------------------------------

CREATE (:Era {
  name: "Age of the Erdtree",
  order: 0,
  description: "The age in which the Golden Order and the Erdtree ruled the Lands Between.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});

CREATE (:Era {
  name: "The Shattering",
  order: 10,
  description: "The era of war following the destruction of the Elden Ring.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});



// --------------------------------------------
// 2. EVENTS (The Shattering)
// --------------------------------------------

CREATE (:Event {
  name: "Shattering of the Elden Ring",
  era_order: 0,
  description: "The Elden Ring was shattered, destabilizing the Golden Order.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});

CREATE (:Event {
  name: "War of the Shattering",
  era_order: 1,
  description: "A war between the demigods over the Great Runes.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});

CREATE (:Event {
  name: "Battle of Aeonia",
  era_order: 2,
  description: "Malenia and Radahn clashed, unleashing the Scarlet Rot.",
  source: "npc_dialogue",
  confidence: 0.9,
  canonical: true
});

CREATE (:Event {
  name: "Stalemate of the Demigods",
  era_order: 3,
  description: "No demigod achieved decisive victory; the war stagnated.",
  source: "opening_cinematic",
  confidence: 0.9,
  canonical: true
});



// --------------------------------------------
// 3. LINK EVENTS TO ERA
// --------------------------------------------

MATCH (e:Event), (era:Era {name: "The Shattering"})
WHERE e.name IN [
  "Shattering of the Elden Ring",
  "War of the Shattering",
  "Battle of Aeonia",
  "Stalemate of the Demigods"
]
CREATE (e)-[:IN_ERA {
  source: "inference",
  confidence: 0.9,
  canonical: true
}]->(era);



// --------------------------------------------
// 4. CHARACTERS
// --------------------------------------------

CREATE (:Character:Demigod {
  name: "Marika",
  description: "Queen Marika the Eternal, vessel of the Elden Ring.",
  source: "opening_cinematic",
  confidence: 0.95,
  canonical: true
});

CREATE (:Character:Demigod {
  name: "Malenia",
  description: "Blade of Miquella, afflicted by the Scarlet Rot.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});

CREATE (:Character:Demigod {
  name: "Radahn",
  description: "General Radahn, conqueror of the stars.",
  source: "item_descriptions",
  confidence: 0.95,
  canonical: true
});



// --------------------------------------------
// 5. EVENT PARTICIPATION
// --------------------------------------------

MATCH
  (ae:Event {name: "Battle of Aeonia"}),
  (m:Character {name: "Malenia"}),
  (r:Character {name: "Radahn"})
CREATE
  (ae)-[:PARTICIPANT {
    source: "npc_dialogue",
    confidence: 0.9,
    canonical: true
  }]->(m),
  (ae)-[:PARTICIPANT {
    source: "npc_dialogue",
    confidence: 0.9,
    canonical: true
  }]->(r);



// --------------------------------------------
// 6. CAUSALITY
// --------------------------------------------

MATCH
  (shatter:Event {name: "Shattering of the Elden Ring"}),
  (war:Event {name: "War of the Shattering"}),
  (stalemate:Event {name: "Stalemate of the Demigods"})
CREATE
  (war)-[:CAUSED_BY {
    source: "inference",
    confidence: 0.9,
    canonical: true
  }]->(shatter),
  (stalemate)-[:RESULTED_IN {
    source: "inference",
    confidence: 0.9,
    canonical: true
  }]->(war);
