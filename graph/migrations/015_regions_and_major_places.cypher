
// Migration: 015_regions_and_major_places
// Canonical: true



//  regions

UNWIND [
  {name:"Limgrave", desc:"A war-torn region on the fringes of the Lands Between."},
  {name:"Liurnia of the Lakes", desc:"A misty land of sorcery ruled by the Carian royals."},
  {name:"Altus Plateau", desc:"The elevated lands leading to Leyndell."},
  {name:"Leyndell, Royal Capital", desc:"Capital of the Golden Order."},
  {name:"Mountaintops of the Giants", desc:"Frozen land tied to the Flame of Ruin."},
  {name:"Caelid", desc:"A scarlet-rotted wasteland."},
  {name:"Mt. Gelmir", desc:"Volcanic region dominated by blasphemy."},
  {name:"Nokron, Eternal City", desc:"An underground eternal city."},
  {name:"Nokstella, Eternal City", desc:"A hidden city of the nightfolk."}
] AS r
MERGE (reg:Region {name:r.name})
SET reg.description = r.desc,
    reg.canonical = true,
    reg.confidence = 0.95,
    reg.source = "map";



//  PLACES

UNWIND [
  {name:"Stormveil Castle", region:"Limgrave"},
  {name:"Academy of Raya Lucaria", region:"Liurnia of the Lakes"},
  {name:"Caria Manor", region:"Liurnia of the Lakes"},
  {name:"Volcano Manor", region:"Mt. Gelmir"},
  {name:"Leyndell, Royal Capital", region:"Leyndell, Royal Capital"},
  {name:"Elphael, Brace of the Haligtree", region:"Mountaintops of the Giants"},
  {name:"Mohgwyn Palace", region:"Caelid"},
  {name:"Redmane Castle", region:"Caelid"},
  {name:"Night's Sacred Ground", region:"Nokron, Eternal City"}
] AS p
MERGE (pl:Place {name:p.name})
SET pl.canonical = true,
    pl.confidence = 0.95,
    pl.source = "map"
WITH pl, p
MATCH (reg:Region {name:p.region})
MERGE (pl)-[:LOCATED_IN]->(reg);



// CHARACTER - PLACE LINKS 

// Godrick → Stormveil
MATCH (c:Character {name:"Godrick"}), (p:Place {name:"Stormveil Castle"})
MERGE (c)-[r:RELATED_TO]->(p)
SET r.kind = "rules",
    r.confidence = 0.95,
    r.canonical = true;

// Rennala → Academy
MATCH (c:Character {name:"Rennala"}), (p:Place {name:"Academy of Raya Lucaria"})
MERGE (c)-[r:RELATED_TO]->(p)
SET r.kind = "rules",
    r.confidence = 0.95,
    r.canonical = true;

// Rykard → Volcano Manor
MATCH (c:Character {name:"Rykard"}), (p:Place {name:"Volcano Manor"})
MERGE (c)-[r:RELATED_TO]->(p)
SET r.kind = "rules",
    r.confidence = 0.95,
    r.canonical = true
;