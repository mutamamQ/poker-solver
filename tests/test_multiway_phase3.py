"""Exactly-three-player bounded postflop tests."""

from fractions import Fraction

import pytest

from poker_solver.game_structure import RakePolicy
from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.multiway import MultiwayConfig, ThreePlayerPostflopState, create_three_player_root
from poker_solver.nplayer import collect_nplayer_infosets
from poker_solver.preflop import WeightedCombo


def wc(a, b, w=1):
    return WeightedCombo((a, b), Fraction(w))


def config(**changes):
    deal = ((6, 7), (8, 9), (10, 11))
    values = dict(
        button=0,
        starting_stacks=(20, 20, 20),
        contributions=(2, 2, 2),
        folded=(False, False, False),
        board=(0, 1, 2),
        ranges=((wc(6, 7), wc(6, 8)), (wc(8, 9),), (wc(10, 11),)),
        wager_targets=(4, 8),
        max_raises=3,
        max_deals=20,
        max_nodes=500,
        odd_chip_order=(1, 2, 0),
        showdown_ranks={deal: (3, 2, 1)},
        rake_policy=None,
    )
    values.update(changes)
    return MultiwayConfig(**values)


def dealt(cfg=None, index=0):
    root = create_three_player_root(cfg or config())
    return root.child(root.chance_outcomes()[index][0])


def test_chance_triples_are_blocker_filtered_exact_and_normalized():
    root = create_three_player_root(config())
    assert root.current_player() == CHANCE
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1  # second P0 combo collides with P1
    assert outcomes[0][1] == Fraction(1)
    assert root.pot == 6
    assert root.remaining == (18, 18, 18)


def test_exactly_three_players_and_strict_config_bounds():
    with pytest.raises(ValueError, match="three"):
        config(starting_stacks=(20, 20))
    with pytest.raises(ValueError):
        config(button=True)
    with pytest.raises(ValueError, match="deal"):
        create_three_player_root(config(max_deals=0))
    with pytest.raises(ValueError, match="node"):
        create_three_player_root(config(max_nodes=1))


def test_postflop_action_order_is_clockwise_after_button():
    state = dealt()
    assert state.current_player() == 1
    assert state.legal_actions() == (Action("CHECK"), Action("RAISE", 4), Action("RAISE", 8), Action("RAISE", 18))


def test_three_checks_close_round_and_settle_showdown():
    terminal = dealt().child(Action("CHECK")).child(Action("CHECK")).child(Action("CHECK"))
    assert terminal.current_player() == TERMINAL
    assert terminal.returns() == (4.0, -2.0, -2.0)
    assert sum(terminal.returns()) == 0


def test_bet_call_fold_call_path_and_accounting():
    state = dealt().child(Action("RAISE", 4))
    assert state.current_player() == 2
    assert state.pot == 10
    assert state.street_committed == (0, 4, 0)
    state = state.child(Action("CALL", 4))
    state = state.child(Action("FOLD"))
    assert state.current_player() == TERMINAL
    assert sum(state.returns()) == 0


def test_full_raise_resets_pending_and_updates_minimum():
    state = dealt().child(Action("RAISE", 4)).child(Action("RAISE", 8))
    assert state.current_player() == 0
    assert state.last_raise_increment == 4
    assert Action("RAISE", 18) in state.legal_actions()


def test_short_all_in_is_legal_and_does_not_reopen_prior_actor():
    cfg = config(starting_stacks=(20, 20, 7), contributions=(2, 2, 2), wager_targets=(4, 8))
    state = dealt(cfg).child(Action("RAISE", 4)).child(Action("RAISE", 5))
    state = state.child(Action("CALL", 5))
    assert state.current_player() == 1
    assert all(action.kind != "RAISE" for action in state.legal_actions())


def test_side_pot_and_tie_odd_chip_settlement():
    deal = ((6, 7), (8, 9), (10, 11))
    cfg = config(
        starting_stacks=(5, 10, 10),
        contributions=(5, 10, 10),
        folded=(False, False, False),
        showdown_ranks={deal: (9, 9, 1)},
    )
    terminal = dealt(cfg)
    # Main 15 split seats 0/1, odd chip follows order seat 1; side 10 to seat 1.
    assert terminal.returns() == (2.0, 8.0, -10.0)


def test_folded_player_funds_but_cannot_win_layer():
    deal = ((6, 7), (8, 9), (10, 11))
    cfg = config(contributions=(5, 5, 5), folded=(True, False, False), showdown_ranks={deal: (99, 2, 1)})
    terminal = dealt(cfg).child(Action("CHECK")).child(Action("CHECK"))
    assert terminal.returns() == (-5.0, 10.0, -5.0)


def test_rake_conservation_and_allocation():
    deal = ((6, 7), (8, 9), (10, 11))
    rake = RakePolicy(1, 10, None, None, False, "floor", "bottom-up")
    cfg = config(contributions=(10, 10, 10), showdown_ranks={deal: (3, 2, 1)}, rake_policy=rake)
    terminal = dealt(cfg).child(Action("CHECK")).child(Action("CHECK")).child(Action("CHECK"))
    assert terminal.returns() == (17.0, -10.0, -10.0)
    assert sum(terminal.returns()) == -3


def test_information_key_never_contains_other_private_cards():
    cfg = config(
        ranges=((wc(6, 7),), (wc(8, 9), wc(8, 12)), (wc(10, 11), wc(10, 13))),
        showdown_ranks={},
    )
    states = [dealt(cfg, i) for i in range(4)]
    assert len({state.information_state_key(0) for state in states}) == 1
    assert len({state.information_state_key(1) for state in states}) == 2


def test_missing_showdown_coverage_fails_closed_and_direct_state_validates():
    state = dealt(config(showdown_ranks={}))
    with pytest.raises(ValueError, match="showdown"):
        state.child(Action("CHECK")).child(Action("CHECK")).child(Action("CHECK"))
    values = {field: getattr(state, field) for field in state.__dataclass_fields__}
    with pytest.raises(ValueError):
        ThreePlayerPostflopState(**(values | {"pot": 999}))
    with pytest.raises(ValueError):
        ThreePlayerPostflopState(**(values | {"acting_player": 8}))


def test_nplayer_collector_accepts_bounded_three_player_game():
    infosets = collect_nplayer_infosets(create_three_player_root(config()), max_nodes=10_000)
    assert infosets
    assert {owner for owner, _ in infosets.values()} == {0, 1, 2}
