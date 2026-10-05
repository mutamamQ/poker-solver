"""Tests for practice scoring (EV loss vs the solver optimum).

Pure-function tests use synthetic Q mappings built from arithmetic (design 01 T7);
real-solve tests use the production catalog + adapter on Kuhn spots. No literal
strategy tables: expected values are re-derived from the solved Q/sigma* fields.
"""

from __future__ import annotations

import json
import math

import pytest

from poker_solver.model import Action
from poker_solver.practice.scoring import (
    EPS_SPREAD,
    GRADE_THRESHOLDS,
    ParsedPlay,
    grade_for,
    parse_play,
    score_distribution,
    score_play,
)

CHECK, BET_SMALL, BET_BIG, FOLD, CALL = (
    Action("check"), Action("bet", 10), Action("bet", 20), Action("fold"), Action("call"))
LEGAL = (CHECK, BET_SMALL, BET_BIG)


def _q(base: float = 0.0) -> dict[Action, float]:
    # Synthetic, strictly ordered Q values (arithmetic, not a strategy table).
    return {a: base + i for i, a in enumerate(LEGAL)}


def _uniform() -> dict[Action, float]:
    return {a: 1.0 / len(LEGAL) for a in LEGAL}


def _score(play_obj, q=None, sigma=None, pot=40.0):
    q = _q() if q is None else q
    sigma = _uniform() if sigma is None else sigma
    return score_distribution(q, sigma, pot, parse_play(play_obj, LEGAL), LEGAL)


# --------------------------------------------------------------------------- grades


@pytest.mark.parametrize("bound,grade", GRADE_THRESHOLDS)
def test_grade_boundaries_inclusive(bound, grade):
    assert grade_for(bound) == grade
    next_index = [g for _, g in GRADE_THRESHOLDS].index(grade) + 1
    expected_next = (GRADE_THRESHOLDS[next_index][1]
                     if next_index < len(GRADE_THRESHOLDS) else "Blunder")
    assert grade_for(bound + 1e-4) == expected_next


def test_grade_extremes_and_validation():
    assert grade_for(0) == "Perfect"
    assert grade_for(1e6) == "Blunder"
    for bad in (-0.1, math.nan, math.inf, True, "1"):
        with pytest.raises(ValueError):
            grade_for(bad)


# --------------------------------------------------------------------------- formulas


def test_formulas_pure():
    q = _q()
    s = _score({"kind": "check"}, q=q)
    best, worst = max(q.values()), min(q.values())
    assert s.best_q == best and s.worst_q == worst
    assert s.chosen_q == q[CHECK]
    assert s.ev_loss_chips == best - q[CHECK]
    assert s.ev_loss_pct_pot == pytest.approx(100 * (best - q[CHECK]) / 40.0)
    assert s.score == 0.0  # worst action
    assert s.best_action == BET_BIG
    assert s.solver_mix_q == pytest.approx(sum(q.values()) / len(q))
    assert s.solver_self_loss == pytest.approx(best - s.solver_mix_q)
    top = _score({"kind": "bet", "amount": 20}, q=q)
    assert top.ev_loss_chips == 0.0 and top.score == 100.0 and top.grade == "Perfect"


def test_all_equal_q_scores_100_and_single_action():
    q = {a: 1.5 for a in LEGAL}
    s = _score({"kind": "check"}, q=q)
    assert s.score == 100.0 and s.ev_loss_chips == 0.0 and s.grade == "Perfect"
    single = score_distribution({FOLD: -1.0}, {FOLD: 1.0}, 2.0,
                                parse_play({"kind": "fold"}, (FOLD,)), (FOLD,))
    assert single.score == 100.0 and single.ev_loss_chips == 0.0
    assert EPS_SPREAD == 1e-12


def test_mix_linearity():
    q = _q()
    pures = {a: _score({"kind": a.kind, "amount": a.amount}, q=q) for a in LEGAL}
    probs = {CHECK: 0.2, BET_SMALL: 0.3, BET_BIG: 0.5}
    mix = _score({"mix": [{"action": {"kind": a.kind, "amount": a.amount},
                           "probability": p} for a, p in probs.items()]}, q=q)
    assert mix.ev_loss_chips == pytest.approx(
        sum(p * pures[a].ev_loss_chips for a, p in probs.items()), abs=1e-12)
    assert mix.score == pytest.approx(
        sum(p * pures[a].score for a, p in probs.items()), abs=1e-9)
    assert mix.chosen_q == pytest.approx(sum(p * q[a] for a, p in probs.items()))
    assert mix.mapped_action is None and not mix.size_mapped


def test_feedback_is_pure_function_of_numbers():
    a = _score({"kind": "check"})
    b = _score({"kind": "check"})
    assert a.feedback == b.feedback
    assert f"{a.ev_loss_chips:.3f}" in a.feedback and a.grade in a.feedback
    assert f"{a.ev_loss_pct_pot:.2f}% pot" in a.feedback
    c = _score({"kind": "check"}, q=_q(base=5.0), sigma={CHECK: 1.0, BET_SMALL: 0.0,
                                                        BET_BIG: 0.0})
    assert c.feedback != a.feedback


def test_to_json_is_strict_json():
    s = _score({"kind": "bet", "amount": 13})
    data = s.to_json()
    json.dumps(data, allow_nan=False)
    assert data["mapped_action"] == {"kind": "bet", "amount": 10}
    assert data["size_mapped"] is True
    assert data["play"] == {"kind": "bet", "amount": 10}


# --------------------------------------------------------------------------- snapping


def test_off_tree_snapping_nearest_and_tie_smaller():
    tie = parse_play({"kind": "bet", "amount": 15}, LEGAL)
    assert tie.mapped_action == BET_SMALL and tie.size_mapped
    big = parse_play({"kind": "bet", "amount": 1000}, LEGAL)
    assert big.mapped_action == BET_BIG
    exact = parse_play({"kind": "bet", "amount": 20}, LEGAL)
    assert exact.mapped_action is None and not exact.size_mapped
    s = _score({"kind": "bet", "amount": 15})
    assert s.chosen_q == _q()[BET_SMALL] and s.size_mapped and s.mapped_action == BET_SMALL


def test_snapped_mix_entries_merge():
    p = parse_play({"mix": [{"action": {"kind": "bet", "amount": 10}, "probability": 0.5},
                            {"action": {"kind": "bet", "amount": 11}, "probability": 0.5}]},
                   LEGAL)
    assert dict(p.distribution) == {BET_SMALL: 1.0}
    assert p.size_mapped and p.mapped_action is None
    assert p.mappings == ((Action("bet", 11), BET_SMALL),)


def test_sized_request_on_unsized_node_rejected():
    with pytest.raises(ValueError):
        parse_play({"kind": "call", "amount": 5}, (FOLD, CALL))
    with pytest.raises(ValueError):
        parse_play({"kind": "raise", "amount": 5}, (FOLD, CALL))
    assert parse_play({"kind": "call"}, (FOLD, CALL)).distribution == {CALL: 1.0}
    with pytest.raises(ValueError):  # ambiguous: two bet sizes, no amount
        parse_play({"kind": "bet"}, LEGAL)


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize("bad", [
    None, [], "check", {"kind": ""}, {"kind": 3}, {"kind": "check", "amount": True},
    {"kind": "check", "amount": -1}, {"kind": "check", "amount": 1.0},
    {"kind": "check", "extra": 1}, {"amount": 0}, {"kind": "jam"},
    {"mix": []}, {"mix": "x"}, {"mix": [{"action": {"kind": "check", "amount": 0},
                                          "probability": 1.0}], "kind": "check"},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 0.6},
             {"action": {"kind": "bet", "amount": 10}, "probability": 0.5}]},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 0.5},
             {"action": {"kind": "check", "amount": 0}, "probability": 0.5}]},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": True}]},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": math.nan}]},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 1.5},
             {"action": {"kind": "bet", "amount": 10}, "probability": -0.5}]},
    {"mix": [{"action": {"kind": "check"}, "probability": 1.0}]},
    {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 1.0, "x": 1}]},
])
def test_parse_play_rejects(bad):
    with pytest.raises(ValueError):
        parse_play(bad, LEGAL)


def test_probability_tolerance():
    ok = {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 0.5},
                  {"action": {"kind": "bet", "amount": 10}, "probability": 0.5 + 5e-10}]}
    parse_play(ok, LEGAL)
    bad = {"mix": [{"action": {"kind": "check", "amount": 0}, "probability": 0.5},
                   {"action": {"kind": "bet", "amount": 10}, "probability": 0.5 + 1e-8}]}
    with pytest.raises(ValueError):
        parse_play(bad, LEGAL)


def test_score_distribution_rejects_bad_inputs():
    play = parse_play({"kind": "check"}, LEGAL)
    with pytest.raises(ValueError):
        score_distribution(_q(), _uniform(), 0.0, play, LEGAL)
    with pytest.raises(ValueError):
        score_distribution({CHECK: 0.0}, _uniform(), 1.0, play, LEGAL)
    with pytest.raises(ValueError):
        score_distribution({**_q(), CHECK: math.nan}, _uniform(), 1.0, play, LEGAL)
    with pytest.raises(ValueError):
        score_distribution(_q(), {CHECK: 0.9, BET_SMALL: 0.0, BET_BIG: 0.0}, 1.0, play,
                           LEGAL)
    with pytest.raises(ValueError):
        score_distribution(_q(), _uniform(), 1.0, {"kind": "check"}, LEGAL)
    assert isinstance(play, ParsedPlay)


# --------------------------------------------------------------------------- real solves


def _kuhn_solved(iterations: int):
    from poker_solver.practice.adapter import SolverAdapter
    from poker_solver.practice.catalog import generate_catalog
    from poker_solver.practice.models import SolveParams

    spots = [s for s in generate_catalog(solve=SolveParams(iterations=iterations))
             if s.backend == "kuhn"]
    assert spots, "catalog must provide kuhn spots"
    adapter = SolverAdapter()
    return [adapter.solve(spot) for spot in spots]


@pytest.fixture(scope="module")
def kuhn_2000():
    return _kuhn_solved(2000)


def test_real_solve_best_action_is_perfect(kuhn_2000):
    for solved in kuhn_2000:
        q = solved.action_values
        best = max(solved.legal_actions, key=lambda a: q[a])
        s = score_play(solved, {"kind": best.kind, "amount": best.amount})
        assert s.ev_loss_chips == pytest.approx(0.0, abs=1e-12)
        assert s.grade == "Perfect" and s.score == pytest.approx(100.0)
        assert s.best_q == q[best]
        # The solver's own mix loses only its (small, measured) self-loss.
        assert s.solver_self_loss == pytest.approx(s.best_q - s.solver_mix_q, abs=1e-12)
        assert s.provenance is solved.provenance
        opt = solved.optimal_action
        so = score_play(solved, {"kind": opt.kind, "amount": opt.amount})
        assert so.ev_loss_chips == pytest.approx(s.best_q - q[opt], abs=1e-12)
        json.dumps(s.to_json(), allow_nan=False)


def test_real_solve_dominated_action_positive_loss(kuhn_2000):
    found = False
    for solved in kuhn_2000:
        legal = set(solved.legal_actions)
        if legal != {Action("fold"), Action("call")}:
            continue
        q = solved.action_values
        if q[Action("call")] <= q[Action("fold")]:
            continue
        found = True  # e.g. K facing a bet: folding is dominated
        s = score_play(solved, {"kind": "fold"})
        assert s.ev_loss_chips == pytest.approx(q[Action("call")] - q[Action("fold")])
        assert s.ev_loss_chips > 0 and s.score == 0.0
        assert s.ev_loss_pct_pot == pytest.approx(100 * s.ev_loss_chips /
                                                  solved.pot_at_decision)
        assert s.grade == grade_for(s.ev_loss_pct_pot)
    assert found, "expected at least one kuhn spot where folding is dominated"


def test_real_solve_mix_linearity(kuhn_2000):
    solved = kuhn_2000[0]
    legal = solved.legal_actions
    pures = {a: score_play(solved, {"kind": a.kind, "amount": a.amount}) for a in legal}
    probs = {a: (i + 1) / sum(range(1, len(legal) + 1)) for i, a in enumerate(legal)}
    mix = score_play(solved, {"mix": [{"action": {"kind": a.kind, "amount": a.amount},
                                       "probability": p} for a, p in probs.items()]})
    assert mix.ev_loss_chips == pytest.approx(
        sum(p * pures[a].ev_loss_chips for a, p in probs.items()), abs=1e-12)
    assert mix.score == pytest.approx(sum(p * pures[a].score for a, p in probs.items()),
                                      abs=1e-9)
