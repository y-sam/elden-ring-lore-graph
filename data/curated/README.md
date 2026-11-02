# Curated corpus

Curated data can be stored either as one complete dataset JSON document or as a
manifest assembled from smaller thematic fragments. The single-file seed remains
supported for backwards compatibility.

Use fragments for new corpus work. A manifest contains dataset metadata and an
ordered list of fragment paths:

```json
{
  "dataset_id": "dataset.main",
  "dataset_version": 1,
  "status": "draft",
  "fragments": [
    "batches/shared-sources.json",
    "batches/base-game-characters.json",
    "batches/shadow-events.json"
  ]
}
```

Each fragment may contain any of the six collections: `entities`, `aliases`,
`sources`, `evidence`, `localized_texts`, and `claims`. Missing collections are
treated as empty. References are validated only after all fragments have been
assembled, so a claim may refer to an entity or evidence record in another
fragment.

Identifiers must remain globally unique across every fragment. Prefer one
cohesive lore area per file and keep shared sources in a dedicated fragment.
Fragment paths cannot escape the manifest directory.

English evidence summaries are required. Spanish and Brazilian Portuguese
localized texts are optional and tracked as coverage metrics; they do not block
English-first corpus expansion.

Run the quality gates before importing:

```bash
make corpus-validate
make corpus-report
make import
```

The report includes semantic duplicate candidates, disconnected entities,
review coverage, verification coverage, entity kinds, continuities, predicates,
and evidence levels. Warnings require editorial inspection but do not block an
import. Errors must be resolved first.
