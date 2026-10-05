"""W5 repairs: C11 (3-max default solve quality), 3-max NashConv, C15 (pseudo-raise facing all-in).

Every number asserted here comes from a runtime solve; references are the repo's own
``nplayer.NPlayerCFRSolver`` and the solver-evaluation benchmark's independent n-player
oracle (``research/solver-evaluation/games.py``).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from math import isfinite
from pathlib import Path

import pytest

from poker_solver.model import Action
from poker_solver.multistreet import MultiStreetConfig, create_root as create_multistreet_root
from poker_solver.nplayer import NPlayerCFRSolver
from poker_solver.nplayer_preflop import create_nplayer_preflop_root
from poker_solver.practice.adapter import (
    CachedState,
    SolverAdapter,
    locate_decision,
    merge_pseudo_raises,
    preflop_config,
    pseudo_raise_aliases,
)
from poker_solver.practice.catalog import FAMILY_DEFAULT_SOLVE, generate_catalog
from poker_solver.practice.evaluate import action_values
from poker_solver.practice.models import SolveParams
from poker_solver.practice.nplayer_metrics import FlatNPlayerCFR, FlatTree, nash_conv_nplayer
from poker_solver.practice.scoring import score_play

ROOT = Path(__file__).resolve().parents[1]


def _games():
    path = ROOT / "research" / "solver-evaluation" / "games.py"
    spec = importlib.util.spec_from_file_location("solver_eval_games_w5", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def games():
    return _games()


def _three_max(index: int = 0):
    return generate_catalog(families=("preflop-3max-open",))[index]


def _preflop_root(spot):
    config = preflop_config(spot)
    return CachedState(create_nplayer_preflop_root(config)), config


# --------------------------------------------------------------------------- flat trainer


@pytest.mark.parametrize("family,index", [("preflop-3max-open", 0), ("preflop-3max-open", 5), ("preflop-hu-open", 0)])
def test_flat_trainer_is_bit_identical_to_nplayer_cfr(family, index):
    spot = generate_catalog(families=(family,))[index]
    root, config = _preflop_root(spot)
    reference = NPlayerCFRSolver(root, max_nodes=config.max_nodes).train(40)
    flat = FlatNPlayerCFR(FlatTree(root))
    flat.train(13)  # chunked training must not change anything
    profile = flat.train(27)
    assert flat._public not in (None, False)  # the deal-vector fast path was used
    assert profile == reference  # exact float equality, every infoset and action


def test_flat_trainer_generic_path_is_bit_identical(games):
    """Three-player Kuhn through the generic (non-public-tree) path."""
    root = games.Memo(games.ThreePlayerKuhn())
    reference = NPlayerCFRSolver(root).train(30)
    flat = FlatNPlayerCFR(FlatTree(root))
    flat._public = False  # force the generic per-node walk
    assert flat.train(30) == reference
    public = FlatNPlayerCFR(FlatTree(root))
    assert public.train(30) == reference


# --------------------------------------------------------------------------- n-player NashConv


def test_nash_conv_nplayer_matches_independent_oracle(games):
    spot = _three_max(5)
    root, config = _preflop_root(spot)
    profile = NPlayerCFRSolver(root, max_nodes=config.max_nodes).train(25)
    ours = nash_conv_nplayer(root, profile)
    oracle = games.nash_conv_n(root, profile, 3)
    assert abs(ours.nash_conv - oracle["nash_conv"]) <= 1e-12
    for a, b in zip(ours.incentives, oracle["incentives"]):
        assert abs(a - b) <= 1e-12 and a >= -1e-12
    # Three-player Kuhn: analytic-family game, NashConv decreases with training.
    kuhn = games.Memo(games.ThreePlayerKuhn())
    solver = NPlayerCFRSolver(kuhn)
    early = nash_conv_nplayer(kuhn, solver.train(50)).nash_conv
    late = nash_conv_nplayer(kuhn, solver.train(950)).nash_conv
    assert abs(late - games.nash_conv_n(kuhn, solver.average_strategy(), 3)["nash_conv"]) <= 1e-12
    assert 0 <= late < early


def test_3max_provenance_reports_finite_runtime_nash_conv(games):
    spot = _three_max(1).with_solve(SolveParams(iterations=60))
    solved = SolverAdapter(cache={}).solve(spot)
    conv = solved.provenance.nash_conv
    assert conv is not None and isfinite(conv) and conv > 0
    assert solved.provenance.to_json()["nash_conv"] == conv  # JSON shape unchanged (a number)
    root, config = _preflop_root(spot)
    profile = NPlayerCFRSolver(root, max_nodes=config.max_nodes).train(60)
    assert abs(games.nash_conv_n(root, profile, 3)["nash_conv"] - conv) <= 1e-12
    # R1: the reported metric is a runtime quantity that moves with the solve.
    more = SolverAdapter(cache={}).solve(spot.with_solve(SolveParams(iterations=240)))
    assert more.provenance.nash_conv < conv


# --------------------------------------------------------------------------- C11 default quality


def test_3max_default_budget_and_quality():
    assert FAMILY_DEFAULT_SOLVE["preflop-3max-open"].iterations == 5000
    spot = _three_max(0)
    assert spot.solve == FAMILY_DEFAULT_SOLVE["preflop-3max-open"]
    solved = SolverAdapter(cache={}, timeout_s=300).solve(spot)
    pct = 100.0 * solved.provenance.nash_conv / 3 / spot.pot
    assert pct < 1.0, pct  # C11 PASS threshold (benchmark: (NashConv / n) / pot)


def test_legacy_spot_ids_unchanged():
    import hashlib
    legacy = generate_catalog(families=("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet"))
    assert len(legacy) == 36
    digest = hashlib.sha256("\n".join(s.spot_id for s in legacy).encode()).hexdigest()
    hashes = hashlib.sha256("\n".join(s.params_hash() for s in legacy).encode()).hexdigest()
    assert digest == "7b5b710061471cede0dcc1f2794b41b3525868c35b52eaaffcd6810c82f2ca23"
    assert hashes == "5d6ec1eb111b2acb0ed9ae3af00cef6b71b16aee7780f334dc09aabc0ef51ac8"


# --------------------------------------------------------------------------- C15 pseudo-raise


def test_pseudo_raise_helpers():
    actions = (Action("FOLD"), Action("CALL", 200), Action("RAISE", 200))
    aliases = pseudo_raise_aliases(actions)
    assert aliases == {Action("RAISE", 200): Action("CALL", 200)}
    merged = merge_pseudo_raises({actions[0]: 0.2, actions[1]: 0.5, actions[2]: 0.3}, aliases)
    assert merged == {actions[0]: 0.2, actions[1]: 0.8}
    assert pseudo_raise_aliases((Action("CHECK"), Action("RAISE", 75))) == {}
    assert pseudo_raise_aliases((Action("FOLD"), Action("CALL", 75), Action("RAISE", 200))) == {}


def _facing_all_in_spot():
    """turn-barrel spot where villain shoves the whole stack and hero (seat 0) must respond."""
    base = next(s for s in generate_catalog(families=("turn-barrel",)) if s.hero_seat == 0)
    stack = base.stacks[0]
    return dataclasses.replace(
        base,
        bet_sizes=(stack,),
        action_history=(Action("CHECK"), Action("RAISE", stack)),
        solve=SolveParams(iterations=40),
    )


def _multistreet_root(spot):
    extra = spot.backend_extra
    config = MultiStreetConfig(
        "multistreet-v1", "turn", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
        extra["allowed_runouts"], extra["betting_mode"], spot.bet_sizes, river_betting=True,
    )
    return CachedState(create_multistreet_root(config))


def test_facing_all_in_user_sees_call_not_pseudo_raise():
    spot = _facing_all_in_spot()
    stack = spot.stacks[0]
    root = _multistreet_root(spot)
    raw = locate_decision(root, spot, spot.hero_hand, spot.backend)
    # The game tree itself still has the degenerate RAISE(target == call target) ...
    assert Action("RAISE", stack) in raw.legal_actions and Action("CALL", stack) in raw.legal_actions
    solved = SolverAdapter(cache={}).solve(spot)
    # ... but the user is only offered truthful actions.
    assert solved.legal_actions == (Action("FOLD"), Action("CALL", stack))
    assert not any(a.kind == "RAISE" for a in solved.legal_actions)
    for policy in solved.range_strategy.values():
        assert set(policy) == set(solved.legal_actions)
    # Solver values are untouched: CALL's Q equals the raw solve's CALL (and pseudo-raise) Q,
    # and the merged probability is the raw CALL + pseudo-raise probability.
    from poker_solver.cfr import CFRSolver
    profile = CFRSolver(root).train(spot.solve.iterations)
    q, _ = action_values(root, profile, 0, raw.info_key)
    assert q[Action("CALL", stack)] == solved.action_values[Action("CALL", stack)]
    assert abs(q[Action("RAISE", stack)] - q[Action("CALL", stack)]) <= 1e-9
    assert q[Action("FOLD")] == solved.action_values[Action("FOLD")]
    raw_policy = profile[raw.info_key]
    assert abs(solved.strategy[Action("CALL", stack)]
               - (raw_policy[Action("CALL", stack)] + raw_policy[Action("RAISE", stack)])) <= 1e-12
    # The provenance NashConv is the solver's own (computed on the unmodified tree).
    from poker_solver.best_response import nash_conv
    assert solved.provenance.nash_conv == nash_conv(root, profile).nash_conv
    # A user trying to "raise" all-in is not scored as a raise: there is no raise to pick.
    with pytest.raises(ValueError):
        score_play(solved, {"kind": "RAISE", "amount": stack})
    assert score_play(solved, {"kind": "CALL", "amount": stack}).chosen_q == solved.action_values[Action("CALL", stack)]


def test_catalog_hero_decisions_never_offer_pseudo_raise():
    """No catalog spot (multistreet / allstreet) exposes a RAISE equal to the call target."""
    adapter = SolverAdapter(cache={})
    for family in ("flop-cbet", "turn-barrel"):
        for spot in generate_catalog(families=(family,)):
            solved = adapter.solve(spot.with_solve(SolveParams(iterations=2)))
            assert pseudo_raise_aliases(solved.legal_actions) == {}


# --------------------------------------------------------------------------- F3 independent Q


def _independent_profile(spot, games):
    """Rebuild the solver game from the spot (benchmark-owned Memo) and train the repo solver."""
    from poker_solver.allstreet import AllStreetPostflopConfig, create_allstreet_root
    from poker_solver.api import complete_strategy
    from poker_solver.cfr import CFRSolver
    extra = spot.backend_extra
    if spot.backend == "nplayer-preflop":
        config = preflop_config(spot)
        root = games.Memo(create_nplayer_preflop_root(config))
        return root, NPlayerCFRSolver(root, max_nodes=config.max_nodes).train(spot.solve.iterations)
    if spot.backend == "allstreet":
        config = AllStreetPostflopConfig(
            "allstreet-postflop-v1", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
            extra["allowed_runouts"], extra["betting_mode"], spot.bet_sizes, extra["max_nodes"], extra["max_depth"],
        )
        root = games.Memo(create_allstreet_root(config))
    else:
        config = MultiStreetConfig(
            "multistreet-v1", "turn", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
            extra["allowed_runouts"], extra["betting_mode"], spot.bet_sizes, river_betting=True,
        )
        root = games.Memo(create_multistreet_root(config))
    return root, complete_strategy(root, CFRSolver(root).train(spot.solve.iterations))


def _hero_key(root, spot):
    for deal, p in root.chance_outcomes():
        state = root.child(deal)
        if p > 0 and tuple(sorted(state.private_deal[spot.hero_seat])) == spot.hero_hand:
            for action in spot.action_history:
                state = state.child(action)
            return state.information_state_key(spot.hero_seat)
    raise AssertionError("hero hand reaches no deal")


@pytest.mark.parametrize("family,iterations,index", [
    ("preflop-hu-open", 60, 0), ("preflop-hu-open", 60, 7),
    ("flop-cbet", 30, 0), ("flop-cbet", 30, 5),
    ("turn-barrel", 40, 0), ("turn-barrel", 40, 6),
])
def test_hero_q_values_match_independent_recompute(games, family, iterations, index):
    """Q, strategy and optimal action re-derived without practice.evaluate / CachedState.

    A mutant that fakes Q (e.g. 0 for the strategy argmax, -1 elsewhere) fails here.
    """
    spot = generate_catalog(families=(family,))[index].with_solve(SolveParams(iterations=iterations))
    solved = SolverAdapter(cache={}).solve(spot)
    root, profile = _independent_profile(spot, games)
    key = _hero_key(root, spot)
    q, mass = games.independent_action_values(root, profile, spot.hero_seat, key)
    assert mass > 0
    assert set(q) == set(solved.legal_actions)  # no pseudo-raises at catalog nodes
    for action in solved.legal_actions:
        assert abs(q[action] - solved.action_values[action]) <= 1e-9, (action, q[action], solved.action_values[action])
        assert abs(profile[key][action] - solved.strategy[action]) <= 1e-12
    support = [a for a in solved.legal_actions if solved.strategy[a] > 0]
    assert q[solved.optimal_action] >= max(q[a] for a in support) - 1e-9
    # Q is not degenerate: the spread is a real runtime quantity.
    assert max(q.values()) - min(q.values()) > 1e-6


# --------------------------------------------------------------------------- F4 optimal action


def test_optimal_action_is_highest_q_within_support():
    from poker_solver.practice.adapter import optimal_action
    actions = (Action("FOLD"), Action("CALL", 2), Action("RAISE", 5), Action("RAISE", 30))
    strategy = {actions[0]: 0.2302, actions[1]: 0.571, actions[2]: 0.0012, actions[3]: 0.1975}
    q = {actions[0]: -1.0, actions[1]: -1.043, actions[2]: -1.1953, actions[3]: -1.1128}
    assert optimal_action(actions, strategy, q) == Action("FOLD")  # audit F4 example
    # An unplayed action is never "optimal", even with the highest Q.
    strategy2 = {actions[0]: 0.0, actions[1]: 1.0, actions[2]: 0.0, actions[3]: 0.0}
    assert optimal_action(actions, strategy2, q) == Action("CALL", 2)
    # Equal Q: the higher-probability action wins.
    flat = {a: 0.0 for a in actions}
    assert optimal_action(actions, strategy, flat) == Action("CALL", 2)


def test_optimal_action_scores_perfect_on_real_solve():
    spot = generate_catalog(families=("preflop-hu-open",))[0].with_solve(SolveParams(iterations=60))
    solved = SolverAdapter(cache={}).solve(spot)
    opt = solved.optimal_action
    support = [a for a in solved.legal_actions if solved.strategy[a] > 0]
    best_supported = max(solved.action_values[a] for a in support)
    assert solved.action_values[opt] == best_supported
    score = score_play(solved, {"kind": opt.kind, "amount": opt.amount})
    assert score.ev_loss_chips == pytest.approx(max(solved.action_values.values()) - solved.action_values[opt])


# --------------------------------------------------------------------------- F6 MCCFR budget


def test_mccfr_allstreet_respects_budget_during_training():
    import time
    spot = generate_catalog(families=("flop-cbet",))[0].with_solve(
        SolveParams(algorithm="external-sampling-mccfr", iterations=20_000, seed=1)
    )
    start = time.perf_counter()
    with pytest.raises(ValueError, match="budget"):
        SolverAdapter(cache={}, timeout_s=1.0).solve(spot)
    assert time.perf_counter() - start < 8.0  # unchunked training ran ~10x longer


def test_mccfr_chunked_equals_single_block():
    from poker_solver.allstreet import AllStreetPostflopConfig, create_allstreet_root
    from poker_solver.api import complete_strategy
    from poker_solver.mccfr import MCCFRSolver
    spot = generate_catalog(families=("flop-cbet",))[0].with_solve(
        SolveParams(algorithm="external-sampling-mccfr", iterations=60, seed=3)
    )
    solved = SolverAdapter(cache={}).solve(spot)
    ex = spot.backend_extra
    config = AllStreetPostflopConfig(
        "allstreet-postflop-v1", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
        ex["allowed_runouts"], ex["betting_mode"], spot.bet_sizes, ex["max_nodes"], ex["max_depth"],
    )
    root = CachedState(create_allstreet_root(config))
    profile = complete_strategy(root, MCCFRSolver(root, 3).train(60))
    key = locate_decision(root, spot, spot.hero_hand, spot.backend).info_key
    assert {a: profile[key][a] for a in solved.legal_actions} == dict(solved.strategy)


# --------------------------------------------------------------------------- F7 single flight


def test_concurrent_cold_solves_are_single_flight():
    import threading
    spot = generate_catalog(families=("turn-barrel",))[1].with_solve(SolveParams(iterations=30))
    adapter = SolverAdapter(cache={})
    results, errors = [], []
    barrier = threading.Barrier(4)

    def worker():
        barrier.wait()
        try:
            results.append(adapter.solve(spot))
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert adapter.solve_count == 1
    assert len(results) == 4 and all(r is results[0] for r in results)
    assert adapter._inflight == {}


def test_single_flight_failure_lets_next_request_solve():
    spot = generate_catalog(families=("turn-barrel",))[1].with_solve(SolveParams(iterations=30))
    adapter = SolverAdapter(cache={}, timeout_s=1e-9)
    with pytest.raises(ValueError):
        adapter.solve(spot)
    assert adapter._inflight == {} and adapter.solve_count == 0
    adapter.timeout_s = 300.0
    assert adapter.solve(spot).spot == spot and adapter.solve_count == 1
