"""Test game_structure.py: ForcedPost, SeatLedger, side pots, rake, conservation."""

import pytest


def test_forced_post_immutable():
    """RED: ForcedPost must be an immutable type."""
    from poker_solver.game_structure import ForcedPost

    post = ForcedPost(seat=0, kind="small-blind", amount=1)
    assert post.seat == 0
    assert post.kind == "small-blind"
    assert post.amount == 1
    with pytest.raises((AttributeError, TypeError)):
        post.amount = 2  # type: ignore


def test_forced_posts_transfer_once_and_effective_stack_is_pairwise():
    from poker_solver.game_structure import ForcedPost, apply_forced_posts, pairwise_effective_stack

    ledgers = apply_forced_posts(
        (100, 80, 40),
        (
            ForcedPost(0, "ante", 5),
            ForcedPost(1, "ante", 5),
            ForcedPost(2, "ante", 5),
            ForcedPost(0, "small-blind", 5),
            ForcedPost(1, "big-blind", 10),
        ),
    )

    assert [(s.remaining, s.street_committed, s.total_contributed) for s in ledgers] == [
        (90, 10, 10), (65, 15, 15), (35, 5, 5)
    ]
    assert sum(s.remaining + s.total_contributed for s in ledgers) == 220
    assert pairwise_effective_stack(ledgers, 0, 1) == 65
    assert pairwise_effective_stack(ledgers, 0, 2) == 35


def test_uncalled_excess_is_refunded_before_side_pots():
    from poker_solver.game_structure import build_pot_layers, refund_uncalled_excess

    matched, refunds = refund_uncalled_excess((100, 60, 20))
    assert matched == (60, 60, 20)
    assert refunds == (40, 0, 0)
    layers = build_pot_layers(matched, folded=frozenset({1}))
    assert [(layer.amount, layer.contributors, layer.eligible) for layer in layers] == [
        (60, frozenset({0, 1, 2}), frozenset({0, 2})),
        (80, frozenset({0, 1}), frozenset({0})),
    ]
    assert sum(layer.amount for layer in layers) + sum(refunds) == 180


def test_rake_uses_exact_rational_rounding_cap_minimum_and_nffd():
    from poker_solver.game_structure import RakePolicy, calculate_rake

    base = dict(
        rate_numerator=5,
        rate_denominator=100,
        cap=None,
        minimum_pot=None,
        no_flop_no_drop=False,
        layer_order="top-down",
    )
    assert calculate_rake(RakePolicy(rounding="floor", **base), 101, flop_seen=True) == 5
    assert calculate_rake(RakePolicy(rounding="ceiling", **base), 101, flop_seen=True) == 6
    assert calculate_rake(RakePolicy(rounding="nearest", **base), 110, flop_seen=True) == 6
    assert calculate_rake(RakePolicy(rounding="ceiling", cap=4, **{k: v for k, v in base.items() if k != "cap"}), 101, flop_seen=True) == 4
    assert calculate_rake(RakePolicy(rounding="floor", minimum_pot=200, **{k: v for k, v in base.items() if k != "minimum_pot"}), 101, flop_seen=True) == 0
    nffd = RakePolicy(rounding="floor", no_flop_no_drop=True, **{k: v for k, v in base.items() if k != "no_flop_no_drop"})
    assert calculate_rake(nffd, 101, flop_seen=False) == 0


def test_rake_allocation_and_odd_chips_conserve_every_layer():
    from poker_solver.game_structure import PotLayer, allocate_rake, award_pot_layers

    layers = (
        PotLayer(3, frozenset({0, 1, 2}), frozenset({0, 1, 2})),
        PotLayer(8, frozenset({0, 1}), frozenset({0, 1})),
    )
    rake_by_layer = allocate_rake(layers, total_rake=5, layer_order="top-down")
    assert rake_by_layer == (0, 5)
    awards = award_pot_layers(
        layers,
        winners_by_layer=(frozenset({0, 1}), frozenset({1})),
        odd_chip_order=(0, 1, 2),
        rake_by_layer=rake_by_layer,
    )
    assert awards == (2, 4, 0)
    assert sum(awards) + sum(rake_by_layer) == sum(layer.amount for layer in layers)


def test_terminal_conservation_includes_house_rake_exactly():
    from poker_solver.game_structure import verify_terminal_conservation

    verify_terminal_conservation((100, 100, 100), (190, 104, 0), house_rake=6)
    with pytest.raises(ValueError, match="conservation"):
        verify_terminal_conservation((100, 100, 100), (190, 105, 0), house_rake=6)


def test_pot_layer_rejects_empty_eligible_set():
    from poker_solver.game_structure import PotLayer

    with pytest.raises(ValueError, match="eligible.*non-empty"):
        PotLayer(100, frozenset({0, 1}), frozenset())


def test_pot_layer_rejects_invalid_seat_members():
    from poker_solver.game_structure import PotLayer

    with pytest.raises(ValueError, match="contributors.*non-negative integers"):
        PotLayer(100, frozenset({-1, 0}), frozenset({0}))
    with pytest.raises(ValueError, match="eligible.*non-negative integers"):
        PotLayer(100, frozenset({0, 1}), frozenset({True}))
