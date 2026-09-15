"""Test suite for bet sizing conversion and selection.

Phase 3 Wave C1: strict sizing with Decimal conversion, legality filtering,
Fixed/Dynamic/Automatic modes, and independent exhaustive subset oracle.
"""

import pytest
from decimal import Decimal


class TestSizeExpressionValidation:
    """Strict size expression schema validation."""

    def test_pot_percent_requires_value(self):
        """Pot-percent expression must have numeric value field."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="value"):
            validate_size_expression({"unit": "pot-percent"})
    
    def test_rejects_boolean_value(self):
        """Boolean values are strictly rejected in numeric fields."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="boolean"):
            validate_size_expression({"unit": "pot-percent", "value": True})
    
    def test_rejects_nonfinite_value(self):
        """NaN and infinity are rejected."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="finite"):
            validate_size_expression({"unit": "pot-percent", "value": float('nan')})
        
        with pytest.raises(ValueError, match="finite"):
            validate_size_expression({"unit": "pot-percent", "value": float('inf')})
    
    def test_geometric_requires_streets_and_scale(self):
        """Geometric expression must have streets and scale."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="streets"):
            validate_size_expression({"unit": "geometric", "scale": 1})
        
        with pytest.raises(ValueError, match="scale"):
            validate_size_expression({"unit": "geometric", "streets": 2})
    
    def test_geometric_rejects_zero_streets(self):
        """Geometric streets must be positive."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="positive"):
            validate_size_expression({"unit": "geometric", "streets": 0, "scale": 1})
    
    def test_geometric_rejects_nonpositive_scale(self):
        """Geometric scale must be positive."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="positive"):
            validate_size_expression({"unit": "geometric", "streets": 2, "scale": 0})
    
    def test_all_in_rejects_extra_fields(self):
        """All-in expression must not have value/streets/scale."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="extra"):
            validate_size_expression({"unit": "all-in", "value": 100})
    
    def test_unknown_unit_rejected(self):
        """Unknown unit strings are rejected."""
        from poker_solver.sizing import validate_size_expression
        
        with pytest.raises(ValueError, match="unknown unit"):
            validate_size_expression({"unit": "magic"})


class TestPotPercentConversion:
    """Pot-percent formula conversion with Decimal rounding."""

    def test_unopened_pot_percent(self):
        """Unopened pot-percent: target = own + q*P."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "pot-percent", "value": 75}, context)
        assert result == 75  # 0 + 0.75*100 = 75
    
    def test_facing_wager_pot_percent(self):
        """Facing wager pot-percent: target = own_call + q*P_call."""
        from poker_solver.sizing import convert_size_to_chips
        
        # Pot 150, opponent bet 50, actor committed 0
        # P_call = 150 + 50 = 200, own_call = 0 + 50 = 50
        # 100% pot raise: 50 + 1.0*200 = 250
        context = {
            "pot": 150,
            "own_commitment": 0,
            "highest_commitment": 50,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "pot-percent", "value": 100}, context)
        assert result == 250
    
    def test_pot_percent_half_up_rounding(self):
        """Pot-percent uses ROUND_HALF_UP."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        # 33% of 100 = 33.333... rounds to 33
        result = convert_size_to_chips({"unit": "pot-percent", "value": 33}, context)
        assert result == 33
        
        # 66.5 rounds up to 67
        result = convert_size_to_chips({"unit": "pot-percent", "value": 66.5}, context)
        assert result == 67


class TestPreviousBetMultiple:
    """Previous-bet-multiple conversion."""

    def test_previous_bet_multiple_basic(self):
        """Previous-bet multiple: target = m * highest_commitment."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 150,
            "own_commitment": 0,
            "highest_commitment": 50,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "previous-bet-multiple", "value": 3}, context)
        assert result == 150  # 3 * 50
    
    def test_previous_bet_multiple_rounding(self):
        """Previous-bet multiple rounds half-up."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 33,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        # 2.5 * 33 = 82.5 rounds to 83
        result = convert_size_to_chips({"unit": "previous-bet-multiple", "value": 2.5}, context)
        assert result == 83


class TestBigBlinds:
    """Big-blinds conversion."""

    def test_big_blinds_basic(self):
        """Big-blinds: target = value * BB."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 500,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "big-blinds", "value": 2.5}, context)
        assert result == 25  # 2.5 * 10
    
    def test_big_blinds_rounding(self):
        """Big-blinds rounds half-up."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 500,
            "big_blind": 3
        }
        
        # 2.5 * 3 = 7.5 rounds to 8
        result = convert_size_to_chips({"unit": "big-blinds", "value": 2.5}, context)
        assert result == 8


class TestAllIn:
    """All-in conversion."""

    def test_all_in_unopened(self):
        """All-in unopened: target = own + remaining."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 10,
            "highest_commitment": 10,
            "remaining_stack": 200,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "all-in"}, context)
        assert result == 210  # 10 + 200
    
    def test_all_in_facing_wager(self):
        """All-in facing wager: target = own + remaining."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 150,
            "own_commitment": 0,
            "highest_commitment": 50,
            "remaining_stack": 300,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "all-in"}, context)
        assert result == 300  # 0 + 300


class TestGeometric:
    """Geometric sizing conversion."""

    def test_geometric_unopened_basic(self):
        """Geometric unopened: g = ((1 + 2*S/P)**(1/n) - 1)/2."""
        from poker_solver.sizing import convert_size_to_chips
        
        # P=100, S=100, n=2, scale=1
        # g = ((1 + 2*100/100)**(1/2) - 1)/2 = ((3)**0.5 - 1)/2 ≈ 0.366
        # target = 0 + 0.366*100 ≈ 36.6 rounds to 37
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 100,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "geometric", "streets": 2, "scale": 1}, context)
        assert result == 37
    
    def test_geometric_facing_wager(self):
        """Geometric facing wager uses post-call pot and stack."""
        from poker_solver.sizing import convert_size_to_chips
        
        # Pot 100, opponent bet 50, actor committed 0, remaining 200
        # P_call = 100 + 50 = 150, remaining after call = 200 - 50 = 150
        # g = ((1 + 2*150/150)**(1/2) - 1)/2 = ((3)**0.5 - 1)/2 ≈ 0.366
        # target = (0+50) + 0.366*150 ≈ 50 + 54.9 = 104.9 rounds to 105
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 50,
            "remaining_stack": 200,
            "big_blind": 10
        }
        
        result = convert_size_to_chips({"unit": "geometric", "streets": 2, "scale": 1}, context)
        assert result == 105
    
    def test_geometric_scale_multiplier(self):
        """Geometric scale multiplies the fraction."""
        from poker_solver.sizing import convert_size_to_chips
        
        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 100,
            "big_blind": 10
        }
        
        # scale=0.5 halves the geometric fraction
        result = convert_size_to_chips({"unit": "geometric", "streets": 2, "scale": 0.5}, context)
        # g ≈ 0.366, scaled = 0.183, target ≈ 18.3 rounds to 18
        assert result == 18


class TestFixedSizingLegality:
    def test_fixed_filters_illegal_targets_and_deduplicates_first_provenance(self):
        from poker_solver.sizing import fixed_sizes

        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 0,
            "remaining_stack": 100,
            "big_blind": 10,
            "minimum_raise_to": 20,
            "pot_limit_max_raise_to": None,
            "short_all_in_allowed": True,
        }
        first = {"unit": "pot-percent", "value": 50}
        duplicate = {"unit": "big-blinds", "value": 5}
        choices = fixed_sizes((first, duplicate, {"unit": "pot-percent", "value": 200}), context)

        assert [(choice.target, choice.expression) for choice in choices] == [(50, first)]

    def test_exact_short_all_in_is_legal_below_full_raise_only_when_allowed(self):
        from poker_solver.sizing import fixed_sizes

        context = {
            "pot": 100,
            "own_commitment": 0,
            "highest_commitment": 80,
            "remaining_stack": 100,
            "big_blind": 10,
            "minimum_raise_to": 120,
            "pot_limit_max_raise_to": None,
            "short_all_in_allowed": True,
        }
        assert [choice.target for choice in fixed_sizes(({"unit": "all-in"},), context)] == [100]
        context["short_all_in_allowed"] = False
        assert fixed_sizes(({"unit": "all-in"},), context) == ()


class TestDynamicAndAutomaticSizing:
    @staticmethod
    def choices():
        from poker_solver.sizing import SizingChoice

        return tuple(SizingChoice({"unit": "big-blinds", "value": target // 10}, target) for target in (20, 40, 60))

    def test_dynamic_exhaustively_maximizes_fixed_cardinality_with_lexical_ties(self):
        from poker_solver.sizing import dynamic_sizes

        choices = self.choices()
        selected = dynamic_sizes(
            choices,
            retained_count=2,
            evaluate=lambda targets: -abs(sum(targets) - 80),
        )
        assert tuple(choice.target for choice in selected.choices) == (20, 60)
        tied = dynamic_sizes(choices, retained_count=2, evaluate=lambda targets: 1.0)
        assert tuple(choice.target for choice in tied.choices) == (20, 40)
        assert len(selected.evaluated) == 3

    def test_automatic_chooses_smallest_subset_within_full_tree_ev_tolerance(self):
        from poker_solver.sizing import automatic_sizes

        choices = self.choices()
        evaluator = lambda targets: float(sum(target in (20, 60) for target in targets))
        exact = automatic_sizes(choices, max_sizes=3, ev_tolerance=0.0, evaluate=evaluator)
        assert tuple(choice.target for choice in exact.choices) == (20, 60)
        tolerant = automatic_sizes(choices, max_sizes=3, ev_tolerance=1.0, evaluate=evaluator)
        assert tuple(choice.target for choice in tolerant.choices) == (20,)
        assert exact.full_tree_ev == 2.0


def test_conversion_rejects_non_strict_expression_and_context_values():
    from poker_solver.sizing import convert_size_to_chips

    context = {
        "pot": 100,
        "own_commitment": 0,
        "highest_commitment": 0,
        "remaining_stack": 100,
        "big_blind": 10,
    }
    with pytest.raises(ValueError, match="exactly"):
        convert_size_to_chips({"unit": "big-blinds", "value": 2, "extra": 1}, context)
    with pytest.raises(ValueError, match="pot"):
        convert_size_to_chips({"unit": "pot-percent", "value": 50}, {**context, "pot": True})
    with pytest.raises(ValueError, match="positive"):
        convert_size_to_chips({"unit": "previous-bet-multiple", "value": 0}, context)
