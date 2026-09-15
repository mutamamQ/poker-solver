"""Exact independent settlement oracles for the typed N-player postflop state."""

from __future__ import annotations

from fractions import Fraction

from poker_solver.game_structure import RakePolicy
from poker_solver.model import Action, TERMINAL
from poker_solver.nplayer_postflop import (
    NPlayerPostflopConfig,
    create_nplayer_postflop_root,
)
from poker_solver.preflop import WeightedCombo


def _all_in_config(
    contributions: tuple[int, ...],
    folded: tuple[bool, ...],
    ranks: tuple[int, ...],
    *,
    rake_policy: RakePolicy | None = None,
    odd_chip_order: tuple[int, ...] | None = None,
) -> NPlayerPostflopConfig:
    n = len(contributions)
    board = (0, 1, 2)
    deal = tuple((3 + 2 * seat, 4 + 2 * seat) for seat in range(n))
    ranges = tuple((WeightedCombo(cards, Fraction(1)),) for cards in deal)
    starting = tuple(value if value > 0 else 500 for value in contributions)
    return NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=n,
        button=n - 1,
        starting_stacks=starting,
        contributions=contributions,
        folded=folded,
        board=board,
        ranges=ranges,
        wager_targets=(1,),
        max_raises=1,
        max_deals=1,
        max_nodes=100,
        odd_chip_order=odd_chip_order or tuple(range(n)),
        showdown_ranks={deal: ranks},
        rake_policy=rake_policy,
    )


def _terminal_returns(config: NPlayerPostflopConfig) -> tuple[float, ...]:
    root = create_nplayer_postflop_root(config)
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1
    state = root.child(outcomes[0][0])
    assert state.current_player() == TERMINAL
    return state.returns()


def test_four_player_side_pots_rake_and_conservation() -> None:
    contributions = (300, 800, 800, 500)
    policy = RakePolicy(
        rate_numerator=5,
        rate_denominator=100,
        cap=100,
        minimum_pot=None,
        no_flop_no_drop=False,
        rounding="floor",
        layer_order="top-down",
    )
    config = _all_in_config(
        contributions,
        (True, False, False, False),
        (0, 1, 9, 2),
        rake_policy=policy,
    )
    returns = _terminal_returns(config)
    assert returns == (-300.0, -800.0, 1500.0, -500.0)
    assert sum(returns) == -100.0


def test_five_player_tie_assigns_real_odd_chip_by_declared_order() -> None:
    contributions = (600, 600, 500, 400, 600)
    policy = RakePolicy(
        rate_numerator=1,
        rate_denominator=2700,
        cap=None,
        minimum_pot=None,
        no_flop_no_drop=False,
        rounding="floor",
        layer_order="top-down",
    )
    config = _all_in_config(
        contributions,
        (False, False, False, True, False),
        (9, 9, 2, 1, 3),
        rake_policy=policy,
        odd_chip_order=(4, 1, 0, 2, 3),
    )
    returns = _terminal_returns(config)
    assert returns == (749.0, 750.0, -500.0, -400.0, -600.0)
    assert returns[1] - returns[0] == 1.0
    assert sum(returns) == -1.0


def test_nine_player_trailing_zero_contributors_are_padded() -> None:
    contributions = (200, 400, 300, 400, 350, 250, 0, 0, 0)
    folded = (False, False, True, False, False, True, True, True, True)
    policy = RakePolicy(
        rate_numerator=10,
        rate_denominator=100,
        cap=None,
        minimum_pot=1000,
        no_flop_no_drop=False,
        rounding="ceiling",
        layer_order="bottom-up",
    )
    config = _all_in_config(
        contributions,
        folded,
        (1, 9, 2, 3, 4, 0, 0, 0, 0),
        rake_policy=policy,
    )
    returns = _terminal_returns(config)
    assert len(returns) == 9
    assert returns == (-200.0, 1310.0, -300.0, -400.0, -350.0, -250.0, 0.0, 0.0, 0.0)
    assert sum(returns) == -190.0


def test_terminal_refund_is_bounded_by_current_street_commitment() -> None:
    deal = ((3, 4), (5, 6))
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(20, 100),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=((WeightedCombo(deal[0], Fraction(1)),), (WeightedCombo(deal[1], Fraction(1)),)),
        wager_targets=(90,),
        max_raises=1,
        max_deals=1,
        max_nodes=100,
        odd_chip_order=(0, 1),
        showdown_ranks={deal: (1, 2)},
        rake_policy=None,
    )
    root = create_nplayer_postflop_root(config)
    state = root.child(root.chance_outcomes()[0][0])
    assert state.current_player() == 1
    state = state.child(Action("RAISE", 90))
    state = state.child(Action("CALL", 10))

    assert state.current_player() == TERMINAL
    assert state.total_contributed == (20, 20)
    assert state.street_committed == (10, 10)
    assert state.remaining == (0, 80)
    assert state.pot == 40
    assert state.house_rake == 0
    assert state.returns() == (-20.0, 20.0)
    assert sum(state.returns()) == 0.0