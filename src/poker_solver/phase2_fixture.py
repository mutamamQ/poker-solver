"""Small deterministic Phase 2 multi-street reference fixture."""

from __future__ import annotations

from .cards import parse_cards
from .equity import WeightedCombo
from .multistreet import MultiStreetConfig, MultiStreetState, create_root


def tiny_multistreet_config() -> MultiStreetConfig:
    """Return a bounded flop-to-river game suitable for exhaustive validation."""
    return MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=parse_cards(("2c", "3d", "4h")),
        initial_dead_pot=2,
        effective_stack=1,
        player0_combos=(WeightedCombo(parse_cards(("As", "5s")), 1.0),),
        player1_combos=(WeightedCombo(parse_cards(("Kh", "Qh")), 1.0),),
        allowed_runouts=(
            parse_cards(("9s", "Kc")),
            parse_cards(("Tc", "Jd")),
        ),
        betting_mode="pot-limit",
        wager_targets=(1,),
    )


def tiny_multistreet_root() -> MultiStreetState:
    """Create the tiny fixture's root chance node."""
    return create_root(tiny_multistreet_config())
