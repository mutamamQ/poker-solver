"""Tests for bounded two-player tree validation."""

from __future__ import annotations

import pytest

from poker_solver.bounded_tree import BoundedTreeStats, validate_bounded_tree
from poker_solver.model import TERMINAL, CHANCE, Action, GameState


class MinimalTerminal:
    """Minimal terminal state for testing."""

    def current_player(self) -> int:
        return TERMINAL

    def legal_actions(self) -> tuple:
        return ()

    def chance_outcomes(self) -> tuple:
        return ()

    def returns(self) -> tuple[float, float]:
        return (1.0, -1.0)


def test_validate_bounded_tree_accepts_minimal_terminal():
    """A minimal valid terminal node should validate successfully."""
    root = MinimalTerminal()
    stats = validate_bounded_tree(root, max_nodes=10, max_depth=5)
    assert isinstance(stats, BoundedTreeStats)
    assert stats.node_count == 1
    assert stats.terminal_count == 1
    assert stats.chance_count == 0
    assert stats.decision_count == 0
    assert stats.max_depth_reached == 0


# RED: max_nodes validation
def test_max_nodes_must_be_positive_int():
    """max_nodes must be a positive integer."""
    root = MinimalTerminal()
    
    with pytest.raises(ValueError, match="max_nodes must be a positive integer"):
        validate_bounded_tree(root, max_nodes=0, max_depth=5)
    
    with pytest.raises(ValueError, match="max_nodes must be a positive integer"):
        validate_bounded_tree(root, max_nodes=-1, max_depth=5)
    
    with pytest.raises(ValueError, match="max_nodes must be a positive integer"):
        validate_bounded_tree(root, max_nodes=True, max_depth=5)


def test_max_depth_must_be_positive_int():
    """max_depth must be a positive integer."""
    root = MinimalTerminal()
    
    with pytest.raises(ValueError, match="max_depth must be a positive integer"):
        validate_bounded_tree(root, max_nodes=10, max_depth=0)
    
    with pytest.raises(ValueError, match="max_depth must be a positive integer"):
        validate_bounded_tree(root, max_nodes=10, max_depth=-1)
    
    with pytest.raises(ValueError, match="max_depth must be a positive integer"):
        validate_bounded_tree(root, max_nodes=10, max_depth=True)


# RED: actor validation
class InvalidActorBool:
    def current_player(self) -> int:
        return True  # type: ignore
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()


def test_actor_must_not_be_bool():
    """Actor must be int, not bool."""
    root = InvalidActorBool()
    with pytest.raises(ValueError, match="actor must be int"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class InvalidActorValue:
    def current_player(self) -> int:
        return 2
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()


def test_actor_must_be_valid_value():
    """Actor must be TERMINAL, CHANCE, 0, or 1."""
    root = InvalidActorValue()
    with pytest.raises(ValueError, match="actor must be TERMINAL, CHANCE, 0, or 1"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


# RED: terminal validation
class TerminalWithActions:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return (Action("fold"),)
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return (1.0, -1.0)


def test_terminal_must_have_no_legal_actions():
    """Terminal node must have no legal actions."""
    root = TerminalWithActions()
    with pytest.raises(ValueError, match="terminal node must have no legal actions"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalWithChance:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 1.0),)
    def returns(self) -> tuple[float, float]:
        return (1.0, -1.0)


def test_terminal_must_have_no_chance_outcomes():
    """Terminal node must have no chance outcomes."""
    root = TerminalWithChance()
    with pytest.raises(ValueError, match="terminal node must have no chance outcomes"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalWrongReturnCount:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return (1.0,)  # type: ignore


def test_terminal_returns_must_be_exactly_two():
    """Terminal returns must be tuple of exactly two values."""
    root = TerminalWrongReturnCount()
    with pytest.raises(ValueError, match="returns must be tuple of exactly two values"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalReturnsBool:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return (True, False)  # type: ignore


def test_terminal_returns_must_not_be_bool():
    """Terminal returns must not be bool."""
    root = TerminalReturnsBool()
    with pytest.raises(ValueError, match="returns\[0\] must not be bool"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalReturnsNonNumeric:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return ("1.0", -1.0)  # type: ignore


def test_terminal_returns_must_be_numeric():
    """Terminal returns must be numeric."""
    root = TerminalReturnsNonNumeric()
    with pytest.raises(ValueError, match="returns\[0\] must be numeric"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalReturnsInfinite:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return (float('inf'), -1.0)


def test_terminal_returns_must_be_finite():
    """Terminal returns must be finite."""
    root = TerminalReturnsInfinite()
    with pytest.raises(ValueError, match="returns\[0\] must be finite"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class TerminalReturnsNonZeroSum:
    def current_player(self) -> int:
        return TERMINAL
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()
    def returns(self) -> tuple[float, float]:
        return (1.0, 1.0)


def test_terminal_returns_must_sum_to_zero():
    """Terminal returns must sum to zero."""
    root = TerminalReturnsNonZeroSum()
    with pytest.raises(ValueError, match="returns must sum to zero"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


# RED: chance validation
class ChanceWithLegalActions:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return (Action("bet"),)
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 1.0),)


def test_chance_legal_actions_must_match_outcomes():
    """If exposed, chance legal actions must equal outcome actions."""
    root = ChanceWithLegalActions()
    with pytest.raises(ValueError, match="chance legal actions must match chance outcomes"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceEmpty:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()


def test_chance_must_have_nonempty_outcomes():
    """Chance node must have nonempty outcomes."""
    root = ChanceEmpty()
    with pytest.raises(ValueError, match="chance node must have nonempty outcomes"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceDuplicateActions:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 0.5), (Action("deal"), 0.5))
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()


def test_chance_actions_must_be_unique():
    """Chance actions must be unique."""
    root = ChanceDuplicateActions()
    with pytest.raises(ValueError, match="duplicate chance action"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceProbBool:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), True),)  # type: ignore


def test_chance_probability_must_not_be_bool():
    """Chance probability must not be bool."""
    root = ChanceProbBool()
    with pytest.raises(ValueError, match="chance probability must not be bool"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceProbNonNumeric:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), "0.5"),)  # type: ignore


def test_chance_probability_must_be_numeric():
    """Chance probability must be numeric."""
    root = ChanceProbNonNumeric()
    with pytest.raises(ValueError, match="chance probability must be numeric"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceProbOutOfRange:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 1.5),)
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()


def test_chance_probability_must_be_in_range():
    """Chance probability must be in [0,1]."""
    root = ChanceProbOutOfRange()
    with pytest.raises(ValueError, match="chance probability must be in \[0,1\]"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class ChanceProbNotSumToOne:
    def current_player(self) -> int:
        return CHANCE
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ((Action("deal1"), 0.3), (Action("deal2"), 0.3))
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()


def test_chance_probabilities_must_sum_to_one():
    """Chance probabilities must sum to 1."""
    root = ChanceProbNotSumToOne()
    with pytest.raises(ValueError, match="chance probabilities must sum to 1"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


# RED: decision validation
class DecisionWithChance:
    def current_player(self) -> int:
        return 0
    def legal_actions(self) -> tuple:
        return (Action("bet"),)
    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 1.0),)


def test_decision_must_have_no_chance_outcomes():
    """Decision node must have no chance outcomes."""
    root = DecisionWithChance()
    with pytest.raises(ValueError, match="decision node must have no chance outcomes"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class DecisionEmpty:
    def current_player(self) -> int:
        return 0
    def legal_actions(self) -> tuple:
        return ()
    def chance_outcomes(self) -> tuple:
        return ()


def test_decision_must_have_nonempty_legal_actions():
    """Decision node must have nonempty legal actions."""
    root = DecisionEmpty()
    with pytest.raises(ValueError, match="decision node must have nonempty legal actions"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class DecisionDuplicateActions:
    def current_player(self) -> int:
        return 0
    def legal_actions(self) -> tuple:
        return (Action("bet"), Action("bet"))
    def chance_outcomes(self) -> tuple:
        return ()
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()
    def information_state_key(self, player: int):
        return "test"


def test_decision_actions_must_be_unique():
    """Decision actions must be unique."""
    root = DecisionDuplicateActions()
    with pytest.raises(ValueError, match="duplicate legal action"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


# RED: infoset signature consistency
class InconsistentInfosetActor:
    def __init__(self, actor: int):
        self.actor = actor
    
    def current_player(self) -> int:
        return self.actor
    
    def legal_actions(self) -> tuple:
        return (Action("bet"),)
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()
    
    def information_state_key(self, player: int):
        return "shared_key"


def test_infoset_actor_must_be_consistent():
    """Infoset must have consistent actor across histories."""
    # Create a tree where two nodes share an infoset key but have different actors
    class RootNode:
        def current_player(self) -> int:
            return CHANCE
        def legal_actions(self) -> tuple:
            return ()
        def chance_outcomes(self) -> tuple:
            return ((Action("left"), 0.5), (Action("right"), 0.5))
        def child(self, action: Action) -> GameState:
            if action == Action("left"):
                return InconsistentInfosetActor(0)
            else:
                return InconsistentInfosetActor(1)
    
    root = RootNode()
    with pytest.raises(ValueError, match="infoset .* has inconsistent actor"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


class InconsistentInfosetActions:
    def __init__(self, actions: tuple):
        self.actions = actions
    
    def current_player(self) -> int:
        return 0
    
    def legal_actions(self) -> tuple:
        return self.actions
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()
    
    def information_state_key(self, player: int):
        return "shared_key"


def test_infoset_actions_must_be_consistent():
    """Infoset must have consistent action signature across histories."""
    class RootNode:
        def current_player(self) -> int:
            return CHANCE
        def legal_actions(self) -> tuple:
            return ()
        def chance_outcomes(self) -> tuple:
            return ((Action("left"), 0.5), (Action("right"), 0.5))
        def child(self, action: Action) -> GameState:
            if action == Action("left"):
                return InconsistentInfosetActions((Action("bet"),))
            else:
                return InconsistentInfosetActions((Action("fold"),))
    
    root = RootNode()
    with pytest.raises(ValueError, match="infoset .* has inconsistent action signature"):
        validate_bounded_tree(root, max_nodes=10, max_depth=5)


# RED: bounds enforcement
class DeepTree:
    def __init__(self, depth: int):
        self.depth = depth
    
    def current_player(self) -> int:
        return 0
    
    def legal_actions(self) -> tuple:
        return (Action("continue"),)
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        if self.depth == 0:
            return MinimalTerminal()
        return DeepTree(self.depth - 1)
    
    def information_state_key(self, player: int):
        return f"depth_{self.depth}"


def test_max_depth_exceeded():
    """Validation must fail when max_depth is exceeded."""
    root = DeepTree(10)
    with pytest.raises(ValueError, match="max_depth 5 exceeded"):
        validate_bounded_tree(root, max_nodes=100, max_depth=5)


class WideTree:
    def __init__(self, width: int):
        self.width = width
    
    def current_player(self) -> int:
        return 0
    
    def legal_actions(self) -> tuple:
        return tuple(Action(f"action_{i}") for i in range(self.width))
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()
    
    def information_state_key(self, player: int):
        return "root"


def test_max_nodes_exceeded():
    """Validation must fail when max_nodes is exceeded."""
    root = WideTree(10)
    with pytest.raises(ValueError, match="max_nodes 5 exceeded"):
        validate_bounded_tree(root, max_nodes=5, max_depth=10)


# RED: cycle detection
class CyclicTree:
    def __init__(self):
        self.terminal = MinimalTerminal()
    
    def current_player(self) -> int:
        return 0
    
    def legal_actions(self) -> tuple:
        return (Action("loop"),)
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        return self  # Cycle!
    
    def information_state_key(self, player: int):
        return "loop"


def test_cycle_detection():
    """Validation must detect cycles."""
    root = CyclicTree()
    with pytest.raises(ValueError, match="cycle detected"):
        validate_bounded_tree(root, max_nodes=100, max_depth=10)


# GREEN: comprehensive valid tree
class ValidDecisionTree:
    def current_player(self) -> int:
        return 0
    
    def legal_actions(self) -> tuple:
        return (Action("bet"), Action("fold"))
    
    def chance_outcomes(self) -> tuple:
        return ()
    
    def child(self, action: Action) -> GameState:
        if action == Action("fold"):
            return MinimalTerminal()
        return ValidChanceTree()
    
    def information_state_key(self, player: int):
        return "decision_root"


class ValidChanceTree:
    def current_player(self) -> int:
        return CHANCE
    
    def legal_actions(self) -> tuple:
        return ()
    
    def chance_outcomes(self) -> tuple:
        return ((Action("card1"), 0.5), (Action("card2"), 0.5))
    
    def child(self, action: Action) -> GameState:
        return MinimalTerminal()


def test_valid_composite_tree():
    """A valid composite tree should validate successfully."""
    root = ValidDecisionTree()
    stats = validate_bounded_tree(root, max_nodes=10, max_depth=5)
    
    assert stats.node_count == 5  # root + fold_terminal + chance + 2 chance children
    assert stats.terminal_count == 3
    assert stats.chance_count == 1
    assert stats.decision_count == 1
    assert stats.max_depth_reached == 2


class TerminalLegalActionsRaises:
    def current_player(self) -> int:
        return TERMINAL

    def legal_actions(self) -> tuple:
        raise RuntimeError("callback explosion")

    def chance_outcomes(self) -> tuple:
        return ()

    def returns(self) -> tuple[float, float]:
        return (1.0, -1.0)


class TerminalChanceOutcomesRaises:
    def current_player(self) -> int:
        return TERMINAL

    def legal_actions(self) -> tuple:
        return ()

    def chance_outcomes(self) -> tuple:
        raise RuntimeError("callback explosion")

    def returns(self) -> tuple[float, float]:
        return (1.0, -1.0)


class ChanceLegalActionsRaises:
    def current_player(self) -> int:
        return CHANCE

    def legal_actions(self) -> tuple:
        raise RuntimeError("callback explosion")

    def chance_outcomes(self) -> tuple:
        return ((Action("deal"), 1.0),)

    def child(self, action: Action):
        return MinimalTerminal()


class DecisionChanceOutcomesRaises:
    def current_player(self) -> int:
        return 0

    def legal_actions(self) -> tuple:
        return (Action("check"),)

    def chance_outcomes(self) -> tuple:
        raise RuntimeError("callback explosion")

    def information_state_key(self, player: int):
        return "decision-callback-probe"

    def child(self, action: Action):
        return MinimalTerminal()


@pytest.mark.parametrize(
    ("fixture_cls", "message"),
    (
        (TerminalLegalActionsRaises, r"legal_actions\(\) failed: callback explosion"),
        (TerminalChanceOutcomesRaises, r"chance_outcomes\(\) failed: callback explosion"),
        (ChanceLegalActionsRaises, r"legal_actions\(\) failed: callback explosion"),
        (DecisionChanceOutcomesRaises, r"chance_outcomes\(\) failed: callback explosion"),
    ),
)
def test_callback_exceptions_normalize_to_valueerror(fixture_cls, message):
    """GameState callback failures use the validator's stable ValueError boundary."""
    with pytest.raises(ValueError, match=message):
        validate_bounded_tree(fixture_cls(), max_nodes=10, max_depth=5)
