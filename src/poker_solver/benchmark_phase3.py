"""Small deterministic-semantic Phase-3 benchmark harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from time import perf_counter

from .engine import EngineConfig, solve_engine
from .icm import calculate_icm_equity
from .inference import Hypothesis, Observation, OpponentInference
from .model import Action, TERMINAL
from .nplayer import collect_nplayer_infosets, unilateral_deviation_certificate


@dataclass(frozen=True)
class TinyThreePlayer:
    history: tuple[Action, ...] = ()

    def num_players(self): return 3
    def current_player(self): return len(self.history) if len(self.history) < 3 else TERMINAL
    def chance_outcomes(self): return ()
    def legal_actions(self): return (Action("A"), Action("B")) if len(self.history) < 3 else ()
    def child(self, action): return TinyThreePlayer(self.history + (action,))
    def information_state_key(self, player): return (player, self.history)
    def returns(self):
        score = sum(action.kind == "A" for action in self.history)
        return (float(score), float(3 - score), 0.0)


@dataclass(frozen=True)
class CheckGame:
    history: tuple[Action, ...] = ()

    def num_players(self): return 2
    def current_player(self): return len(self.history) if len(self.history) < 2 else TERMINAL
    def chance_outcomes(self): return ()
    def legal_actions(self): return (Action("CHECK"), Action("BET", 1)) if len(self.history) < 2 else ()
    def child(self, action): return CheckGame(self.history + (action,))
    def information_state_key(self, player): return (player, self.history)
    def returns(self): return (1.0, -1.0)


def _timed(function):
    started = perf_counter()
    fingerprint, valid = function()
    return {
        "elapsed_seconds": perf_counter() - started,
        "result_fingerprint": fingerprint,
        "semantic_check": valid,
        "scope": "synthetic bounded regression benchmark",
    }


def run_benchmarks():
    def icm():
        values = calculate_icm_equity([10] * 10, list(range(10, 0, -1)))
        return json.dumps(values), abs(sum(values) - 55.0) < 1e-9

    def inference():
        hypotheses = tuple(
            Hypothesis(
                f"h{i}", Fraction(1),
                {"root": {"a": Fraction(1, 2), "b": Fraction(1, 2)}},
                "synthetic benchmark",
            )
            for i in range(64)
        )
        result = OpponentInference(hypotheses).update((Observation("root", "a"),))
        fingerprint = ",".join(f"{key}:{value}" for key, value in result.posterior.items())
        return fingerprint, sum(result.posterior.values(), Fraction()) == 1

    def deviation():
        root = TinyThreePlayer()
        infosets = collect_nplayer_infosets(root)
        strategy = {key: {action: 0.5 for action in actions} for key, (_, actions) in infosets.items()}
        result = unilateral_deviation_certificate(root, strategy)
        return repr((result.values, result.incentives)), result.total_incentive >= 0

    def checkdown():
        result = solve_engine(CheckGame(), EngineConfig("checkdown-equity"))
        return repr(result.values), result.approximate and result.values == (1.0, -1.0)

    return {
        "icm_10": _timed(icm),
        "inference_64": _timed(inference),
        "deviation_3p": _timed(deviation),
        "checkdown": _timed(checkdown),
    }
