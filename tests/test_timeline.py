from elden_lore_api.timeline import topological_layers


def test_topological_layers_preserve_partial_order() -> None:
    layers, cycle_nodes = topological_layers(
        {"shattering", "war", "aeonia", "other-battle", "stalemate"},
        [
            ("shattering", "war"),
            ("war", "aeonia"),
            ("war", "other-battle"),
            ("aeonia", "stalemate"),
            ("other-battle", "stalemate"),
        ],
    )

    assert layers == [
        ["shattering"],
        ["war"],
        ["aeonia", "other-battle"],
        ["stalemate"],
    ]
    assert cycle_nodes == []


def test_topological_layers_report_cycle() -> None:
    layers, cycle_nodes = topological_layers(
        {"one", "two", "independent"},
        [("one", "two"), ("two", "one")],
    )

    assert layers == [["independent"]]
    assert cycle_nodes == ["one", "two"]
