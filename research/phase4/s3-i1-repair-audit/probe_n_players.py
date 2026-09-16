#!/usr/bin/env python3
"""Independent N=3..9 root creation probes for R3A3 audit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    create_nplayer_preflop_root,
)
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import CHANCE
from fractions import Fraction


def _combo(cards, weight=1):
    return WeightedCombo(cards, Fraction(weight))


def _continuation():
    return NPlayerPreflopContinuation(
        kind="terminal-table",
        provenance="R3A3-probe",
        source="supplied",
        payoff_table={},
        showdown_ranks={},
        odd_chip_order=(),
    )


def probe_n(n):
    button = 0 if n == 2 else n - 1
    cfg = NPlayerPreflopConfig(
        version="nplayer-preflop-v1",
        num_players=n,
        button=button,
        starting_stacks=(100,) * n,
        forced_posts=(
            ForcedPost(seat=0, kind="small-blind", amount=1),
            ForcedPost(seat=1, kind="big-blind", amount=2),
        ),
        straddle_variant="none",
        ranges=tuple((_combo((2 * seat, 2 * seat + 1)),) for seat in range(n)),
        sizing_rules=(),
        max_raises=3,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=_continuation(),
    )
    root = create_nplayer_preflop_root(cfg)
    assert root.current_player() == CHANCE
    return {
        "n": n,
        "pot": root.pot,
        "street_committed": root.street_committed,
        "current_player": str(root.current_player()),
    }


if __name__ == "__main__":
    import json

    results = {}
    for n in range(3, 10):
        try:
            results[f"N={n}"] = probe_n(n)
        except Exception as e:
            results[f"N={n}"] = {"error": str(e)}

    print(json.dumps(results, indent=2))
