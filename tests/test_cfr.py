import pytest

from poker_solver.best_response import nash_conv
from poker_solver.cfr import CFRSolver, expected_values, regret_matching
from poker_solver.kuhn import KUHN_VALUE_P0, kuhn_root
from poker_solver.model import Action


def test_regret_matching():
    actions = (Action("a"), Action("b"), Action("c"))
    assert regret_matching({a: 0.0 for a in actions}, actions) == {a: 1 / 3 for a in actions}
    policy = regret_matching({actions[0]: -2, actions[1]: 1, actions[2]: 3}, actions)
    assert policy == {actions[0]: 0.0, actions[1]: 0.25, actions[2]: 0.75}


def test_kuhn_cfr_is_deterministic_and_approaches_value():
    solver1 = CFRSolver(kuhn_root())
    strategy1 = solver1.train(5_000)
    solver2 = CFRSolver(kuhn_root())
    strategy2 = solver2.train(5_000)
    assert strategy1 == strategy2
    value = expected_values(kuhn_root(), strategy1)[0]
    assert value == pytest.approx(KUHN_VALUE_P0, abs=0.003)
    assert nash_conv(kuhn_root(), strategy1).nash_conv < 0.03


def test_training_can_continue_and_probabilities_normalize():
    solver = CFRSolver(kuhn_root())
    solver.train(10)
    solver.train(10)
    assert solver.iterations == 20
    for policy in solver.average_strategy().values():
        assert sum(policy.values()) == pytest.approx(1.0)
        assert all(p >= 0 for p in policy.values())
    with pytest.raises(ValueError):
        solver.train(0)
