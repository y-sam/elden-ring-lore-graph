"""Controlled vocabulary for relationships in the curated lore graph.

Predicates describe reusable graph semantics. Narrative nuance belongs in claim
qualifiers, roles, temporal scopes, or dedicated Event entities.
"""

CORE_PREDICATES = frozenset(
    {
        "ABANDONED", "AFFLICTED_BY", "BASED_IN", "BEFORE", "CATALYST_FOR",
        "CAUSED", "CHILD_OF", "CONSORT_OF", "CONTAINS", "CREATED",
        "DEFEATED", "DEFENDS", "FOLLOWED", "FOLLOWS", "GUARDED", "GUIDED",
        "HELD_TITLE", "INHABITS", "IN_ERA", "LEADS", "LOCATED_IN",
        "MEMBER_OF", "OCCURRED_IN", "OPPOSED", "PARTICIPANT", "RULED",
        "SEEKS", "SERVES", "SIBLING_OF", "SOURCE_OF", "TARGETED", "TWIN_OF",
        "VESSEL_OF", "WIELDS",
    }
)

# Less frequent, but still stable and reusable semantics.
EXTENSION_PREDICATES = frozenset(
    {
        "ASPECT_OF", "ATTACKED", "CLAIMED_BY", "DRAWS_POWER_FROM", "EMBODIES",
        "ENTERED_VIA", "FOUGHT", "FRAGMENTS_OF", "GRANTS_POWER_TO",
        "IDENTITY_OF", "INTERPRETS", "OBSCURED_BY", "PROGENITOR_OF", "ROUTE_TO",
        "SPREAD_AFTER",
    }
)

CANONICAL_PREDICATES = CORE_PREDICATES | EXTENSION_PREDICATES

# Explicit migration knowledge lets tooling explain old data instead of silently
# changing its meaning.
DEPRECATED_PREDICATES = {
    "ABANDONED_ASPECT": "ABANDONED",
    "BECAME_LORD_OF": "VESSEL_OF",
    "BLADE_OF": "SERVES",
    "DEVASTATED": "AFFLICTED_BY",
    "FIRST_ARRIVED_IN": "PARTICIPANT + OCCURRED_IN",
    "FOUNDER_OF": "CREATED",
    "GUARDED_BY": "GUARDED (inverse direction)",
    "HARMS_VASSALS_OF": "OPPOSED",
    "ORDER_OF": "SOURCE_OF (inverse direction)",
    "RESTS_IN": "LOCATED_IN",
    "SAME_BEING_AS": "IDENTITY_OF",
    "SEEKS_TO_END": "OPPOSED",
    "SERVED": "SERVES",
    "SHATTERED_IN": "TARGETED (through an Event)",
    "STOLE_FRAGMENT_OF": "PARTICIPANT + TARGETED (through an Event)",
}
