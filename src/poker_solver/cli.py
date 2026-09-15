"""Deterministic command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .api import (
    compute_exploitability,
    deserialize_strategy,
    load_json_input,
    load_multistreet_config,
    serialize_strategy,
    solve_multistreet,
)
from .api_v3 import dispatch_v3
from .api_v4 import dispatch_v4
from .best_response import nash_conv
from .cards import format_card, parse_card, parse_cards
from .cfr import CFRSolver
from .equity import WeightedCombo, exact_equity
from .evaluator import CATEGORY_NAMES, evaluate
from .kuhn import KUHN_VALUE_P0, kuhn_root
from .mccfr import MCCFRSolver
from .multistreet import create_root
from .river import RiverConfig, river_root


def _pair(text: str) -> tuple[int, int]:
    cards = parse_cards(part for part in text.split(",") if part)
    if len(cards) != 2:
        raise ValueError("hand must contain two comma-separated cards")
    return (cards[0], cards[1])


def _board(text: str | None) -> tuple[int, ...]:
    if not text:
        return ()
    return parse_cards(part for part in text.split(",") if part)


def _action_name(action: Any) -> str:
    return action.kind if action.amount == 0 else f"{action.kind}:{action.amount}"


def _strategy_json(strategy: dict[Any, dict[Any, float]]) -> dict[str, dict[str, float]]:
    return {
        repr(key): {_action_name(action): policy[action] for action in sorted(policy)}
        for key, policy in sorted(strategy.items(), key=lambda item: repr(item[0]))
    }


def _emit(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False))
    else:
        print(data)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a JSON number")
    return float(value)


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a JSON integer")
    return value


def _load_combo(item: dict[str, Any]) -> WeightedCombo:
    if not isinstance(item, dict):
        raise ValueError("each combo must be an object")
    if set(item) != {"cards", "weight"}:
        raise ValueError("each combo requires exactly cards and weight fields")
    cards_value = item["cards"]
    if not isinstance(cards_value, list) or len(cards_value) != 2:
        raise ValueError("combo cards must be a two-item list")
    return WeightedCombo(
        (parse_card(cards_value[0]), parse_card(cards_value[1])),
        _number(item["weight"], "combo weight"),
    )


def _load_spot(path: str) -> RiverConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"version", "board", "pot", "stack", "bet", "range0", "range1"}
    if not isinstance(data, dict) or set(data) != required or data["version"] != 1:
        raise ValueError(f"spot config requires exactly {sorted(required)} and version 1")
    board = parse_cards(data["board"])
    if len(board) != 5:
        raise ValueError("spot board must contain five card strings")
    return RiverConfig(
        board, _number(data["pot"], "pot"), _integer(data["stack"], "stack"),
        _integer(data["bet"], "bet"),
        tuple(_load_combo(item) for item in data["range0"]),
        tuple(_load_combo(item) for item in data["range1"]),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="poker-solver", description="Finite-game poker solver reference")
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="evaluate exactly five or seven cards")
    evaluate_parser.add_argument("cards", nargs="+")
    evaluate_parser.add_argument("--json", action="store_true")

    equity_parser = sub.add_parser("equity", help="enumerate exact heads-up equity")
    equity_parser.add_argument("--hero", required=True)
    equity_parser.add_argument("--villain", required=True)
    equity_parser.add_argument("--board", default="")
    equity_parser.add_argument("--json", action="store_true")

    kuhn_parser = sub.add_parser("solve-kuhn", help="solve standard Kuhn poker")
    kuhn_parser.add_argument("--iterations", type=int, default=20_000)
    kuhn_parser.add_argument("--json", action="store_true")

    spot_parser = sub.add_parser("solve-spot", help="solve a compact river spot JSON file")
    spot_parser.add_argument("config")
    spot_parser.add_argument("--iterations", type=int, default=20_000)
    spot_parser.add_argument("--json", action="store_true")

    multistreet_parser = sub.add_parser("solve-multistreet", help="solve a multi-street game (version 2)")
    multistreet_parser.add_argument("config", help="JSON config file path or '-' for stdin")
    multistreet_parser.add_argument("--algorithm", required=True, choices=["vanilla-cfr", "external-sampling-mccfr"])
    multistreet_parser.add_argument("--iterations", type=int, required=True)
    multistreet_parser.add_argument("--seed", type=int, default=None)
    multistreet_parser.add_argument("--json", action="store_true")

    exploitability_parser = sub.add_parser("exploitability", help="compute exploitability of a multi-street strategy")
    exploitability_parser.add_argument("config", help="JSON config file path or '-' for stdin")
    exploitability_parser.add_argument("strategy", help="JSON strategy file path")
    exploitability_parser.add_argument("--json", action="store_true")

    phase3_parser = sub.add_parser("phase3", help="run a strict bounded version-3 JSON operation")
    phase3_parser.add_argument("request", help="JSON request file path or '-' for stdin")
    phase3_parser.add_argument("--json", action="store_true")

    phase4_parser = sub.add_parser("phase4", help="run a strict bounded version-4 JSON operation")
    phase4_parser.add_argument("request", help="JSON request file path or '-' for stdin")
    phase4_parser.add_argument("--json", action="store_true")

    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "evaluate":
        cards = parse_cards(args.cards)
        rank = evaluate(cards)
        _emit({"cards": [format_card(c) for c in cards], "category": CATEGORY_NAMES[rank[0]], "rank": list(rank)}, args.json)
        return 0
    if args.command == "equity":
        result = exact_equity(_pair(args.hero), _pair(args.villain), _board(args.board))
        _emit({"equity": result.equity, "losses": result.losses, "ties": result.ties, "total": result.total, "wins": result.wins}, args.json)
        return 0
    if args.command == "solve-kuhn":
        solver = CFRSolver(kuhn_root())
        strategy = solver.train(args.iterations)
        metric = nash_conv(solver.root, strategy)
        _emit({
            "algorithm": "vanilla-cfr", "exploitability_half_nash_conv": metric.exploitability,
            "iterations": solver.iterations, "known_value_p0": KUHN_VALUE_P0,
            "nash_conv": metric.nash_conv, "strategy": _strategy_json(strategy),
            "values": list(metric.values),
        }, args.json)
        return 0
    if args.command == "solve-spot":
        root = river_root(_load_spot(args.config))
        solver = CFRSolver(root)
        strategy = solver.train(args.iterations)
        metric = nash_conv(root, strategy)
        _emit({
            "algorithm": "vanilla-cfr", "exploitability_half_nash_conv": metric.exploitability,
            "iterations": solver.iterations, "nash_conv": metric.nash_conv,
            "strategy": _strategy_json(strategy), "values": list(metric.values),
        }, args.json)
        return 0
    if args.command == "solve-multistreet":
        data = load_json_input(args.config)
        config = load_multistreet_config(data)
        result = solve_multistreet(config, args.algorithm, args.iterations, args.seed)
        _emit({
            "algorithm": result.algorithm,
            "exploitability_half_nash_conv": result.half_nash_conv,
            "iterations": result.iterations,
            "metadata": result.metadata,
            "nash_conv": result.nash_conv,
            "seed": result.seed,
            "strategy": serialize_strategy(result.strategy),
            "values": list(result.values),
        }, args.json)
        return 0
    if args.command == "exploitability":
        config_data = load_json_input(args.config)
        config = load_multistreet_config(config_data)
        root = create_root(config)
        strategy_data = json.loads(Path(args.strategy).read_text(encoding="utf-8"))
        strategy = deserialize_strategy(root, strategy_data)
        result = compute_exploitability(root, strategy)
        _emit({
            "best_response_values": list(result.best_response_values),
            "exploitability_half_nash_conv": result.half_nash_conv,
            "incentives": list(result.incentives),
            "nash_conv": result.nash_conv,
            "values": list(result.values),
        }, args.json)
        return 0
    if args.command == "phase3":
        _emit(dispatch_v3(load_json_input(args.request)), args.json)
        return 0
    if args.command == "phase4":
        _emit(dispatch_v4(load_json_input(args.request)), args.json)
        return 0
    raise ValueError("unknown command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if hasattr(args, "iterations") and args.iterations <= 0:
            raise ValueError("iterations must be positive")
        return run(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
