from elden_lore_api.api_models import EntityDetail, SuggestedQuestion


def build_suggested_questions(
    entity: EntityDetail, *, limit: int = 6
) -> list[SuggestedQuestion]:
    """Build deterministic prompts from relationships already visible to the user."""
    suggestions: list[SuggestedQuestion] = []
    seen: set[str] = set()

    def add(question: str, category: str, related_entity_id: str | None = None) -> None:
        if question not in seen and len(suggestions) < limit:
            seen.add(question)
            suggestions.append(
                SuggestedQuestion(
                    question=question,
                    category=category,
                    related_entity_id=related_entity_id,
                )
            )

    name = entity.canonical_name
    if entity.kind in {"character", "people", "faction"}:
        add(f"Who is {name}?", "introduction")
    else:
        add(f"What is {name}?", "introduction")

    participant_event = next(
        (
            claim.subject
            for claim in entity.claims
            if claim.predicate == "PARTICIPANT" and claim.subject.kind == "event"
        ),
        None,
    )
    if participant_event:
        add(
            f"What happened during {participant_event.canonical_name}?",
            "event",
            participant_event.id,
        )

    location_claim = next(
        (
            claim
            for claim in entity.claims
            if claim.predicate in {"BASED_IN", "INHABITS", "LOCATED_IN", "OCCURRED_IN"}
        ),
        None,
    )
    if location_claim or entity.kind in {"location", "landmark"}:
        verb = "did" if entity.kind == "event" else "is"
        add(f"Where {verb} {name}{' occur' if entity.kind == 'event' else ''}?", "location")

    if any(
        claim.predicate == "SERVES" and claim.direction == "incoming"
        for claim in entity.claims
    ):
        add(f"Who serves {name}?", "affiliation")

    for claim in entity.claims:
        counterpart = claim.object if claim.direction == "outgoing" else claim.subject
        if counterpart is None or counterpart.id == entity.id:
            continue
        add(
            f"What is the relationship between {name} and {counterpart.canonical_name}?",
            "relationship",
            counterpart.id,
        )
    return suggestions
