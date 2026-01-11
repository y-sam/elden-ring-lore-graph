// ============================================
// Migration: 014_relationship_normalization_related_to
// Description: Normalizes SERVES, ASSOCIATED_WITH,
//              BOUND_TO (and optionally LEADS) into
//              RELATED_TO with properties.
// Canonical: true
// ============================================



// --- SERVES -> RELATED_TO(kind="service")
MATCH (a)-[r:SERVES]->(b)
MERGE (a)-[nr:RELATED_TO]->(b)
SET nr.kind = "service",
    nr.source = coalesce(r.source, "migration_normalization"),
    nr.confidence = coalesce(r.confidence, 0.9),
    nr.canonical = coalesce(r.canonical, true)
DELETE r;


// --- ASSOCIATED_WITH -> RELATED_TO(kind="association")
MATCH (a)-[r:ASSOCIATED_WITH]->(b)
MERGE (a)-[nr:RELATED_TO]->(b)
SET nr.kind = "association",
    nr.source = coalesce(r.source, "migration_normalization"),
    nr.confidence = coalesce(r.confidence, 0.9),
    nr.canonical = coalesce(r.canonical, true)
DELETE r;


// --- BOUND_TO -> RELATED_TO(kind="bond", role=r.type if exists)
MATCH (a)-[r:BOUND_TO]->(b)
MERGE (a)-[nr:RELATED_TO]->(b)
SET nr.kind = "bond",
    nr.role = coalesce(r.type, "bound"),
    nr.source = coalesce(r.source, "migration_normalization"),
    nr.confidence = coalesce(r.confidence, 0.95),
    nr.canonical = coalesce(r.canonical, true)
DELETE r;


// --- OPTIONAL: LEADS -> RELATED_TO(kind="authority", role="leader")
MATCH (a)-[r:LEADS]->(b)
MERGE (a)-[nr:RELATED_TO]->(b)
SET nr.kind = "authority",
    nr.role = "leader",
    nr.source = coalesce(r.source, "migration_normalization"),
    nr.confidence = coalesce(r.confidence, 0.95),
    nr.canonical = coalesce(r.canonical, true)
DELETE r;
