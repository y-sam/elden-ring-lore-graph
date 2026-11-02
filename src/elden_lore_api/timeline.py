from collections import defaultdict


def topological_layers(
    event_ids: set[str], precedence: list[tuple[str, str]]
) -> tuple[list[list[str]], list[str]]:
    """Return deterministic topological layers and any nodes involved in cycles."""
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming_count = dict.fromkeys(event_ids, 0)

    for before, after in precedence:
        if before not in event_ids or after not in event_ids or before == after:
            continue
        if after not in outgoing[before]:
            outgoing[before].add(after)
            incoming_count[after] += 1

    available = sorted(node for node, count in incoming_count.items() if count == 0)
    layers: list[list[str]] = []
    processed: set[str] = set()
    while available:
        layer = available
        layers.append(layer)
        processed.update(layer)
        next_available: list[str] = []
        for node in layer:
            for successor in sorted(outgoing[node]):
                incoming_count[successor] -= 1
                if incoming_count[successor] == 0:
                    next_available.append(successor)
        available = sorted(next_available)

    cycle_nodes = sorted(event_ids - processed)
    return layers, cycle_nodes
