

// Migration: 016_individual_great_runes
// Canonical: true

// GREAT RUNES

UNWIND [
  {name:"Great Rune of Godrick", owner:"Godrick"},
  {name:"Great Rune of Radahn", owner:"Radahn"},
  {name:"Great Rune of Morgott", owner:"Morgott"},
  {name:"Great Rune of Mohg", owner:"Mohg"},
  {name:"Great Rune of Rykard", owner:"Rykard"},
  {name:"Great Rune of Malenia", owner:"Malenia"},
  {name:"Great Rune of Rennala", owner:"Rennala"}
] AS gr
MERGE (a:Artifact {name:gr.name})
SET a.canonical = true,
    a.confidence = 0.95,
    a.source = "item_descriptions"
WITH a, gr
MATCH (owner:Character {name:gr.owner})
MERGE (owner)-[r:CLAIMED]->(a)
SET r.canonical = true,
    r.confidence = 0.95;


// LINK TO GREAT RUNES

MATCH (ind:Artifact), (col:Artifact {name:"Great Runes"})
WHERE ind.name STARTS WITH "Great Rune of"
MERGE (ind)-[:PART_OF]->(col);
