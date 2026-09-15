import pytest

from poker_solver.best_response import nash_conv
from poker_solver.cards import parse_cards
from poker_solver.cfr import CFRSolver
from poker_solver.equity import WeightedCombo
from poker_solver.model import CHANCE, TERMINAL
from poker_solver.river import CALL, CHECK, FOLD, RiverConfig, RiverState, river_root


def combo(text, weight=1.0):
    cards = parse_cards(text.split())
    return WeightedCombo((cards[0], cards[1]), weight)


def config():
    return RiverConfig(
        parse_cards("2c 3d 4h 9s Kc".split()), 2.0, 1, 1,
        (combo("As 5s"), combo("Qs Js")),
        (combo("Kh Qh"), combo("9h 8h")),
    )


def test_chance_pairs_and_probabilities():
    root = river_root(config())
    assert root.current_player() == CHANCE
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 4
    assert [p for _, p in outcomes] == pytest.approx([0.25] * 4)
    assert len({root.child(a).deal for a, _ in outcomes}) == 4


def test_public_tree_actions_and_terminal_payoffs():
    b = config().bet_action
    dealt = RiverState(config(), (combo("As 5s").cards, combo("Kh Qh").cards))
    assert dealt.legal_actions() == (CHECK, b)
    assert dealt.child(CHECK).legal_actions() == (CHECK, b)
    assert dealt.child(b).legal_actions() == (FOLD, CALL)
    assert dealt.child(CHECK).child(b).legal_actions() == (FOLD, CALL)
    assert dealt.child(b).child(FOLD).returns() == (1.0, -1.0)
    assert dealt.child(b).child(CALL).returns() == (2.0, -2.0)
    assert dealt.child(CHECK).child(b).child(FOLD).returns() == (-1.0, 1.0)
    assert dealt.child(CHECK).child(CHECK).current_player() == TERMINAL


def test_infoset_hides_opponent_cards():
    cfg = config()
    own = combo("Qs Js").cards
    state1 = RiverState(cfg, (own, combo("Kh Qh").cards))
    state2 = RiverState(cfg, (own, combo("9h 8h").cards))
    assert state1.information_state_key(0) == state2.information_state_key(0)


def test_config_rejects_bad_inputs_and_blockers_renormalize():
    with pytest.raises(ValueError):
        RiverConfig(parse_cards("2c 3d 4h 9s Kc".split()), 2.0, 1, 2, (combo("As 5s"),), (combo("Kh Qh"),))
    cfg = RiverConfig(
        parse_cards("2c 3d 4h 9s Kc".split()), 2.0, 1, 1,
        (combo("As 5s", 3), combo("Qs Js", 1)),
        (combo("As Ah", 5), combo("Kh Qh", 1)),
    )
    outcomes = river_root(cfg).chance_outcomes()
    assert len(outcomes) == 3
    assert [p for _, p in outcomes] == pytest.approx([3 / 9, 5 / 9, 1 / 9])
    assert sum(p for _, p in outcomes) == pytest.approx(1.0)


def test_compact_river_cfr_reaches_low_nashconv():
    root = river_root(config())
    strategy = CFRSolver(root).train(5_000)
    metric = nash_conv(root, strategy)
    assert metric.nash_conv < 0.01
    assert sum(metric.values) == pytest.approx(0.0, abs=1e-12)
