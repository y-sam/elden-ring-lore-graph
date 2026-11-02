# Architecture

## First vertical slice

The first vertical slice covers a reviewed subset of The Shattering and proves
three connected experiences:

1. answer a question with claim-level evidence;
2. open an entity and explore its bounded neighborhood;
3. view reviewed events in a relative timeline.

## Components

```text
Curated source metadata
        |
        v
Validation/import pipeline ---> Neo4j <--- migration runner
                                  |  \
                                  |   +--> graph and timeline queries
                                  v
                       hybrid evidence retrieval
                                  |
                                  v
                        answer generation API
                                  |
                                  v
                         web user interface
```

The Python API owns database access and response policy. The future frontend
does not connect directly to Neo4j. Production uses separate read-only runtime
and write-capable ingestion credentials.

## Web archive

FastAPI serves a dependency-free progressive web interface from the application
package. It consumes only the public HTTP API and provides entity search,
evidence-aware relationship inspection, a bounded interactive subgraph, and
the relative timeline. Development on localhost may request draft records;
production rejects that flag at the API boundary.

The graph renderer uses semantic API data and generated SVG primitives for the
visualization itself. It does not bundle official artwork, logos, maps, fonts,
or other protected game assets.

## Curated import

`elden-lore-import` validates the complete JSON document before opening a write
transaction. Unknown fields, duplicate IDs, unresolved references, and unsafe
rights flags fail closed. Import uses stable IDs and `MERGE`, so rerunning the
same dataset updates owned properties and relationships without duplication.
When a dataset version removes one of its records, import removes that dataset's
ownership and deletes the record only if no other dataset owns it.

Draft claims are excluded from entity details and subgraphs by default. They
may be requested explicitly during development, but the API rejects draft
visibility in production.

Evidence summaries are canonical in English. Spanish and Brazilian Portuguese
translations are stored as `LocalizedText` nodes linked by `HAS_TEXT` and remain
draft while machine-assisted. API consumers fall back to English whenever a
requested locale is absent.

## Relative timeline

Timeline data uses ordinary audited claims:

- `event -[IN_ERA]-> era` assigns an event to an era;
- `event -[BEFORE]-> event` establishes only the precedence supported by evidence.

The API performs a deterministic topological sort and returns layers rather
than fabricated dates or sequence numbers. Multiple events in a layer remain
unordered. A cycle is surfaced as an editorial data error through
`cycle_event_ids`.

## Data boundaries

- `graph/migrations/`: legacy prototype, preserved but not loaded into v2.
- `graph/v2/migrations/`: versioned production schema.
- `data/raw/`: local-only inputs; protected raw material must not be committed.
- `data/curated/`: reviewable project-authored records suitable for import.
- `src/elden_lore_api/`: API, retrieval, and migration code.

## Query policy

Known question classes use parameterized Cypher. Future text-to-Cypher is
read-only, bounded by timeout and result size, and never receives write access.
Graph exploration always limits depth and node count. Timeline ordering is
partial and must preserve uncertainty rather than invent dates.
