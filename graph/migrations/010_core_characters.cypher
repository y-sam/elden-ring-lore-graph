

// Migration: 010_core_characters
// Canonical: true



//  CHARACTERS

UNWIND [
  "Marika","Radagon","Godwyn","Morgott","Mohg",
  "Malenia","Miquella","Ranni","Radahn","Rykard",
  "Godrick","Rennala","Melina","Blaidd","Maliketh",
  "Gideon Ofnir","Enia","Miriel","Preceptor Seluvis"
] AS name
MERGE (c:Character {name: name})
SET c.canonical = true,
    c.confidence = 0.95,
    c.source = "item_descriptions";


// CONSORTS / UNIONS

MATCH (a:Character {name:"Marika"}), (b:Character {name:"Radagon"})
MERGE (a)-[r:CONSORT_OF]->(b)
SET r.canonical = true,
    r.confidence = 0.95;

MATCH (a:Character {name:"Radagon"}), (b:Character {name:"Rennala"})
MERGE (a)-[r:CONSORT_OF]->(b)
SET r.canonical = true,
    r.confidence = 0.95;

// PARENTAGE

UNWIND [
  ["Godwyn","Marika"],
  ["Morgott","Marika"],
  ["Mohg","Marika"],
  ["Malenia","Marika"],
  ["Miquella","Marika"]
] AS rel
MATCH (c:Character {name:rel[0]}), (p:Character {name:rel[1]})
MERGE (c)-[r:CHILD_OF]->(p)
SET r.canonical = true,
    r.confidence = 0.95;

UNWIND [
  ["Radahn","Radagon","Rennala"],
  ["Rykard","Radagon","Rennala"],
  ["Ranni","Radagon","Rennala"]
] AS rel
MATCH (c:Character {name:rel[0]}),
      (p1:Character {name:rel[1]}),
      (p2:Character {name:rel[2]})
MERGE (c)-[r1:CHILD_OF]->(p1)
MERGE (c)-[r2:CHILD_OF]->(p2)
SET r1.canonical = true, r1.confidence = 0.95,
    r2.canonical = true, r2.confidence = 0.95;


// SHADOWS / BOUND COMPANIONS

MATCH (b:Character {name:"Blaidd"}), (r:Character {name:"Ranni"})
MERGE (b)-[rel:BOUND_TO]->(r)
SET rel.type = "shadow",
    rel.canonical = true,
    rel.confidence = 0.95;

MATCH (m:Character {name:"Maliketh"}), (mk:Character {name:"Marika"})
MERGE (m)-[rel:BOUND_TO]->(mk)
SET rel.type = "shadow",
    rel.canonical = true,
    rel.confidence = 0.95;



// ASSOCIATION

MATCH (s:Character {name:"Preceptor Seluvis"}), (r:Character {name:"Ranni"})
MERGE (s)-[rel:ASSOCIATED_WITH]->(r)
SET rel.confidence = 0.9;

MATCH (g:Character {name:"Gideon Ofnir"}), (m:Character {name:"Marika"})
MERGE (g)-[rel:SERVES]->(m)
SET rel.confidence = 0.9;
