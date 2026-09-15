"""Tests for external-sampling MCCFR."""

import pytest

from poker_solver.best_response import nash_conv
from poker_solver.kuhn import KUHN_VALUE_P0, kuhn_root
from poker_solver.mccfr import MCCFRSolver, expected_values, regret_matching
from poker_solver.model import Action


def test_regret_matching():
    """Regret matching should convert regrets to probabilities."""
    actions = (Action("a"), Action("b"), Action("c"))
    assert regret_matching({a: 0.0 for a in actions}, actions) == {a: 1 / 3 for a in actions}
    policy = regret_matching({actions[0]: -2, actions[1]: 1, actions[2]: 3}, actions)
    assert policy == {actions[0]: 0.0, actions[1]: 0.25, actions[2]: 0.75}


def test_action_probabilities_normalize():
    """All action probabilities should sum to 1.0."""
    solver = MCCFRSolver(kuhn_root(), seed=42)
    solver.train(100)
    for policy in solver.average_strategy().values():
        assert sum(policy.values()) == pytest.approx(1.0)
        assert all(p >= 0 for p in policy.values())


def test_lazy_infoset_discovery():
    """Infosets should be discovered lazily during traversal."""
    solver = MCCFRSolver(kuhn_root(), seed=42)
    assert len(solver.infosets) == 0
    solver.train(1)
    # After one iteration, some infosets should be discovered
    assert len(solver.infosets) > 0
    count_after_one = len(solver.infosets)
    solver.train(10)
    # More iterations may discover more infosets
    assert len(solver.infosets) >= count_after_one


def test_same_seed_produces_identical_output():
    """Same seed should produce identical strategies."""
    solver1 = MCCFRSolver(kuhn_root(), seed=123)
    strategy1 = solver1.train(1000)
    values1 = solver1.values()

    solver2 = MCCFRSolver(kuhn_root(), seed=123)
    strategy2 = solver2.train(1000)
    values2 = solver2.values()

    assert strategy1 == strategy2
    assert values1 == values2


def test_different_seeds_produce_different_output():
    """Different seeds should produce different intermediate strategies."""
    solver1 = MCCFRSolver(kuhn_root(), seed=100)
    strategy1 = solver1.train(50)

    solver2 = MCCFRSolver(kuhn_root(), seed=200)
    strategy2 = solver2.train(50)

    # Strategies should differ with different seeds at low iteration counts
    assert strategy1 != strategy2


# Predeclared seed matrix for Kuhn poker convergence tests
KUHN_SEED_MATRIX = [
    (42, 10000, 0.010, 0.10),
    (123, 10000, 0.010, 0.10),
    (999, 10000, 0.010, 0.10),
    (2024, 10000, 0.010, 0.10),
    (7777, 10000, 0.010, 0.10),
]


@pytest.mark.parametrize("seed,iterations,ev_tol,nashconv_tol", KUHN_SEED_MATRIX)
def test_kuhn_analytical_ev_and_nashconv(seed, iterations, ev_tol, nashconv_tol):
    """MCCFR should converge to analytical Kuhn value and low NashConv."""
    solver = MCCFRSolver(kuhn_root(), seed=seed)
    strategy = solver.train(iterations)
    value = expected_values(kuhn_root(), strategy)[0]
    nc = nash_conv(kuhn_root(), strategy).nash_conv

    assert value == pytest.approx(KUHN_VALUE_P0, abs=ev_tol)
    assert nc < nashconv_tol


def test_training_can_continue():
    """Training should be resumable and iteration count should accumulate."""
    solver = MCCFRSolver(kuhn_root(), seed=42)
    solver.train(10)
    assert solver.iterations == 10
    solver.train(10)
    assert solver.iterations == 20


def test_invalid_iterations_rejected():
    """Non-positive iterations should raise ValueError."""
    solver = MCCFRSolver(kuhn_root(), seed=42)
    with pytest.raises(ValueError):
        solver.train(0)
    with pytest.raises(ValueError):
        solver.train(-5)
    with pytest.raises(ValueError):
        solver.train(True)


def test_invalid_seed_rejected():
    """Non-integer seed should raise ValueError."""
    with pytest.raises(ValueError):
        MCCFRSolver(kuhn_root(), seed=3.14)
    with pytest.raises(ValueError):
        MCCFRSolver(kuhn_root(), seed="random")
    with pytest.raises(ValueError):
        MCCFRSolver(kuhn_root(), seed=True)


@pytest.mark.slow
def test_kuhn_convergence_high_iterations():
    """MCCFR should converge very close to Nash with many iterations."""
    solver = MCCFRSolver(kuhn_root(), seed=42)
    strategy = solver.train(50_000)
    value = expected_values(kuhn_root(), strategy)[0]
    nc = nash_conv(kuhn_root(), strategy).nash_conv

    assert value == pytest.approx(KUHN_VALUE_P0, abs=0.003)
    assert nc < 0.03
