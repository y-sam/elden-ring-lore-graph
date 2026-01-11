// Lineage
// (:Character)-[:CHILD_OF]->(:Character)
// (:Character)-[:SIBLING_OF]->(:Character)

// Power & Influence
// (:OuterGod)-[:INFLUENCES]->(:Character)
// (:Concept)-[:CORRUPTS]->(:Character)
// (:Character)-[:AFFILIATED_WITH]->(:Faction)

// Events
// (:Event)-[:OCCURRED_AT]->(:Place)
// (:Event)-[:PARTICIPANT]->(:Character)
// (:Event)-[:CAUSED_BY]->(:Event)
// (:Event)-[:RESULTED_IN]->(:Event)
// (:Event)-[:IN_ERA]->(:Era)

// Geography
// (:Place)-[:LOCATED_IN]->(:Region)
// (:Region)-[:PART_OF]->(:Region)

// Items
// (:Weapon)-[:WIELDED_BY]->(:Character)
// (:Artifact)-[:OWNED_BY]->(:Character)
