import pytest

from poker_solver.audit import audit_game
from poker_solver.kuhn import BET, CALL, CHECK, FOLD, KUHN_VALUE_P0, KuhnState, kuhn_root
from poker_solver.model import CHANCE, TERMINAL


def test_root_deals_all_six_uniformly():
    root = kuhn_root()
    assert root.current_player() == CHANCE
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 6
    assert sum(p for _, p in outcomes) == pytest.approx(1.0)
    deals = {root.child(action).deal for action, _ in outcomes}
    assert deals == {"JQ", "JK", "QJ", "QK", "KJ", "KQ"}


@pytest.mark.parametrize(("deal","history","value"), [
    ("KJ", (CHECK, CHECK), 1.0),
    ("JK", (CHECK, CHECK), -1.0),
    ("JK", (BET, FOLD), 1.0),
    ("KJ", (BET, CALL), 2.0),
    ("JK", (CHECK, BET, FOLD), -1.0),
    ("KJ", (CHECK, BET, CALL), 2.0),
])
def test_terminal_utilities(deal, history, value):
    state = KuhnState(deal, history)
    assert state.current_player() == TERMINAL
    assert state.returns() == (value, -value)


def test_infoset_hides_opponent_card_and_actions_are_stable():
    assert KuhnState("JQ").information_state_key(0) == KuhnState("JK").information_state_key(0)
    assert KuhnState("QJ", (BET,)).information_state_key(1) == KuhnState("KJ", (BET,)).information_state_key(1)
    assert KuhnState("JQ").legal_actions() == (CHECK, BET)
    assert KuhnState("JQ", (BET,)).legal_actions() == (FOLD, CALL)


def test_full_tree_counts_and_known_value_constant():
    report = audit_game(kuhn_root())
    assert (report.nodes, report.terminals, report.decision_nodes, report.chance_nodes, report.infosets) == (55, 30, 24, 1, 12)
    assert KUHN_VALUE_P0 == pytest.approx(-1 / 18)
