# Modeling Principles

1. The graph reflects lore statements, not gameplay mechanics
2. Relationships are first-class lore claims
3. Canon and speculation are explicitly labeled
4. No node or relationship exists without a source
5. Contradictions are modeled, not resolved

## Relationship Ontology

- Predicates express reusable graph semantics, not one-off prose.
- Narrative nuance belongs in `role`, `qualifier`, and `temporal_scope`.
- A multi-step action with its own participants, place, or chronology is an
  `Event`, connected through predicates such as `PARTICIPANT`, `TARGETED`, and
  `OCCURRED_IN`.
- Rare predicates are allowed when they express stable semantics such as
  identity, origin, embodiment, or route. The audit reports every predicate
  used once so that rarity is an explicit editorial choice.
- Replaced predicates remain traceable through `legacy_predicate`. The active
  predicate must always belong to the controlled vocabulary in
  `src/elden_lore_api/ontology.py`.

For example, Malenia's title is modeled as `SERVES` with `role: "blade"`, not
as the one-off predicate `BLADE_OF`. Ranni's theft of a fragment of the Rune of
Death is an Event because it connects an instigator, a target, and chronology.

## Chronology Rules

- Era order is relative and sparse
- Lower values indicate older eras
- Gaps are intentional
- Event ordering is local to an era


