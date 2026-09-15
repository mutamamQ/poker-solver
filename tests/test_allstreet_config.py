"""Strict configuration and public-contract tests for AllStreetPostflopConfig.

S1-I1 exclusive ownership: tests/test_allstreet_config.py only.
Tests the exact public API in ARCHITECTURE_PHASE4_S1.md:
- immutable/defensively copied AllStreetPostflopConfig
- load_allstreet_config strict exact payload fields
- card/combo/runout validation
- bool/nonfinite/negative/zero-mass rejection
- algorithm seed/iteration validation
- standard requests containing no continuation/payoff table
- truthful result metadata

Tests must import and call poker_solver.allstreet; no pass/placeholders/oracle-only tests.
"""

from __future__ import annotations

import math
import sys
from typing import Any

import pytest

from poker_solver.allstreet import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
)

from poker_solver.equity import WeightedCombo
from poker_solver.cards import parse_card

# Helper to create card integers from string notation
def Card(notation: str) -> int:
    """Parse card notation like 'As', 'Kh' into card integer."""
    return parse_card(notation)


class TestAllStreetPostflopConfigConstruction:
    """Test strict construction and immutability of AllStreetPostflopConfig."""

    def test_minimal_valid_config(self) -> None:
        """Minimal valid configuration constructs successfully."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50, 100, 200),
        )
        assert config.version == "allstreet-postflop-v1"
        assert len(config.starting_board) == 3
        assert config.initial_dead_pot == 100
        assert config.effective_stack == 1000

    def test_version_must_be_exact(self) -> None:
        """Version field must be exactly 'allstreet-postflop-v1'."""
        with pytest.raises(ValueError, match="version"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v2",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_starting_board_must_be_three_cards(self) -> None:
        """Starting board must contain exactly 3 unique cards for flop."""
        with pytest.raises(ValueError, match="3 cards"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_starting_board_cards_must_be_unique(self) -> None:
        """Starting board cards must be unique."""
        with pytest.raises(ValueError, match="unique"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("As"), Card("Kh")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_initial_dead_pot_rejects_negative(self) -> None:
        """Initial dead pot must be non-negative integer."""
        with pytest.raises(ValueError, match="non-negative"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=-100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_initial_dead_pot_rejects_bool(self) -> None:
        """Initial dead pot must reject boolean."""
        with pytest.raises(ValueError, match="integer"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=True,  # type: ignore
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_effective_stack_must_be_positive(self) -> None:
        """Effective stack must be positive integer."""
        with pytest.raises(ValueError, match="positive"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=0,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_effective_stack_rejects_bool(self) -> None:
        """Effective stack must reject boolean."""
        with pytest.raises(ValueError, match="integer"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=False,  # type: ignore
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_combo_weight_must_be_finite(self) -> None:
        """Combo weights must be finite."""
        with pytest.raises(ValueError, match="finite"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=math.inf),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_combo_weight_must_be_nonnegative(self) -> None:
        """Combo weights must be non-negative."""
        with pytest.raises(ValueError, match="non-?negative"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=-1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_combo_weight_zero_is_allowed(self) -> None:
        """Zero weight combos are allowed (for masking)."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(
                WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=0.0),
                WeightedCombo(cards=(Card("Jd"), Card("Td")), weight=1.0),
            ),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert config.player0_combos[0].weight == 0.0

    def test_combo_cards_must_not_overlap_board(self) -> None:
        """Combo cards must not overlap with starting board."""
        with pytest.raises(ValueError, match="overlap"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("As"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_runouts_must_be_two_cards_for_flop(self) -> None:
        """Runouts must contain exactly 2 cards for flop starting street."""
        with pytest.raises(ValueError, match="2 cards"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"),),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_runouts_must_not_overlap_board(self) -> None:
        """Runout cards must not overlap with starting board."""
        with pytest.raises(ValueError, match="overlap"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("As"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_runouts_must_be_unique(self) -> None:
        """Runouts must be unique sequences."""
        with pytest.raises(ValueError, match="unique"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=(
                    (Card("7s"), Card("6s")),
                    (Card("7s"), Card("6s")),
                ),
                betting_mode="no-limit",
                wager_targets=(50,),
            )

    def test_betting_mode_must_be_valid(self) -> None:
        """Betting mode must be 'no-limit' or 'pot-limit'."""
        with pytest.raises(ValueError, match="betting_mode"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="fixed-limit",  # type: ignore
                wager_targets=(50,),
            )

    def test_wager_targets_must_be_nonnegative_integers(self) -> None:
        """Wager targets must be non-negative integers."""
        with pytest.raises(ValueError, match="non-negative"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(-50, 100),
            )

    def test_wager_targets_must_be_unique_and_increasing(self) -> None:
        """Wager targets must be unique and in increasing order."""
        with pytest.raises(ValueError, match="unique and increasing"):
            AllStreetPostflopConfig(
                version="allstreet-postflop-v1",
                starting_board=(Card("As"), Card("Kh"), Card("Qd")),
                initial_dead_pot=100,
                effective_stack=1000,
                player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
                player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
                allowed_runouts=((Card("7s"), Card("6s")),),
                betting_mode="no-limit",
                wager_targets=(100, 50, 200),
            )

    def test_max_nodes_default(self) -> None:
        """max_nodes defaults to 100_000."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert config.max_nodes == 100_000

    def test_max_depth_default(self) -> None:
        """max_depth defaults to 512."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert config.max_depth == 512

    def test_config_is_immutable(self) -> None:
        """AllStreetPostflopConfig is frozen and immutable."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises((AttributeError, TypeError)):
            config.effective_stack = 2000  # type: ignore


class TestAllStreetDefensiveCopies:
    """Test that AllStreetPostflopConfig defensively copies nested input."""

    def test_starting_board_list_input_converted_to_tuple(self) -> None:
        """Starting board list input is defensively converted to tuple."""
        board_list = [Card("As"), Card("Kh"), Card("Qd")]
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=board_list,  # Pass list directly
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert isinstance(config.starting_board, tuple)
        # Mutate original list
        board_list.append(Card("Jd"))
        # Config must be unaffected
        assert len(config.starting_board) == 3
        assert config.starting_board == (Card("As"), Card("Kh"), Card("Qd"))

    def test_player0_combos_list_input_converted_to_tuple(self) -> None:
        """Player0 combos list input is defensively converted to tuple."""
        combos_list = [WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0)]
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=combos_list,  # Pass list directly
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert isinstance(config.player0_combos, tuple)
        original_len = len(config.player0_combos)
        # Mutate original list
        combos_list.append(WeightedCombo(cards=(Card("Jd"), Card("Td")), weight=1.0))
        # Config must be unaffected
        assert len(config.player0_combos) == original_len

    def test_player1_combos_list_input_converted_to_tuple(self) -> None:
        """Player1 combos list input is defensively converted to tuple."""
        combos_list = [WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0)]
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=combos_list,  # Pass list directly
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert isinstance(config.player1_combos, tuple)
        original_len = len(config.player1_combos)
        # Mutate original list
        combos_list.clear()
        # Config must be unaffected
        assert len(config.player1_combos) == original_len

    def test_allowed_runouts_list_input_converted_to_tuple(self) -> None:
        """Allowed runouts list input is defensively converted to tuple."""
        runouts_list = [[Card("7s"), Card("6s")], [Card("5d"), Card("4d")]]
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=runouts_list,  # Pass list of lists
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        assert isinstance(config.allowed_runouts, tuple)
        assert all(isinstance(r, tuple) for r in config.allowed_runouts)
        original_len = len(config.allowed_runouts)
        # Mutate original outer list
        runouts_list.append([Card("3c"), Card("2c")])
        # Config must be unaffected
        assert len(config.allowed_runouts) == original_len
        # Mutate original inner list
        runouts_list[0].append(Card("Jd"))
        # Config inner tuple must be unaffected
        assert len(config.allowed_runouts[0]) == 2

    def test_wager_targets_list_input_converted_to_tuple(self) -> None:
        """Wager targets list input is defensively converted to tuple."""
        wager_list = [50, 100, 200]
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=wager_list,  # Pass list directly
        )
        assert isinstance(config.wager_targets, tuple)
        original_len = len(config.wager_targets)
        # Mutate original list
        wager_list.append(300)
        # Config must be unaffected
        assert len(config.wager_targets) == original_len
        assert config.wager_targets == (50, 100, 200)


class TestCreateAllStreetRoot:
    """Test create_allstreet_root produces valid MultiStreetState."""

    def test_creates_root_state(self) -> None:
        """create_allstreet_root produces a valid root state."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50, 100),
        )
        root = create_allstreet_root(config)
        from poker_solver.model import CHANCE
        assert root.current_player() == CHANCE


class TestSolveAllStreetPostflopAlgorithmValidation:
    """Test algorithm and seed/iteration validation."""

    def test_vanilla_cfr_algorithm(self) -> None:
        """vanilla-cfr algorithm is accepted."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        # Should not raise
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
            seed=None,
        )
        assert result is not None

    def test_external_sampling_mccfr_algorithm(self) -> None:
        """external-sampling-mccfr algorithm is accepted."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="external-sampling-mccfr",
            iterations=10,
            seed=42,
        )
        assert result is not None

    def test_invalid_algorithm_rejected(self) -> None:
        """Invalid algorithm names are rejected."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises(ValueError, match="algorithm"):
            solve_allstreet_postflop(
                config,
                algorithm="invalid-algorithm",  # type: ignore
                iterations=10,
            )

    def test_vanilla_cfr_rejects_seed(self) -> None:
        """vanilla-cfr must reject seed parameter."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises(ValueError, match="seed"):
            solve_allstreet_postflop(
                config,
                algorithm="vanilla-cfr",
                iterations=10,
                seed=42,
            )

    def test_mccfr_requires_integer_seed(self) -> None:
        """external-sampling-mccfr requires an integer seed."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises(ValueError, match="seed"):
            solve_allstreet_postflop(
                config,
                algorithm="external-sampling-mccfr",
                iterations=10,
                seed=None,
            )

    def test_iterations_must_be_positive(self) -> None:
        """Iterations must be a positive integer."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises(ValueError, match="iterations"):
            solve_allstreet_postflop(
                config,
                algorithm="vanilla-cfr",
                iterations=0,
            )

    def test_iterations_rejects_negative(self) -> None:
        """Iterations must reject negative values."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        with pytest.raises(ValueError, match="iterations"):
            solve_allstreet_postflop(
                config,
                algorithm="vanilla-cfr",
                iterations=-10,
            )


class TestAllStreetResultMetadata:
    """Test that solve results contain truthful metadata."""

    def test_result_contains_config_version(self) -> None:
        """Result metadata includes config_version=4."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "config_version")
        assert result.config_version == 4

    def test_result_contains_game_version(self) -> None:
        """Result metadata includes game_version='allstreet-postflop-v1'."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "game_version")
        assert result.game_version == "allstreet-postflop-v1"

    def test_result_contains_starting_street(self) -> None:
        """Result metadata includes starting_street='flop'."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "starting_street")
        assert result.starting_street == "flop"

    def test_result_contains_continuation_mode(self) -> None:
        """Result metadata includes continuation='automatic-natural-terminal'."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "continuation")
        assert result.continuation == "automatic-natural-terminal"

    def test_result_contains_algorithm(self) -> None:
        """Result metadata includes the algorithm used."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "algorithm")
        assert result.algorithm == "vanilla-cfr"

    def test_result_contains_iterations(self) -> None:
        """Result metadata includes the iteration count."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        assert hasattr(result, "iterations")
        assert result.iterations == 10

    def test_result_contains_seed_for_mccfr(self) -> None:
        """Result metadata includes seed for MCCFR."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="external-sampling-mccfr",
            iterations=10,
            seed=42,
        )
        assert hasattr(result, "seed")
        assert result.seed == 42

    def test_result_does_not_claim_exact_equilibrium(self) -> None:
        """Result metadata does not falsely claim 'exact equilibrium'."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        # Check that result does not contain misleading claims
        result_str = str(result).lower()
        assert "exact equilibrium" not in result_str
        assert "converged" not in result_str
        assert "gto parity" not in result_str


class TestAllStreetResultDeepImmutability:
    """Test that AllStreetSolveResult enforces deep immutability.
    
    S1-I1 immutability repair: prove result fields, metadata dict, strategy dict,
    and nested policy dicts are all immutable, and separate solves are isolated.
    """

    def test_result_field_assignment_blocked(self) -> None:
        """Result fields cannot be reassigned after creation."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        
        # Frozen dataclass should block field assignment
        with pytest.raises((AttributeError, TypeError)):
            result.iterations = 999  # type: ignore
        
        with pytest.raises((AttributeError, TypeError)):
            result.algorithm = "fake-algorithm"  # type: ignore
        
        with pytest.raises((AttributeError, TypeError)):
            result.nash_conv = 0.0  # type: ignore

    def test_metadata_dict_mutation_blocked(self) -> None:
        """Result metadata dict cannot be mutated after solve."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        
        original_terminal_count = result.metadata["terminal_count"]
        
        # Attempt to mutate metadata dict should fail
        with pytest.raises(TypeError):
            result.metadata["terminal_count"] = 999
        
        with pytest.raises(TypeError):
            result.metadata["injected_key"] = "malicious"
        
        with pytest.raises(TypeError):
            del result.metadata["terminal_count"]
        
        # Verify metadata unchanged
        assert result.metadata["terminal_count"] == original_terminal_count

    def test_nested_metadata_is_defensively_copied_and_immutable(self) -> None:
        """Nested metadata mappings and sequences cannot retain mutable aliases."""
        caller_metadata: dict[str, Any] = {"diagnostics": {"samples": [1, 2]}}
        result = AllStreetSolveResult(
            algorithm="vanilla-cfr",
            seed=None,
            iterations=10,
            values=(0.0, 0.0),
            nash_conv=0.0,
            half_nash_conv=0.0,
            strategy={"infoset": {"CHECK": 1.0}},
            config_version=4,
            game_version="allstreet-postflop-v1",
            starting_street="flop",
            continuation="automatic-natural-terminal",
            max_nodes=100,
            max_depth=10,
            node_count=1,
            max_depth_reached=0,
            approximate=False,
            provenance="test fixture",
            metadata=caller_metadata,
        )

        caller_metadata["diagnostics"]["samples"].append(3)
        caller_metadata["diagnostics"]["injected"] = True

        diagnostics = result.metadata["diagnostics"]
        assert diagnostics["samples"] == (1, 2)
        assert "injected" not in diagnostics
        with pytest.raises(TypeError):
            diagnostics["injected"] = True
        with pytest.raises(AttributeError):
            diagnostics["samples"].append(4)

    def test_strategy_dict_mutation_blocked(self) -> None:
        """Result strategy dict cannot be mutated after solve."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        
        # Strategy should be non-empty
        assert len(result.strategy) > 0
        
        original_strategy_keys = set(result.strategy.keys())
        
        # Attempt to add new infoset should fail
        with pytest.raises(TypeError):
            result.strategy["fake_infoset"] = {"action": 1.0}
        
        # Attempt to delete infoset should fail
        first_key = next(iter(result.strategy.keys()))
        with pytest.raises(TypeError):
            del result.strategy[first_key]
        
        # Verify strategy unchanged
        assert set(result.strategy.keys()) == original_strategy_keys

    def test_nested_policy_mutation_blocked(self) -> None:
        """Nested policy dicts within strategy cannot be mutated."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        result = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        
        # Get a policy dict from strategy
        assert len(result.strategy) > 0
        first_infoset = next(iter(result.strategy.keys()))
        policy = result.strategy[first_infoset]
        
        # Policy should be non-empty
        assert len(policy) > 0
        
        original_policy_keys = set(policy.keys())
        first_action = next(iter(policy.keys()))
        original_prob = policy[first_action]
        
        # Attempt to mutate action probability should fail
        with pytest.raises(TypeError):
            policy[first_action] = 0.999
        
        # Attempt to add new action should fail
        with pytest.raises(TypeError):
            policy["fake_action"] = 0.5
        
        # Attempt to delete action should fail
        with pytest.raises(TypeError):
            del policy[first_action]
        
        # Verify policy unchanged
        assert set(policy.keys()) == original_policy_keys
        assert policy[first_action] == original_prob

    def test_separate_solves_are_isolated(self) -> None:
        """Multiple solves produce isolated immutable results."""
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=(Card("As"), Card("Kh"), Card("Qd")),
            initial_dead_pot=100,
            effective_stack=1000,
            player0_combos=(WeightedCombo(cards=(Card("Jc"), Card("Tc")), weight=1.0),),
            player1_combos=(WeightedCombo(cards=(Card("9h"), Card("8h")), weight=1.0),),
            allowed_runouts=((Card("7s"), Card("6s")),),
            betting_mode="no-limit",
            wager_targets=(50,),
        )
        
        # Run two separate solves
        result1 = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=10,
        )
        
        result2 = solve_allstreet_postflop(
            config,
            algorithm="vanilla-cfr",
            iterations=20,
        )
        
        # Results should be distinct objects
        assert result1 is not result2
        
        # Results should have different iteration counts
        assert result1.iterations == 10
        assert result2.iterations == 20
        
        # Strategy dicts should be distinct objects
        assert result1.strategy is not result2.strategy
        
        # Metadata dicts should be distinct objects
        assert result1.metadata is not result2.metadata
        
        # Get a shared infoset key if it exists
        shared_keys = set(result1.strategy.keys()) & set(result2.strategy.keys())
        if shared_keys:
            shared_key = next(iter(shared_keys))
            # Policy dicts should be distinct objects
            assert result1.strategy[shared_key] is not result2.strategy[shared_key]
