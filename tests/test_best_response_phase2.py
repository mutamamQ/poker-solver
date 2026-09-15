"""Independent adversarial tests for scalable best-response implementation.

Compares best_response and exhaustive_best_response to <=1e-12 across:
- Uniform and trained Kuhn profiles for both players
- Compact river profiles if tractable
- Hidden-bit information trap
- Malformed opponent profile
- Constructed perfect-information chain with impractical Cartesian enumeration
"""

from dataclasses import dataclass

import pytest

from poker_solver.best_response import best_response, exhaustive_best_response
from poker_solver.cards import parse_cards
from poker_solver.cfr import CFRSolver, collect_infosets
from poker_solver.equity import WeightedCombo
from poker_solver.kuhn import kuhn_root
from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.river import RiverConfig, river_root

D0 = Action("deal", 0)
D1 = Action("deal", 1)
G0 = Action("guess", 0)
G1 = Action("guess", 1)


def combo(text, weight=1.0):
    """Helper to create WeightedCombo from text like 'As 5s'."""
    cards = parse_cards(text.split())
    return WeightedCombo((cards[0], cards[1]), weight)


@dataclass(frozen=True)
class HiddenBitState:
    """Information trap: responder has no information about chance outcome."""
    bit: int | None = None
    guess: int | None = None

    def current_player(self):
        return CHANCE if self.bit is None else 1 if self.guess is None else TERMINAL

    def legal_actions(self):
        return (D0, D1) if self.bit is None else (G0, G1) if self.guess is None else ()

    def chance_outcomes(self):
        return ((D0, 0.5), (D1, 0.5)) if self.bit is None else ()

    def child(self, action):
        if action not in self.legal_actions():
            raise ValueError
        return HiddenBitState(action.amount, None) if self.bit is None else HiddenBitState(self.bit, action.amount)

    def information_state_key(self, player):
        if self.current_player() != player:
            raise ValueError
        return ("hidden-guess", player)

    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError
        p1 = 1.0 if self.bit == self.guess else -1.0
        return (-p1, p1)


@dataclass(frozen=True)
class PerfectInfoChain:
    """Perfect-information chain with many responder infosets.
    
    Cartesian enumeration is impractical (2^depth pure strategies),
    but dynamic BR has analytically obvious value.
    """
    depth: int
    position: int = 0
    stopped: bool = False

    def current_player(self):
        if self.stopped or self.position >= self.depth:
            return TERMINAL
        return self.position % 2

    def legal_actions(self):
        if self.current_player() == TERMINAL:
            return ()
        return (Action("left"), Action("right"))

    def chance_outcomes(self):
        return ()

    def child(self, action):
        if action not in self.legal_actions():
            raise ValueError
        if action.kind == "left":
            return PerfectInfoChain(self.depth, self.position, True)
        return PerfectInfoChain(self.depth, self.position + 1)

    def information_state_key(self, player):
        if self.current_player() != player:
            raise ValueError
        return ("chain", player, self.position)

    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError
        # Player 0 gets +1 at even depth, -1 at odd depth
        value = 1.0 if self.depth % 2 == 0 else -1.0
        return (value, -value)


def uniform_strategy(root):
    """Build uniform random strategy for all infosets."""
    infosets = collect_infosets(root)
    strategy = {}
    for key, (_, actions) in infosets.items():
        prob = 1.0 / len(actions)
        strategy[key] = {action: prob for action in actions}
    return strategy


def test_kuhn_uniform_player0():
    """Kuhn uniform profile, player 0 best response."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    value_scalable, response_scalable = best_response(root, profile, 0)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 0)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_kuhn_uniform_player1():
    """Kuhn uniform profile, player 1 best response."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_kuhn_trained_player0():
    """Kuhn trained profile, player 0 best response."""
    root = kuhn_root()
    solver = CFRSolver(root)
    profile = solver.train(1000)
    value_scalable, response_scalable = best_response(root, profile, 0)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 0)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_kuhn_trained_player1():
    """Kuhn trained profile, player 1 best response."""
    root = kuhn_root()
    solver = CFRSolver(root)
    profile = solver.train(1000)
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_compact_river_uniform_player0():
    """Compact river uniform profile, player 0 best response."""
    config = RiverConfig(
        parse_cards("2c 3d 4h 9s Kc".split()),
        2.0,
        1,
        1,
        (combo("As 5s"),),
        (combo("Kh Qh"),),
    )
    root = river_root(config)
    profile = uniform_strategy(root)
    value_scalable, response_scalable = best_response(root, profile, 0)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 0)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_compact_river_uniform_player1():
    """Compact river uniform profile, player 1 best response."""
    config = RiverConfig(
        parse_cards("2c 3d 4h 9s Kc".split()),
        2.0,
        1,
        1,
        (combo("As 5s"),),
        (combo("Kh Qh"),),
    )
    root = river_root(config)
    profile = uniform_strategy(root)
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert set(response_scalable.keys()) == set(response_exhaustive.keys())


def test_hidden_bit_uniform():
    """Hidden-bit information trap, uniform profile."""
    root = HiddenBitState()
    profile = {("hidden-guess", 1): {G0: 0.5, G1: 0.5}}
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert value_scalable == pytest.approx(0.0)


def test_hidden_bit_biased():
    """Hidden-bit information trap, biased profile."""
    root = HiddenBitState()
    profile = {("hidden-guess", 1): {G0: 0.7, G1: 0.3}}
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    assert value_scalable == pytest.approx(0.0)


def test_malformed_opponent_profile_missing_key():
    """Malformed opponent profile: missing information set."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    # Remove one opponent infoset
    opponent_keys = [k for k, (owner, _) in collect_infosets(root).items() if owner == 1]
    if opponent_keys:
        del profile[opponent_keys[0]]
        with pytest.raises(ValueError, match="missing opponent policy"):
            best_response(root, profile, 0)


def test_malformed_opponent_profile_wrong_actions():
    """Malformed opponent profile: wrong action set."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    opponent_keys = [k for k, (owner, _) in collect_infosets(root).items() if owner == 1]
    if opponent_keys:
        key = opponent_keys[0]
        profile[key] = {Action("invalid"): 1.0}
        with pytest.raises(ValueError, match="wrong opponent actions"):
            best_response(root, profile, 0)


def test_malformed_opponent_profile_invalid_probability():
    """Malformed opponent profile: negative probability."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    opponent_keys = [k for k, (owner, _) in collect_infosets(root).items() if owner == 1]
    if opponent_keys:
        key = opponent_keys[0]
        actions = list(profile[key].keys())
        profile[key] = {actions[0]: -0.5, actions[1]: 1.5}
        with pytest.raises(ValueError, match="invalid opponent probability"):
            best_response(root, profile, 0)


def test_malformed_opponent_profile_probabilities_not_sum_to_one():
    """Malformed opponent profile: probabilities don't sum to one."""
    root = kuhn_root()
    profile = uniform_strategy(root)
    opponent_keys = [k for k, (owner, _) in collect_infosets(root).items() if owner == 1]
    if opponent_keys:
        key = opponent_keys[0]
        actions = list(profile[key].keys())
        profile[key] = {a: 0.3 for a in actions}
        with pytest.raises(ValueError, match="do not sum to one"):
            best_response(root, profile, 0)


def test_perfect_info_chain_depth_20():
    """Perfect-information chain with 20 infosets (2^20 pure strategies).
    
    Cartesian enumeration is impractical, but dynamic BR is trivial.
    Player 0 moves at even positions, player 1 at odd positions.
    At depth 20 (even), player 0 wins by choosing optimally.
    """
    root = PerfectInfoChain(depth=20)
    # Uniform opponent strategy
    profile = uniform_strategy(root)
    
    # Player 0 best response
    value_scalable, response_scalable = best_response(root, profile, 0)
    # Exhaustive would enumerate 2^10 = 1024 pure strategies for player 0
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 0)
    
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    # With uniform opponent, player 0 can guarantee +1.0
    assert value_scalable == pytest.approx(1.0)
    assert len(response_scalable) == 10  # Player 0 has 10 infosets


def test_perfect_info_chain_depth_21():
    """Perfect-information chain with 21 infosets, odd depth.
    
    At depth 21 (odd), player 1 wins by choosing optimally.
    """
    root = PerfectInfoChain(depth=21)
    profile = uniform_strategy(root)
    
    # Player 1 best response
    value_scalable, response_scalable = best_response(root, profile, 1)
    value_exhaustive, response_exhaustive = exhaustive_best_response(root, profile, 1)
    
    assert abs(value_scalable - value_exhaustive) <= 1e-12
    # With uniform opponent, player 1 can guarantee +1.0
    assert value_scalable == pytest.approx(1.0)
    assert len(response_scalable) == 10  # Player 1 has 10 infosets (positions 1,3,5,...,19)


def test_dynamic_path_scales_beyond_cartesian_oracle():
    """Thirty responder infosets imply over one billion pure strategies."""
    root = PerfectInfoChain(depth=60)
    profile = uniform_strategy(root)
    value, response = best_response(root, profile, 0)
    assert value == pytest.approx(1.0)
    assert len(response) == 30
