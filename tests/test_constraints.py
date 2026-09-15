"""Tests for nodelocking and player-profile constraints."""

import math
from types import MappingProxyType
import pytest
from poker_solver.model import Action, TERMINAL, CHANCE
from poker_solver.cfr import CFRSolver, collect_infosets, expected_values


class TestNodelockValidation:
    """Test strict probability validation for nodelocks."""

    def test_reject_missing_action_in_lock(self):
        """Lock distribution omits a legal action."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        # Omit one action
        incomplete_lock = {p1_actions[0]: 1.0}
        
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="action.*mismatch|missing"):
            validate_locks(root, {p1_key: incomplete_lock})

    def test_reject_extra_action_in_lock(self):
        """Lock distribution includes an action not in the legal set."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        # Add an extra action
        extra_lock = {a: 0.5 for a in p1_actions}
        extra_lock[Action("Z", 0)] = 0.0
        
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="action.*mismatch|extra"):
            validate_locks(root, {p1_key: extra_lock})

    def test_reject_nonfinite_probability(self):
        """Lock distribution contains NaN or infinite probability."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        # NaN probability
        nan_lock = {p1_actions[0]: float('nan'), p1_actions[1]: 1.0}
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="non-finite"):
            validate_locks(root, {p1_key: nan_lock})
        
        # Infinite probability
        inf_lock = {p1_actions[0]: float('inf'), p1_actions[1]: 0.0}
        with pytest.raises(ValueError, match="non-finite"):
            validate_locks(root, {p1_key: inf_lock})

    def test_reject_negative_probability(self):
        """Lock distribution contains negative probability."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        negative_lock = {p1_actions[0]: -0.1, p1_actions[1]: 1.1}
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="negative"):
            validate_locks(root, {p1_key: negative_lock})

    def test_reject_non_unit_sum(self):
        """Lock distribution probabilities do not sum to 1.0."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        # Sum to 0.99
        low_lock = {p1_actions[0]: 0.49, p1_actions[1]: 0.50}
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="sum"):
            validate_locks(root, {p1_key: low_lock})
        
        # Sum to 1.01
        high_lock = {p1_actions[0]: 0.51, p1_actions[1]: 0.50}
        with pytest.raises(ValueError, match="sum"):
            validate_locks(root, {p1_key: high_lock})

    def test_reject_unknown_key(self):
        """Lock references an InfoKey not in the game tree."""
        root = _matrix_game_root()
        unknown_key = ("UNKNOWN", "key")
        fake_lock = {Action("X", 0): 1.0}
        
        from poker_solver.constraints import validate_locks
        with pytest.raises(ValueError, match="not found"):
            validate_locks(root, {unknown_key: fake_lock})

    def test_accept_valid_lock(self):
        """Valid lock passes validation."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        
        valid_lock = {p1_actions[0]: 0.7, p1_actions[1]: 0.3}
        from poker_solver.constraints import validate_locks
        # Should not raise
        validate_locks(root, {p1_key: valid_lock})

    def test_reject_boolean_probability_and_iteration_count(self):
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        key = _find_p1_key(infosets)
        actions = infosets[key][1]
        from poker_solver.constraints import ConstrainedCFRSolver, validate_locks

        with pytest.raises((TypeError, ValueError), match="boolean"):
            validate_locks(root, {key: {actions[0]: True, actions[1]: 0.0}})
        with pytest.raises(ValueError, match="positive integer"):
            ConstrainedCFRSolver(root, {}).train(True)


class TestBehaviorProfiles:
    def test_profile_resolves_complete_scaled_locks_with_provenance(self):
        root = _profile_game_root()
        infosets = collect_infosets(root)
        key = _find_p1_key(infosets)
        actions = infosets[key][1]
        baseline = {key: {actions[0]: 0.25, actions[1]: 0.75}}
        from poker_solver.constraints import BehaviorProfile, resolve_profile_locks

        profile = BehaviorProfile(
            target_seat=1,
            baseline=baseline,
            multipliers={"fold": 1, "check": 1, "call": 1, "aggressive": 2},
            baseline_provenance="fixture-v1",
        )
        resolved = resolve_profile_locks(root, profile)

        assert resolved.provenance == "fixture-v1"
        assert resolved.locks[key][actions[0]] == pytest.approx(0.4)
        assert resolved.locks[key][actions[1]] == pytest.approx(0.6)
        assert isinstance(resolved.locks, MappingProxyType)
        with pytest.raises(TypeError):
            resolved.locks[key] = {}  # type: ignore[index]

    def test_profile_rejects_zero_denominator_and_hidden_conditioning(self):
        root = _profile_game_root()
        infosets = collect_infosets(root)
        key = _find_p1_key(infosets)
        actions = infosets[key][1]
        from poker_solver.constraints import BehaviorProfile, resolve_profile_locks

        with pytest.raises(ValueError, match="public-observable"):
            BehaviorProfile(
                1,
                {key: {actions[0]: 0.5, actions[1]: 0.5}},
                {"fold": 1, "check": 1, "call": 1, "aggressive": 1},
                "fixture",
                conditioning_fields=("private_cards",),
            )
        profile = BehaviorProfile(
            1,
            {key: {actions[0]: 0.5, actions[1]: 0.5}},
            {"fold": 0, "check": 0, "call": 0, "aggressive": 0},
            "fixture",
        )
        with pytest.raises(ValueError, match="zero denominator"):
            resolve_profile_locks(root, profile)


class TestConstrainedCFRTraversal:
    """Test constrained CFR traversal with locks."""

    def test_lock_p1_to_x_only(self):
        """Lock P1 to always choose X; P0 should best-respond with A."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        x_action = [a for a in p1_actions if a.kind == "X"][0]
        y_action = [a for a in p1_actions if a.kind == "Y"][0]
        
        locks = {p1_key: {x_action: 1.0, y_action: 0.0}}
        
        from poker_solver.constraints import ConstrainedCFRSolver
        solver = ConstrainedCFRSolver(root, locks)
        solver.train(1000)
        
        strategy = solver.average_strategy()
        
        # P1 should play exactly the lock
        assert abs(strategy[p1_key][x_action] - 1.0) < 1e-3
        assert abs(strategy[p1_key][y_action] - 0.0) < 1e-3
        
        # P0 should best-respond with A (EV=2 vs B EV=0)
        p0_key = _find_p0_key(infosets)
        p0_actions = infosets[p0_key][1]
        a_action = [a for a in p0_actions if a.kind == "A"][0]
        assert strategy[p0_key][a_action] > 0.95
        
        # Expected value should be 2.0
        ev = expected_values(root, strategy)
        assert abs(ev[0] - 2.0) < 1e-2

    def test_lock_p1_to_y_only(self):
        """Lock P1 to always choose Y; P0 should best-respond with B."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        x_action = [a for a in p1_actions if a.kind == "X"][0]
        y_action = [a for a in p1_actions if a.kind == "Y"][0]
        
        locks = {p1_key: {x_action: 0.0, y_action: 1.0}}
        
        from poker_solver.constraints import ConstrainedCFRSolver
        solver = ConstrainedCFRSolver(root, locks)
        solver.train(1000)
        
        strategy = solver.average_strategy()
        
        # P1 should play exactly the lock
        assert abs(strategy[p1_key][y_action] - 1.0) < 1e-3
        
        # P0 should best-respond with B (EV=1 vs A EV=-1)
        p0_key = _find_p0_key(infosets)
        p0_actions = infosets[p0_key][1]
        b_action = [a for a in p0_actions if a.kind == "B"][0]
        assert strategy[p0_key][b_action] > 0.95
        
        # Expected value should be 1.0
        ev = expected_values(root, strategy)
        assert abs(ev[0] - 1.0) < 1e-2

    def test_lock_p1_mixed(self):
        """Lock P1 to 50/50 mix; P0 should best-respond with A."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        x_action = [a for a in p1_actions if a.kind == "X"][0]
        y_action = [a for a in p1_actions if a.kind == "Y"][0]
        
        locks = {p1_key: {x_action: 0.5, y_action: 0.5}}
        
        from poker_solver.constraints import ConstrainedCFRSolver
        solver = ConstrainedCFRSolver(root, locks)
        solver.train(1000)
        
        strategy = solver.average_strategy()
        
        # P1 should play exactly the lock
        assert abs(strategy[p1_key][x_action] - 0.5) < 1e-3
        assert abs(strategy[p1_key][y_action] - 0.5) < 1e-3
        
        # P0 should best-respond with A (EV=0.5 vs B EV=0.5)
        # Actually A gives 2*0.5 + (-1)*0.5 = 0.5, B gives 0*0.5 + 1*0.5 = 0.5
        # So P0 is indifferent, but should converge to one or mix
        ev = expected_values(root, strategy)
        assert abs(ev[0] - 0.5) < 1e-2

    def test_lock_preserved_over_training(self):
        """Lock remains exact over multiple training calls."""
        root = _matrix_game_root()
        infosets = collect_infosets(root)
        p1_key = _find_p1_key(infosets)
        p1_actions = infosets[p1_key][1]
        x_action = [a for a in p1_actions if a.kind == "X"][0]
        y_action = [a for a in p1_actions if a.kind == "Y"][0]
        
        locks = {p1_key: {x_action: 0.7, y_action: 0.3}}
        
        from poker_solver.constraints import ConstrainedCFRSolver
        solver = ConstrainedCFRSolver(root, locks)
        solver.train(500)
        
        strategy1 = solver.average_strategy()
        assert abs(strategy1[p1_key][x_action] - 0.7) < 1e-3
        
        solver.train(500)
        strategy2 = solver.average_strategy()
        assert abs(strategy2[p1_key][x_action] - 0.7) < 1e-3


def _matrix_game_root():
    """One-step matrix game: P0 chooses A/B, P1 chooses X/Y.
    
    P0 payoff matrix:
            X   Y
        A   2  -1
        B   0   1
    """
    class MatrixGame:
        def __init__(self, p0_choice=None, p1_choice=None):
            self.p0_choice = p0_choice
            self.p1_choice = p1_choice
        
        def current_player(self):
            if self.p0_choice is None:
                return 0
            if self.p1_choice is None:
                return 1
            return TERMINAL
        
        def legal_actions(self):
            if self.p0_choice is None:
                return (Action("A", 0), Action("B", 0))
            if self.p1_choice is None:
                return (Action("X", 0), Action("Y", 0))
            return ()
        
        def chance_outcomes(self):
            return ()
        
        def child(self, action):
            if self.p0_choice is None:
                return MatrixGame(p0_choice=action.kind, p1_choice=None)
            if self.p1_choice is None:
                return MatrixGame(p0_choice=self.p0_choice, p1_choice=action.kind)
            raise ValueError("terminal state has no children")
        
        def information_state_key(self, player):
            if player == 0:
                return ("P0", self.p0_choice)
            else:
                # P1 cannot see P0's choice (imperfect information)
                return ("P1", "blind")
        
        def returns(self):
            if self.p0_choice == "A" and self.p1_choice == "X":
                return (2.0, -2.0)
            elif self.p0_choice == "A" and self.p1_choice == "Y":
                return (-1.0, 1.0)
            elif self.p0_choice == "B" and self.p1_choice == "X":
                return (0.0, 0.0)
            elif self.p0_choice == "B" and self.p1_choice == "Y":
                return (1.0, -1.0)
            raise ValueError("invalid terminal state")
    
    return MatrixGame()


def _profile_game_root():
    class ProfileGame:
        def __init__(self, choice=None):
            self.choice = choice

        def current_player(self):
            return 1 if self.choice is None else TERMINAL

        def legal_actions(self):
            return (Action("RAISE", 10), Action("CALL", 5)) if self.choice is None else ()

        def chance_outcomes(self):
            return ()

        def child(self, action):
            return ProfileGame(action)

        def information_state_key(self, player):
            return ("profile", player)

        def returns(self):
            return (0.0, 0.0)

    return ProfileGame()


def _find_p1_key(infosets):
    """Find P1's information key in the matrix game."""
    for key, (player, actions) in infosets.items():
        if player == 1:
            return key
    raise ValueError("P1 key not found")


def _find_p0_key(infosets):
    """Find P0's information key in the matrix game."""
    for key, (player, actions) in infosets.items():
        if player == 0:
            return key
    raise ValueError("P0 key not found")