"""Strict additive version-3 JSON facade for bounded Phase-3 utilities."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any

from .bounties import compute_ko_bounty
from .icm import calculate_icm_equity
from .inference import Hypothesis, Observation, OpponentInference
from .presets import get_preset, list_presets
from .ranges import export_range_text, import_range_text
from .sizing import convert_size_to_chips


_FEATURES = {
    "preflop": {"status": "implemented-bounded", "continuation": "terminal-table-only"},
    "sizing": {"status": "implemented-bounded", "modes": ["fixed", "dynamic", "automatic"]},
    "ranges": {"status": "implemented"},
    "tree-edit": {"status": "implemented-bounded", "interface": "programmatic"},
    "n-player-cfr": {"status": "implemented-bounded", "players": [2, 9], "deviation_certificate": "exhaustive-diagnostic-only"},
    "engine": {"status": "implemented-bounded", "modes": ["classic", "checkdown-equity"], "interface": "programmatic"},
    "nodelocks-profiles": {"status": "implemented-bounded", "interface": "programmatic"},
    "rake": {"status": "implemented-declared-policy"},
    "multiway-postflop": {"status": "implemented-bounded", "players": 3, "streets": "one-betting-round"},
    "range-tables": {"status": "implemented-bounded", "interface": "programmatic"},
    "opponent-inference": {"status": "implemented-bounded"},
    "icm": {"status": "implemented-bounded", "max_players": 10},
    "bounties": {"status": "implemented-immediate-one-hand"},
    "allstreet-postflop": {
        "status": "implemented-bounded",
        "starting_street": "flop",
        "continuation": "automatic-natural-terminal",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
    },
    "fast-ddls": {"status": "unavailable", "reason": "no shipped neural continuation model"},
    "nine-way-strategic-solving": {"status": "unavailable"},
    "plo": {"status": "unavailable"},
}


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    extra = set(value) - fields
    missing = fields - set(value)
    if extra:
        raise ValueError(f"unknown {label} fields: {sorted(extra)}")
    if missing:
        raise ValueError(f"missing {label} fields: {sorted(missing)}")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list")
    return value


def _fraction(value: Any, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{label} must be rational JSON text or number")
    if isinstance(value, str) and len(value) > 256:
        raise ValueError(f"{label} is too long")
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"{label} must be rational") from exc
    return result


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def dispatch_v3(data: dict[str, Any]) -> dict[str, Any]:
    request = _object(data, {"version", "operation", "payload"}, "request")
    if isinstance(request["version"], bool) or request["version"] != 3:
        raise ValueError("version must be JSON integer 3")
    operation = request["operation"]
    if not isinstance(operation, str) or not operation:
        raise ValueError("operation must be non-empty text")
    payload = request["payload"]

    if operation == "capabilities":
        _object(payload, set(), "payload")
        return {"version": 3, "operation": operation, "features": deepcopy(_FEATURES)}
    if operation == "list-presets":
        _object(payload, set(), "payload")
        return {
            "version": 3,
            "operation": operation,
            "presets": [{"name": name, "config": get_preset(name)} for name in list_presets()],
        }
    if operation == "icm":
        item = _object(payload, {"stacks", "payouts"}, "payload")
        equities = calculate_icm_equity(_list(item["stacks"], "stacks"), _list(item["payouts"], "payouts"))
        return {"operation": operation, "equities": list(equities), "scope": "bounded-small-field"}
    if operation == "bounty-ko":
        item = _object(payload, {"eliminated_bounty", "recipient_shares"}, "payload")
        shares_raw = item["recipient_shares"]
        if not isinstance(shares_raw, dict) or not shares_raw:
            raise ValueError("recipient_shares must be a non-empty object")
        shares = {}
        for seat_text, share in shares_raw.items():
            if not isinstance(seat_text, str) or not seat_text.isdigit():
                raise ValueError("recipient share keys must be non-negative integer text")
            shares[int(seat_text)] = _fraction(share, "recipient share")
        result = compute_ko_bounty(_fraction(item["eliminated_bounty"], "eliminated_bounty"), shares)
        return {
            "operation": operation,
            "immediate_cash": {str(seat): _fraction_text(value) for seat, value in result["immediate_cash"].items()},
            "scope": "immediate-one-hand-only",
        }
    if operation == "range-normalize":
        item = _object(payload, {"text"}, "payload")
        if not isinstance(item["text"], str) or len(item["text"]) > 1_000_000:
            raise ValueError("range text must be text of at most 1000000 characters")
        editor = import_range_text(item["text"])
        return {"operation": operation, "text": export_range_text(editor), "combo_count": len(editor.combos())}
    if operation == "size-convert":
        item = _object(payload, {"expression", "context"}, "payload")
        return {"operation": operation, "raise_to": convert_size_to_chips(item["expression"], item["context"])}
    if operation == "inference":
        item = _object(payload, {"hypotheses", "observations"}, "payload")
        hypotheses_raw = _list(item["hypotheses"], "hypotheses")
        observations_raw = _list(item["observations"], "observations")
        if len(hypotheses_raw) > 64:
            raise ValueError("too many hypotheses; maximum is 64")
        if len(observations_raw) > 4096:
            raise ValueError("too many observations; maximum is 4096")
        hypotheses = []
        for index, raw in enumerate(hypotheses_raw):
            entry = _object(raw, {"label", "prior", "likelihoods", "provenance"}, f"hypothesis {index}")
            likelihoods_raw = entry["likelihoods"]
            if not isinstance(likelihoods_raw, dict):
                raise ValueError("likelihoods must be an object")
            likelihoods = {}
            for public_key, row in likelihoods_raw.items():
                if not isinstance(row, dict):
                    raise ValueError("likelihood row must be an object")
                likelihoods[public_key] = {action: _fraction(value, "likelihood") for action, value in row.items()}
            hypotheses.append(Hypothesis(entry["label"], _fraction(entry["prior"], "prior"), likelihoods, entry["provenance"]))
        observations = []
        for index, raw in enumerate(observations_raw):
            entry = _object(raw, {"public_key", "action"}, f"observation {index}")
            observations.append(Observation(entry["public_key"], entry["action"]))
        result = OpponentInference(tuple(hypotheses)).update(tuple(observations))
        return {
            "operation": operation,
            "posterior": {label: _fraction_text(value) for label, value in result.posterior.items()},
            "provenance": list(result.provenance),
        }
    raise ValueError(f"unsupported version-3 operation {operation!r}")
