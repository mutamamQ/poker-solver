"""Exact range/strategy table tests on bounded games."""

from fractions import Fraction

import pytest

from poker_solver.model import Action
from poker_solver.multiway import MultiwayConfig, create_three_player_root
from poker_solver.nplayer import collect_nplayer_infosets, expected_values_nplayer
from poker_solver.preflop import WeightedCombo
from poker_solver.range_table import build_range_table


def wc(a, b, w=1):
    return WeightedCombo((a, b), Fraction(w))


def fixture():
    deals = [
        ((6, 7), p1, p2)
        for p1 in ((8, 9), (8, 12))
        for p2 in ((10, 11), (10, 13))
    ]
    cfg = MultiwayConfig(
        button=0,
        starting_stacks=(10, 10, 10),
        contributions=(2, 2, 2),
        folded=(False, False, False),
        board=(0, 1, 2),
        ranges=((wc(6, 7),), (wc(8, 9, 3), wc(8, 12)), (wc(10, 11), wc(10, 13))),
        wager_targets=(4,),
        max_raises=1,
        max_deals=10,
        max_nodes=1000,
        odd_chip_order=(1, 2, 0),
        showdown_ranks={deal: (3, 2, 1) for deal in deals},
    )
    root = create_three_player_root(cfg)
    infosets = collect_nplayer_infosets(root, max_nodes=10_000)
    strategy = {
        key: {action: 1.0 / len(actions) for action in actions}
        for key, (_, actions) in infosets.items()
    }
    return root, strategy


def test_own_range_rows_have_exact_reach_probabilities_and_actions():
    root, strategy = fixture()
    table = build_range_table(root, strategy, seat=1)
    assert tuple(row.combo for row in table.rows) == ((8, 9), (8, 12))
    assert tuple(row.source_weight for row in table.rows) == (Fraction(3), Fraction(1))
    assert tuple(row.range_probability for row in table.rows) == (0.75, 0.25)
    assert all(row.conditional_reach == row.range_probability for row in table.rows)
    assert all(row.actions == tuple(strategy[row.info_key]) for row in table.rows)
    assert all(sum(row.action_probabilities.values()) == pytest.approx(1.0) for row in table.rows)


def test_per_action_ev_mixes_back_to_row_ev():
    root, strategy = fixture()
    table = build_range_table(root, strategy, seat=1)
    for row in table.rows:
        oracle = sum(row.action_probabilities[action] * row.action_evs[action] for action in row.actions)
        assert row.mixed_ev == pytest.approx(oracle)


def test_aggregate_frequencies_and_ev_are_reach_weighted():
    root, strategy = fixture()
    table = build_range_table(root, strategy, seat=1)
    for action, frequency in table.action_frequencies.items():
        oracle = sum(row.range_probability * row.action_probabilities[action] for row in table.rows)
        assert frequency == pytest.approx(oracle)
    oracle_ev = sum(row.range_probability * row.mixed_ev for row in table.rows)
    assert table.mixed_ev == pytest.approx(oracle_ev)


def test_opponent_view_without_action_omits_action_columns():
    root, strategy = fixture()
    table = build_range_table(root, strategy, seat=0)
    assert len(table.rows) == 1
    row = table.rows[0]
    assert row.actions == ()
    assert dict(row.action_probabilities) == {}
    assert dict(row.action_evs) == {}
    assert table.action_frequencies == {}


def test_table_ev_matches_raw_root_expected_value_for_acting_seat():
    root, strategy = fixture()
    table = build_range_table(root, strategy, seat=1)
    values = expected_values_nplayer(root, strategy)
    assert table.mixed_ev == pytest.approx(values[1])


def test_outputs_are_deeply_immutable_and_input_strategy_unchanged():
    root, strategy = fixture()
    before = {key: dict(policy) for key, policy in strategy.items()}
    table = build_range_table(root, strategy, seat=1)
    assert strategy == before
    with pytest.raises(TypeError):
        table.action_frequencies[Action("X")] = 1.0
    with pytest.raises(TypeError):
        table.rows[0].action_probabilities[table.rows[0].actions[0]] = 0.0


def test_missing_extra_or_nonunit_strategy_fails_closed():
    root, strategy = fixture()
    key = next(iter(strategy))
    missing = dict(strategy)
    del missing[key]
    with pytest.raises(ValueError):
        build_range_table(root, missing, seat=1)
    extra = dict(strategy)
    extra[("extra",)] = {Action("X"): 1.0}
    with pytest.raises(ValueError):
        build_range_table(root, extra, seat=1)
    bad = {k: dict(v) for k, v in strategy.items()}
    bad[key] = {action: 0.0 for action in bad[key]}
    with pytest.raises(ValueError):
        build_range_table(root, bad, seat=1)


def test_strict_seat_root_and_zero_reach_validation():
    root, strategy = fixture()
    for seat in (True, -1, 3, 1.0):
        with pytest.raises(ValueError):
            build_range_table(root, strategy, seat=seat)
    dealt = root.child(root.chance_outcomes()[0][0])
    with pytest.raises(ValueError, match="chance"):
        build_range_table(dealt, strategy, seat=1)
