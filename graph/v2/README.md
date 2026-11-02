# Graph schema v2

The v2 graph is evidence-first. It intentionally does not import the legacy
migrations automatically: legacy facts must be reviewed and attached to precise
evidence before promotion.

## Core nodes

- `Entity`: a language-neutral lore entity with a stable `id` and `kind`.
- `Source`: the work or official material in which evidence appears.
- `Evidence`: a locator plus an original editorial summary; not a copied passage.
- `Claim`: a reviewable assertion connecting a subject and, optionally, an object.
- `LocalizedText`: project-authored display text in `en`, `es`, or `pt-BR`.

## Core relationships

```text
(Source)-[:CONTAINS]->(Evidence)
(Claim)-[:SUBJECT]->(Entity)
(Claim)-[:OBJECT]->(Entity)
(Claim)-[:SUPPORTED_BY]->(Evidence)
(Claim)-[:CONTRADICTS]->(Claim)
(Entity|Claim|Evidence)-[:HAS_TEXT]->(LocalizedText)
```

Direct domain relationships such as `CHILD_OF` may later be materialized for
fast graph exploration. `Claim` remains the auditable source of truth.

## Migration rules

- Never edit an applied migration; add a new numbered migration.
- Keep exactly one Cypher statement in each migration file.
- Each migration must be idempotent because schema changes are recorded only
  after Neo4j accepts the complete file.
- Do not place copyrighted game text in a migration.
