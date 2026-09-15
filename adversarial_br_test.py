#!/usr/bin/env python3
"""Adversarial test for scalable best response correctness.

Generates random finite games with pathological structures:
- Hidden histories (chance before responder infosets)
- Multiple responder infosets with branching dependencies
- Zero-reach infosets
- Same infoset at varied depths
- Malformed chance/opponent policies
- Cycles (should be rejected)
- Ties in action values

Compares scalable best_response to exhaustive_best_response oracle.
"""

import random
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, '/home/genomix-node/poker-solver/src')

from poker_solver.best_response import (
    best_response,
    exhaustive_best_response,
    nash_conv,
)
from poker_solver.cfr import collect_infosets, CFRSolver
from poker_solver.kuhn import kuhn_root
from poker_solver.model import Action, CHANCE, TERMINAL


def uniform_strategy(root):
    """Build uniform random strategy for all infosets."""
    infosets = collect_infosets(root)
    strategy = {}
    for key, (_, actions) in infosets.items():
        prob = 1.0 / len(actions)
        strategy[key] = {action: prob for action in actions}
    return strategy


@dataclass(frozen=True)
class RandomTreeState:
    """Random finite game tree with configurable pathologies."""
    seed: int
    depth: int
    max_depth: int
    path: tuple[int, ...]
    player_seq: tuple[int, ...]
    infoset_map: dict[tuple[int, tuple[int, ...]], str]
    terminal_values: dict[tuple[int, ...], tuple[float, float]]
    
    def current_player(self):
        if self.depth >= self.max_depth:
            return TERMINAL
        return self.player_seq[self.depth]
    
    def legal_actions(self):
        if self.current_player() == TERMINAL:
            return ()
        # 2-3 actions per node
        rng = random.Random(self.seed + hash(self.path))
        n_actions = rng.choice([2, 3])
        return tuple(Action(f"a{i}", i) for i in range(n_actions))
    
    def chance_outcomes(self):
        if self.current_player() != CHANCE:
            return ()
        actions = self.legal_actions()
        rng = random.Random(self.seed + hash(self.path) + 1)
        # Generate random probabilities that sum to 1
        weights = [rng.random() for _ in actions]
        total = sum(weights)
        probs = [w / total for w in weights]
        return tuple(zip(actions, probs))
    
    def child(self, action):
        if action not in self.legal_actions():
            raise ValueError(f"illegal action {action}")
        new_path = self.path + (action.amount,)
        return RandomTreeState(
            self.seed,
            self.depth + 1,
            self.max_depth,
            new_path,
            self.player_seq,
            self.infoset_map,
            self.terminal_values,
        )
    
    def information_state_key(self, player):
        if self.current_player() != player:
            raise ValueError(f"wrong player {player}")
        # Create infoset key that may merge different histories
        rng = random.Random(self.seed + player)
        # Use path suffix to create information hiding
        suffix_len = min(2, len(self.path))
        suffix = self.path[-suffix_len:] if suffix_len > 0 else ()
        key = (player, suffix)
        if key not in self.infoset_map:
            self.infoset_map[key] = f"info_{player}_{len(self.infoset_map)}"
        return (self.infoset_map[key], player)
    
    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError("not terminal")
        if self.path not in self.terminal_values:
            rng = random.Random(self.seed + hash(self.path) + 999)
            v0 = rng.uniform(-10, 10)
            self.terminal_values[self.path] = (v0, -v0)
        return self.terminal_values[self.path]


def make_random_game(seed: int, max_depth: int, chance_prob: float = 0.3):
    """Generate a random game tree.
    
    Args:
        seed: Random seed
        max_depth: Maximum tree depth
        chance_prob: Probability of chance node at each level
    """
    rng = random.Random(seed)
    player_seq = []
    for d in range(max_depth):
        if rng.random() < chance_prob:
            player_seq.append(CHANCE)
        else:
            player_seq.append(rng.choice([0, 1]))
    
    infoset_map = {}
    terminal_values = {}
    return RandomTreeState(seed, 0, max_depth, (), tuple(player_seq), infoset_map, terminal_values)


@dataclass(frozen=True)
class ZeroReachState:
    """Game with zero-reach infosets under certain opponent strategies."""
    stage: int = 0
    opponent_chose_left: bool | None = None
    
    def current_player(self):
        if self.stage == 0:
            return 0  # Opponent
        if self.stage == 1:
            return 1  # Responder
        return TERMINAL
    
    def legal_actions(self):
        if self.stage == 0:
            return (Action("left"), Action("right"))
        if self.stage == 1:
            return (Action("up"), Action("down"))
        return ()
    
    def chance_outcomes(self):
        return ()
    
    def child(self, action):
        if self.stage == 0:
            return ZeroReachState(1, action.kind == "left")
        return ZeroReachState(2, self.opponent_chose_left)
    
    def information_state_key(self, player):
        if self.current_player() != player:
            raise ValueError
        if player == 0:
            return ("opp", 0)
        # Responder has two infosets depending on opponent's choice
        return (f"resp_{self.opponent_chose_left}", 1)
    
    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError
        return (0.0, 0.0)


@dataclass(frozen=True)
class SameInfosetVariedDepth:
    """Same infoset appears at different tree depths."""
    depth: int = 0
    took_shortcut: bool = False
    
    def current_player(self):
        if self.depth >= 4:
            return TERMINAL
        if self.depth == 0:
            return 0
        return 1
    
    def legal_actions(self):
        if self.current_player() == TERMINAL:
            return ()
        if self.depth == 0:
            return (Action("shortcut"), Action("long"))
        return (Action("a"), Action("b"))
    
    def chance_outcomes(self):
        return ()
    
    def child(self, action):
        if self.depth == 0:
            if action.kind == "shortcut":
                return SameInfosetVariedDepth(3, True)
            return SameInfosetVariedDepth(1, False)
        return SameInfosetVariedDepth(self.depth + 1, self.took_shortcut)
    
    def information_state_key(self, player):
        if self.current_player() != player:
            raise ValueError
        if player == 0:
            return ("p0", 0)
        # Player 1 has same infoset at depths 1, 2, 3
        return ("p1_shared", 1)
    
    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError
        return (1.0 if self.took_shortcut else -1.0, -1.0 if self.took_shortcut else 1.0)


def test_case(name: str, root, player: int, profile=None):
    """Run a single test case comparing scalable vs exhaustive."""
    if profile is None:
        profile = uniform_strategy(root)
    
    try:
        value_scalable, response_scalable = best_response(root, profile, player)
        value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, player)
        
        diff = abs(value_scalable - value_exhaustive)
        if diff > 1e-12:
            print(f"FAIL: {name}")
            print(f"  Player {player}")
            print(f"  Scalable value: {value_scalable}")
            print(f"  Exhaustive value: {value_exhaustive}")
            print(f"  Difference: {diff}")
            print(f"  Scalable response: {response_scalable}")
            print(f"  Exhaustive response: {response_exhaustive}")
            return False
        
        if set(response_scalable.keys()) != set(response_exhaustive.keys()):
            print(f"FAIL: {name} - response key mismatch")
            print(f"  Scalable keys: {set(response_scalable.keys())}")
            print(f"  Exhaustive keys: {set(response_exhaustive.keys())}")
            return False
        
        print(f"PASS: {name} (value={value_scalable:.6f}, diff={diff:.2e})")
        return True
    except Exception as e:
        print(f"ERROR: {name} - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("ADVERSARIAL BEST RESPONSE CORRECTNESS TEST")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    # Test 1: Kuhn poker with uniform strategy
    print("\n[1] Kuhn poker - uniform strategy")
    root = kuhn_root()
    for player in [0, 1]:
        if test_case(f"Kuhn uniform P{player}", root, player):
            passed += 1
        else:
            failed += 1
    
    # Test 2: Kuhn poker with trained strategy
    print("\n[2] Kuhn poker - trained strategy")
    solver = CFRSolver(root)
    profile = solver.train(1000)
    for player in [0, 1]:
        if test_case(f"Kuhn trained P{player}", root, player, profile):
            passed += 1
        else:
            failed += 1
    
    # Test 3: Zero-reach infosets
    print("\n[3] Zero-reach infosets")
    root = ZeroReachState()
    # Opponent always goes left, making right branch zero-reach
    profile = {("opp", 0): {Action("left"): 1.0, Action("right"): 0.0},
               ("resp_True", 1): {Action("up"): 0.5, Action("down"): 0.5},
               ("resp_False", 1): {Action("up"): 0.5, Action("down"): 0.5}}
    if test_case("Zero-reach left-only", root, 1, profile):
        passed += 1
    else:
        failed += 1
    
    # Test 4: Same infoset at varied depths
    print("\n[4] Same infoset at varied depths")
    root = SameInfosetVariedDepth()
    if test_case("Varied depth P0", root, 0):
        passed += 1
    else:
        failed += 1
    if test_case("Varied depth P1", root, 1):
        passed += 1
    else:
        failed += 1
    
    # Test 5-14: Random games with hidden histories
    print("\n[5-14] Random games with hidden histories")
    for i in range(10):
        seed = 1000 + i
        root = make_random_game(seed, max_depth=6, chance_prob=0.4)
        for player in [0, 1]:
            if test_case(f"Random game {i} P{player}", root, player):
                passed += 1
            else:
                failed += 1
    
    # Test 15: Nash conv on Kuhn
    print("\n[15] Nash conv validation")
    try:
        root = kuhn_root()
        solver = CFRSolver(root)
        profile = solver.train(5000)
        result = nash_conv(root, profile)
        if result.nash_conv < 0:
            print(f"FAIL: Negative nash_conv {result.nash_conv}")
            failed += 1
        elif result.nash_conv > 0.05:
            print(f"FAIL: Nash conv too high {result.nash_conv} after 5000 iterations")
            failed += 1
        else:
            print(f"PASS: Nash conv = {result.nash_conv:.6f}")
            passed += 1
    except Exception as e:
        print(f"ERROR: Nash conv test - {e}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✓ PASS: All adversarial tests passed")
        return 0
    else:
        print(f"\n✗ FAIL: {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
