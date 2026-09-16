"""Strict config, forced-post, straddle, and bounded-deal contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction

import pytest

from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, CHANCE
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule,
    create_nplayer_preflop_root,
    enumerate_nplayer_preflop_deals,
)
from poker_solver.preflop import WeightedCombo


def _combo(cards: tuple[int, int], weight: int = 1) -> WeightedCombo:
    return WeightedCombo(cards, Fraction(weight))


def _continuation() -> NPlayerPreflopContinuation:
    return NPlayerPreflopContinuation(
        kind="terminal-table",
        provenance="config-red-fixture",
        source="supplied",
        payoff_table={},
        showdown_ranks={},
        odd_chip_order=(),
    )


def _config(n: int, **changes) -> NPlayerPreflopConfig:
    button = 0 if n == 2 else n - 1
    values = dict(
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
    values.update(changes)
    return NPlayerPreflopConfig(**values)


@pytest.mark.parametrize(
    ("n", "expected_actor", "expected_pending"),
    (
        (2, 0, (0, 1)),
        (9, 2, (2, 3, 4, 5, 6, 7, 8, 0, 1)),
    ),
)
def test_n2_and_n9_root_deal_and_action_order(
    n: int,
    expected_actor: int,
    expected_pending: tuple[int, ...],
) -> None:
    root = create_nplayer_preflop_root(_config(n))
    assert root.current_player() == CHANCE
    assert root.pot == 3
    assert root.street_committed == (1, 2) + (0,) * (n - 2)
    outcomes = root.chance_outcomes()
    assert outcomes == ((Action("DEAL", 0), Fraction(1)),)

    dealt = root.child(Action("DEAL", 0))
    assert dealt.current_player() == expected_actor
    assert dealt.pending == expected_pending


@pytest.mark.parametrize("num_players", (True, 1, 10))
def test_num_players_rejects_bool_and_out_of_range(num_players: object) -> None:
    with pytest.raises(ValueError, match="num_players"):
        replace(_config(2), num_players=num_players)


def test_uniform_ante_ledger_excludes_antes_from_street_commitment() -> None:
    config = _config(
        3,
        button=0,
        forced_posts=(
            ForcedPost(seat=0, kind="ante", amount=1),
            ForcedPost(seat=1, kind="ante", amount=1),
            ForcedPost(seat=2, kind="ante", amount=1),
            ForcedPost(seat=1, kind="small-blind", amount=1),
            ForcedPost(seat=2, kind="big-blind", amount=2),
        ),
    )
    root = create_nplayer_preflop_root(config)
    assert root.pot == 6
    assert root.total_contributed == (1, 2, 3)
    assert root.street_committed == (0, 1, 2)
    assert root.remaining == (99, 98, 97)


def test_standard_straddle_boundary_and_hu_mississippi_rejection() -> None:
    standard = _config(
        3,
        button=0,
        forced_posts=(
            ForcedPost(seat=1, kind="small-blind", amount=1),
            ForcedPost(seat=2, kind="big-blind", amount=2),
            ForcedPost(seat=0, kind="straddle", amount=4),
        ),
        straddle_variant="standard",
    )
    root = create_nplayer_preflop_root(standard)
    assert root.pot == 7
    assert root.street_committed == (4, 1, 2)
    assert root.last_raise_increment == 4
    dealt = root.child(Action("DEAL", 0))
    assert dealt.current_player() == 1
    assert dealt.pending == (1, 2, 0)

    with pytest.raises(ValueError, match="mississippi|straddle"):
        _config(
            2,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
                ForcedPost(seat=0, kind="straddle", amount=4),
            ),
            straddle_variant="mississippi",
        )


@pytest.mark.parametrize(
    ("variant", "posts", "expected_pot", "expected_street", "expected_pending", "expected_actions"),
    (
        (
            "double",
            (
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
                ForcedPost(seat=2, kind="straddle", amount=4),
                ForcedPost(seat=3, kind="straddle", amount=8),
            ),
            15,
            (1, 2, 4, 8, 0, 0),
            (4, 5, 0, 1, 2, 3),
            (Action("FOLD"), Action("CALL", 8), Action("RAISE", 100)),
        ),
        (
            "mississippi",
            (
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
                ForcedPost(seat=5, kind="straddle", amount=4),
            ),
            7,
            (1, 2, 0, 0, 0, 4),
            (0, 1, 2, 3, 4, 5),
            (Action("FOLD"), Action("CALL", 4), Action("RAISE", 100)),
        ),
    ),
)
def test_double_and_mississippi_straddles_have_distinct_repeatable_roots(
    variant: str,
    posts: tuple[ForcedPost, ...],
    expected_pot: int,
    expected_street: tuple[int, ...],
    expected_pending: tuple[int, ...],
    expected_actions: tuple[Action, ...],
) -> None:
    config = _config(6, forced_posts=posts, straddle_variant=variant)
    first = create_nplayer_preflop_root(config)
    second = create_nplayer_preflop_root(config)

    assert first == second
    assert first.pot == expected_pot
    assert first.street_committed == expected_street
    dealt = first.child(Action("DEAL", 0))
    assert dealt.pending == expected_pending
    assert dealt.current_player() == expected_pending[0]
    assert dealt.legal_actions() == expected_actions


@pytest.mark.parametrize(
    ("variant", "stacks", "posts", "all_in_seat"),
    (
        (
            "standard",
            (100, 100, 4, 100, 100, 100),
            (
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
                ForcedPost(2, "straddle", 4),
            ),
            2,
        ),
        (
            "double",
            (100, 100, 100, 8, 100, 100),
            (
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
                ForcedPost(2, "straddle", 4),
                ForcedPost(3, "straddle", 8),
            ),
            3,
        ),
    ),
)
def test_exact_all_in_straddler_has_no_pending_option(
    variant: str,
    stacks: tuple[int, ...],
    posts: tuple[ForcedPost, ...],
    all_in_seat: int,
) -> None:
    root = create_nplayer_preflop_root(
        _config(6, starting_stacks=stacks, forced_posts=posts, straddle_variant=variant)
    )
    assert all_in_seat not in root.pending
    assert not root.can_raise[all_in_seat]


@pytest.mark.parametrize("kind", ("garbage", None, 42))
def test_unsupported_forced_post_kinds_fail_at_config(kind: object) -> None:
    base = _config(2)
    with pytest.raises(ValueError, match="forced post|kind|type"):
        replace(
            base,
            forced_posts=base.forced_posts
            + (ForcedPost(0, kind, 3),),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("order", ((False, True), (0.0, 1.0)))
def test_odd_chip_order_rejects_non_strict_seat_aliases(order: tuple[object, ...]) -> None:
    deal = ((0, 1), (2, 3))
    with pytest.raises(ValueError, match="odd_chip_order|seat"):
        NPlayerPreflopContinuation(
            kind="showdown-ranks",
            provenance="strict-seat-fixture",
            source="supplied",
            payoff_table={},
            showdown_ranks={deal: (1, 2)},
            odd_chip_order=order,  # type: ignore[arg-type]
        )


def test_sizing_expression_backing_is_immutable_and_hash_stable() -> None:
    rule = NPlayerPreflopSizingRule(
        position="BTN/SB",
        raise_count=0,
        cold_callers=0,
        relation="NA",
        expressions=({"unit": "big-blinds", "value": 3},),
    )
    state = create_nplayer_preflop_root(_config(2, sizing_rules=(rule,))).child(
        Action("DEAL", 0)
    )
    original_actions = state.legal_actions()
    original_key = state.information_state_key(0)
    original_hash = hash(rule)

    with pytest.raises((AttributeError, TypeError)):
        getattr(rule.expressions[0], "_data")["value"] = 8
    with pytest.raises((AttributeError, FrozenInstanceError)):
        setattr(rule.expressions[0], "_items", (("unit", "all-in"),))

    assert state.legal_actions() == original_actions
    assert state.information_state_key(0) == original_key
    assert hash(rule) == original_hash
    assert rule == replace(rule)
    assert hash(rule) == hash(replace(rule))


@pytest.mark.parametrize("value", (Decimal("NaN"), Decimal("Infinity")))
def test_sizing_rules_reject_nonfinite_decimal_values(value: Decimal) -> None:
    with pytest.raises(ValueError, match="invalid sizing expression|finite"):
        NPlayerPreflopSizingRule(
            position="BTN/SB",
            raise_count=0,
            cold_callers=0,
            relation="NA",
            expressions=({"unit": "big-blinds", "value": value},),
        )


@pytest.mark.parametrize(
    "changes",
    (
        {"raise_count": 1},
        {"pending": ()},
        {"can_raise": (False, False)},
        {"last_raise_increment": 99},
        {
            "pot": 0,
            "street_committed": (0, 0),
            "total_contributed": (0, 0),
            "remaining": (100, 100),
        },
    ),
)
def test_direct_chance_root_rejects_impossible_state(changes: dict[str, object]) -> None:
    root = create_nplayer_preflop_root(_config(2))
    with pytest.raises(ValueError, match="chance root|root invariant"):
        replace(root, **changes)


def test_max_raises_rejects_structural_depth_beyond_recursive_solver_limit() -> None:
    with pytest.raises(ValueError, match="max_raises|structural depth"):
        replace(_config(2), max_raises=1_000)


@pytest.mark.parametrize(
    "posts",
    (
        (
            ForcedPost(0, "small-blind", 1),
            ForcedPost(1, "big-blind", 2),
            ForcedPost(0, "ante", 1),
        ),
        (
            ForcedPost(0, "small-blind", 1),
            ForcedPost(1, "big-blind", 2),
            ForcedPost(0, "ante", 1),
            ForcedPost(1, "ante", 2),
        ),
        (
            ForcedPost(0, "small-blind", 1),
            ForcedPost(1, "big-blind", 2),
            ForcedPost(0, "ante", 100),
            ForcedPost(1, "ante", 100),
        ),
    ),
)
def test_invalid_ante_arrangements_fail_closed(posts: tuple[ForcedPost, ...]) -> None:
    with pytest.raises(ValueError, match="ante|stack|post"):
        _config(2, forced_posts=posts)


def test_double_straddle_amounts_must_strictly_increase() -> None:
    with pytest.raises(ValueError, match="strictly increase"):
        _config(
            6,
            forced_posts=(
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
                ForcedPost(2, "straddle", 4),
                ForcedPost(3, "straddle", 4),
            ),
            straddle_variant="double",
        )


def test_strict_config_boundary_matrix() -> None:
    base = _config(2)
    sizing_rule = NPlayerPreflopSizingRule(
        "BTN/SB", 0, 0, "NA", ({"unit": "big-blinds", "value": 3},)
    )
    invalid_changes: tuple[dict[str, object], ...] = (
        {"button": True},
        {"starting_stacks": (100,)},
        {"starting_stacks": (100, False)},
        {"ranges": base.ranges[:1]},
        {
            "ranges": (
                (_combo((0, 1)), _combo((1, 0))),
                base.ranges[1],
            )
        },
        {
            "ranges": (
                (_combo((0, 52)),),
                base.ranges[1],
            )
        },
        {"sizing_rules": (sizing_rule, sizing_rule)},
        {"max_raises": True},
        {"max_deals": 0},
        {"max_nodes": 1.5},
        {"short_all_in_reopens": 1},
        {"continuation": object()},
        {"straddle_variant": "unknown"},
    )

    for changes in invalid_changes:
        with pytest.raises(ValueError):
            replace(base, **changes)


def test_blocker_pruning_exact_mass_and_candidate_product_bound() -> None:
    ranges = (
        (_combo((0, 1), 1), _combo((2, 3), 2)),
        (_combo((4, 5), 3), _combo((0, 6), 1)),
    )
    config = _config(2, ranges=ranges, max_deals=4)
    deals = enumerate_nplayer_preflop_deals(config)
    assert tuple(deal for deal, _ in deals) == (
        ((0, 1), (4, 5)),
        ((2, 3), (4, 5)),
        ((2, 3), (0, 6)),
    )
    assert tuple(probability for _, probability in deals) == (
        Fraction(3, 11),
        Fraction(6, 11),
        Fraction(2, 11),
    )

    with pytest.raises(ValueError, match="max_deals|candidate"):
        _config(2, ranges=ranges, max_deals=3)