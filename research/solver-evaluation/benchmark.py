#!/usr/bin/env python3
"""Solver-evaluation benchmark for the poker solver behind practice mode.

Usage::

    .venv/bin/python research/solver-evaluation/benchmark.py --mode quick|full [--out DIR]

Every number is produced by running the solver now (no copied numbers).  References
are independent of the solver: closed-form game values (Kuhn -1/18, polarized river
toy, 3-player Kuhn -1/48), hand-derived card counts, Malmuth-Harville enumeration and
a benchmark-owned best-response / action-value oracle (``games.py``).

Thresholds for every criterion are declared up front in :data:`THRESHOLDS`; each
criterion is graded PASS / PARTIAL / FAIL from them.  Capabilities (the mission's
list) are graded from their evidence criteria plus a documented scope cap.  The
overall verdict is the WORST verdict over every criterion and capability.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
import traceback
from itertools import combinations, product
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _path in (str(HERE), str(ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from games import (  # noqa: E402  (benchmark-owned oracles)
    K3_SEAT0_RANGE,
    K3_SEAT1_VALUE,
    K3_SEAT2_RANGE,
    Memo,
    ThreePlayerKuhn,
    independent_action_values,
    malmuth_harville,
    nash_conv_n,
)
from poker_solver.allstreet import AllStreetPostflopConfig, create_allstreet_root  # noqa: E402
from poker_solver.api import complete_strategy  # noqa: E402
from poker_solver.best_response import nash_conv  # noqa: E402
from poker_solver.cards import parse_cards  # noqa: E402
from poker_solver.cfr import CFRSolver, expected_values  # noqa: E402
from poker_solver.equity import WeightedCombo, exact_equity  # noqa: E402
from poker_solver.game_structure import ForcedPost  # noqa: E402
from poker_solver.icm import calculate_icm_equity  # noqa: E402
from poker_solver.kuhn import BET, CALL, CHECK, KUHN_VALUE_P0, kuhn_root  # noqa: E402
from poker_solver.mccfr import MCCFRSolver  # noqa: E402
from poker_solver.model import CHANCE, TERMINAL, Action  # noqa: E402
from poker_solver.multistreet import MultiStreetConfig, create_root as create_multistreet_root  # noqa: E402
from poker_solver.nplayer import NPlayerCFRSolver, unilateral_deviation_certificate  # noqa: E402
from poker_solver.nplayer_preflop import (  # noqa: E402
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    create_nplayer_preflop_root,
)
from poker_solver.preflop import WeightedCombo as PreflopCombo  # noqa: E402
from poker_solver.river import RiverConfig, river_root  # noqa: E402

SCHEMA_VERSION = "solver-evaluation-v1"
ORDER = {"PASS": 0, "PARTIAL": 1, "FAIL": 2}
KUHN_REF = -1.0 / 18.0
assert abs(KUHN_VALUE_P0 - KUHN_REF) < 1e-15  # the repo constant must equal the analytic value

VERDICT_RULE = (
    "Each criterion is graded from its THRESHOLDS entry. A capability's verdict is the worst of "
    "its evidence criteria and its documented scope cap. overall = worst(all criteria + all "
    "capabilities) with FAIL > PARTIAL > PASS. correctness_verdict = worst over the correctness "
    "criteria only (excludes timing, default-solve quality and scale)."
)

# --------------------------------------------------------------------------- run modes

MODES: dict[str, dict[str, Any]] = {
    "quick": {
        "kuhn_checkpoints": (100, 300, 1000),
        "mccfr_checkpoints": (1000, 5000),
        "river_toy_iters": 1500,
        "sizing_iters": 600,
        "conv_river": (25, 100, 200),
        "conv_flop": (10, 40, 120),
        "conv_turn": (10, 40, 120),
        "conv_preflop": (10, 40, 160),
        "kuhn3_checkpoints": (100, 300, 1000),
        "practice_families": ("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet"),
        "kuhn_spots": 3,
        "sensitivity_iters": 60,
        "scale_combos": (2, 4, 8),
    },
    "full": {
        "kuhn_checkpoints": (100, 300, 1000, 3000, 10000),
        "mccfr_checkpoints": (1000, 5000, 20000),
        "river_toy_iters": 4000,
        "sizing_iters": 3000,
        "conv_river": (25, 100, 400, 1600),
        "conv_flop": (10, 40, 160, 640),
        "conv_turn": (10, 40, 160, 640),
        "conv_preflop": (10, 40, 160, 640, 2560),
        "kuhn3_checkpoints": (100, 300, 1000, 3000, 10000),
        "practice_families": None,  # every family in the live catalog
        "kuhn_spots": 12,
        "sensitivity_iters": 200,
        "scale_combos": (2, 4, 8, 16, 32, 48),
    },
}

# --------------------------------------------------------------------------- thresholds (declared up front)

THRESHOLDS: dict[str, dict[str, Any]] = {
    "C1-kuhn-analytic": {
        "reference": "Kuhn (1950): P0 game value -1/18; alpha-family equilibrium structure",
        "pass_value_error": 1e-3, "partial_value_error": 1e-2,
        "pass_final_nash_conv": 0.02,
        "pass_ratio_last_first": 0.5,
        "pass_loglog_slope_max": -0.35,
        "value_error_le_nash_conv_every_checkpoint": True,
        "structure_tolerance": "5 x final nash_conv",
    },
    "C2-kuhn-mccfr": {
        "reference": "Kuhn value -1/18 via external-sampling MCCFR (seed 0)",
        "pass_value_error": 5e-3, "partial_value_error": 2e-2,
        "pass_final_nash_conv": 0.05, "require_decreasing": True,
    },
    "C3-river-closed-form": {
        "reference": "polarized river toy, closed form: air bet B/(P+B), call P/(P+B), EV0 PB/(2(P+B))",
        "pass_freq_error": 0.03, "partial_freq_error": 0.08,
        "pass_value_error": "<= nash_conv (exploitability bound |u0 - v*| <= NashConv)",
        "nuts_bet_min": 0.95, "require_monotone_in_bet_size": True,
    },
    "C4-sizing-menu": {
        "reference": "menu {5,20}: equilibrium value = max single-size closed-form value; small size unused",
        "pass_value_error": "<= nash_conv of the menu solve",
        "pass_small_size_weight": 0.05, "partial_small_size_weight": 0.15,
    },
    "C5-convergence": {
        "metric": "NashConv(last checkpoint) / NashConv(first checkpoint)",
        "pass_ratio": 0.5, "partial_ratio": 1.0,
        "note": "checkpoint (not per-iteration) monotonicity, per research/validation_strategy.md 6",
    },
    "C6-br-oracle-agreement": {
        "metric": "|repo nash_conv (or 3p unilateral certificate) - independent oracle| / max(1, |oracle|)",
        "pass_rel_error": 1e-9, "partial_rel_error": 1e-6,
    },
    "C7-kuhn3-analytic": {
        "reference": "3-player Kuhn (Szafron, Gibson & Sturtevant 2013): seat1 = -1/48, seat0 in "
                     "[-3/48,-1/48], seat2 in [1/24,1/12]",
        "pass_final_nash_conv": 0.02,
        "pass_seat1_error": "<= final nash_conv (heuristic: n-player has no minimax bound)",
        "pass_ranges_slack": "final nash_conv",
        "partial": "NashConv decreasing (ratio < 1) and seat1 error <= 1e-2",
    },
    "C8-determinism": {
        "requirement": "identical params -> identical strategy, action values and params_hash; "
                       "MCCFR identical for equal seeds and different for different seeds; catalog "
                       "deterministic",
        "float_tolerance": 0.0,
    },
    "C9-param-sensitivity": {
        "requirement": "each perturbation (iterations, pot, bet size, villain range, stack) changes "
                       "params_hash AND the solved strategy or action values",
        "min_output_change": 1e-9,
        "partial": "every params_hash changes but some output is unchanged",
    },
    "C10-score-crosscheck": {
        "requirement": "practice Q / strategy / pot / score / grade == independent recomputation",
        "pass_abs_error": 1e-9, "partial_abs_error": 1e-6,
        "score_formula": "100*max(0, 1-(best_q-chosen_q)/(best_q-worst_q))",
        "grade_bounds_pct_pot": [0.25, 1.0, 3.0, 8.0],
    },
    "C11-practice-solve-quality": {
        "metric": "exploitability % of starting pot = 100 * (NashConv / n_players) / spot.pot at the "
                  "family default solve (NashConv from the independent oracle)",
        "pass_pct_pot": 1.0, "partial_pct_pot": 5.0,
    },
    "C12-practice-timing": {
        "metric": "cold SolverAdapter.solve wall time at the family default (empty cache)",
        "pass_seconds": 20.0, "partial_seconds": 90.0,
        "source": "W4 CONTRACT cold budget 20 s; server timeout 90 s",
    },
    "C13-equity-icm": {
        "requirement": "exact equity == hand-derived win/tie/loss counts; ICM == Malmuth-Harville "
                       "finishing-order enumeration",
        "icm_abs_error": 1e-9,
    },
    "C14-scale": {
        "metric": "projected seconds for 1000 vanilla-CFR iterations on a single-bet-size river with "
                  "100 combos per side (power-law fit of s/iteration vs deals; a LOWER bound for "
                  "realistic multi-size trees)",
        "pass_seconds": 60.0, "partial_seconds": 3600.0,
    },
    "C15-all-in": {
        "requirement": "all-in-only wager tree: zero-sum terminals, all-in showdowns reached, NashConv "
                       "decreases; no RAISE whose target equals the CALL target and no decision node "
                       "for a seat with 0 chips behind",
        "partial": "value checks pass and the structural defect is value-neutral (gap <= 1e-9)",
    },
    "C16-mixed-strategy": {
        "requirement": "where theory requires a strictly mixed equilibrium action (Kuhn P1 J-bluff and "
                       "Q-call = 1/3; river-toy air bet = B/(P+B)) the solver's mix lies strictly inside",
        "mixed_band": [0.05, 0.95],
    },
}

CRITERIA_IDS = (
    "C1-kuhn-analytic", "C2-kuhn-mccfr", "C3-river-closed-form", "C4-sizing-menu",
    "C5-convergence-river", "C5-convergence-flop", "C5-convergence-turn",
    "C5-convergence-preflop-hu", "C5-convergence-preflop-3p", "C6-br-oracle-agreement",
    "C7-kuhn3-analytic", "C8-determinism", "C9-param-sensitivity", "C10-score-crosscheck",
    "C11-practice-solve-quality", "C12-practice-timing", "C13-equity-icm", "C14-scale",
    "C15-all-in", "C16-mixed-strategy",
)
NON_CORRECTNESS = {"C11-practice-solve-quality", "C12-practice-timing", "C14-scale"}

RIVER_FAMS = ("river-oop-bet-or-check", "river-ip-facing-bet")


def _fam(cid: str, *families: str) -> tuple[str, ...]:
    """Per-family sub-verdict references, e.g. ``C11-practice-solve-quality[flop-cbet]``."""
    return tuple(f"{cid}[{f}]" for f in families)


Q, T = "C11-practice-solve-quality", "C12-practice-timing"

#: capability -> (evidence criteria, scope cap verdict, scope reason)
CAPABILITY_RULES: dict[str, tuple[tuple[str, ...], str, str]] = {
    "2-player NL": (
        ("C3-river-closed-form", "C4-sizing-menu", "C5-convergence-river", "C5-convergence-flop",
         "C5-convergence-turn", "C5-convergence-preflop-hu", "C6-br-oracle-agreement",
         "C10-score-crosscheck", "C14-scale", "C15-all-in")
        + _fam(Q, *RIVER_FAMS, "preflop-hu-open", "flop-cbet", "turn-barrel"),
        "PARTIAL",
        "bounded abstraction only: fixed wager menus, explicit tiny ranges (<= ~5 combos/side in the "
        "catalog), enumerated runout subsets; no full-range NLHE solve",
    ),
    "3-max": (
        ("C5-convergence-preflop-3p", "C6-br-oracle-agreement", "C7-kuhn3-analytic")
        + _fam(Q, "preflop-3max-open") + _fam(T, "preflop-3max-open"),
        "PARTIAL",
        "3-way only preflop (open/fold/call/jam trees, sampled-equity continuation); no multi-street "
        "3-way postflop in practice; the adapter reports nash_conv=None for 3-max",
    ),
    "preflop": (
        ("C5-convergence-preflop-hu", "C5-convergence-preflop-3p")
        + _fam(Q, "preflop-hu-open", "preflop-3max-open") + _fam(T, "preflop-hu-open", "preflop-3max-open"),
        "PARTIAL",
        "preflop leaves are settled by sampled-board showdown equity (no postflop play), tiny ranges",
    ),
    "postflop": (
        ("C3-river-closed-form", "C5-convergence-river", "C5-convergence-flop", "C5-convergence-turn",
         "C10-score-crosscheck", "C14-scale")
        + _fam(Q, *RIVER_FAMS, "flop-cbet", "turn-barrel") + _fam(T, *RIVER_FAMS, "flop-cbet", "turn-barrel"),
        "PARTIAL",
        "single wager size per spot in the catalog, <= 4 enumerated runouts, tiny ranges",
    ),
    "multi-street": (
        ("C5-convergence-flop", "C5-convergence-turn")
        + _fam(Q, "flop-cbet", "turn-barrel") + _fam(T, "flop-cbet", "turn-barrel"),
        "PARTIAL",
        "flop->river and turn->river only over an explicit runout subset (not all 49x48 runouts)",
    ),
    "ICM": (
        ("C13-equity-icm",),
        "PARTIAL",
        "icm.calculate_icm_equity is an evaluator only; no ICM-aware solve path in the solver "
        "facades or practice mode",
    ),
    "mixed strategy": (("C1-kuhn-analytic", "C3-river-closed-form", "C16-mixed-strategy"), "PASS", ""),
    "sizing": (
        ("C4-sizing-menu", "C9-param-sensitivity"),
        "PARTIAL",
        "fixed menus; practice spots expose one size; off-tree user sizes are snapped, never solved",
    ),
}
CAPABILITIES = tuple(CAPABILITY_RULES)


# --------------------------------------------------------------------------- grading helpers


def worst(verdicts) -> str:
    """Worst verdict (FAIL > PARTIAL > PASS); empty -> PASS."""
    result = "PASS"
    for verdict in verdicts:
        if ORDER[verdict] > ORDER[result]:
            result = verdict
    return result


def grade_upper(value: float, *, pass_max: float, partial_max: float) -> str:
    """Grade a lower-is-better metric (NaN/inf -> FAIL)."""
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return "FAIL"
    if value <= pass_max:
        return "PASS"
    if value <= partial_max:
        return "PARTIAL"
    return "FAIL"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _host() -> dict[str, Any]:
    try:
        load = list(os.getloadavg())
    except OSError:
        load = None
    return {
        "platform": platform.platform(), "python": platform.python_version(),
        "implementation": platform.python_implementation(), "machine": platform.machine(),
        "processor": platform.processor(), "cpu_count": os.cpu_count(), "hostname": platform.node(),
        "loadavg_at_start": load,
    }


def _clean(value: Any) -> Any:
    """JSON-safe copy (finite floats only; tuples -> lists; non-str keys -> str)."""
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, Action):
        return f"{value.kind}" if not value.amount else f"{value.kind}:{value.amount}"
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return repr(value)


def _loglog_slope(xs, ys) -> float:
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pts) < 2:
        return float("nan")
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else float("nan")


def _act(a: Action) -> str:
    return a.kind if not a.amount else f"{a.kind}:{a.amount}"


def _max_diff(a, b) -> float:
    keys = set(a) | set(b)
    return max((abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys), default=0.0)


# --------------------------------------------------------------------------- toy games


def _cards(text: str) -> tuple[int, ...]:
    return tuple(sorted(parse_cards(text.split())))


def _wc(text: str, weight: float = 1.0) -> WeightedCombo:
    return WeightedCombo(_cards(text), weight)


def river_toy(bet: int, pot: float = 10.0, stack: int = 20) -> RiverConfig:
    """Polarized toy: P0 {nuts KsKc (quads), air 3c4d} vs P1 bluff-catcher QsQc."""
    return RiverConfig(parse_cards("Kh Kd 8s 5c 2h".split()), pot, stack, bet,
                       (_wc("Ks Kc"), _wc("3c 4d")), (_wc("Qs Qc"),))


def flop_toy() -> AllStreetPostflopConfig:
    return AllStreetPostflopConfig(
        "allstreet-postflop-v1", parse_cards(["Td", "8h", "2c"]), 100, 100,
        (_wc("As Ah"), _wc("5s 4s")), (_wc("Qs Qh"), _wc("Jd Jc")),
        (tuple(parse_cards(["3d", "7c"])),), "no-limit", (33,), 4000, 40)


def turn_toy(stack: int = 100, targets: tuple[int, ...] = (50,)) -> MultiStreetConfig:
    return MultiStreetConfig(
        "multistreet-v1", "turn", parse_cards(["Td", "8h", "2c", "3d"]), 100, stack,
        (_wc("As Ah"), _wc("5s 4s")), (_wc("Qs Qh"), _wc("Jd Jc")),
        ((parse_cards(["7c"])[0],), (parse_cards(["Ks"])[0],)), "no-limit", targets, river_betting=True)


def _preflop_toy(players: int) -> NPlayerPreflopConfig:
    """Declared-rank push/fold-style preflop toys (ranks declared, not solver output)."""
    strength = {_cards("As Ah"): 4, _cards("Ks Kh"): 3, _cards("Qs Qh"): 2, _cards("7s 7h"): 1}
    if players == 3:
        seats = [[_cards("As Ah"), _cards("7s 7h")], [_cards("Ks Kh")], [_cards("Qs Qh")]]
        posts = (ForcedPost(1, "small-blind", 1), ForcedPost(2, "big-blind", 2))
        raises = 1
    else:
        seats = [[_cards("As Ah"), _cards("7s 7h")], [_cards("Ks Kh"), _cards("Qs Qh")]]
        posts = (ForcedPost(0, "small-blind", 1), ForcedPost(1, "big-blind", 2))
        raises = 2
    ranges = tuple(tuple(PreflopCombo(h, 1) for h in seat) for seat in seats)
    ranks = {deal: tuple(strength[c] for c in deal) for deal in product(*seats)}
    return NPlayerPreflopConfig(
        version="nplayer-preflop-v1", num_players=players, button=0, starting_stacks=(10,) * players,
        forced_posts=posts, straddle_variant="none", ranges=ranges, sizing_rules=(), max_raises=raises,
        max_deals=64, max_nodes=100_000, short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(
            kind="showdown-ranks", provenance="benchmark declared pair ranks AA>KK>QQ>77",
            source="supplied", payoff_table={}, showdown_ranks=ranks, odd_chip_order=tuple(range(players))))


# --------------------------------------------------------------------------- criteria


class Ctx:
    """Shared state between criteria (e.g. C6 aggregates C5 oracle discrepancies)."""

    def __init__(self, mode: str):
        self.mode = mode
        self.cfg = MODES[mode]
        self.oracle_checks: list[dict[str, Any]] = []
        self.mixed_checks: list[dict[str, Any]] = []
        self.practice: list[dict[str, Any]] = []


def c1_kuhn(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C1-kuhn-analytic"]
    root = kuhn_root()
    solver = CFRSolver(root)
    rows, done, t0, profile = [], 0, time.perf_counter(), {}
    for n in ctx.cfg["kuhn_checkpoints"]:
        profile = solver.train(n - done)
        done = n
        train_s = time.perf_counter() - t0
        metric = nash_conv(root, profile)
        oracle = nash_conv_n(root, profile, 2)
        ctx.oracle_checks.append({"game": f"kuhn@{n}", "repo": metric.nash_conv, "oracle": oracle["nash_conv"]})
        ev0 = metric.values[0]
        rows.append({"iterations": n, "train_s_cumulative": train_s, "nash_conv": metric.nash_conv,
                     "exploitability": metric.exploitability, "ev0": ev0, "value_error": abs(ev0 - KUHN_REF)})
    final = rows[-1]
    tol = 5.0 * final["nash_conv"]
    s = lambda p, c, h, a: profile[("kuhn-v1", p, c, h)][a]  # noqa: E731
    alpha = s(0, "J", (), BET)
    structure = {
        "p0_J_bet_alpha<=1/3": (alpha, alpha <= 1 / 3 + tol),
        "p0_K_bet=3alpha": (s(0, "K", (), BET), abs(s(0, "K", (), BET) - 3 * alpha) <= tol),
        "p0_Q_call=alpha+1/3": (s(0, "Q", (CHECK, BET), CALL), abs(s(0, "Q", (CHECK, BET), CALL) - (alpha + 1 / 3)) <= tol),
        "p0_Q_bet=0": (s(0, "Q", (), BET), s(0, "Q", (), BET) <= tol),
        "p0_J_call=0": (s(0, "J", (CHECK, BET), CALL), s(0, "J", (CHECK, BET), CALL) <= tol),
        "p0_K_call=1": (s(0, "K", (CHECK, BET), CALL), s(0, "K", (CHECK, BET), CALL) >= 1 - tol),
        "p1_J_bluff=1/3": (s(1, "J", (CHECK,), BET), abs(s(1, "J", (CHECK,), BET) - 1 / 3) <= tol),
        "p1_Q_call=1/3": (s(1, "Q", (BET,), CALL), abs(s(1, "Q", (BET,), CALL) - 1 / 3) <= tol),
        "p1_K_call=1": (s(1, "K", (BET,), CALL), s(1, "K", (BET,), CALL) >= 1 - tol),
        "p1_K_bet=1": (s(1, "K", (CHECK,), BET), s(1, "K", (CHECK,), BET) >= 1 - tol),
        "p1_J_call=0": (s(1, "J", (BET,), CALL), s(1, "J", (BET,), CALL) <= tol),
    }
    ctx.mixed_checks.append({"check": "kuhn p1 J bluff strictly mixed", "value": s(1, "J", (CHECK,), BET)})
    ctx.mixed_checks.append({"check": "kuhn p1 Q call strictly mixed", "value": s(1, "Q", (BET,), CALL)})
    slope = _loglog_slope([r["iterations"] for r in rows], [r["nash_conv"] for r in rows])
    bound_ok = all(r["value_error"] <= r["nash_conv"] + 1e-12 for r in rows)
    ratio = final["nash_conv"] / rows[0]["nash_conv"]
    structure_ok = all(ok for _v, ok in structure.values())
    if (final["value_error"] <= th["pass_value_error"] and bound_ok and structure_ok
            and final["nash_conv"] <= th["pass_final_nash_conv"] and ratio <= th["pass_ratio_last_first"]
            and slope <= th["pass_loglog_slope_max"]):
        verdict = "PASS"
    elif final["value_error"] <= th["partial_value_error"] and ratio < 1:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {
        "reference_value_p0": KUHN_REF, "checkpoints": rows, "loglog_slope": slope,
        "ratio_last_first": ratio, "value_error_within_nash_conv_bound": bound_ok,
        "structure_tolerance": tol,
        "structure": {k: {"value": v, "ok": ok} for k, (v, ok) in structure.items()},
        "seconds_per_iteration": final["train_s_cumulative"] / final["iterations"]}}


def c2_mccfr(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C2-kuhn-mccfr"]
    root = kuhn_root()
    solver = MCCFRSolver(root, 0)
    rows, done, t0 = [], 0, time.perf_counter()
    for n in ctx.cfg["mccfr_checkpoints"]:
        profile = complete_strategy(root, solver.train(n - done))
        done = n
        metric = nash_conv(root, profile)
        rows.append({"iterations": n, "train_s_cumulative": time.perf_counter() - t0,
                     "nash_conv": metric.nash_conv, "ev0": metric.values[0],
                     "value_error": abs(metric.values[0] - KUHN_REF)})
    final = rows[-1]
    decreasing = final["nash_conv"] < rows[0]["nash_conv"]
    if final["value_error"] <= th["pass_value_error"] and final["nash_conv"] <= th["pass_final_nash_conv"] and decreasing:
        verdict = "PASS"
    elif final["value_error"] <= th["partial_value_error"]:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {"seed": 0, "checkpoints": rows, "decreasing": decreasing}}


def c3_river(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C3-river-closed-form"]
    pot, rows = 10.0, []
    air, nuts, catcher = _cards("3c 4d"), _cards("Ks Kc"), _cards("Qs Qc")
    for bet in (5, 10, 20):
        cfg = river_toy(bet, pot)
        root = river_root(cfg)
        t0 = time.perf_counter()
        profile = CFRSolver(root).train(ctx.cfg["river_toy_iters"])
        secs = time.perf_counter() - t0
        metric = nash_conv(root, profile)
        ctx.oracle_checks.append({"game": f"river-toy-B{bet}", "repo": metric.nash_conv,
                                  "oracle": nash_conv_n(root, profile, 2)["nash_conv"]})
        b = Action("bet", bet)
        key = lambda p, own, h: ("river-v1", p, own, cfg.board, h, cfg.pot, cfg.stack, cfg.bet)  # noqa: E731
        air_bet = profile[key(0, air, ())][b]
        nuts_bet = profile[key(0, nuts, ())][b]
        call = profile[key(1, catcher, (b,))][CALL]
        ref_air, ref_call, ref_ev = bet / (pot + bet), pot / (pot + bet), pot * bet / (2 * (pot + bet))
        rows.append({"bet": bet, "iterations": ctx.cfg["river_toy_iters"], "seconds": secs,
                     "nash_conv": metric.nash_conv, "air_bet": air_bet, "ref_air_bet": ref_air,
                     "call": call, "ref_call": ref_call, "nuts_bet": nuts_bet, "ev0": metric.values[0],
                     "ref_ev0": ref_ev, "value_error": abs(metric.values[0] - ref_ev),
                     "freq_error": max(abs(air_bet - ref_air), abs(call - ref_call))})
        ctx.mixed_checks.append({"check": f"river toy B={bet} air bet strictly mixed", "value": air_bet})
    monotone = (all(rows[i]["air_bet"] < rows[i + 1]["air_bet"] for i in range(2))
                and all(rows[i]["call"] > rows[i + 1]["call"] for i in range(2))
                and all(rows[i]["ev0"] < rows[i + 1]["ev0"] for i in range(2)))
    max_freq = max(r["freq_error"] for r in rows)
    values_ok = all(r["value_error"] <= r["nash_conv"] for r in rows)
    nuts_ok = all(r["nuts_bet"] >= th["nuts_bet_min"] for r in rows)
    if max_freq <= th["pass_freq_error"] and values_ok and monotone and nuts_ok:
        verdict = "PASS"
    elif max_freq <= th["partial_freq_error"] and monotone:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {"pot": pot, "stack": 20, "rows": rows, "monotone_in_bet": monotone,
                                             "max_freq_error": max_freq, "values_within_bound": values_ok}}


def c4_sizing(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C4-sizing-menu"]
    pot, iters, out = 10, ctx.cfg["sizing_iters"], {}
    board = parse_cards("Kh Kd 8s 5c 2h".split())
    nuts = _cards("Ks Kc")
    for menu in ((5,), (20,), (5, 20)):
        cfg = MultiStreetConfig("multistreet-v1", "river", board, pot, 20, (_wc("Ks Kc"), _wc("3c 4d")),
                                (_wc("Qs Qc"),), (), "no-limit", menu)
        root = Memo(create_multistreet_root(cfg))
        t0 = time.perf_counter()
        profile = complete_strategy(root, CFRSolver(root).train(iters))
        metric = nash_conv(root, profile)
        root_policies = {k[2]: v for k, v in profile.items() if k[1] == 0 and k[4] == ()}
        out[str(menu)] = {"seconds": time.perf_counter() - t0, "ev0": metric.values[0], "nash_conv": metric.nash_conv,
                          "nuts_policy": {_act(a): p for a, p in root_policies[nuts].items()},
                          "closed_form_ev0": [pot * b / (2 * (pot + b)) for b in menu]}
    menu = out["(5, 20)"]
    ref = max(pot * b / (2 * (pot + b)) for b in (5, 20))
    small = menu["nuts_policy"].get("RAISE:5", 0.0)
    single_ok = all(abs(out[k]["ev0"] - out[k]["closed_form_ev0"][0]) <= out[k]["nash_conv"] for k in ("(5,)", "(20,)"))
    value_ok = abs(menu["ev0"] - ref) <= menu["nash_conv"]
    if value_ok and single_ok and small <= th["pass_small_size_weight"]:
        verdict = "PASS"
    elif small <= th["partial_small_size_weight"]:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {"iterations": iters, "menus": out, "menu_reference_ev0": ref,
                                             "menu_value_error": abs(menu["ev0"] - ref), "nuts_small_size_weight": small,
                                             "single_size_values_within_bound": single_ok}}


def _convergence(ctx: Ctx, name: str, root, checkpoints, players: int, *, complete: bool, pot: float,
                 solver=None, certificate: bool = False) -> dict[str, Any]:
    th = THRESHOLDS["C5-convergence"]
    solver = solver or (CFRSolver(root) if players == 2 else NPlayerCFRSolver(root, max_nodes=200_000))
    rows, done, t0, profile = [], 0, time.perf_counter(), {}
    for n in checkpoints:
        profile = solver.train(n - done)
        if complete:
            profile = complete_strategy(root, profile)
        done = n
        elapsed = time.perf_counter() - t0
        conv = nash_conv(root, profile).nash_conv if players == 2 else nash_conv_n(root, profile, players)["nash_conv"]
        rows.append({"iterations": n, "train_s_cumulative": elapsed, "nash_conv": conv, "nash_conv_pct_pot": 100 * conv / pot})
        t0 = time.perf_counter() - elapsed  # restart the clock so metric time is excluded from training time
    oracle = nash_conv_n(root, profile, players)["nash_conv"]
    if players == 2:
        repo = rows[-1]["nash_conv"]
    else:
        repo = unilateral_deviation_certificate(root, profile).total_incentive if certificate else None
    if repo is not None:
        ctx.oracle_checks.append({"game": f"{name}@{rows[-1]['iterations']}", "repo": repo, "oracle": oracle})
    ratio = rows[-1]["nash_conv"] / rows[0]["nash_conv"] if rows[0]["nash_conv"] > 0 else 0.0
    verdict = "PASS" if ratio <= th["pass_ratio"] else "PARTIAL" if ratio < th["partial_ratio"] else "FAIL"
    infosets = len(getattr(solver, "infosets", {}))
    return {"verdict": verdict, "evidence": {
        "players": players, "pot": pot, "infosets": infosets, "checkpoints": rows, "ratio_last_first": ratio,
        "loglog_slope": _loglog_slope([r["iterations"] for r in rows], [r["nash_conv"] for r in rows]),
        "seconds_per_iteration": rows[-1]["train_s_cumulative"] / rows[-1]["iterations"]}}


def c5_river(ctx: Ctx) -> dict[str, Any]:
    from poker_solver.practice.catalog import generate_catalog  # public API (input generator only)
    spot = generate_catalog(families=("river-oop-bet-or-check",), limit=1)[0]
    cfg = RiverConfig(spot.board, spot.pot, spot.stacks[0], spot.bet_sizes[0], spot.ranges[0], spot.ranges[1])
    result = _convergence(ctx, "river-catalog", river_root(cfg), ctx.cfg["conv_river"], 2, complete=False, pot=spot.pot)
    result["evidence"]["game"] = f"river backend, first river-oop-bet-or-check catalog input ({spot.spot_id})"
    return result


def c5_flop(ctx: Ctx) -> dict[str, Any]:
    cfg = flop_toy()
    result = _convergence(ctx, "flop-allstreet", Memo(create_allstreet_root(cfg)), ctx.cfg["conv_flop"], 2,
                          complete=True, pot=cfg.initial_dead_pot)
    result["evidence"]["game"] = "allstreet flop Td8h2c, {AA,54s} vs {QQ,JJ}, runout 3d7c, bet 33, stack 100"
    return result


def c5_turn(ctx: Ctx) -> dict[str, Any]:
    cfg = turn_toy()
    result = _convergence(ctx, "turn-multistreet", Memo(create_multistreet_root(cfg)), ctx.cfg["conv_turn"], 2,
                          complete=True, pot=cfg.initial_dead_pot)
    result["evidence"]["game"] = "multistreet turn Td8h2c3d, {AA,54s} vs {QQ,JJ}, rivers {7c,Ks}, bet 50, stack 100"
    return result


def c5_preflop_hu(ctx: Ctx) -> dict[str, Any]:
    root = Memo(create_nplayer_preflop_root(_preflop_toy(2)))
    result = _convergence(ctx, "preflop-hu", root, ctx.cfg["conv_preflop"], 2, complete=False, pot=3.0,
                          solver=NPlayerCFRSolver(root, max_nodes=200_000))
    result["evidence"]["game"] = "nplayer_preflop 2p, SB {AA,77} vs BB {KK,QQ}, stacks 10, blinds 1/2, all-in raises"
    return result


def c5_preflop_3p(ctx: Ctx) -> dict[str, Any]:
    root = Memo(create_nplayer_preflop_root(_preflop_toy(3)))
    result = _convergence(ctx, "preflop-3p", root, ctx.cfg["conv_preflop"], 3, complete=False, pot=3.0,
                          certificate=True)
    result["evidence"]["game"] = "nplayer_preflop 3p, BTN {AA,77}, SB KK, BB QQ, stacks 10, blinds 1/2"
    result["evidence"]["metric"] = "independent n-player NashConv oracle (sum of best-response incentives)"
    return result


def c6_oracle(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C6-br-oracle-agreement"]
    rows = []
    for check in ctx.oracle_checks:
        rel = abs(check["repo"] - check["oracle"]) / max(1.0, abs(check["oracle"]))
        rows.append({**check, "rel_error": rel})
    if not rows:
        return {"verdict": "FAIL", "evidence": {"error": "no oracle comparisons were recorded"}}
    worst_rel = max(r["rel_error"] for r in rows)
    return {"verdict": grade_upper(worst_rel, pass_max=th["pass_rel_error"], partial_max=th["partial_rel_error"]),
            "evidence": {"comparisons": rows, "max_rel_error": worst_rel}}


def c7_kuhn3(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C7-kuhn3-analytic"]
    root = Memo(ThreePlayerKuhn())
    solver = NPlayerCFRSolver(root)
    rows, done, train = [], 0, 0.0
    for n in ctx.cfg["kuhn3_checkpoints"]:
        t0 = time.perf_counter()
        profile = solver.train(n - done)
        train += time.perf_counter() - t0
        done = n
        m = nash_conv_n(root, profile, 3)
        rows.append({"iterations": n, "train_s_cumulative": train, "nash_conv": m["nash_conv"], "values": m["values"],
                     "seat1_error": abs(m["values"][1] - K3_SEAT1_VALUE)})
    f = rows[-1]
    slack = f["nash_conv"]
    v0, v2 = f["values"][0], f["values"][2]
    in_ranges = (K3_SEAT0_RANGE[0] - slack <= v0 <= K3_SEAT0_RANGE[1] + slack
                 and K3_SEAT2_RANGE[0] - slack <= v2 <= K3_SEAT2_RANGE[1] + slack)
    ratio = f["nash_conv"] / rows[0]["nash_conv"]
    if f["nash_conv"] <= th["pass_final_nash_conv"] and f["seat1_error"] <= slack and in_ranges and ratio < 1:
        verdict = "PASS"
    elif ratio < 1 and f["seat1_error"] <= 1e-2:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {
        "reference": {"seat1": K3_SEAT1_VALUE, "seat0_range": K3_SEAT0_RANGE, "seat2_range": K3_SEAT2_RANGE},
        "checkpoints": rows, "ratio_last_first": ratio, "values_in_analytic_ranges": in_ranges,
        "infosets": len(solver.infosets)}}


def _solved_signature(solved) -> dict[str, Any]:
    data = solved.to_json()
    prov = dict(data.get("provenance") or {})
    prov.pop("wall_time_s", None)
    data["provenance"] = prov
    return data


def c8_determinism(ctx: Ctx) -> dict[str, Any]:
    from poker_solver.practice.adapter import SolverAdapter
    from poker_solver.practice.catalog import generate_catalog
    from poker_solver.practice.models import SolveParams
    checks: dict[str, bool] = {}
    spots = [generate_catalog(families=("kuhn-intro",), limit=1)[0],
             generate_catalog(families=("river-oop-bet-or-check",), solve=SolveParams(iterations=60), limit=1)[0]]
    for spot in spots:
        a = SolverAdapter(cache={}).solve(spot)
        b = SolverAdapter(cache={}).solve(spot)
        checks[f"adapter repeat identical ({spot.family})"] = _solved_signature(a) == _solved_signature(b)
        checks[f"params_hash stable ({spot.family})"] = (a.provenance.params_hash == b.provenance.params_hash
                                                          == spot.params_hash())
    cat1 = [(s.spot_id, s.params_hash()) for s in generate_catalog(families=("kuhn-intro", "river-oop-bet-or-check"))]
    cat2 = [(s.spot_id, s.params_hash()) for s in generate_catalog(families=("kuhn-intro", "river-oop-bet-or-check"))]
    checks["catalog deterministic"] = cat1 == cat2
    root = kuhn_root()
    checks["vanilla CFR repeat identical"] = CFRSolver(root).train(200) == CFRSolver(root).train(200)
    m0a, m0b, m1 = (MCCFRSolver(root, s).train(500) for s in (0, 0, 1))
    checks["MCCFR equal seeds identical"] = m0a == m0b
    checks["MCCFR different seeds differ"] = m0a != m1
    proot = Memo(create_nplayer_preflop_root(_preflop_toy(3)))
    checks["n-player CFR repeat identical"] = (NPlayerCFRSolver(proot).train(30) == NPlayerCFRSolver(proot).train(30))
    verdict = "PASS" if all(checks.values()) else "FAIL"
    return {"verdict": verdict, "evidence": {"checks": checks}}


def c9_sensitivity(ctx: Ctx) -> dict[str, Any]:
    import dataclasses

    from poker_solver.practice.adapter import SolverAdapter
    from poker_solver.practice.catalog import generate_catalog
    from poker_solver.practice.models import PracticeSpot, SolveParams
    th = THRESHOLDS["C9-param-sensitivity"]
    iters = ctx.cfg["sensitivity_iters"]
    base = generate_catalog(families=("river-oop-bet-or-check",), solve=SolveParams(iterations=iters), limit=1)[0]
    villain = base.ranges[1]
    reweighted = (villain[0].__class__(villain[0].cards, villain[0].weight * 0.25),) + tuple(villain[1:])
    bet = base.bet_sizes[0]
    variants = {
        "iterations x2": base.with_solve(SolveParams(iterations=iters * 2)),
        "pot x1.5": dataclasses.replace(base, pot=base.pot * 1.5),
        "bet size": dataclasses.replace(base, bet_sizes=(max(1, bet // 2),)),
        "villain range weight": dataclasses.replace(base, ranges=(base.ranges[0], reweighted)),
    }
    flop_board = parse_cards(["Td", "8h", "2c"])
    flop = PracticeSpot(
        family="bench-flop-stack", backend="allstreet", game_type="heads-up", street="flop", board=flop_board,
        hero_seat=1, villain_seats=(0,), ranges=((_wc("As Ah"), _wc("5s 4s")), (_wc("Qs Qh"), _wc("Jd Jc"))),
        pot=100, stacks=(40, 40), action_history=(Action("CHECK"),), bet_sizes=(33,),
        hero_hand=_cards("Qs Qh"), solve=SolveParams(iterations=15),
        backend_extra={"allowed_runouts": [list(parse_cards(["3d", "7c"]))], "betting_mode": "no-limit",
                       "max_nodes": 4000, "max_depth": 40})
    adapter = SolverAdapter(cache={})
    rows = {}
    solved_base, solved_flop = adapter.solve(base), adapter.solve(flop)
    pairs = [(name, base, solved_base, spot) for name, spot in variants.items()]
    pairs.append(("stack 40 -> 400 (allstreet)", flop, solved_flop, dataclasses.replace(flop, stacks=(400, 400))))
    for name, ref_spot, ref, spot in pairs:
        other = adapter.solve(spot)
        rows[name] = {
            "hash_changed": spot.params_hash() != ref_spot.params_hash(),
            "provenance_hash_matches_spot": other.provenance.params_hash == spot.params_hash(),
            "strategy_change": _max_diff({_act(a): p for a, p in ref.strategy.items()},
                                         {_act(a): p for a, p in other.strategy.items()}),
            "action_value_change": _max_diff({_act(a): q for a, q in ref.action_values.items()},
                                             {_act(a): q for a, q in other.action_values.items()}),
        }
        rows[name]["output_changed"] = max(rows[name]["strategy_change"], rows[name]["action_value_change"]) > th["min_output_change"]
    hashes = all(r["hash_changed"] and r["provenance_hash_matches_spot"] for r in rows.values())
    outputs = all(r["output_changed"] for r in rows.values())
    verdict = "PASS" if hashes and outputs else "PARTIAL" if hashes else "FAIL"
    return {"verdict": verdict, "evidence": {"base_spot": base.spot_id, "iterations": iters, "perturbations": rows,
                                             "note": "river stack is only a bet cap there, so the stack perturbation "
                                                     "runs on an allstreet flop spot where it binds"}}


# ---- practice families: shared pass used by C10, C11, C12


def _rebuild(spot, adapter_mod):
    """Re-create the solver game for ``spot`` and re-run the solver (benchmark side)."""
    iters = spot.solve.iterations
    if spot.solve.algorithm != "vanilla-cfr":
        raise ValueError("benchmark rebuild supports vanilla-cfr spots only")
    extra = spot.backend_extra
    players = len(spot.stacks)
    if spot.backend == "kuhn":
        root = kuhn_root()
        return root, CFRSolver(root).train(iters), 2
    if spot.backend == "river":
        root = river_root(RiverConfig(spot.board, spot.pot, spot.stacks[0], spot.bet_sizes[0], spot.ranges[0], spot.ranges[1]))
        return root, CFRSolver(root).train(iters), 2
    if spot.backend == "allstreet":
        cfg = AllStreetPostflopConfig("allstreet-postflop-v1", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0],
                                      spot.ranges[1], extra["allowed_runouts"], extra["betting_mode"], spot.bet_sizes,
                                      extra["max_nodes"], extra["max_depth"])
        root = Memo(create_allstreet_root(cfg))
        return root, complete_strategy(root, CFRSolver(root).train(iters)), 2
    if spot.backend == "multistreet":
        cfg = MultiStreetConfig("multistreet-v1", "turn", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0],
                                spot.ranges[1], extra["allowed_runouts"], extra["betting_mode"], spot.bet_sizes,
                                river_betting=True)
        root = Memo(create_multistreet_root(cfg))
        return root, complete_strategy(root, CFRSolver(root).train(iters)), 2
    if spot.backend == "nplayer-preflop":
        config = adapter_mod.preflop_config(spot)  # public adapter API: builds the solver config
        root = Memo(create_nplayer_preflop_root(config))
        depth = 2 + config.num_players + config.max_raises * (config.num_players - 1)
        return root, NPlayerCFRSolver(root, max_nodes=config.max_nodes, max_depth=depth).train(iters), players
    raise ValueError(f"unknown backend {spot.backend!r}")


def _own(state, seat):
    deal = getattr(state, "private_deal", None)
    if deal is None:
        deal = getattr(state, "deal")
    own = deal[seat]
    return own if isinstance(own, str) else tuple(sorted(own))


def _pot_here(state, backend: str) -> float:
    """Chips in the middle at a decision, derived from the state (benchmark definition)."""
    if backend == "kuhn":
        return 2.0 + sum(1.0 for a in state.history if a.kind in ("bet", "call"))
    if backend == "river":
        return float(state.config.pot) + sum(float(a.amount) for a in state.history if a.kind == "bet")
    if backend == "nplayer-preflop":
        return float(state.pot)
    return float(state.pot + sum(state.committed))


def _locate(root, spot):
    hand = spot.backend_extra["kuhn_card"] if spot.backend == "kuhn" else tuple(sorted(spot.hero_hand))
    for deal, p in root.chance_outcomes():
        if p <= 0:
            continue
        state = root.child(deal)
        if _own(state, spot.hero_seat) != hand:
            continue
        for action in spot.action_history:
            state = state.child(action)
        return state.information_state_key(spot.hero_seat), state.legal_actions(), _pot_here(state, spot.backend)
    raise ValueError("hero hand reaches no deal")


def _grade(pct: float) -> str:
    for bound, name in zip(THRESHOLDS["C10-score-crosscheck"]["grade_bounds_pct_pot"],
                           ("Perfect", "Good", "Inaccuracy", "Mistake")):
        if pct <= bound:
            return name
    return "Blunder"


def practice_pass(ctx: Ctx) -> None:
    from poker_solver.practice import adapter as adapter_mod
    from poker_solver.practice.catalog import FAMILIES, generate_catalog
    from poker_solver.practice.scoring import score_play
    families = ctx.cfg["practice_families"] or FAMILIES
    for family in families:
        if family not in FAMILIES:
            ctx.practice.append({"family": family, "error": "family not in live catalog"})
            continue
        spots = generate_catalog(families=(family,))
        spots = spots[: ctx.cfg["kuhn_spots"]] if family == "kuhn-intro" else spots[:1]
        for spot in spots:
            rec: dict[str, Any] = {"family": family, "spot_id": spot.spot_id, "backend": spot.backend,
                                   "game_type": spot.game_type, "street": spot.street, "pot": spot.pot,
                                   "solve": spot.solve.canonical()}
            try:
                t0 = time.perf_counter()
                solved = adapter_mod.SolverAdapter(cache={}, timeout_s=600.0).solve(spot)
                rec["cold_solve_s"] = time.perf_counter() - t0
                rec["provenance_wall_time_s"] = solved.provenance.wall_time_s
                rec["provenance_nash_conv"] = solved.provenance.nash_conv
                t1 = time.perf_counter()
                root, profile, players = _rebuild(spot, adapter_mod)
                key, legal, pot_here = _locate(root, spot)
                q_ind, _mass = independent_action_values(root, profile, spot.hero_seat, key)
                rec["rebuild_s"] = time.perf_counter() - t1
                rec["legal_match"] = tuple(legal) == tuple(solved.legal_actions)
                rec["q_abs_error"] = max(abs(q_ind[a] - solved.action_values[a]) for a in legal)
                rec["strategy_abs_error"] = max(abs(profile[key][a] - solved.strategy[a]) for a in legal)
                rec["pot_abs_error"] = abs(pot_here - solved.pot_at_decision)
                best, worst_q = max(q_ind.values()), min(q_ind.values())
                spread = best - worst_q
                score_err, grade_ok, plays = 0.0, True, []
                mix = [{"action": {"kind": a.kind, "amount": a.amount}, "probability": float(solved.strategy[a])}
                       for a in legal]
                total = sum(m["probability"] for m in mix)
                mix[-1]["probability"] = max(0.0, mix[-1]["probability"] + 1.0 - total)
                candidates = [({"kind": a.kind, "amount": a.amount}, {a: 1.0}) for a in legal]
                candidates.append(({"mix": mix}, {a: m["probability"] for a, m in zip(legal, mix)}))
                for play, dist in candidates:
                    got = score_play(solved, play)
                    chosen = sum(p * q_ind[a] for a, p in dist.items())
                    loss = max(0.0, best - chosen)
                    exp_score = 100.0 if spread <= 1e-12 else 100.0 * max(0.0, 1.0 - loss / spread)
                    exp_pct = 100.0 * loss / pot_here
                    score_err = max(score_err, abs(got.score - exp_score), abs(got.ev_loss_chips - loss),
                                    abs(got.ev_loss_pct_pot - exp_pct))
                    ok = got.grade == _grade(exp_pct)
                    grade_ok &= ok
                    plays.append({"play": "mix" if "mix" in play else _act(next(iter(dist))), "score": got.score,
                                  "expected_score": exp_score, "grade": got.grade, "expected_grade": _grade(exp_pct)})
                rec["score_abs_error"] = score_err
                rec["grades_match"] = grade_ok
                rec["plays"] = plays
                t2 = time.perf_counter()
                oracle = nash_conv_n(root, profile, players)
                rec["oracle_nash_conv"] = oracle["nash_conv"]
                rec["players"] = players
                rec["exploitability_pct_pot"] = 100.0 * (oracle["nash_conv"] / players) / spot.pot
                rec["oracle_s"] = time.perf_counter() - t2
                if solved.provenance.nash_conv is not None:
                    ctx.oracle_checks.append({"game": f"practice:{spot.spot_id}", "repo": solved.provenance.nash_conv,
                                              "oracle": oracle["nash_conv"]})
            except Exception as exc:  # recorded as evidence (FAIL), never swallowed silently
                rec["error"] = f"{type(exc).__name__}: {exc}"
            ctx.practice.append(rec)


def c10_scores(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C10-score-crosscheck"]
    if not ctx.practice:
        practice_pass(ctx)
    rows = [{k: r.get(k) for k in ("family", "spot_id", "legal_match", "q_abs_error", "strategy_abs_error",
                                   "pot_abs_error", "score_abs_error", "grades_match", "error")} for r in ctx.practice]
    errors = [r for r in rows if r.get("error")]
    if errors:
        return {"verdict": "FAIL", "evidence": {"spots": rows, "errors": len(errors)}}
    worst_err = max(max(r["q_abs_error"], r["strategy_abs_error"], r["pot_abs_error"], r["score_abs_error"]) for r in rows)
    structural = all(r["legal_match"] and r["grades_match"] for r in rows)
    verdict = grade_upper(worst_err, pass_max=th["pass_abs_error"], partial_max=th["partial_abs_error"])
    if not structural:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {"spots": rows, "max_abs_error": worst_err,
                                             "plays_checked": sum(len(r.get("plays", [])) for r in ctx.practice)}}


def c11_quality(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C11-practice-solve-quality"]
    if not ctx.practice:
        practice_pass(ctx)
    per_family: dict[str, float] = {}
    for r in ctx.practice:
        if r.get("error") or "exploitability_pct_pot" not in r:
            per_family[r["family"]] = float("inf")
        else:
            per_family[r["family"]] = max(per_family.get(r["family"], 0.0), r["exploitability_pct_pot"])
    verdicts = {f: grade_upper(v, pass_max=th["pass_pct_pot"], partial_max=th["partial_pct_pot"]) for f, v in per_family.items()}
    return {"verdict": worst(verdicts.values()) if verdicts else "FAIL",
            "evidence": {"exploitability_pct_pot": per_family, "per_family_verdict": verdicts}}


def c12_timing(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C12-practice-timing"]
    if not ctx.practice:
        practice_pass(ctx)
    per_family: dict[str, float] = {}
    for r in ctx.practice:
        value = float("inf") if r.get("error") and "cold_solve_s" not in r else r.get("cold_solve_s", float("inf"))
        per_family[r["family"]] = max(per_family.get(r["family"], 0.0), value)
    verdicts = {f: grade_upper(v, pass_max=th["pass_seconds"], partial_max=th["partial_seconds"]) for f, v in per_family.items()}
    return {"verdict": worst(verdicts.values()) if verdicts else "FAIL",
            "evidence": {"cold_solve_seconds": per_family, "per_family_verdict": verdicts,
                         "solve_params": {r["family"]: r["solve"] for r in ctx.practice}}}


def c13_equity_icm(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C13-equity-icm"]
    checks: dict[str, Any] = {}
    # Hand-derived: AhKh vs QsQc on 2h7h9cJd; 44 rivers; hero wins with 9 hearts + 3 aces + 3 kings = 15.
    eq = exact_equity(_cards("Ah Kh"), _cards("Qs Qc"), parse_cards("2h 7h 9c Jd".split()))
    checks["equity AhKh vs QsQc on 2h7h9cJd = 15/0/29"] = {"got": [eq.wins, eq.ties, eq.losses], "ok": (eq.wins, eq.ties, eq.losses) == (15, 0, 29)}
    eq2 = exact_equity(_cards("2c 3d"), _cards("4h 5h"), parse_cards("As Ks Qs Js Ts".split()))
    checks["equity royal-flush board = 1 tie"] = {"got": [eq2.wins, eq2.ties, eq2.losses], "ok": (eq2.wins, eq2.ties, eq2.losses) == (0, 1, 0)}
    rng = random.Random(11)
    icm_err = 0.0
    cases = [((50, 30, 20), (50, 30, 20)), ((1000, 1000), (65, 35)), ((10, 20, 30, 40), (50, 30, 20, 0))]
    for n in (3, 4, 5, 6):
        stacks = tuple(rng.randint(1, 100) for _ in range(n))
        cases.append((stacks, tuple(sorted((rng.randint(0, 100) for _ in range(n)), reverse=True))))
    for stacks, payouts in cases:
        a, b = calculate_icm_equity(stacks, payouts), malmuth_harville(stacks, payouts)
        icm_err = max(icm_err, max(abs(x - y) for x, y in zip(a, b)))
    checks["ICM == Malmuth-Harville enumeration"] = {"cases": len(cases), "max_abs_error": icm_err, "ok": icm_err <= th["icm_abs_error"]}
    verdict = "PASS" if all(c["ok"] for c in checks.values()) else "FAIL"
    return {"verdict": verdict, "evidence": {"checks": checks}}


def c15_allin(ctx: Ctx) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    # All-in: turn toy where the only wager is the whole stack.
    cfg = turn_toy(stack=60, targets=(60,))
    root = Memo(create_multistreet_root(cfg))
    stats = {"terminals": 0, "max_abs_sum": 0.0, "allin_decisions": 0, "allin_showdowns": 0,
             "degenerate_raises": 0}
    degenerate_nodes: list = []

    def walk(state) -> None:
        p = state.current_player()
        if p == TERMINAL:
            stats["terminals"] += 1
            stats["max_abs_sum"] = max(stats["max_abs_sum"], abs(sum(state.returns())))
            if all(r == 0 for r in state.remaining):
                stats["allin_showdowns"] += 1
            return
        if p == CHANCE:
            for a, _ in state.chance_outcomes():
                walk(state.child(a))
            return
        if state.remaining[p] == 0:
            stats["allin_decisions"] += 1
        call = [a for a in state.legal_actions() if a.kind == "CALL"]
        for a in state.legal_actions():
            # a RAISE whose target equals the CALL target is not a raise (duplicate of CALL)
            if a.kind == "RAISE" and call and a.amount == call[0].amount:
                stats["degenerate_raises"] += 1
                degenerate_nodes.append((state, call[0], a))
        for a in state.legal_actions():
            walk(state.child(a))

    walk(root)
    solver = CFRSolver(root)
    first = nash_conv(root, complete_strategy(root, solver.train(10))).nash_conv
    profile = complete_strategy(root, solver.train(150))
    last = nash_conv(root, profile).nash_conv
    from poker_solver.practice.evaluate import subtree_value  # noqa: PLC0415 - value walker
    neutral = max((abs(subtree_value(st.child(c), profile, st.current_player())
                       - subtree_value(st.child(r), profile, st.current_player())) for st, c, r in degenerate_nodes),
                  default=0.0)
    checks["all-in tree zero-sum, reaches all-in showdowns, converges"] = {
        "terminals": stats["terminals"], "max_abs_sum": stats["max_abs_sum"],
        "allin_showdowns": stats["allin_showdowns"], "nash_conv_10": first, "nash_conv_160": last,
        "ok": stats["max_abs_sum"] <= 1e-9 and stats["allin_showdowns"] > 0 and last < first}
    checks["no degenerate RAISE==CALL facing all-in / no decisions for all-in seats"] = {
        "degenerate_raise_actions": stats["degenerate_raises"], "allin_seat_decision_nodes": stats["allin_decisions"],
        "max_value_gap_call_vs_degenerate_raise": neutral,
        "value_neutral": neutral <= 1e-9,
        "ok": stats["degenerate_raises"] == 0 and stats["allin_decisions"] == 0,
        "defect": "multistreet.MultiStreetState.legal_actions offers RAISE(target==call target) when the "
                  "all-in shove target equals the call amount; the all-in players then get CHECK-only "
                  "decision nodes. Value-neutral (gap above) but bloats the tree and lets practice users "
                  "pick a 'raise' that is a call."}
    structural = "no degenerate RAISE==CALL facing all-in / no decisions for all-in seats"
    hard = checks["all-in tree zero-sum, reaches all-in showdowns, converges"]["ok"]
    soft = checks[structural]
    if hard and soft["ok"]:
        verdict = "PASS"
    elif hard and soft["value_neutral"]:
        verdict = "PARTIAL"  # value-neutral structural defect only
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "evidence": {"checks": checks}}


def c16_mixed(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C16-mixed-strategy"]
    checks: dict[str, Any] = {}
    lo, hi = th["mixed_band"]
    for item in ctx.mixed_checks:
        checks[item["check"]] = {"value": item["value"], "ok": lo < item["value"] < hi}
    if not ctx.mixed_checks:
        return {"verdict": "FAIL", "evidence": {"error": "C1/C3 produced no mixed-strategy evidence"}}
    return {"verdict": "PASS" if all(c["ok"] for c in checks.values()) else "FAIL", "evidence": {"checks": checks}}


def c14_scale(ctx: Ctx) -> dict[str, Any]:
    th = THRESHOLDS["C14-scale"]
    board = parse_cards("Kh Kd 8s 5c 2h".split())
    deck = [c for c in range(52) if c not in board]
    pairs = list(combinations(deck, 2))
    random.Random(7).shuffle(pairs)
    rows = []
    for k in ctx.cfg["scale_combos"]:
        r0 = tuple(WeightedCombo(p) for p in pairs[:k])
        r1 = tuple(WeightedCombo(p) for p in pairs[k:2 * k])
        root = river_root(RiverConfig(board, 10.0, 20, 10, r0, r1))
        deals = len(root.chance_outcomes())
        t0 = time.perf_counter()
        solver = CFRSolver(root)
        build = time.perf_counter() - t0
        iters = 5 if deals < 1000 else 2
        t1 = time.perf_counter()
        solver.train(iters)
        per_iter = (time.perf_counter() - t1) / iters
        rows.append({"combos_per_side": k, "deals": deals, "infosets": len(solver.infosets), "build_s": build,
                     "iterations_timed": iters, "seconds_per_iteration": per_iter})
    slope = _loglog_slope([r["deals"] for r in rows], [r["seconds_per_iteration"] for r in rows])
    last = rows[-1]
    compat = last["deals"] / (last["combos_per_side"] ** 2)
    target_deals = compat * 100 * 100
    measured = last["combos_per_side"] >= 100
    per_iter_target = (last["seconds_per_iteration"] if measured
                       else last["seconds_per_iteration"] * (target_deals / last["deals"]) ** max(slope, 1.0))
    projected = 1000 * per_iter_target
    return {"verdict": grade_upper(projected, pass_max=th["pass_seconds"], partial_max=th["partial_seconds"]),
            "evidence": {"rows": rows, "loglog_slope_time_vs_deals": slope, "exponent_used": max(slope, 1.0),
                         "target_combos_per_side": 100, "target_deals": target_deals,
                         "projected_seconds_per_iteration": per_iter_target,
                         "target_measured_directly": measured,
                         "projected_seconds_1000_iterations": projected,
                         "note": "single bet size, river only; real multi-size / multi-street trees are larger"}}


CRITERIA: tuple[tuple[str, Callable[[Ctx], dict[str, Any]], str], ...] = (
    ("C1-kuhn-analytic", c1_kuhn, "Kuhn poker: CFR vs analytic value -1/18 and alpha-family structure"),
    ("C2-kuhn-mccfr", c2_mccfr, "Kuhn poker: external-sampling MCCFR vs -1/18"),
    ("C3-river-closed-form", c3_river, "Polarized river toy vs closed-form frequencies/value (3 sizes)"),
    ("C4-sizing-menu", c4_sizing, "Multi-size menu: solver picks the value-maximizing size"),
    ("C5-convergence-river", c5_river, "NashConv vs iterations: river backend (catalog input)"),
    ("C5-convergence-flop", c5_flop, "NashConv vs iterations: allstreet flop backend"),
    ("C5-convergence-turn", c5_turn, "NashConv vs iterations: multistreet turn backend"),
    ("C5-convergence-preflop-hu", c5_preflop_hu, "NashConv vs iterations: nplayer_preflop heads-up"),
    ("C5-convergence-preflop-3p", c5_preflop_3p, "NashConv vs iterations: nplayer_preflop 3-player"),
    ("C6-br-oracle-agreement", c6_oracle, "Repo best response / certificate vs independent oracle"),
    ("C7-kuhn3-analytic", c7_kuhn3, "3-player Kuhn vs analytic equilibrium family"),
    ("C8-determinism", c8_determinism, "Same params -> identical strategy, values and params_hash"),
    ("C9-param-sensitivity", c9_sensitivity, "R1: parameter changes change hash and solver output"),
    ("C10-score-crosscheck", c10_scores, "Practice Q/strategy/score/grade vs independent recomputation"),
    ("C11-practice-solve-quality", c11_quality, "Exploitability of practice families at default solve"),
    ("C12-practice-timing", c12_timing, "Cold solve time of practice families at default solve"),
    ("C13-equity-icm", c13_equity_icm, "Exact equity and ICM vs hand-derived / enumerated references"),
    ("C14-scale", c14_scale, "Scaling to realistic range sizes (measured + projection)"),
    ("C15-all-in", c15_allin, "All-in edge case: tree structure, zero-sum, convergence"),
    ("C16-mixed-strategy", c16_mixed, "Strictly mixed equilibria reproduced where theory requires"),
)
assert tuple(c[0] for c in CRITERIA) == CRITERIA_IDS


# --------------------------------------------------------------------------- runner


def _resolve(ref: str, by_id: dict[str, dict[str, Any]]) -> str | None:
    """Verdict for ``ref``; ``CID[family]`` reads the per-family sub-verdict (None = not measured)."""
    if "[" in ref:
        cid, family = ref[:-1].split("[", 1)
        crit = by_id.get(cid)
        if crit is None:
            return None
        return crit["evidence"].get("per_family_verdict", {}).get(family)
    crit = by_id.get(ref)
    return None if crit is None else crit["verdict"]


def _capabilities(by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for name, (ids, cap, reason) in CAPABILITY_RULES.items():
        resolved = {ref: _resolve(ref, by_id) for ref in ids}
        evidence = {ref: v for ref, v in resolved.items() if v is not None}
        missing = [ref for ref, v in resolved.items() if v is None]
        verdict = worst(list(evidence.values()) + [cap])
        gaps = [reason] if reason else []
        gaps += [f"{ref} is {v}" for ref, v in evidence.items() if v != "PASS"]
        out.append({"capability": name, "verdict": verdict, "scope_cap": cap, "evidence": evidence,
                    "not_measured_in_this_mode": missing, "gaps": gaps})
    return out


def run(mode: str = "quick", out_dir: str | Path | None = None, only: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Run the benchmark and write ``results.json`` + ``results.md`` into ``out_dir``."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    out = Path(out_dir) if out_dir is not None else HERE
    out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(mode)
    started, t_start = _now(), time.perf_counter()
    git = {"commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
           "dirty": bool(_git("status", "--porcelain", "--untracked-files=no"))}
    results = []
    for cid, fn, title in CRITERIA:
        if only and cid not in only:
            continue
        t0 = time.perf_counter()
        try:
            res = fn(ctx)
        except Exception as exc:  # a crashing criterion is recorded as FAIL with its traceback
            res = {"verdict": "FAIL", "evidence": {"error": f"{type(exc).__name__}: {exc}",
                                                   "traceback": traceback.format_exc()[-2000:]}}
        res = {"id": cid, "title": title, "verdict": res["verdict"], "thresholds": THRESHOLDS[cid.split("-convergence")[0] + "-convergence" if cid.startswith("C5-") else cid],
               "evidence": res["evidence"], "wall_time_s": time.perf_counter() - t0}
        results.append(res)
        print(f"[{mode}] {cid:28s} {res['verdict']:8s} {res['wall_time_s']:7.2f}s", flush=True)
    by_id = {r["id"]: r for r in results}
    caps = _capabilities(by_id) if not only else []
    correctness = worst(r["verdict"] for r in results if r["id"] not in NON_CORRECTNESS)
    overall = worst([r["verdict"] for r in results] + [c["verdict"] for c in caps])
    payload = _clean({
        "schema_version": SCHEMA_VERSION, "mode": mode, "started_at": started, "finished_at": _now(),
        "wall_time_s": time.perf_counter() - t_start, "host": _host(), "git": git,
        "solver_version": _solver_version(), "verdict_rule": VERDICT_RULE, "thresholds": THRESHOLDS,
        "criteria": results, "capabilities": caps, "correctness_verdict": correctness, "overall": overall,
    })
    (out / "results.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "results.md").write_text(render_markdown(payload), encoding="utf-8")
    return payload


def _solver_version() -> str:
    try:
        from importlib import metadata
        return metadata.version("poker-solver")
    except Exception:  # noqa: BLE001 - metadata lookup is informational only
        return "unknown"


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def render_markdown(p: dict[str, Any]) -> str:
    lines = [f"# Solver evaluation results ({p['mode']} mode)", "",
             f"- generated: {p['started_at']} -> {p['finished_at']} ({p['wall_time_s']:.1f} s)",
             f"- git: `{p['git']['commit']}` on `{p['git']['branch']}` (dirty={p['git']['dirty']})",
             f"- host: {p['host']['platform']}, Python {p['host']['python']}, {p['host']['cpu_count']} CPUs, "
             f"load {p['host']['loadavg_at_start']}",
             f"- **overall: {p['overall']}** (correctness-only: {p['correctness_verdict']})",
             f"- rule: {p['verdict_rule']}", "", "## Criteria", "", "| id | verdict | s | title |", "|---|---|---|---|"]
    for c in p["criteria"]:
        lines.append(f"| {c['id']} | **{c['verdict']}** | {c['wall_time_s']:.1f} | {c['title']} |")
    lines += ["", "## Capabilities", "", "| capability | verdict | scope cap | evidence | gaps |", "|---|---|---|---|---|"]
    for c in p["capabilities"]:
        ev = ", ".join(f"{k}={v}" for k, v in c["evidence"].items())
        lines.append(f"| {c['capability']} | **{c['verdict']}** | {c['scope_cap']} | {ev} | {'; '.join(c['gaps'])} |")
    lines += ["", "## Key numbers", ""]
    for c in p["criteria"]:
        ev = c["evidence"]
        if "checkpoints" in ev:
            pts = ", ".join(f"{r['iterations']}:{_fmt(r['nash_conv'])}" for r in ev["checkpoints"])
            lines.append(f"- {c['id']}: NashConv by iterations {pts}")
        for key in ("max_freq_error", "menu_value_error", "max_rel_error", "max_abs_error",
                    "exploitability_pct_pot", "cold_solve_seconds", "projected_seconds_1000_iterations"):
            if key in ev:
                lines.append(f"- {c['id']}: {key} = {_fmt(ev[key]) if not isinstance(ev[key], dict) else {k: _fmt(v) for k, v in ev[key].items()}}")
        if "error" in ev:
            lines.append(f"- {c['id']}: ERROR {ev['error']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=sorted(MODES), default="quick")
    parser.add_argument("--out", default=None, help="output directory (default: research/solver-evaluation)")
    parser.add_argument("--only", default=None, help="comma-separated criterion ids (debugging)")
    args = parser.parse_args(argv)
    only = tuple(args.only.split(",")) if args.only else None
    payload = run(args.mode, args.out, only)
    print(f"overall={payload['overall']} correctness={payload['correctness_verdict']} "
          f"wall={payload['wall_time_s']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
