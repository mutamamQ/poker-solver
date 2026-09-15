"""
Test exact small-field ICM equity calculation.

Vertical TDD: tests written first, must fail before implementation.
Independent Fraction-based permutation oracle for validation.
"""

import pytest
from fractions import Fraction
from itertools import permutations


# ============================================================================
# Independent Fraction-based permutation oracle (test-only)
# ============================================================================

def icm_equity_oracle(stacks: tuple, payouts: tuple) -> tuple:
    """
    Independent permutation-based ICM oracle using exact Fraction arithmetic.
    
    For each finish order permutation, compute probability as:
    P(order) = product_{k=1..n} s_ik / (S - sum_{j<k} s_ij)
    
    Player equity is sum over all orders of P(order) * payout[place].
    """
    n = len(stacks)
    assert len(payouts) >= n, "Must have at least n payouts"
    
    # Convert to Fraction for exact arithmetic
    stacks_frac = [Fraction(s) for s in stacks]
    payouts_frac = [Fraction(p) for p in payouts[:n]]
    
    total_stack = sum(stacks_frac)
    
    # Accumulate equity for each player
    equities = [Fraction(0) for _ in range(n)]
    
    # Enumerate all finish order permutations
    for order in permutations(range(n)):
        # Compute probability of this finish order
        prob = Fraction(1)
        remaining_stack = total_stack
        
        for place_idx, player_idx in enumerate(order):
            prob *= stacks_frac[player_idx] / remaining_stack
            remaining_stack -= stacks_frac[player_idx]
        
        # Add contribution to each player's equity
        for place_idx, player_idx in enumerate(order):
            equities[player_idx] += prob * payouts_frac[place_idx]
    
    return tuple(equities)


# ============================================================================
# Test fixtures: validation failures before implementation
# ============================================================================

def test_public_icm_evaluator_exists():
    """The bounded ICM module exposes one deterministic evaluator."""
    from poker_solver.icm import calculate_icm_equity

    assert callable(calculate_icm_equity)


def test_validation_positive_stacks():
    """RED: Must reject zero or negative stacks."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(ValueError, match="positive"):
        calculate_icm_equity([0, 100], [100, 0])
    
    with pytest.raises(ValueError, match="positive"):
        calculate_icm_equity([-10, 100], [100, 0])
    
    with pytest.raises(ValueError, match="positive"):
        calculate_icm_equity([50, 0, 50], [100, 50, 0])


def test_validation_nonincreasing_payouts():
    """RED: Payouts must be non-increasing."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(ValueError, match="non-increasing"):
        calculate_icm_equity([50, 50], [50, 100])
    
    with pytest.raises(ValueError, match="non-increasing"):
        calculate_icm_equity([30, 30, 40], [100, 80, 90])


def test_validation_nonnegative_payouts():
    """RED: Payouts must be non-negative."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(ValueError, match="non-negative"):
        calculate_icm_equity([50, 50], [100, -10])


def test_validation_finite_values():
    """RED: Must reject NaN and infinity."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(ValueError, match="finite"):
        calculate_icm_equity([float('nan'), 50], [100, 0])
    
    with pytest.raises(ValueError, match="finite"):
        calculate_icm_equity([50, float('inf')], [100, 0])
    
    with pytest.raises(ValueError, match="finite"):
        calculate_icm_equity([50, 50], [float('inf'), 0])


def test_validation_no_booleans():
    """RED: Must reject boolean values."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(TypeError, match="bool"):
        calculate_icm_equity([True, 50], [100, 0])
    
    with pytest.raises(TypeError, match="bool"):
        calculate_icm_equity([50, 50], [True, False])


def test_validation_sufficient_payouts():
    """RED: Must have at least as many payouts as players."""
    from poker_solver.icm import calculate_icm_equity
    
    with pytest.raises(ValueError, match="payout"):
        calculate_icm_equity([50, 50, 50], [100, 50])


def test_validation_player_count_limit():
    """RED: Must enforce 10-player limit."""
    from poker_solver.icm import calculate_icm_equity
    
    stacks = [100] * 11
    payouts = [1000 - i*50 for i in range(11)]
    
    with pytest.raises(ValueError, match="10 players"):
        calculate_icm_equity(stacks, payouts)


# ============================================================================
# Exact fixtures from research/phase3/icm-bounties.md
# ============================================================================

def test_exact_fixture_equal_stacks_two_players():
    """RED: Equal stacks (1,1), payouts (100,0) → equities (50,50)."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([1, 1], [100, 0])
    
    # Compare with oracle
    oracle = icm_equity_oracle((1, 1), (100, 0))
    assert len(equities) == 2
    assert abs(equities[0] - float(oracle[0])) < 1e-12
    assert abs(equities[1] - float(oracle[1])) < 1e-12
    
    # Exact expected values
    assert abs(equities[0] - 50.0) < 1e-12
    assert abs(equities[1] - 50.0) < 1e-12


def test_exact_fixture_equal_stacks_three_players():
    """RED: Equal stacks (1,1,1), payouts (100,60,30) → each 190/3."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([1, 1, 1], [100, 60, 30])
    
    oracle = icm_equity_oracle((1, 1, 1), (100, 60, 30))
    expected = float(Fraction(190, 3))
    
    for i in range(3):
        assert abs(equities[i] - float(oracle[i])) < 1e-12
        assert abs(equities[i] - expected) < 1e-12


def test_exact_fixture_unequal_stacks_three_players():
    """RED: Stacks (50,30,20), payouts (100,60,0) → (985/14, 105/2, 260/7)."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([50, 30, 20], [100, 60, 0])
    
    oracle = icm_equity_oracle((50, 30, 20), (100, 60, 0))
    expected = (
        float(Fraction(985, 14)),
        float(Fraction(105, 2)),
        float(Fraction(260, 7))
    )
    
    for i in range(3):
        assert abs(equities[i] - float(oracle[i])) < 1e-12
        assert abs(equities[i] - expected[i]) < 1e-12


def test_exact_fixture_biased_stacks_three_players():
    """RED: Stacks (2,1,1), payouts (100,60,20) → (220/3, 160/3, 160/3)."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([2, 1, 1], [100, 60, 20])
    
    oracle = icm_equity_oracle((2, 1, 1), (100, 60, 20))
    expected = (
        float(Fraction(220, 3)),
        float(Fraction(160, 3)),
        float(Fraction(160, 3))
    )
    
    for i in range(3):
        assert abs(equities[i] - float(oracle[i])) < 1e-12
        assert abs(equities[i] - expected[i]) < 1e-12


# ============================================================================
# Conservation and symmetry properties
# ============================================================================

def test_equity_sum_equals_payout_sum():
    """RED: Sum of equities must equal sum of payouts."""
    from poker_solver.icm import calculate_icm_equity
    
    test_cases = [
        ([1, 1], [100, 0]),
        ([1, 1, 1], [100, 60, 30]),
        ([50, 30, 20], [100, 60, 0]),
        ([100, 200, 300], [1000, 500, 200]),
    ]
    
    for stacks, payouts in test_cases:
        equities = calculate_icm_equity(stacks, payouts)
        total_equity = sum(equities)
        total_payout = sum(payouts[:len(stacks)])
        
        assert abs(total_equity - total_payout) < 1e-12, \
            f"Equity sum {total_equity} != payout sum {total_payout}"


def test_equal_stack_symmetry():
    """RED: Equal stacks must produce equal equities."""
    from poker_solver.icm import calculate_icm_equity
    
    # Two players
    equities = calculate_icm_equity([100, 100], [200, 50])
    assert abs(equities[0] - equities[1]) < 1e-12
    
    # Three players
    equities = calculate_icm_equity([50, 50, 50], [300, 150, 50])
    assert abs(equities[0] - equities[1]) < 1e-12
    assert abs(equities[1] - equities[2]) < 1e-12
    
    # Four players
    equities = calculate_icm_equity([25, 25, 25, 25], [400, 200, 100, 50])
    for i in range(3):
        assert abs(equities[i] - equities[i+1]) < 1e-12


def test_scale_invariance():
    """RED: Scaling all stacks by same factor preserves equities."""
    from poker_solver.icm import calculate_icm_equity
    
    base_stacks = [50, 30, 20]
    payouts = [100, 60, 30]
    
    base_equities = calculate_icm_equity(base_stacks, payouts)
    
    # Scale by various factors
    for scale in [2, 10, 0.5, 100]:
        scaled_stacks = [s * scale for s in base_stacks]
        scaled_equities = calculate_icm_equity(scaled_stacks, payouts)
        
        for i in range(len(base_equities)):
            assert abs(scaled_equities[i] - base_equities[i]) < 1e-12, \
                f"Scale {scale} changed equity at position {i}"


def test_permutation_invariance():
    """RED: Permuting players only permutes output equities."""
    from poker_solver.icm import calculate_icm_equity
    
    stacks = [50, 30, 20]
    payouts = [100, 60, 30]
    
    equities_original = calculate_icm_equity(stacks, payouts)
    
    # Permute: [50,30,20] -> [20,50,30]
    stacks_perm = [20, 50, 30]
    equities_perm = calculate_icm_equity(stacks_perm, payouts)
    
    # Original player 0 (stack 50) is now at position 1
    assert abs(equities_perm[1] - equities_original[0]) < 1e-12
    # Original player 1 (stack 30) is now at position 2
    assert abs(equities_perm[2] - equities_original[1]) < 1e-12
    # Original player 2 (stack 20) is now at position 0
    assert abs(equities_perm[0] - equities_original[2]) < 1e-12


# ============================================================================
# Oracle comparison on exhaustive small grids
# ============================================================================

def test_oracle_agreement_two_players():
    """RED: Production must match oracle for all 2-player cases."""
    from poker_solver.icm import calculate_icm_equity
    
    stack_cases = [(1, 1), (1, 2), (2, 3), (10, 5)]
    payout_cases = [(100, 0), (100, 50), (200, 100)]
    
    for stacks in stack_cases:
        for payouts in payout_cases:
            equities = calculate_icm_equity(list(stacks), list(payouts))
            oracle = icm_equity_oracle(stacks, payouts)
            
            for i in range(2):
                assert abs(equities[i] - float(oracle[i])) < 1e-12, \
                    f"Mismatch for stacks={stacks}, payouts={payouts}"


def test_oracle_agreement_three_players():
    """RED: Production must match oracle for 3-player grid."""
    from poker_solver.icm import calculate_icm_equity
    
    stack_cases = [
        (1, 1, 1),
        (2, 1, 1),
        (3, 2, 1),
        (10, 5, 3),
    ]
    payout_cases = [
        (100, 60, 30),
        (100, 50, 0),
        (200, 100, 50),
    ]
    
    for stacks in stack_cases:
        for payouts in payout_cases:
            equities = calculate_icm_equity(list(stacks), list(payouts))
            oracle = icm_equity_oracle(stacks, payouts)
            
            for i in range(3):
                assert abs(equities[i] - float(oracle[i])) < 1e-12, \
                    f"Mismatch for stacks={stacks}, payouts={payouts}"


def test_oracle_agreement_four_players():
    """RED: Production must match oracle for 4-player cases."""
    from poker_solver.icm import calculate_icm_equity
    
    stack_cases = [
        (1, 1, 1, 1),
        (4, 3, 2, 1),
        (10, 8, 5, 2),
    ]
    payout_cases = [
        (400, 250, 150, 100),
        (1000, 600, 300, 100),
    ]
    
    for stacks in stack_cases:
        for payouts in payout_cases:
            equities = calculate_icm_equity(list(stacks), list(payouts))
            oracle = icm_equity_oracle(stacks, payouts)
            
            for i in range(4):
                assert abs(equities[i] - float(oracle[i])) < 1e-12, \
                    f"Mismatch for stacks={stacks}, payouts={payouts}"


# ============================================================================
# Edge cases and boundary conditions
# ============================================================================

def test_single_player():
    """RED: Single player gets first-place payout."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([100], [500, 300, 100])
    assert abs(equities[0] - 500.0) < 1e-12


def test_chip_leader_dominance():
    """RED: Massive chip leader approaches first-place payout."""
    from poker_solver.icm import calculate_icm_equity
    
    equities = calculate_icm_equity([1000000, 1, 1], [100, 60, 30])
    
    # Chip leader should be very close to 100
    assert equities[0] > 99.99
    assert equities[0] < 100.0
    
    # Short stacks split remaining equity
    assert equities[1] > 0
    assert equities[2] > 0
    assert abs(equities[1] - equities[2]) < 1e-10


def test_zero_payouts_for_late_positions():
    """RED: Zero payouts for positions beyond money."""
    from poker_solver.icm import calculate_icm_equity
    
    # Only top 2 paid
    equities = calculate_icm_equity([50, 30, 20], [100, 50, 0])
    
    oracle = icm_equity_oracle((50, 30, 20), (100, 50, 0))
    
    for i in range(3):
        assert abs(equities[i] - float(oracle[i])) < 1e-12
    
    # Third place has positive equity from chance of finishing 2nd
    assert equities[2] > 0


def test_extra_payouts_ignored():
    """RED: Extra payouts beyond player count are ignored."""
    from poker_solver.icm import calculate_icm_equity
    
    # 3 players, but 5 payouts provided
    equities = calculate_icm_equity([50, 30, 20], [100, 60, 30, 10, 5])
    
    # Should match case with exactly 3 payouts
    oracle = icm_equity_oracle((50, 30, 20), (100, 60, 30))
    
    for i in range(3):
        assert abs(equities[i] - float(oracle[i])) < 1e-12


# ============================================================================
# Complexity and performance bounds
# ============================================================================

def test_ten_player_limit_accepted():
    """RED: 10 players should be accepted and computed."""
    from poker_solver.icm import calculate_icm_equity
    
    stacks = [100 - i*5 for i in range(10)]
    payouts = [1000 - i*100 for i in range(10)]
    
    equities = calculate_icm_equity(stacks, payouts)
    
    assert len(equities) == 10
    assert abs(sum(equities) - sum(payouts)) < 1e-12


def test_deterministic_output():
    """RED: Multiple calls with same input produce identical output."""
    from poker_solver.icm import calculate_icm_equity
    
    stacks = [50, 30, 20, 15, 10]
    payouts = [500, 300, 200, 100, 50]
    
    equities1 = calculate_icm_equity(stacks, payouts)
    equities2 = calculate_icm_equity(stacks, payouts)
    equities3 = calculate_icm_equity(stacks, payouts)
    
    for i in range(5):
        assert equities1[i] == equities2[i]
        assert equities2[i] == equities3[i]


# ============================================================================
# Integration: no tournament strategy claims
# ============================================================================

def test_no_strategy_solving_claim():
    """
    ICM is a utility evaluator, not a strategy solver.
    This test documents that boundary.
    """
    # This is a documentation test - ICM computes equity given stacks,
    # it does NOT solve for optimal tournament strategy, future bounty EV,
    # or provide exploitability guarantees.
    pass
