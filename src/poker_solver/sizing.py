"""Bet sizing conversion and selection.

Phase 3 Wave C1: strict sizing with Decimal conversion, pot-percent/geometric/
previous-bet-multiple/big-blinds/all-in formulas, legality filtering without
clamping, Fixed/Dynamic/Automatic modes with exhaustive subset selection.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from math import isfinite
from typing import Any, Callable, Dict


@dataclass(frozen=True, slots=True)
class SizingChoice:
    expression: dict[str, Any]
    target: int


@dataclass(frozen=True, slots=True)
class SizingSelection:
    choices: tuple[SizingChoice, ...]
    ev: float
    evaluated: tuple[tuple[tuple[int, ...], float], ...]
    full_tree_ev: float | None = None


def validate_size_expression(expr: Dict[str, Any]) -> None:
    """Validate a strict size expression schema.
    
    Args:
        expr: Size expression dictionary with 'unit' and unit-specific fields.
    
    Raises:
        ValueError: If expression is malformed, contains booleans, non-finite
                   values, missing required fields, or invalid parameters.
    """
    if not isinstance(expr, dict):
        raise ValueError("size expression must be a dictionary")
    
    if "unit" not in expr:
        raise ValueError("size expression must have 'unit' field")
    
    unit = expr["unit"]
    expected_fields = {
        "pot-percent": {"unit", "value"},
        "geometric": {"unit", "streets", "scale"},
        "previous-bet-multiple": {"unit", "value"},
        "big-blinds": {"unit", "value"},

    }
    if unit in expected_fields and set(expr) != expected_fields[unit]:
        raise ValueError(f"{unit} expression must contain exactly {sorted(expected_fields[unit])}")
    
    if unit == "pot-percent":
        if "value" not in expr:
            raise ValueError("pot-percent expression must have 'value' field")
        _validate_numeric_value(expr["value"], "pot-percent value")
        if Decimal(str(expr["value"])) <= 0:
            raise ValueError("pot-percent value must be positive")
    
    elif unit == "geometric":
        if "streets" not in expr:
            raise ValueError("geometric expression must have 'streets' field")
        if "scale" not in expr:
            raise ValueError("geometric expression must have 'scale' field")
        
        streets = expr["streets"]
        scale = expr["scale"]
        
        _validate_numeric_value(streets, "geometric streets")
        _validate_numeric_value(scale, "geometric scale")
        
        if not (isinstance(streets, int) and streets > 0):
            raise ValueError("geometric streets must be a positive integer")
        if not (isinstance(scale, (int, float)) and scale > 0):
            raise ValueError("geometric scale must be positive")
    
    elif unit == "previous-bet-multiple":
        if "value" not in expr:
            raise ValueError("previous-bet-multiple expression must have 'value' field")
        _validate_numeric_value(expr["value"], "previous-bet-multiple value")
        if Decimal(str(expr["value"])) <= 0:
            raise ValueError("previous-bet-multiple value must be positive")
    
    elif unit == "big-blinds":
        if "value" not in expr:
            raise ValueError("big-blinds expression must have 'value' field")
        _validate_numeric_value(expr["value"], "big-blinds value")
        if Decimal(str(expr["value"])) <= 0:
            raise ValueError("big-blinds value must be positive")
    
    elif unit == "all-in":
        # All-in must not have extra fields
        extra_fields = set(expr.keys()) - {"unit"}
        if extra_fields:
            raise ValueError(f"all-in expression must not have extra fields: {extra_fields}")
    
    else:
        raise ValueError(f"unknown unit: {unit}")


def _validate_numeric_value(value: Any, field_name: str) -> None:
    """Validate that a value is numeric, finite, and not a boolean.
    
    Args:
        value: Value to validate.
        field_name: Field name for error messages.
    
    Raises:
        ValueError: If value is boolean, non-numeric, or non-finite.
    """
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must not be a boolean")
    
    if not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{field_name} must be numeric")
    
    # Check for non-finite float values
    if isinstance(value, float):
        import math
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite")


def convert_size_to_chips(expr: Dict[str, Any], context: Dict[str, Any]) -> int:
    """Convert a size expression to integer chips using context.
    
    Args:
        expr: Size expression dictionary.
        context: Betting context with pot, own_commitment, highest_commitment,
                remaining_stack, big_blind.
    
    Returns:
        Integer chip target (raise-to amount for current street).
    
    Raises:
        ValueError: If expression is invalid or context is insufficient.
    """
    validate_size_expression(expr)
    _strict_context(context, legality=False)
    
    unit = expr["unit"]
    pot = Decimal(str(context["pot"]))
    own = Decimal(str(context["own_commitment"]))
    highest = Decimal(str(context["highest_commitment"]))
    remaining = Decimal(str(context["remaining_stack"]))
    bb = Decimal(str(context["big_blind"]))
    
    call_amount = highest - own
    
    if unit == "pot-percent":
        q = Decimal(str(expr["value"])) / Decimal("100")
        if call_amount == 0:
            # Unopened: target = own + q*P
            target = own + q * pot
        else:
            # Facing wager: target = own_call + q*P_call
            pot_call = pot + call_amount
            own_call = own + call_amount
            target = own_call + q * pot_call
    
    elif unit == "previous-bet-multiple":
        m = Decimal(str(expr["value"]))
        target = m * highest
    
    elif unit == "big-blinds":
        target = Decimal(str(expr["value"])) * bb
    
    elif unit == "all-in":
        target = own + remaining
    
    elif unit == "geometric":
        streets = expr["streets"]
        scale = Decimal(str(expr["scale"]))
        
        if call_amount == 0:
            # Unopened
            S = remaining
            P = pot
        else:
            # Facing wager: use post-call state
            S = remaining - call_amount
            P = pot + call_amount
        
        # g = ((1 + 2*S/P)**(1/n) - 1)/2
        ratio = Decimal("1") + Decimal("2") * S / P
        g = (ratio ** (Decimal("1") / Decimal(str(streets))) - Decimal("1")) / Decimal("2")
        g_scaled = g * scale
        
        if call_amount == 0:
            target = own + g_scaled * pot
        else:
            target = own + call_amount + g_scaled * (pot + call_amount)
    
    else:
        raise ValueError(f"unknown unit: {unit}")
    
    # Round half-up to integer
    return int(target.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _strict_context(context: Dict[str, Any], *, legality: bool) -> None:
    required = {"pot", "own_commitment", "highest_commitment", "remaining_stack", "big_blind"}
    if legality:
        required |= {"minimum_raise_to", "pot_limit_max_raise_to", "short_all_in_allowed"}
    if not isinstance(context, dict) or not required.issubset(context):
        raise ValueError(f"sizing context requires fields {sorted(required)}")
    for field in ("pot", "own_commitment", "highest_commitment", "remaining_stack", "big_blind"):
        value = context[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} must be a non-negative integer")
    if context["big_blind"] <= 0:
        raise ValueError("big_blind must be positive")
    if context["highest_commitment"] < context["own_commitment"]:
        raise ValueError("highest_commitment cannot be below own_commitment")
    if legality:
        minimum = context["minimum_raise_to"]
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
            raise ValueError("minimum_raise_to must be a non-negative integer")
        maximum = context["pot_limit_max_raise_to"]
        if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0):
            raise ValueError("pot_limit_max_raise_to must be a non-negative integer or None")
        if not isinstance(context["short_all_in_allowed"], bool):
            raise ValueError("short_all_in_allowed must be boolean")


def fixed_sizes(
    expressions: tuple[dict[str, Any], ...], context: Dict[str, Any]
) -> tuple[SizingChoice, ...]:
    """Convert, legally filter, and target-deduplicate fixed expressions."""
    _strict_context(context, legality=True)
    own = int(context["own_commitment"])
    highest = int(context["highest_commitment"])
    maximum = own + int(context["remaining_stack"])
    minimum = context["minimum_raise_to"]
    pot_limit = context["pot_limit_max_raise_to"]
    result: list[SizingChoice] = []
    seen: set[int] = set()
    for expression in expressions:
        target = convert_size_to_chips(expression, context)
        legal = highest < target <= maximum
        if legal and pot_limit is not None and target > pot_limit:
            legal = False
        if legal and target < minimum:
            legal = target == maximum and context["short_all_in_allowed"]
        if legal and target not in seen:
            seen.add(target)
            result.append(SizingChoice(dict(expression), target))
    return tuple(result)


def _selection_inputs(
    choices: tuple[SizingChoice, ...], count: int, evaluate: Callable[[tuple[int, ...]], float]
) -> tuple[SizingChoice, ...]:
    if not callable(evaluate):
        raise ValueError("evaluate must be callable")
    if not choices or len(choices) > 10:
        raise ValueError("candidate count must be between 1 and 10")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= min(5, len(choices)):
        raise ValueError("retained size count must be between 1 and min(5, candidates)")
    if any(not isinstance(choice, SizingChoice) for choice in choices):
        raise ValueError("candidates must be SizingChoice values")
    ordered = tuple(sorted(choices, key=lambda choice: choice.target))
    if len({choice.target for choice in ordered}) != len(ordered):
        raise ValueError("candidate targets must be unique")
    return ordered


def _evaluate(evaluate: Callable[[tuple[int, ...]], float], targets: tuple[int, ...]) -> float:
    value = evaluate(targets)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValueError("size evaluator must return a finite number")
    return float(value)


def dynamic_sizes(
    choices: tuple[SizingChoice, ...],
    *,
    retained_count: int,
    evaluate: Callable[[tuple[int, ...]], float],
    tie_tolerance: float = 1e-12,
) -> SizingSelection:
    """Exhaustively maximize EV over fixed-cardinality candidate subsets."""
    ordered = _selection_inputs(choices, retained_count, evaluate)
    if isinstance(tie_tolerance, bool) or not isinstance(tie_tolerance, (int, float)) or not isfinite(tie_tolerance) or tie_tolerance < 0:
        raise ValueError("tie_tolerance must be finite and non-negative")
    evaluated: list[tuple[tuple[int, ...], float]] = []
    best_subset: tuple[SizingChoice, ...] | None = None
    best_ev = float("-inf")
    for subset in combinations(ordered, retained_count):
        targets = tuple(choice.target for choice in subset)
        ev = _evaluate(evaluate, targets)
        evaluated.append((targets, ev))
        if ev > best_ev + tie_tolerance or (
            abs(ev - best_ev) <= tie_tolerance
            and (best_subset is None or targets < tuple(choice.target for choice in best_subset))
        ):
            best_subset = subset
            best_ev = ev
    assert best_subset is not None
    return SizingSelection(best_subset, best_ev, tuple(evaluated))


def automatic_sizes(
    choices: tuple[SizingChoice, ...],
    *,
    max_sizes: int,
    ev_tolerance: float,
    evaluate: Callable[[tuple[int, ...]], float],
    tie_tolerance: float = 1e-12,
) -> SizingSelection:
    """Choose the smallest subset within tolerance of the all-candidate EV."""
    ordered = _selection_inputs(choices, max_sizes, evaluate)
    if isinstance(ev_tolerance, bool) or not isinstance(ev_tolerance, (int, float)) or not isfinite(ev_tolerance) or ev_tolerance < 0:
        raise ValueError("ev_tolerance must be finite and non-negative")
    full_targets = tuple(choice.target for choice in ordered)
    full_ev = _evaluate(evaluate, full_targets)
    all_evaluated: list[tuple[tuple[int, ...], float]] = [(full_targets, full_ev)]
    for count in range(1, max_sizes + 1):
        selection = dynamic_sizes(
            ordered, retained_count=count, evaluate=evaluate, tie_tolerance=tie_tolerance
        )
        all_evaluated.extend(selection.evaluated)
        if full_ev - selection.ev <= ev_tolerance + tie_tolerance:
            return SizingSelection(selection.choices, selection.ev, tuple(all_evaluated), full_ev)
    raise ValueError("no subset within EV tolerance and max_sizes")
