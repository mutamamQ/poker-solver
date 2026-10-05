"""Practice-mode scoring: EV loss of a user play versus the solver optimum.

Implements PRACTICE_MODE_DESIGN.md section 5 exactly (no score floor):

    best_q           = max_a Q(a)
    worst_q          = min_a Q(a)
    spread           = best_q - worst_q
    solver_mix_q     = sum_a sigma*(a) Q(a)
    solver_self_loss = best_q - solver_mix_q
    chosen_q         = sum_a pi_u(a) Q(a)
    ev_loss          = max(0, best_q - chosen_q)
    ev_loss_pct_pot  = 100 * ev_loss / pot_at_decision
    score            = 100 if spread <= 1e-12 else 100 * max(0, 1 - ev_loss / spread)

Every Q value comes from ``solved.action_values`` (a real solve or its cache); this
module contains no strategy or value literals. The pure helpers operate on plain
``Mapping[Action, float]`` objects so they can be tested without a solver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..model import Action

__all__ = [
    "EPS_SPREAD",
    "PROB_TOLERANCE",
    "SIZED_KINDS",
    "GRADE_THRESHOLDS",
    "ParsedPlay",
    "PlayScore",
    "grade_for",
    "parse_play",
    "score_distribution",
    "score_play",
]

EPS_SPREAD = 1e-12
PROB_TOLERANCE = 1e-9
SELF_LOSS_TOLERANCE = 1e-9
# Kinds whose amount is a wager size and may be snapped to the nearest solved size.
SIZED_KINDS = frozenset({"bet", "raise", "BET", "RAISE"})
# (inclusive upper bound on ev_loss_pct_pot, grade); anything above the last is Blunder.
GRADE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.25, "Perfect"),
    (1.0, "Good"),
    (3.0, "Inaccuracy"),
    (8.0, "Mistake"),
)
BLUNDER = "Blunder"
NOISE_NOTE_PCT = 0.25


# --------------------------------------------------------------------------- helpers


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value: Any, label: str) -> float:
    if not _is_number(value):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _action_json(action: Action) -> dict[str, Any]:
    return {"kind": action.kind, "amount": action.amount}


def _action_label(action: Action) -> str:
    return action.kind if action.amount == 0 else f"{action.kind}[{action.amount}]"


def grade_for(ev_loss_pct_pot: float) -> str:
    """Map an EV loss in percent of the pot to a grade (inclusive thresholds)."""
    pct = _finite(ev_loss_pct_pot, "ev_loss_pct_pot")
    if pct < 0.0:
        raise ValueError("ev_loss_pct_pot must be non-negative")
    for bound, grade in GRADE_THRESHOLDS:
        if pct <= bound:
            return grade
    return BLUNDER


def _legal_tuple(legal_actions: Sequence[Action]) -> tuple[Action, ...]:
    legal = tuple(legal_actions)
    if not legal:
        raise ValueError("legal_actions must be non-empty")
    for action in legal:
        if not isinstance(action, Action):
            raise ValueError("legal_actions must contain Action objects")
    if len(set(legal)) != len(legal):
        raise ValueError("legal_actions must be unique")
    return legal


# --------------------------------------------------------------------------- play parsing


@dataclass(frozen=True)
class ParsedPlay:
    """A validated user play, mapped onto the solved legal actions.

    ``distribution`` is the evaluated play (legal Action -> probability, legal order,
    snapped duplicates merged). ``mappings`` lists (requested, snapped) pairs for every
    off-tree size that was snapped. ``mapped_action`` is the snapped Action for a pure
    play whose size was snapped, otherwise None.
    """

    is_mix: bool
    distribution: Mapping[Action, float]
    mappings: tuple[tuple[Action, Action], ...]
    mapped_action: Action | None
    size_mapped: bool
    original: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "distribution", MappingProxyType(dict(self.distribution)))
        object.__setattr__(self, "mappings", tuple(self.mappings))

    def to_json(self) -> dict[str, Any]:
        """Canonical evaluated play: a pure Action or ``{mix: [...]}`` in legal order."""
        if not self.is_mix:
            (action,) = tuple(self.distribution)
            return _action_json(action)
        return {"mix": [{"action": _action_json(a), "probability": float(p)}
                        for a, p in self.distribution.items()]}


def _parse_action_obj(obj: Any, label: str, *, require_amount: bool) -> tuple[str, int | None]:
    if not isinstance(obj, Mapping):
        raise ValueError(f"{label} must be an object")
    keys = set(obj)
    allowed = {"kind", "amount"}
    if not keys <= allowed:
        raise ValueError(f"{label} has unknown fields: {sorted(map(str, keys - allowed))}")
    if "kind" not in obj:
        raise ValueError(f"{label} is missing 'kind'")
    if require_amount and "amount" not in obj:
        raise ValueError(f"{label} is missing 'amount'")
    kind = obj["kind"]
    if not isinstance(kind, str) or not kind:
        raise ValueError(f"{label}.kind must be a non-empty string")
    if "amount" not in obj:
        return kind, None
    amount = obj["amount"]
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError(f"{label}.amount must be an integer")
    if amount < 0:
        raise ValueError(f"{label}.amount must be non-negative")
    return kind, amount


def _map_to_legal(kind: str, amount: int | None, legal: tuple[Action, ...],
                  label: str) -> tuple[Action, bool]:
    """Return (legal action, snapped?) for a requested kind/amount."""
    same_kind = [a for a in legal if a.kind == kind]
    if not same_kind:
        raise ValueError(f"{label}: action kind {kind!r} is not legal here "
                         f"(legal: {[_action_label(a) for a in legal]})")
    if amount is None:
        if len(same_kind) == 1:
            return same_kind[0], False
        raise ValueError(f"{label}: amount is required for kind {kind!r} "
                         f"(sizes: {[a.amount for a in same_kind]})")
    exact = Action(kind, amount)
    if exact in legal:
        return exact, False
    if kind not in SIZED_KINDS:
        raise ValueError(f"{label}: {kind!r} amount {amount} is not legal and only "
                         f"bet/raise sizes may be snapped")
    # Nearest solved size of the same kind; ties go to the smaller size.
    snapped = min(same_kind, key=lambda a: (abs(a.amount - amount), a.amount))
    return snapped, True


def parse_play(obj: Any, legal_actions: Sequence[Action]) -> ParsedPlay:
    """Validate a JSON play against the legal actions of the solved decision.

    Accepts a pure action ``{kind, amount?}`` or ``{mix: [{action: {kind, amount},
    probability}, ...]}``. Probabilities must be finite, >= 0, and sum to 1 within
    1e-9; duplicate requested actions are rejected; bool is never a number. Off-tree
    bet/raise sizes snap to the nearest legal size of the same kind (ties -> smaller);
    snapped duplicates in a mix have their probabilities summed.
    """
    legal = _legal_tuple(legal_actions)
    if not isinstance(obj, Mapping):
        raise ValueError("play must be an object")
    if "mix" in obj:
        if set(obj) != {"mix"}:
            raise ValueError("play must be either an action or {mix: [...]}, not both")
        entries = obj["mix"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("play.mix must be a non-empty list")
        seen: set[tuple[str, int]] = set()
        merged: dict[Action, float] = {}
        mappings: list[tuple[Action, Action]] = []
        total = 0.0
        for index, entry in enumerate(entries):
            label = f"play.mix[{index}]"
            if not isinstance(entry, Mapping):
                raise ValueError(f"{label} must be an object")
            if set(entry) != {"action", "probability"}:
                raise ValueError(f"{label} must have exactly 'action' and 'probability'")
            kind, amount = _parse_action_obj(entry["action"], f"{label}.action",
                                             require_amount=True)
            assert amount is not None
            if (kind, amount) in seen:
                raise ValueError(f"{label}: duplicate action {kind}[{amount}]")
            seen.add((kind, amount))
            prob = _finite(entry["probability"], f"{label}.probability")
            if prob < 0.0:
                raise ValueError(f"{label}.probability must be non-negative")
            total += prob
            target, snapped = _map_to_legal(kind, amount, legal, label)
            if snapped:
                mappings.append((Action(kind, amount), target))
            merged[target] = merged.get(target, 0.0) + prob
        if abs(total - 1.0) > PROB_TOLERANCE:
            raise ValueError(f"play.mix probabilities must sum to 1 (got {total!r})")
        ordered = {a: merged[a] for a in legal if a in merged}
        return ParsedPlay(True, ordered, tuple(mappings), None, bool(mappings), obj)
    kind, amount = _parse_action_obj(obj, "play", require_amount=False)
    target, snapped = _map_to_legal(kind, amount, legal, "play")
    if snapped:
        assert amount is not None
        return ParsedPlay(False, {target: 1.0}, ((Action(kind, amount), target),),
                          target, True, obj)
    return ParsedPlay(False, {target: 1.0}, (), None, False, obj)


# --------------------------------------------------------------------------- scoring


@dataclass(frozen=True)
class PlayScore:
    """Result of scoring one play against a solved spot (section 5)."""

    ev_loss_chips: float
    ev_loss_pct_pot: float
    score: float
    grade: str
    chosen_q: float
    best_q: float
    worst_q: float
    solver_mix_q: float
    solver_self_loss: float
    best_action: Action
    feedback: str
    mapped_action: Action | None
    size_mapped: bool
    play: ParsedPlay
    provenance: Any = None

    def to_json(self) -> dict[str, Any]:
        """JSON-safe dict (finite floats, string keys)."""
        prov = self.provenance
        if prov is not None and hasattr(prov, "to_json"):
            prov = prov.to_json()
        return {
            "ev_loss_chips": float(self.ev_loss_chips),
            "ev_loss_pct_pot": float(self.ev_loss_pct_pot),
            "score": float(self.score),
            "grade": self.grade,
            "chosen_q": float(self.chosen_q),
            "best_q": float(self.best_q),
            "worst_q": float(self.worst_q),
            "solver_mix_q": float(self.solver_mix_q),
            "solver_self_loss": float(self.solver_self_loss),
            "best_action": _action_json(self.best_action),
            "feedback": self.feedback,
            "mapped_action": None if self.mapped_action is None
            else _action_json(self.mapped_action),
            "size_mapped": self.size_mapped,
            "play": self.play.to_json(),
            "mappings": [{"requested": _action_json(r), "mapped": _action_json(m)}
                         for r, m in self.play.mappings],
            "provenance": prov,
        }


def _validated_policy(policy: Mapping[Action, float], legal: tuple[Action, ...],
                      label: str, *, probabilities: bool) -> dict[Action, float]:
    if not isinstance(policy, Mapping):
        raise ValueError(f"{label} must be a mapping")
    if set(policy) != set(legal):
        raise ValueError(f"{label} keys must equal the legal actions")
    out = {a: _finite(policy[a], f"{label}[{_action_label(a)}]") for a in legal}
    if probabilities:
        if any(p < 0.0 for p in out.values()):
            raise ValueError(f"{label} has a negative probability")
        if abs(sum(out.values()) - 1.0) > PROB_TOLERANCE:
            raise ValueError(f"{label} must sum to 1")
    return out


def _feedback(strategy: Mapping[Action, float], q: Mapping[Action, float],
              play: ParsedPlay, ev_loss: float, pct: float, grade: str,
              best_action: Action, best_q: float, self_loss: float, pot: float) -> str:
    """Deterministic template built only from computed numbers."""
    order = {a: i for i, a in enumerate(strategy)}
    mix = sorted(strategy.items(), key=lambda item: (-item[1], order[item[0]]))
    mix_text = ", ".join(f"{_action_label(a)} {100.0 * p:.1f}%" for a, p in mix)
    if play.is_mix:
        you = ", ".join(f"{_action_label(a)} {100.0 * p:.1f}%"
                        for a, p in play.distribution.items())
    else:
        you = _action_label(next(iter(play.distribution)))
    if play.mappings:
        you += " (mapped from " + ", ".join(
            f"{_action_label(r)} -> {_action_label(m)}" for r, m in play.mappings) + ")"
    text = (f"Solver: {mix_text}. You: {you}. "
            f"EV loss {ev_loss:.3f} chips ({pct:.2f}% pot) -> {grade}. "
            f"Best EV action: {_action_label(best_action)} (Q={best_q:+.3f})")
    chosen = set(play.distribution) if not play.is_mix else set()
    alternatives = [(a, p) for a, p in mix if a not in chosen and p > 0.0]
    if alternatives:
        alt = alternatives[0][0]
        text += f"; most-weighted alternative: {_action_label(alt)} (Q={q[alt]:+.3f})"
    text += "."
    if 100.0 * self_loss / pot > NOISE_NOTE_PCT:
        text += f" Solver noise: {self_loss:.3f} chips."
    return text


def score_distribution(action_values: Mapping[Action, float],
                       strategy: Mapping[Action, float],
                       pot_at_decision: float,
                       play: ParsedPlay,
                       legal_actions: Sequence[Action] | None = None,
                       provenance: Any = None) -> PlayScore:
    """Score a parsed play from plain Q / sigma* mappings (pure function)."""
    legal = _legal_tuple(legal_actions if legal_actions is not None else tuple(action_values))
    q = _validated_policy(action_values, legal, "action_values", probabilities=False)
    sigma = _validated_policy(strategy, legal, "strategy", probabilities=True)
    pot = _finite(pot_at_decision, "pot_at_decision")
    if pot <= 0.0:
        raise ValueError("pot_at_decision must be positive")
    if not isinstance(play, ParsedPlay):
        raise ValueError("play must be a ParsedPlay")
    for action in play.distribution:
        if action not in q:
            raise ValueError(f"play action {_action_label(action)} is not legal")

    best_action = max(legal, key=lambda a: (q[a], -legal.index(a)))
    best_q = q[best_action]
    worst_q = min(q.values())
    spread = best_q - worst_q
    solver_mix_q = sum(sigma[a] * q[a] for a in legal)
    self_loss = best_q - solver_mix_q
    if self_loss < -SELF_LOSS_TOLERANCE:
        raise ArithmeticError(f"negative solver self-loss {self_loss!r}")
    self_loss = max(0.0, self_loss)
    chosen_q = sum(p * q[a] for a, p in play.distribution.items())
    ev_loss = max(0.0, best_q - chosen_q)
    pct = 100.0 * ev_loss / pot
    score = 100.0 if spread <= EPS_SPREAD else 100.0 * max(0.0, 1.0 - ev_loss / spread)
    grade = grade_for(pct)
    feedback = _feedback(sigma, q, play, ev_loss, pct, grade, best_action, best_q,
                         self_loss, pot)
    return PlayScore(
        ev_loss_chips=ev_loss, ev_loss_pct_pot=pct, score=score, grade=grade,
        chosen_q=chosen_q, best_q=best_q, worst_q=worst_q, solver_mix_q=solver_mix_q,
        solver_self_loss=self_loss, best_action=best_action, feedback=feedback,
        mapped_action=play.mapped_action, size_mapped=play.size_mapped, play=play,
        provenance=provenance,
    )


def score_play(solved: Any, play: Any) -> PlayScore:
    """Score ``play`` (JSON object or ParsedPlay) against a ``SolvedSpot``.

    Uses ``solved.legal_actions``, ``solved.action_values`` (Q, chips, hero view),
    ``solved.strategy`` (sigma* for the hero hand), ``solved.pot_at_decision`` and
    attaches ``solved.provenance``.
    """
    legal = _legal_tuple(solved.legal_actions)
    parsed = play if isinstance(play, ParsedPlay) else parse_play(play, legal)
    return score_distribution(solved.action_values, solved.strategy,
                              solved.pot_at_decision, parsed, legal,
                              provenance=solved.provenance)
