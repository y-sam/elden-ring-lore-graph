
// Migration: 017_greater_will
// Canonical: true
// Sources: item descriptions, dialogue


// -OUTER GOD: GREATER WILL

MERGE (gw:OuterGod {name:"Greater Will"})
SET gw.description = "An Outer God that imposed order upon the Lands Between.",
    gw.source = "item_descriptions",
    gw.confidence = 0.95,
    gw.canonical = true;



// GREATER WILL - GOLDEN ORDER

MATCH (gw:OuterGod {name:"Greater Will"}),
      (go:Concept {name:"Golden Order"})
MERGE (gw)-[r:IMPOSES]->(go)
SET r.source = "item_descriptions",
    r.confidence = 0.95,
    r.canonical = true;



// GREATER WILL - ELDEN RING

MATCH (gw:OuterGod {name:"Greater Will"}),
      (er:Artifact {name:"Elden Ring"})
MERGE (gw)-[r:EMPOWERS]->(er)
SET r.source = "item_descriptions",
    r.confidence = 0.95,
    r.canonical = true;



// GREATER WILL - MARIKA 

MATCH (gw:OuterGod {name:"Greater Will"}),
      (m:Character {name:"Marika"})
MERGE (gw)-[r:INFLUENCES]->(m)
SET r.source = "item_descriptions",
    r.confidence = 0.9,
    r.canonical = true;


// SHADOW SYSTEM 

// Greater Will establishes the system of Shadows
MATCH (gw:OuterGod {name:"Greater Will"})
MERGE (gw)-[r:ESTABLISHES]->(:Concept {name:"Shadowbound Servants"})
SET r.source = "item_descriptions",
    r.confidence = 0.9,
    r.canonical = true;
