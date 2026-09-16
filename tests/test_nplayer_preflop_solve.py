"""Permanent S3-I2 facade contracts with independently exercised tiny fixtures."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from itertools import product
from math import isfinite, prod

import pytest

from poker_solver.game_structure import ForcedPost
from poker_solver.model import CHANCE, TERMINAL
from poker_solver.nplayer import NPlayerCFRSolver
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig, NPlayerPreflopContinuation,
    create_nplayer_preflop_root, enumerate_nplayer_preflop_deals,
)
from poker_solver.preflop import WeightedCombo


def _config(n, *, weighted=False, max_raises=1):
    # All seats participate in settlement; only the two blind seats retain chips.
    # Uniform antes make the six-player exhaustive oracle genuinely tractable.
    sb, bb = (0, 1) if n == 2 else (1, 2)
    deal = tuple((2 * seat, 2 * seat + 1) for seat in range(n))
    ranges = [(WeightedCombo(cards, 1),) for cards in deal]
    ranks = {deal: tuple(range(n, 0, -1))}
    if weighted:
        ranges[0] += (WeightedCombo((40, 41), 3),)
        ranks[((40, 41),) + deal[1:]] = tuple(range(1, n + 1))
    return NPlayerPreflopConfig(
        version="nplayer-preflop-v1", num_players=n, button=0,
        starting_stacks=tuple(3 if seat in (sb, bb) else 1 for seat in range(n)),
        forced_posts=tuple(ForcedPost(seat, "ante", 1) for seat in range(n)) + (
            ForcedPost(sb, "small-blind", 1), ForcedPost(bb, "big-blind", 1)),
        straddle_variant="none", ranges=tuple(ranges), sizing_rules=(),
        max_raises=max_raises, max_deals=2 if weighted else 1, max_nodes=100,
        short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(
            kind="showdown-ranks", provenance="declared tiny synthetic ranks",
            source="supplied", payoff_table={}, showdown_ranks=ranks,
            odd_chip_order=tuple(range(n))),
    )


def _solve(config, **kwargs):
    from poker_solver.nplayer_preflop import solve_nplayer_preflop
    kwargs.setdefault("algorithm", "vanilla-cfr")
    return solve_nplayer_preflop(config, **kwargs)


def _tree(config):
    root = create_nplayer_preflop_root(config)
    nodes, infosets = [], {}

    def visit(state, depth):
        nodes.append((state, depth))
        assert len(nodes) <= config.max_nodes
        assert state.pot == sum(state.total_contributed)
        assert tuple(a + b for a, b in zip(state.remaining, state.total_contributed)) == config.starting_stacks
        player = state.current_player()
        if player == TERMINAL:
            assert len(state.terminal_values) == config.num_players
            assert sum(state.terminal_values, Fraction()) == 0
            return
        if player == CHANCE:
            edges = tuple(action for action, _ in state.chance_outcomes())
        else:
            edges = state.legal_actions()
            key = state.information_state_key(player)
            assert infosets.setdefault(key, (player, edges)) == (player, edges)
        assert edges
        for action in edges:
            visit(state.child(action), depth + 1)

    visit(root, 0)
    assert any(state.current_player() == TERMINAL for state, _ in nodes)
    return root, nodes, infosets


def _values(state, strategy):
    """Independent full-tree expectation; no production EV/certificate helpers."""
    actor = state.current_player()
    if actor == TERMINAL:
        return state.terminal_values
    edges = (state.chance_outcomes() if actor == CHANCE else
             strategy[state.information_state_key(actor)].items())
    total = [Fraction() for _ in range(state.num_players())]
    for action, probability in edges:
        for seat, value in enumerate(_values(state.child(action), strategy)):
            total[seat] += Fraction(probability) * value
    return tuple(total)


def _oracle(root, infosets, strategy):
    baseline = _values(root, strategy)
    best, counts = [], []
    for player in range(root.num_players()):
        owned = [(key, actions) for key, (seat, actions) in infosets.items() if seat == player]
        count = prod(len(actions) for _, actions in owned)
        assert count <= 64  # Proven before any potentially explosive enumeration.
        counts.append(count)
        candidates = []
        for choices in product(*(actions for _, actions in owned)):
            deviated = dict(strategy)
            for (key, actions), choice in zip(owned, choices, strict=True):
                deviated[key] = {action: Fraction(action == choice) for action in actions}
            candidates.append(_values(root, deviated)[player])
        best.append(max(candidates))
    incentives = tuple(max(Fraction(), best[i] - baseline[i]) for i in range(root.num_players()))
    return baseline, tuple(best), incentives, tuple(counts)


@pytest.mark.parametrize("n", [2, 6, 9])
@pytest.mark.parametrize("weighted,max_raises", [(False, 1), (True, 1), (False, 2)])
def test_fixtures_construct_and_traverse_without_facade(n, weighted, max_raises):
    config = _config(n, weighted=weighted, max_raises=max_raises)
    root, nodes, infosets = _tree(config)
    deals = enumerate_nplayer_preflop_deals(config)
    assert set(dict(deals)) == set(config.continuation.showdown_ranks)
    assert tuple(mass for _, mass in deals) == ((Fraction(1, 4), Fraction(3, 4)) if weighted else (Fraction(1),))
    assert root.chance_outcomes() == create_nplayer_preflop_root(config).chance_outcomes()
    assert sum(mass for _, mass in root.chance_outcomes()) == 1
    depth = 2 + n + max_raises * (n - 1)
    assert max(d for _, d in nodes) <= depth
    solver = NPlayerCFRSolver(root, max_nodes=config.max_nodes, max_depth=depth)
    strategy = solver.train(1)
    assert set(strategy) == set(infosets)
    assert sum(_values(root, strategy)) == 0


def test_six_player_oracle_runs_independently_before_facade():
    root, _, infosets = _tree(_config(6))
    uniform = {key: {a: 1.0 / len(actions) for a in actions}
               for key, (_, actions) in infosets.items()}
    baseline, best, incentives, counts = _oracle(root, infosets, uniform)
    assert sum(baseline) == 0
    assert max(counts) > 1
    assert all(b >= v for b, v in zip(best, baseline))
    assert counts == (1, 4, 4, 1, 1, 1)
    assert baseline == (5, Fraction(1, 8), Fraction(-17, 8), -1, -1, -1)
    assert incentives == (0, Fraction(3, 8), Fraction(3, 8), 0, 0, 0)
    # Compare production to the independent enumeration, never use it as oracle.
    from poker_solver.nplayer import unilateral_deviation_certificate
    certificate = unilateral_deviation_certificate(root, uniform, max_pure_strategies=4)
    assert certificate.values == pytest.approx(baseline, abs=1e-12)
    assert certificate.best_response_values == pytest.approx(best, abs=1e-12)
    assert certificate.incentives == pytest.approx(incentives, abs=1e-12)
    assert certificate.total_incentive == pytest.approx(sum(incentives), abs=1e-12)
    with pytest.raises(ValueError, match="pure-strategy bound exceeded"):
        unilateral_deviation_certificate(root, uniform, max_pure_strategies=3)


def test_result_type_exists():
    from poker_solver.nplayer_preflop import NPlayerPreflopSolveResult
    assert NPlayerPreflopSolveResult.__module__ == "poker_solver.nplayer_preflop"


@pytest.mark.parametrize("algorithm", ["unknown", "cfr+", "", None, True, 1])
def test_strict_algorithm(algorithm):
    config = _config(2)
    with pytest.raises(ValueError, match="algorithm"):
        _solve(config, algorithm=algorithm, iterations=1)


@pytest.mark.parametrize("iterations", [0, -1, True, False, 1.5, "1", None])
def test_strict_iterations(iterations):
    config = _config(2)
    with pytest.raises(ValueError, match="iterations"):
        _solve(config, iterations=iterations)


@pytest.mark.parametrize("include", [0, 1, "true", None])
def test_strict_include_certificate(include):
    config = _config(2)
    with pytest.raises(ValueError, match="include_deviation_certificate"):
        _solve(config, iterations=1, include_deviation_certificate=include)


@pytest.mark.parametrize("cap", [0, -1, True, False, 1.5, "1", None])
@pytest.mark.parametrize("include", [False, True])
def test_strict_pure_cap_even_when_not_requested(cap, include):
    config = _config(2)
    with pytest.raises(ValueError, match="max_pure_strategies"):
        _solve(config, iterations=1, include_deviation_certificate=include, max_pure_strategies=cap)


@pytest.mark.parametrize("n", [2, 6, 9])
def test_solve_deterministic_finite_immutable_result(n):
    config = _config(n, weighted=True)
    root, _, infosets = _tree(config)
    first = _solve(config, iterations=3)
    second = _solve(config, iterations=3)
    from poker_solver.nplayer_preflop import NPlayerPreflopSolveResult
    assert isinstance(first, NPlayerPreflopSolveResult)
    assert first.strategy == second.strategy
    assert first.expected_values == second.expected_values
    assert first.metadata == second.metadata
    assert first.certificate is None
    assert first.algorithm == "vanilla-cfr" and first.iterations == 3
    assert first.config_version == 4 and first.game_version == config.version
    assert first.max_nodes == config.max_nodes
    assert first.max_depth == 2 + n + config.max_raises * (n - 1)
    assert first.metadata["converged"] is False
    assert first.metadata["convergence_claim"] == "none"
    assert first.metadata["deterministic"] is True
    assert first.provenance
    assert len(first.expected_values) == n
    assert all(isfinite(v) for v in first.expected_values)
    assert sum(first.expected_values) == pytest.approx(0, abs=1e-12)
    assert first.expected_values == pytest.approx(_values(root, first.strategy), abs=1e-12)
    assert set(first.strategy) == set(infosets)
    for key, policy in first.strategy.items():
        assert set(policy) == set(infosets[key][1])
        assert all(isfinite(p) and 0 <= p <= 1 for p in policy.values())
        assert sum(policy.values()) == pytest.approx(1, abs=1e-12)
    key = next(iter(first.strategy))
    action = next(iter(first.strategy[key]))
    with pytest.raises(TypeError):
        first.strategy[key][action] = 0
    with pytest.raises(TypeError):
        first.strategy[key] = {}
    with pytest.raises(TypeError):
        first.metadata["converged"] = True
    with pytest.raises(FrozenInstanceError):
        first.iterations = 99
    # Public result construction must detach caller-owned outer AND inner maps.
    source = {k: dict(p) for k, p in first.strategy.items()}
    metadata = {"nested": {"flags": [False]}}
    detached = replace(first, strategy=source, metadata=metadata)
    source[key][action] = -99
    source.clear()
    metadata["nested"]["flags"].append(True)
    assert detached.strategy == second.strategy
    assert tuple(detached.metadata["nested"]["flags"]) == (False,)
    with pytest.raises(TypeError):
        detached.metadata["nested"]["new"] = True
    assert _solve(config, iterations=3).strategy == second.strategy


@pytest.mark.parametrize("n", [2, 6, 9])
def test_exact_structural_depth(n):
    config = _config(n, max_raises=2)
    assert _solve(config, iterations=1).max_depth == 2 + n + 2 * (n - 1)


def test_direct_solver_bounds():
    root, _, _ = _tree(_config(2))
    with pytest.raises(ValueError, match="node bound"):
        NPlayerCFRSolver(root, max_nodes=1, max_depth=100)
    with pytest.raises(ValueError, match="depth bound"):
        NPlayerCFRSolver(root, max_nodes=100, max_depth=1)


def test_facade_forwards_node_bound():
    config = replace(_config(2), max_nodes=2)
    create_nplayer_preflop_root(config)
    with pytest.raises(ValueError, match="node bound"):
        _solve(config, iterations=1)


def test_six_player_exhaustive_certificate_and_exact_cap():
    config = _config(6)
    root, _, infosets = _tree(config)
    cap = max(prod(len(actions) for owner, actions in infosets.values() if owner == seat)
              for seat in range(6))
    assert 1 < cap <= 64
    first = _solve(config, iterations=3, include_deviation_certificate=True, max_pure_strategies=cap)
    second = _solve(config, iterations=3, include_deviation_certificate=True, max_pure_strategies=cap)
    baseline, best, incentives, _ = _oracle(root, infosets, first.strategy)
    cert = first.certificate
    assert cert is not None and cert == second.certificate
    assert cert.values == pytest.approx(baseline, abs=1e-12)
    assert cert.best_response_values == pytest.approx(best, abs=1e-12)
    assert cert.incentives == pytest.approx(incentives, abs=1e-12)
    assert cert.total_incentive == pytest.approx(sum(incentives), abs=1e-12)
    assert cert.provenance == "exhaustive finite pure unilateral deviations; diagnostic only"
    with pytest.raises(ValueError, match="pure-strategy bound exceeded"):
        _solve(config, iterations=1, include_deviation_certificate=True, max_pure_strategies=cap - 1)


def test_certificate_cap_fails_closed():
    config = _config(6)
    with pytest.raises(ValueError, match="pure-strategy bound exceeded"):
        _solve(config, iterations=1, include_deviation_certificate=True, max_pure_strategies=1)
