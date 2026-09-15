"""Small deterministic Phase-3 example preset catalog."""

from copy import deepcopy
from types import MappingProxyType


_PRESETS = MappingProxyType({
    "btn-vs-bb-25bb": {
        "kind": "heads-up-preflop-template",
        "starting_stacks": [2500, 2500],
        "forced_posts": [50, 100],
        "sizing_expressions": [
            {"unit": "big-blinds", "value": 2.5},
            {"unit": "all-in"},
        ],
        "continuation": "caller-supplied-terminal-table-required",
        "provenance": "poker-solver bundled example; not presolved",
    },
    "threeway-flop-demo": {
        "kind": "three-player-postflop-template",
        "button": 0,
        "starting_stacks": [1000, 1000, 1000],
        "contributions": [100, 100, 100],
        "board": [0, 1, 2],
        "wager_targets": [200, 500],
        "showdown": "caller-supplied-ranks-required",
        "provenance": "poker-solver bundled example; not presolved",
    },
})


def list_presets() -> tuple[str, ...]:
    return tuple(_PRESETS)


def get_preset(name: str) -> dict[str, object]:
    if not isinstance(name, str) or name not in _PRESETS:
        raise ValueError("unknown preset")
    return deepcopy(_PRESETS[name])
