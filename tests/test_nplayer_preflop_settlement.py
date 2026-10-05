"""S3-I1 Settlement RED Suite - Exclusive ownership R3I1-3.

Permanent behavioral tests for n-player preflop settlement:
- Fold awards with uniform-ante cancellation
- Uncalled bet refunds
- Side-pot layers with exact zero-sum utilities
- Ties and odd-chip resolution
- Terminal-table exact coverage
- Showdown-rank continuation
- No-rake sum(utilities)=0 invariant

All expected values hand-calculated independently; no production helpers imported.
Direct module-scope production imports only; no catch/importorskip/skip/xfail/fakes/placeholders.
"""

import pytest
from fractions import Fraction
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopPublicAction,
    NPlayerPreflopSizingRule,
    create_nplayer_preflop_root,
)
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import Action, TERMINAL


class TestFoldAwardsUniformAnte:
    """Fold awards with uniform-ante cancellation."""

    def test_heads_up_fold_after_ante(self):
        """HU: both post 1 ante, BTN folds to BB.
        
        Seats: 0=BTN/SB, 1=BB
        Ante: 1 each
        SB=1, BB=2
        Pot after posts: 5
        BTN folds
        BB wins pot=5
        BTN utility: -2 (ante+SB)
        BB utility: 5-3=+2 (pot minus ante+BB)
        Sum: -2+2=0 ✓
        
        Trace: DEAL -> BTN FOLD
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(100, 100),
            forced_posts=(
                ForcedPost(0, "ante", 1),
                ForcedPost(1, "ante", 1),
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="terminal-table",
                provenance="test-fold-ante",
                source="supplied",
                payoff_table={},
                showdown_ranks={},
                odd_chip_order=(),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        terminal = dealt.child(Action("FOLD", 0))
        
        assert terminal.current_player() == TERMINAL
        assert terminal.total_contributed == (2, 2)
        assert terminal.returns() == (-2, 2)
        assert sum(terminal.returns()) == 0


class TestUncalledRefunds:
    """Uncalled bet refunds with exact accounting."""

    def test_three_player_uncalled_raise(self):
        """3-player: BTN raises, SB/BB fold.
        
        Seats: 0=BTN, 1=SB, 2=BB
        SB=1, BB=2
        BTN raises to 6, SB folds, BB folds
        Pot after posts: 3
        BTN posts 6, pot=9
        SB/BB fold
        Uncalled excess: 6-2=4 refunded to BTN
        Matched pot: 5
        BTN wins 5, utility: 5-6=+3 (with refund)
        SB utility: -1
        BB utility: -2
        Sum: 3-1-2=0 ✓
        
        Trace: DEAL -> BTN RAISE6 -> SB FOLD -> BB FOLD
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
            (WeightedCombo((4, 5), Fraction(1)),),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=3,
            button=0,
            starting_stacks=(100, 100, 100),
            forced_posts=(
                ForcedPost(1, "small-blind", 1),
                ForcedPost(2, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(
                NPlayerPreflopSizingRule(
                    position="BTN",
                    raise_count=0,
                    cold_callers=0,
                    relation="NA",
                    expressions=({"unit": "big-blinds", "value": 3},),
                ),
            ),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="terminal-table",
                provenance="test-uncalled-refund",
                source="supplied",
                payoff_table={},
                showdown_ranks={},
                odd_chip_order=(),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        s1 = dealt.child(Action("RAISE", 6))
        s2 = s1.child(Action("FOLD", 0))
        terminal = s2.child(Action("FOLD", 0))
        
        assert terminal.current_player() == TERMINAL
        assert terminal.total_contributed == (2, 1, 2)
        assert terminal.returns() == (3, -1, -2)
        assert sum(terminal.returns()) == 0


class TestSidePotLayers:
    """Side-pot layers with exact zero-sum utilities."""

    def test_three_level_side_pot(self):
        """4-player with three side-pot levels.
        
        Seats: 0=CO, 1=BTN, 2=SB, 3=BB
        Stacks: 10, 30, 50, 100
        SB=1, BB=2
        All-in sequence:
        CO all-in 10
        BTN all-in 30
        SB all-in 50
        BB call 50
        
        Contributions: (10, 30, 50, 50)
        Main pot: 4*10=40 (all eligible)
        Side pot 1: 3*(30-10)=60 (BTN, SB, BB)
        Side pot 2: 2*(50-30)=40 (SB, BB)
        Total: 140
        
        Showdown ranks: BB=4 (best), SB=3, BTN=2, CO=1
        BB wins all pots: 40+60+40=140
        
        Utilities:
        CO: -10
        BTN: -30
        SB: -50
        BB: 140-50=+90
        Sum: -10-30-50+90=0 ✓
        
        Trace: DEAL -> CO RAISE10 -> BTN RAISE30 -> SB RAISE50 -> BB CALL50
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
            (WeightedCombo((4, 5), Fraction(1)),),
            (WeightedCombo((6, 7), Fraction(1)),),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=4,
            button=1,
            starting_stacks=(10, 30, 50, 100),
            forced_posts=(
                ForcedPost(2, "small-blind", 1),
                ForcedPost(3, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="showdown-ranks",
                provenance="test-three-level-side-pot",
                source="supplied",
                payoff_table={},
                showdown_ranks={
                    ((0, 1), (2, 3), (4, 5), (6, 7)): (1, 2, 3, 4)
                },
                odd_chip_order=(3, 2, 1, 0),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        s1 = dealt.child(Action("RAISE", 10))
        s2 = s1.child(Action("RAISE", 30))
        s3 = s2.child(Action("RAISE", 50))
        terminal = s3.child(Action("CALL", 50))
        
        assert terminal.current_player() == TERMINAL
        assert terminal.total_contributed == (10, 30, 50, 50)
        assert terminal.returns() == (-10, -30, -50, 90)
        assert sum(terminal.returns()) == 0


class TestTiesAndOddChips:
    """Ties and odd-chip resolution."""

    def test_three_way_partial_tie_odd_chip(self):
        """3-player: uniform ante 1, all match street 2, seats 0/1 tie best, seat 2 loses.
        
        Seats: 0=BTN, 1=SB, 2=BB
        Ante: 1 each
        SB=1, BB=2
        All call 2
        Pot: 1+1+1 + 1+2 + 2+2 = 9
        
        Showdown ranks: seat0=10, seat1=10 (tie), seat2=5 (loses)
        Pot split between seats 0 and 1: 9/2 = 4 each + 1 odd chip
        Odd chip order: (0, 1, 2) - seat 0 gets odd chip
        
        Awards:
        seat0: 5
        seat1: 4
        seat2: 0
        
        Utilities:
        seat0: 5-3=+2
        seat1: 4-3=+1
        seat2: 0-3=-3
        Sum: 2+1-3=0 ✓
        
        Trace: DEAL -> BTN CALL2 -> SB CALL2 -> BB CHECK2
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
            (WeightedCombo((4, 5), Fraction(1)),),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=3,
            button=0,
            starting_stacks=(100, 100, 100),
            forced_posts=(
                ForcedPost(0, "ante", 1),
                ForcedPost(1, "ante", 1),
                ForcedPost(2, "ante", 1),
                ForcedPost(1, "small-blind", 1),
                ForcedPost(2, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="showdown-ranks",
                provenance="test-tie-odd-chip",
                source="supplied",
                payoff_table={},
                showdown_ranks={
                    ((0, 1), (2, 3), (4, 5)): (10, 10, 5)
                },
                odd_chip_order=(0, 1, 2),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        s1 = dealt.child(Action("CALL", 2))
        s2 = s1.child(Action("CALL", 2))
        terminal = s2.child(Action("CHECK"))
        
        assert terminal.current_player() == TERMINAL
        assert terminal.total_contributed == (3, 3, 3)
        assert terminal.returns() == (2, 1, -3)
        assert sum(terminal.returns()) == 0


class TestTerminalTableExactCoverage:
    """Terminal-table exact coverage and rejection."""

    def test_terminal_table_supplied_values_success(self):
        """HU with exact terminal-table continuation - successful lookup.
        
        Seats: 0=BTN/SB, 1=BB
        SB=1, BB=2
        
        Supplied terminal table for one deal and action sequence:
        Deal: ((0,1), (2,3))
        History: (NPlayerPreflopPublicAction(0, CALL2), NPlayerPreflopPublicAction(1, CHECK2))
        Values: (-1, +1) - BB wins
        
        Trace: DEAL -> BTN CALL2 -> BB CHECK2
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
        )
        
        deal = ((0, 1), (2, 3))
        history = (
            NPlayerPreflopPublicAction(0, Action("CALL", 2)),
            NPlayerPreflopPublicAction(1, Action("CHECK")),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(100, 100),
            forced_posts=(
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="terminal-table",
                provenance="test-terminal-table",
                source="supplied",
                payoff_table={
                    (deal, history): (Fraction(-1), Fraction(1))
                },
                showdown_ranks={},
                odd_chip_order=(),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        s1 = dealt.child(Action("CALL", 2))
        terminal = s1.child(Action("CHECK"))
        
        assert terminal.current_player() == TERMINAL
        assert terminal.returns() == (-1, 1)
        assert sum(terminal.returns()) == 0

    def test_terminal_table_missing_key_failure(self):
        """HU terminal-table with missing key - should fail at leaf.
        
        Seats: 0=BTN/SB, 1=BB
        SB=1, BB=2
        
        Empty payoff table - any terminal should fail.
        
        Trace: DEAL -> BTN CALL2 -> BB CHECK2 (missing key)
        """
        ranges = (
            (WeightedCombo((0, 1), Fraction(1)),),
            (WeightedCombo((2, 3), Fraction(1)),),
        )
        
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(100, 100),
            forced_posts=(
                ForcedPost(0, "small-blind", 1),
                ForcedPost(1, "big-blind", 2),
            ),
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=1000,
            short_all_in_reopens=False,
            continuation=NPlayerPreflopContinuation(
                kind="terminal-table",
                provenance="test-terminal-table-missing",
                source="supplied",
                payoff_table={},
                showdown_ranks={},
                odd_chip_order=(),
            ),
        )
        
        root = create_nplayer_preflop_root(config)
        dealt = root.child(Action("DEAL", 0))
        s1 = dealt.child(Action("CALL", 2))
        
        with pytest.raises((KeyError, ValueError, LookupError)):
            s1.child(Action("CHECK"))
