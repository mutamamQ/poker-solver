"""Phase 2 determinism tests: serialization, hashing, and trajectory evidence.

Tests vanilla CFR and MCCFR determinism without brittle wall-clock timing.
Runtime performance tests are marked separately.
"""

import hashlib
import json

import pytest

from poker_solver.cfr import CFRSolver
from poker_solver.kuhn import kuhn_root
from poker_solver.mccfr import MCCFRSolver
from poker_solver.model import Action


def _serialize_strategy(strategy: dict) -> str:
    """Deterministic JSON serialization of a strategy."""
    # Convert Action objects to tuples for JSON serialization
    serializable = {}
    for key, policy in strategy.items():
        # Key is a tuple, policy is dict[Action, float]
        serializable[str(key)] = {
            f"{action.kind}:{action.amount}": prob
            for action, prob in sorted(policy.items(), key=lambda x: (x[0].kind, x[0].amount))
        }
    return json.dumps(serializable, sort_keys=True, separators=(',', ':'))


def _strategy_hash(strategy: dict) -> str:
    """Compute SHA256 hash of serialized strategy."""
    serialized = _serialize_strategy(strategy)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def test_vanilla_cfr_deterministic_serialization():
    """Vanilla CFR produces identical serialization across runs."""
    solver1 = CFRSolver(kuhn_root())
    strategy1 = solver1.train(100)
    hash1 = _strategy_hash(strategy1)

    solver2 = CFRSolver(kuhn_root())
    strategy2 = solver2.train(100)
    hash2 = _strategy_hash(strategy2)

    assert hash1 == hash2, "Vanilla CFR must be byte-identical across runs"
    assert strategy1 == strategy2, "Strategies must be equal"


def test_mccfr_same_seed_deterministic():
    """MCCFR with same seed produces identical output."""
    seed = 42
    solver1 = MCCFRSolver(kuhn_root(), seed=seed)
    strategy1 = solver1.train(500)
    hash1 = _strategy_hash(strategy1)

    solver2 = MCCFRSolver(kuhn_root(), seed=seed)
    strategy2 = solver2.train(500)
    hash2 = _strategy_hash(strategy2)

    assert hash1 == hash2, "MCCFR with same seed must be byte-identical"
    assert strategy1 == strategy2, "Strategies must be equal"


def test_mccfr_different_seed_diverges():
    """MCCFR with different seeds produces different trajectories."""
    solver1 = MCCFRSolver(kuhn_root(), seed=1)
    strategy1 = solver1.train(500)
    hash1 = _strategy_hash(strategy1)

    solver2 = MCCFRSolver(kuhn_root(), seed=2)
    strategy2 = solver2.train(500)
    hash2 = _strategy_hash(strategy2)

    # Different seeds should produce different strategies (with high probability)
    assert hash1 != hash2, "Different seeds should produce different trajectories"
    assert strategy1 != strategy2, "Strategies should differ"


def test_mccfr_seed_type_validation():
    """MCCFR rejects invalid seed types."""
    with pytest.raises(ValueError, match="seed must be an integer"):
        MCCFRSolver(kuhn_root(), seed=True)
    with pytest.raises(ValueError, match="seed must be an integer"):
        MCCFRSolver(kuhn_root(), seed=3.14)
    with pytest.raises(ValueError, match="seed must be an integer"):
        MCCFRSolver(kuhn_root(), seed="42")


def test_vanilla_cfr_regret_accumulation_deterministic():
    """Vanilla CFR internal regret state is deterministic."""
    solver1 = CFRSolver(kuhn_root())
    solver1.train(50)
    regrets1 = {key: dict(data.regrets) for key, data in solver1.infosets.items()}

    solver2 = CFRSolver(kuhn_root())
    solver2.train(50)
    regrets2 = {key: dict(data.regrets) for key, data in solver2.infosets.items()}

    assert regrets1 == regrets2, "Regret accumulation must be deterministic"


def test_mccfr_lazy_infoset_discovery_deterministic():
    """MCCFR lazy infoset discovery is deterministic with same seed."""
    seed = 123
    solver1 = MCCFRSolver(kuhn_root(), seed=seed)
    solver1.train(100)
    keys1 = set(solver1.infosets.keys())

    solver2 = MCCFRSolver(kuhn_root(), seed=seed)
    solver2.train(100)
    keys2 = set(solver2.infosets.keys())

    assert keys1 == keys2, "Lazy infoset discovery must be deterministic"


def test_serialization_roundtrip():
    """Serialized strategy can be parsed back."""
    solver = CFRSolver(kuhn_root())
    strategy = solver.train(50)
    serialized = _serialize_strategy(strategy)
    parsed = json.loads(serialized)
    assert isinstance(parsed, dict)
    assert len(parsed) > 0
