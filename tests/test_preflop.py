"""Bounded heads-up preflop state-machine tests."""

from fractions import Fraction

import pytest

from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.preflop import (
    Continuation,
    PreflopConfig,
    WeightedCombo,
    create_preflop_root,
)


def combo(a: int, b: int, weight=1) -> WeightedCombo:
    return WeightedCombo((a, b), Fraction(weight))


def config(**changes) -> PreflopConfig:
    values = dict(
        starting_stacks=(20, 20),
        forced_posts=(1, 2),
        ranges=((combo(0, 1), combo(0, 2)), (combo(3, 4), combo(1, 5))),
        sizing_expressions=({"unit": "big-blinds", "value": 3}, {"unit": "all-in"}),
        max_raises=3,
        max_deals=20,
        max_nodes=500,
        short_all_in_reopens=False,
        continuation=Continuation("terminal-table", {}, "fixture-v1"),
    )
    values.update(changes)
    return PreflopConfig(**values)


def deal(root, index=0):
    return root.child(root.chance_outcomes()[index][0])


def test_root_posts_once_and_enumerates_blocker_compatible_deals():
    root = create_preflop_root(config())
    assert root.current_player() == CHANCE
    assert root.pot == 3
    assert root.committed == (1, 2)
    assert root.total_contributed == (1, 2)
    assert root.remaining == (19, 18)
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 3  # (0,1)x(1,5) is blocked
    assert sum(probability for _, probability in outcomes) == 1
    assert all(probability == Fraction(1, 3) for _, probability in outcomes)


def test_chance_weight_is_product_normalized_and_bounded():
    cfg = config(ranges=((combo(0, 1, 2), combo(0, 2)), (combo(3, 4, 3),)))
    outcomes = create_preflop_root(cfg).chance_outcomes()
    assert tuple(p for _, p in outcomes) == (Fraction(2, 3), Fraction(1, 3))
    with pytest.raises(ValueError, match="deal"):
        create_preflop_root(config(max_deals=2))


def test_heads_up_action_order_and_information_noninterference():
    root = create_preflop_root(config(ranges=((combo(0, 1), combo(0, 2)), (combo(3, 4), combo(5, 6)))))
    states = [root.child(action) for action, _ in root.chance_outcomes()]
    assert all(state.current_player() == 0 for state in states)
    same_hero = [state for state in states if state.private_deal[0] == (0, 1)]
    assert len(same_hero) == 2
    assert same_hero[0].information_state_key(0) == same_hero[1].information_state_key(0)
    assert same_hero[0].information_state_key(1) != same_hero[1].information_state_key(1)


def test_fold_terminal_uses_preposting_wealth_baseline():
    state = deal(create_preflop_root(config()))
    terminal = state.child(Action("FOLD"))
    assert terminal.current_player() == TERMINAL
    assert terminal.returns() == (-1.0, 1.0)
    assert sum(terminal.returns()) == 0


def test_limp_then_big_blind_check_closes_to_declared_continuation():
    root = create_preflop_root(config())
    state = deal(root)
    call = state.child(Action("CALL", 2))
    assert call.current_player() == 1
    assert call.committed == (2, 2)
    assert call.legal_actions()[0] == Action("CHECK")
    key = (call.private_deal, call.history + (Action("CHECK"),))
    cfg = config(continuation=Continuation("terminal-table", {key: (Fraction(1), Fraction(-1))}, "fixture-v1"))
    closed = deal(create_preflop_root(cfg)).child(Action("CALL", 2)).child(Action("CHECK"))
    assert closed.returns() == (1.0, -1.0)


def test_fixed_sizing_integration_uses_raise_to_amounts_and_deduplicates():
    cfg = config(sizing_expressions=(
        {"unit": "big-blinds", "value": 3},
        {"unit": "previous-bet-multiple", "value": 3},
        {"unit": "all-in"},
    ))
    actions = deal(create_preflop_root(cfg)).legal_actions()
    assert actions == (Action("FOLD"), Action("CALL", 2), Action("RAISE", 6), Action("RAISE", 20))


def test_full_raise_updates_minimum_and_reopens_other_player():
    state = deal(create_preflop_root(config())).child(Action("RAISE", 6))
    assert state.current_player() == 1
    assert state.committed == (6, 2)
    assert state.last_raise_increment == 4
    assert Action("RAISE", 20) in state.legal_actions()


def test_exact_short_all_in_allowed_but_does_not_reopen():
    cfg = config(starting_stacks=(20, 7), sizing_expressions=({"unit": "big-blinds", "value": 3}, {"unit": "all-in"}))
    state = deal(create_preflop_root(cfg)).child(Action("RAISE", 6))
    short = state.child(Action("RAISE", 7))
    assert short.current_player() == 0
    assert short.legal_actions() == (Action("FOLD"), Action("CALL", 7))
    key = (short.private_deal, short.history + (Action("CALL", 7),))
    cfg = config(
        starting_stacks=(20, 7),
        sizing_expressions=({"unit": "big-blinds", "value": 3}, {"unit": "all-in"}),
        continuation=Continuation("terminal-table", {key: (0, 0)}, "short-allin"),
    )
    short = deal(create_preflop_root(cfg)).child(Action("RAISE", 6)).child(Action("RAISE", 7))
    assert short.child(Action("CALL", 7)).current_player() == TERMINAL


def test_short_all_in_can_explicitly_reopen():
    cfg = config(
        starting_stacks=(20, 7),
        short_all_in_reopens=True,
        sizing_expressions=({"unit": "big-blinds", "value": 3}, {"unit": "all-in"}),
    )
    short = deal(create_preflop_root(cfg)).child(Action("RAISE", 6)).child(Action("RAISE", 7))
    assert Action("RAISE", 20) in short.legal_actions()


def test_unmatched_all_in_excess_is_refunded_before_continuation():
    root0 = create_preflop_root(config(starting_stacks=(20, 7), short_all_in_reopens=False))
    dealt0 = deal(root0)
    key = (dealt0.private_deal, (Action("RAISE", 20), Action("CALL", 7)))
    cfg = config(
        starting_stacks=(20, 7),
        short_all_in_reopens=False,
        continuation=Continuation("terminal-table", {key: (Fraction(-7), Fraction(7))}, "allin-oracle"),
    )
    closed = deal(create_preflop_root(cfg)).child(Action("RAISE", 20)).child(Action("CALL", 7))
    assert closed.committed == (7, 7)
    assert closed.total_contributed == (7, 7)
    assert closed.remaining == (13, 0)
    assert closed.pot == 14
    assert closed.returns() == (-7.0, 7.0)


def test_missing_nonfold_continuation_fails_closed():
    state = deal(create_preflop_root(config())).child(Action("CALL", 2))
    with pytest.raises(ValueError, match="continuation"):
        state.child(Action("CHECK"))


def test_strict_config_and_action_validation_and_node_bound():
    with pytest.raises(ValueError):
        create_preflop_root(config(starting_stacks=(True, 20)))
    with pytest.raises(ValueError):
        create_preflop_root(config(forced_posts=(2, 1)))
    with pytest.raises(ValueError):
        create_preflop_root(config(max_raises=True))
    state = deal(create_preflop_root(config()))
    with pytest.raises(ValueError, match="legal"):
        state.child(Action("CALL", 99))
    with pytest.raises(ValueError, match="node"):
        create_preflop_root(config(max_nodes=1))


def test_config_isolated_from_and_immutable_to_sizing_mutation():
    expression = {"unit": "big-blinds", "value": 3}
    cfg = config(sizing_expressions=(expression,))
    expression["value"] = 99
    assert cfg.sizing_expressions[0]["value"] == 3
    with pytest.raises(TypeError):
        cfg.sizing_expressions[0]["value"] = 4


def test_nonfinite_exact_inputs_fail_with_value_error():
    with pytest.raises(ValueError):
        WeightedCombo((0, 1), float("inf"))
    with pytest.raises(ValueError):
        Continuation("terminal-table", {(((0, 1), (2, 3)), ()): (float("inf"), float("-inf"))}, "x")


def test_direct_state_construction_enforces_accounting_and_phase_invariants():
    valid = deal(create_preflop_root(config()))
    values = {field: getattr(valid, field) for field in valid.__dataclass_fields__}
    for changes in (
        {"pot": 999},
        {"remaining": (50, 50)},
        {"acting_player": 999},
        {"acting_player": TERMINAL, "terminal_values": None},
        {"private_deal": None},
        {"acted": (True, 1)},
    ):
        with pytest.raises(ValueError):
            type(valid)(**(values | changes))


def test_sizing_expressions_are_validated_at_config_boundary():
    with pytest.raises(ValueError):
        config(sizing_expressions=({"unit": "big-blinds", "value": []},))
