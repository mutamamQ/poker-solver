"""Strict additive version-4 S1 programmatic API for automatic all-street postflop."""

from __future__ import annotations

from math import isfinite
from types import MappingProxyType
from typing import Any, Literal, Mapping, cast


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


def _object_with_optional(
    value: Any,
    required: set[str],
    optional: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    extra = set(value) - required - optional
    missing = required - set(value)
    if extra:
        raise ValueError(f"unknown {label} fields: {sorted(extra)}")
    if missing:
        raise ValueError(f"missing {label} fields: {sorted(missing)}")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list")
    return value


def _int(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be a JSON integer")
    if positive and value <= 0:
        raise ValueError(f"{label} must be positive")
    if nonnegative and value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _float(value: Any, label: str, *, finite: bool = True, nonnegative: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if finite and not isfinite(result):
        raise ValueError(f"{label} must be finite")
    if nonnegative and result < 0:
        raise ValueError(f"{label} must be non-negative")
    return result


def _str(value: Any, label: str, *, allowed: set[str] | None = None) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if allowed is not None and value not in allowed:
        raise ValueError(f"{label} must be one of {sorted(allowed)}")
    return value


def _dispatch_nplayer_postflop(payload_value: Any) -> dict[str, Any]:
    """Parse and execute the strict direct S2 N-player request."""
    from .equity import WeightedCombo
    from .game_structure import RakePolicy
    from .nplayer_postflop import NPlayerPostflopConfig, solve_nplayer_postflop

    fields = {
        "version", "num_players", "button", "starting_stacks", "contributions",
        "folded", "board", "ranges", "wager_targets", "max_raises",
        "max_deals", "max_nodes", "odd_chip_order", "showdowns", "rake_policy",
        "algorithm", "iterations", "seed", "include_deviation_certificate",
        "max_pure_strategies",
    }
    payload = _object(payload_value, fields, "payload")
    game_version = _str(
        payload["version"],
        "payload.version",
        allowed={"nplayer-postflop-v1"},
    )
    num_players = _int(payload["num_players"], "num_players", positive=True)
    if not 2 <= num_players <= 9:
        raise ValueError("num_players must be from 2 to 9")
    button = _int(payload["button"], "button", nonnegative=True)

    def n_ints(name: str, *, positive: bool = False, nonnegative: bool = False) -> tuple[int, ...]:
        items = _list(payload[name], name)
        if len(items) != num_players:
            raise ValueError(f"{name} length must equal num_players")
        return tuple(
            _int(value, f"{name}[{index}]", positive=positive, nonnegative=nonnegative)
            for index, value in enumerate(items)
        )

    starting_stacks = n_ints("starting_stacks", positive=True)
    contributions = n_ints("contributions", nonnegative=True)
    folded_raw = _list(payload["folded"], "folded")
    if len(folded_raw) != num_players or any(not isinstance(value, bool) for value in folded_raw):
        raise ValueError("folded must contain num_players booleans")
    folded = tuple(folded_raw)
    board = tuple(
        _int(value, f"board[{index}]", nonnegative=True)
        for index, value in enumerate(_list(payload["board"], "board"))
    )

    ranges_raw = _list(payload["ranges"], "ranges")
    if len(ranges_raw) != num_players:
        raise ValueError("ranges length must equal num_players")
    ranges = []
    for seat, range_value in enumerate(ranges_raw):
        entries = _list(range_value, f"ranges[{seat}]")
        if not entries:
            raise ValueError(f"ranges[{seat}] must be non-empty")
        combos = []
        for index, entry_value in enumerate(entries):
            entry = _object(entry_value, {"cards", "weight"}, f"ranges[{seat}][{index}]")
            cards_raw = _list(entry["cards"], f"ranges[{seat}][{index}].cards")
            if len(cards_raw) != 2:
                raise ValueError("range combo cards must contain exactly two cards")
            cards = cast(tuple[int, int], tuple(
                _int(card, f"ranges[{seat}][{index}].cards[{card_index}]", nonnegative=True)
                for card_index, card in enumerate(cards_raw)
            ))
            weight = _float(entry["weight"], f"ranges[{seat}][{index}].weight")
            if weight <= 0.0:
                raise ValueError("range weights must be positive")
            combos.append(WeightedCombo(cards, weight))
        ranges.append(tuple(combos))

    wager_targets = tuple(
        _int(value, f"wager_targets[{index}]", positive=True)
        for index, value in enumerate(_list(payload["wager_targets"], "wager_targets"))
    )
    max_raises = _int(payload["max_raises"], "max_raises", positive=True)
    max_deals = _int(payload["max_deals"], "max_deals", positive=True)
    max_nodes = _int(payload["max_nodes"], "max_nodes", positive=True)
    odd_chip_order = n_ints("odd_chip_order", nonnegative=True)

    showdowns_raw = _list(payload["showdowns"], "showdowns")
    if not showdowns_raw:
        raise ValueError("showdowns must be non-empty")
    showdown_ranks: dict[tuple[tuple[int, int], ...], tuple[int, ...]] = {}
    for index, showdown_value in enumerate(showdowns_raw):
        showdown = _object(showdown_value, {"deal", "ranks"}, f"showdowns[{index}]")
        deal_raw = _list(showdown["deal"], f"showdowns[{index}].deal")
        ranks_raw = _list(showdown["ranks"], f"showdowns[{index}].ranks")
        if len(deal_raw) != num_players or len(ranks_raw) != num_players:
            raise ValueError("showdown deal and ranks lengths must equal num_players")
        deal = []
        for seat, combo_value in enumerate(deal_raw):
            combo_raw = _list(combo_value, f"showdowns[{index}].deal[{seat}]")
            if len(combo_raw) != 2:
                raise ValueError("showdown combos must contain exactly two cards")
            deal.append(tuple(
                _int(card, f"showdowns[{index}].deal[{seat}][{card_index}]", nonnegative=True)
                for card_index, card in enumerate(combo_raw)
            ))
        deal_tuple = tuple(deal)
        if deal_tuple in showdown_ranks:
            raise ValueError("duplicate showdown deal")
        showdown_ranks[deal_tuple] = tuple(
            _int(rank, f"showdowns[{index}].ranks[{seat}]")
            for seat, rank in enumerate(ranks_raw)
        )

    rake_raw = payload["rake_policy"]
    if rake_raw is None:
        rake_policy = None
    else:
        rake = _object(
            rake_raw,
            {
                "rate_numerator", "rate_denominator", "cap", "minimum_pot",
                "no_flop_no_drop", "rounding", "layer_order",
            },
            "rake_policy",
        )
        if not isinstance(rake["no_flop_no_drop"], bool):
            raise ValueError("rake_policy.no_flop_no_drop must be boolean")

        def optional_nonnegative(name: str) -> int | None:
            value = rake[name]
            return None if value is None else _int(value, f"rake_policy.{name}", nonnegative=True)

        rake_policy = RakePolicy(
            rate_numerator=_int(rake["rate_numerator"], "rake_policy.rate_numerator", nonnegative=True),
            rate_denominator=_int(rake["rate_denominator"], "rake_policy.rate_denominator", positive=True),
            cap=optional_nonnegative("cap"),
            minimum_pot=optional_nonnegative("minimum_pot"),
            no_flop_no_drop=rake["no_flop_no_drop"],
            rounding=cast(
                Literal["floor", "ceiling", "nearest"],
                _str(rake["rounding"], "rake_policy.rounding", allowed={"floor", "ceiling", "nearest"}),
            ),
            layer_order=cast(
                Literal["top-down", "bottom-up"],
                _str(rake["layer_order"], "rake_policy.layer_order", allowed={"top-down", "bottom-up"}),
            ),
        )

    algorithm = _str(payload["algorithm"], "algorithm", allowed={"vanilla-cfr"})
    iterations = _int(payload["iterations"], "iterations", positive=True)
    if payload["seed"] is not None:
        raise ValueError("vanilla-cfr requires seed null")
    include_certificate = payload["include_deviation_certificate"]
    if not isinstance(include_certificate, bool):
        raise ValueError("include_deviation_certificate must be boolean")
    max_pure_strategies = _int(
        payload["max_pure_strategies"],
        "max_pure_strategies",
        positive=True,
    )

    config = NPlayerPostflopConfig(
        version=game_version,
        num_players=num_players,
        button=button,
        starting_stacks=starting_stacks,
        contributions=contributions,
        folded=folded,
        board=board,
        ranges=tuple(ranges),
        wager_targets=wager_targets,
        max_raises=max_raises,
        max_deals=max_deals,
        max_nodes=max_nodes,
        odd_chip_order=odd_chip_order,
        showdown_ranks=showdown_ranks,
        rake_policy=rake_policy,
    )
    result = solve_nplayer_postflop(
        config,
        algorithm=algorithm,
        iterations=iterations,
        include_deviation_certificate=include_certificate,
        max_pure_strategies=max_pure_strategies,
    )
    strategy = {
        str(key): {str(action): float(probability) for action, probability in policy.items()}
        for key, policy in result.strategy.items()
    }
    certificate = None
    if result.certificate is not None:
        certificate = {
            "values": list(result.certificate.values),
            "best_response_values": list(result.certificate.best_response_values),
            "incentives": list(result.certificate.incentives),
            "total_incentive": float(result.certificate.total_incentive),
            "provenance": result.certificate.provenance,
        }
    return {
        "version": 4,
        "operation": "solve-nplayer-postflop",
        "config_version": result.config_version,
        "game_version": result.game_version,
        "algorithm": result.algorithm,
        "iterations": result.iterations,
        "seed": None,
        "max_nodes": result.max_nodes,
        "max_depth": result.max_depth,
        "strategy": strategy,
        "values": list(result.expected_values),
        "certificate": certificate,
        "metadata": dict(result.metadata),
        "provenance": result.provenance,
        "approximate": result.approximate,
    }


def dispatch_v4(data: dict[str, Any]) -> dict[str, Any]:
    """Strict version-4 dispatcher for S1 automatic all-street postflop.
    
    Accepts exactly:
    {
        "version": 4,
        "operation": "solve-allstreet-postflop",
        "payload": {
            "starting_board": [int, int, int],
            "initial_dead_pot": int,
            "effective_stack": int,
            "player0_combos": [{"cards": [int, int], "weight": float}, ...],
            "player1_combos": [{"cards": [int, int], "weight": float}, ...],
            "allowed_runouts": [[int, int], ...],
            "betting_mode": "no-limit" | "pot-limit",
            "wager_targets": [int, ...],
            "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
            "iterations": int,
            "seed": int | null,
            "max_nodes": int (optional, default 100000),
            "max_depth": int (optional, default 512)
        }
    }
    
    Returns deterministic JSON-safe result with strategy, metadata, and provenance.
    """
    # Import here to avoid circular dependencies and to fail fast if allstreet module is missing
    try:
        from .allstreet import (
            AllStreetPostflopConfig,
            create_allstreet_root,
            solve_allstreet_postflop,
        )
        from .equity import WeightedCombo
    except ImportError as exc:
        raise ValueError(f"S1 allstreet module not available: {exc}") from exc

    request = _object(data, {"version", "operation", "payload"}, "request")
    
    version_value = request["version"]
    if isinstance(version_value, bool) or not isinstance(version_value, int) or version_value != 4:
        raise ValueError("version must be JSON integer 4")
    
    operation = _str(
        request["operation"],
        "operation",
        allowed={"solve-allstreet-postflop", "solve-nplayer-postflop"},
    )
    if operation == "solve-nplayer-postflop":
        return _dispatch_nplayer_postflop(request["payload"])
    payload = _object_with_optional(
        request["payload"],
        {
            "version",
            "starting_board",
            "initial_dead_pot",
            "effective_stack",
            "player0_combos",
            "player1_combos",
            "allowed_runouts",
            "betting_mode",
            "wager_targets",
            "algorithm",
            "iterations",
            "seed",
        },
        {"max_nodes", "max_depth"},
        "payload",
    )
    game_version = _str(
        payload["version"],
        "payload.version",
        allowed={"allstreet-postflop-v1"},
    )

    # Parse and validate starting_board
    starting_board_raw = _list(payload["starting_board"], "starting_board")
    if len(starting_board_raw) != 3:
        raise ValueError("starting_board must contain exactly 3 cards")
    starting_board = tuple(_int(c, f"starting_board[{i}]", nonnegative=True) for i, c in enumerate(starting_board_raw))
    if len(set(starting_board)) != 3:
        raise ValueError("starting_board cards must be unique")

    # Parse and validate stacks and pot
    initial_dead_pot = _int(payload["initial_dead_pot"], "initial_dead_pot", nonnegative=True)
    effective_stack = _int(payload["effective_stack"], "effective_stack", positive=True)

    # Parse and validate combos
    def parse_combos(raw: Any, label: str) -> tuple[WeightedCombo, ...]:
        combos_list = _list(raw, label)
        if not combos_list:
            raise ValueError(f"{label} must be non-empty")
        result = []
        for i, combo_raw in enumerate(combos_list):
            combo_obj = _object(combo_raw, {"cards", "weight"}, f"{label}[{i}]")
            cards_raw = _list(combo_obj["cards"], f"{label}[{i}].cards")
            if len(cards_raw) != 2:
                raise ValueError(f"{label}[{i}].cards must contain exactly 2 cards")
            cards = tuple(_int(c, f"{label}[{i}].cards[{j}]", nonnegative=True) for j, c in enumerate(cards_raw))
            if cards[0] == cards[1]:
                raise ValueError(f"{label}[{i}].cards must be unique")
            weight = _float(combo_obj["weight"], f"{label}[{i}].weight", finite=True, nonnegative=True)
            result.append(WeightedCombo(cards, weight))
        return tuple(result)

    player0_combos = parse_combos(payload["player0_combos"], "player0_combos")
    player1_combos = parse_combos(payload["player1_combos"], "player1_combos")

    # Parse and validate allowed_runouts
    allowed_runouts_raw = _list(payload["allowed_runouts"], "allowed_runouts")
    if not allowed_runouts_raw:
        raise ValueError("allowed_runouts must be non-empty")
    allowed_runouts = []
    for i, runout_raw in enumerate(allowed_runouts_raw):
        runout_list = _list(runout_raw, f"allowed_runouts[{i}]")
        if len(runout_list) != 2:
            raise ValueError(f"allowed_runouts[{i}] must contain exactly 2 cards (turn, river)")
        runout = tuple(_int(c, f"allowed_runouts[{i}][{j}]", nonnegative=True) for j, c in enumerate(runout_list))
        if runout[0] == runout[1]:
            raise ValueError(f"allowed_runouts[{i}] cards must be unique")
        allowed_runouts.append(runout)
    allowed_runouts = tuple(allowed_runouts)

    # Parse betting_mode and wager_targets
    betting_mode = _str(payload["betting_mode"], "betting_mode", allowed={"no-limit", "pot-limit"})
    wager_targets_raw = _list(payload["wager_targets"], "wager_targets")
    if not wager_targets_raw:
        raise ValueError("wager_targets must be non-empty")
    wager_targets = tuple(_int(t, f"wager_targets[{i}]", nonnegative=True) for i, t in enumerate(wager_targets_raw))

    # Parse algorithm, iterations, seed
    algorithm = _str(payload["algorithm"], "algorithm", allowed={"vanilla-cfr", "external-sampling-mccfr"})
    iterations = _int(payload["iterations"], "iterations", positive=True)
    seed_raw = payload["seed"]
    if seed_raw is None:
        seed = None
    else:
        seed = _int(seed_raw, "seed")

    # Validate algorithm-seed consistency
    if algorithm == "vanilla-cfr" and seed is not None:
        raise ValueError("vanilla-cfr does not accept a seed")
    if algorithm == "external-sampling-mccfr" and seed is None:
        raise ValueError("external-sampling-mccfr requires an integer seed")

    # Parse optional bounds
    max_nodes = 100_000
    max_depth = 512
    if "max_nodes" in payload:
        max_nodes = _int(payload["max_nodes"], "max_nodes", positive=True)
    if "max_depth" in payload:
        max_depth = _int(payload["max_depth"], "max_depth", positive=True)

    # Build immutable config
    config = AllStreetPostflopConfig(
        version=game_version,
        starting_board=starting_board,
        initial_dead_pot=initial_dead_pot,
        effective_stack=effective_stack,
        player0_combos=player0_combos,
        player1_combos=player1_combos,
        allowed_runouts=allowed_runouts,
        betting_mode=betting_mode,
        wager_targets=wager_targets,
        max_nodes=max_nodes,
        max_depth=max_depth,
    )

    # Solve
    result = solve_allstreet_postflop(
        config,
        algorithm=algorithm,
        iterations=iterations,
        seed=seed,
    )

    # Serialize result defensively
    def serialize_strategy(strategy: Mapping[Any, Mapping[Any, float]]) -> dict[str, dict[str, float]]:
        """Convert immutable strategy mapping to JSON-safe nested dict with string keys."""
        output = {}
        for info_key, policy in strategy.items():
            key_str = str(info_key)
            output[key_str] = {str(action): float(prob) for action, prob in policy.items()}
        return output

    def serialize_values(values: tuple[float, float]) -> list[float]:
        """Convert the zero-sum value vector to a JSON-safe list."""
        v0, v1 = values
        if not isfinite(v0) or not isfinite(v1):
            raise ValueError(f"non-finite value vector: ({v0}, {v1})")
        return [float(v0), float(v1)]

    response = {
        "version": 4,
        "operation": operation,
        "config_version": result.config_version,
        "game_version": result.game_version,
        "starting_street": result.starting_street,
        "continuation": result.continuation,
        "algorithm": result.algorithm,
        "iterations": result.iterations,
        "seed": result.seed,
        "max_nodes": result.max_nodes,
        "max_depth": result.max_depth,
        "strategy": serialize_strategy(result.strategy),
        "values": serialize_values(result.values),
        "nashconv": float(result.nash_conv),
        "exploitability": float(result.half_nash_conv),
        "metadata": dict(result.metadata),
        "provenance": result.provenance,
        "approximate": result.approximate,
    }

    return response
