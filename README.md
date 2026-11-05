# Elden Ring Lore Graph

An evidence-first Neo4j knowledge graph and API for answering questions about
the lore of *Elden Ring* and exploring entities, relationships, and relative
chronology.

## Current milestone

The repository is transitioning from its original graph-modeling prototype to a
reviewable v2 schema. Legacy Cypher is preserved in `graph/migrations`; new work
uses `graph/v2/migrations` and does not promote legacy claims without evidence.

## Core Principles
- Lore is represented as a graph, not tables
- Relationships carry meaning
- Ambiguity is explicit and preserved
- Every assertion has a source
- Copyrighted source material is referenced, not redistributed
- Answers distinguish explicit evidence, inference, and theory

## Local development

Requirements: Python 3.11+, `uv`, and Docker or another local Neo4j 5.26+
installation.

```bash
cp .env.example .env
make sync
docker compose up -d neo4j
make migrate
make audit
make import
make run
```

For larger corpus contributions, use thematic fragment manifests documented in
[`data/curated/README.md`](data/curated/README.md). `make corpus-validate` checks
referential and editorial invariants, while `make corpus-report` also exposes
coverage, duplicate candidates, and disconnected entities.

The API is available at `http://127.0.0.1:8000`; interactive documentation is
at `/docs`. The web archive is served at the root URL. Run checks with:

```bash
make check
make evaluate
```

The Make targets keep the virtual environment in `/tmp` because macOS
AppleDouble files created on some external volumes can invalidate installed
Python wheels. Override `UV_ENVIRONMENT` and `UV_CACHE` if this is unnecessary.

See [the editorial policy](docs/editorial-policy.md), [architecture](docs/architecture.md),
and [v2 graph model](graph/v2/README.md).

## Entity API

The curated seed is imported idempotently with `make import`. Its claims remain
`draft`, so public responses omit unreviewed records by default. Version 8 connects 95
entities through 128 evidence-backed claims across the base game and
*Shadow of the Erdtree*, including family lines, major powers, places, artifacts,
the Shattering and the Realm of Shadow crusade. All 40 project-authored evidence
summaries also have machine-assisted Spanish and Brazilian Portuguese drafts;
English remains the canonical fallback.

Five evidence records and 17 dependent claims have completed primary-source
review against official Bandai Namco pages. The remaining 35 evidence records
and 111 claims stay in `draft` until their in-game dialogue, description,
remembrance, monument, or scene locators can be checked directly.

Editorial approval is independent from verification strength. Fan-maintained
references may produce `community_verified` records when their URL is retained;
first-party publications produce `official_verified`, and only direct in-game
comparison produces the highest level, `game_verified`. Claims cannot outrank
their supporting evidence.

```text
GET /api/v1/entities?q=ring&kind=artifact&limit=25&offset=0
GET /api/v1/entities/artifact.elden-ring
GET /api/v1/entities/artifact.elden-ring?include_drafts=true
GET /api/v1/entities/artifact.elden-ring/subgraph?depth=1&limit=100
GET /api/v1/claims/claim.elden-ring.shattered-in-event?include_drafts=true
GET /api/v1/answers?q=What+is+the+relationship+between+Marika+and+Radagon
GET /api/v1/answers?q=Quem+é+Miquella&lang=pt-BR
GET /api/v1/search?q=elden+ring
GET /api/v1/timeline
GET /api/v1/timeline?era_id=era.the-shattering
GET /api/v1/discovery?spoiler_level=minimal
GET /api/v1/discovery/start.main-characters?spoiler_level=minimal
```

The public web archive includes a spoiler-aware **New to Elden Ring? Start here**
mode. Curated journeys open an exact five-node graph, preselect an introductory
entity, provide a short supported orientation, and recommend the next entities
to explore. Journey URLs retain both the collection and spoiler preference, for
example `/?journey=start.main-characters&spoilers=minimal`. The available
spoiler levels are `minimal`, `base_game`, and `full`; expanding beyond the
curated starting graph is explicitly identified as potentially revealing wider
relationships.

Subgraphs contain entity nodes and claim edges. `depth` is limited to 3 and
`limit` to 200. `include_drafts=true` is rejected when `APP_ENV=production`.

The timeline returns explicit membership and precedence claims plus deterministic
topological layers. Events in the same layer are not asserted to have a known
order. Cycles are reported in `cycle_event_ids` instead of being silently
resolved.

Search uses a Neo4j full-text index over entity names and project-authored
evidence summaries. Protected source text is not indexed. Draft evidence is
hidden by default.

Answers are assembled deterministically from matched entities, claims and
evidence. Explicit claims and synthesis are separated from inference, evidence
records are returned as citations, and unsupported questions return `unknown`.
Question intent narrows claims for who, where, when, why, event and relationship
questions. Response language is detected or selected with `lang=en|es|pt-BR`.
Canonical entity names and evidence summaries remain English until reviewed
localizations are added. No language model is required for this evidence-first
answer path.

Entity inspectors link to permanent, shareable profiles at
`/entity.html?id=<entity-id>`. Profiles provide an English factual summary,
relationship cards, evidence, confidence, continuity, related-entity links,
graph navigation, and moderated reader feedback.

Search and question answering include a conservative typo fallback when exact
full-text and alias matching fail. `make evaluate` runs 100 deterministic
English reference questions against Neo4j and checks their expected entities
and claims.

Each answer has a deterministic `answer_id`. Readers can rate it as helpful,
mixed, or not helpful and optionally explain why with `POST /api/v1/feedback`.
Feedback starts as `pending`; only moderated feedback contributes to the public
community signal, and it never changes canonical confidence automatically. The
local editorial console is available at `/editorial.html` and its API requires
the `X-Editorial-Token` configured by `EDITORIAL_TOKEN`.

The optional generative mode supports `ANSWER_GENERATOR=gemini` with
`GEMINI_API_KEY` (free-tier friendly), or `ANSWER_GENERATOR=openai` with
`OPENAI_API_KEY`. Deterministic generation remains the safe default. Generative
answers use bounded graph context, structured output,
verified claim/evidence identifiers, an in-memory TTL cache, output limits, and
automatic deterministic fallback. Unsupported questions never call the model;
enabling the setting does not bypass evidence or review policy.
See [production operations](docs/production.md) before deployment.

Run `make audit` before every import. The audit rejects invalid temporal types,
self-relations, reviewed claims backed by draft evidence, and precedence cycles.
