"""S3-I1 Betting/Reopening RED Suite — R3I1-2S

Minimal executable protocol-correct behavioral tests:
- Exact imports (Action/TERMINAL from model, WeightedCombo from preflop)
- Unique seat cards via _make_tiny_ranges
- N=2/6/9 initial action order
- One straddle boundary (standard)
- One exact sizing/caller case
- One full-raise reopening case
- Mandatory CO30-BTNcall-SBcall-BB35 trace for reopens=False/True

All expected values are independent calculations.
"""

from fractions import Fraction
import pytest

from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule,
    create_nplayer_preflop_root,
)
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import Action, TERMINAL


def _make_tiny_ranges(n: int) -> tuple[tuple[WeightedCombo, ...], ...]:
    """Tiny synthetic ranges with unique seat cards."""
    ranges = []
    for i in range(n):
        combo = WeightedCombo((2 * i, 2 * i + 1), Fraction(1))
        ranges.append((combo,))
    return tuple(ranges)


def _terminal_table_continuation() -> NPlayerPreflopContinuation:
    """Empty terminal-table continuation for structure tests."""
    return NPlayerPreflopContinuation(
        kind="terminal-table",
        provenance="RED-suite-empty",
        source="supplied",
        payoff_table={},
        showdown_ranks={},
        odd_chip_order=(),
    )


def _config(n: int, **changes: object) -> NPlayerPreflopConfig:
    values: dict[str, object] = dict(
        version="nplayer-preflop-v1",
        num_players=n,
        button=0 if n == 2 else n - 1,
        starting_stacks=(100,) * n,
        forced_posts=(
            ForcedPost(seat=0, kind="small-blind", amount=1),
            ForcedPost(seat=1, kind="big-blind", amount=2),
        ),
        straddle_variant="none",
        ranges=_make_tiny_ranges(n),
        sizing_rules=(),
        max_raises=4,
        max_deals=10,
        max_nodes=10_000,
        short_all_in_reopens=False,
        continuation=_terminal_table_continuation(),
    )
    values.update(changes)
    return NPlayerPreflopConfig(**values)  # type: ignore[arg-type]


class TestInitialActionOrder:
    """N=2/6/9 initial action order."""

    def test_hu_initial_pending(self):
        """HU: both BTN/SB and BB initially pending."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(100, 100),
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(2),
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        assert deal_state.current_player() == 0
        assert deal_state.pending == (0, 1)

    def test_6p_no_straddle_first_actor_utg(self):
        """6p no straddle: first actor is UTG (seat 2)."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=6,
            button=5,
            starting_stacks=(100,) * 6,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(6),
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        assert deal_state.current_player() == 2

    def test_9p_no_straddle_first_actor_utg(self):
        """9p no straddle: first actor is UTG (seat 2)."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=9,
            button=8,
            starting_stacks=(100,) * 9,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(9),
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        assert deal_state.current_player() == 2


class TestStraddleBoundary:
    """Standard straddle first-actor verification."""

    def test_6p_standard_straddle_first_actor_after_utg(self):
        """6p standard straddle: first actor is seat 3."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=6,
            button=5,
            starting_stacks=(100,) * 6,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
                ForcedPost(seat=2, kind="straddle", amount=4),
            ),
            straddle_variant="standard",
            ranges=_make_tiny_ranges(6),
            sizing_rules=(),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        assert deal_state.current_player() == 3


class TestExactSizingCaller:
    """Exact sizing-key selection with cold_callers."""

    def test_cold_callers_after_raise(self):
        """After CO raises, BTN calls, SB has cold_callers=1."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=4,
            button=3,
            starting_stacks=(100,) * 4,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(4),
            sizing_rules=(
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=0,
                    cold_callers=0,
                    relation="NA",
                    expressions=({"unit": "big-blinds", "value": 3},),
                ),
                NPlayerPreflopSizingRule(
                    position="SB",
                    raise_count=1,
                    cold_callers=1,
                    relation="OOP",
                    expressions=({"unit": "big-blinds", "value": 10},),
                ),
            ),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        # CO raises to 6
        state = deal_state.child(Action("RAISE", 6))
        # BTN calls
        state = state.child(Action("CALL", 6))
        # SB should have raise to 20 with cold_callers=1
        legal = [a for a in state.legal_actions() if a.kind == "RAISE"]
        assert any(a.amount == 20 for a in legal)

    def test_limp_counts_as_pre_raise_caller(self):
        """CO limp selects BTN's unopened-pot cold_callers=1 rule."""
        rule = NPlayerPreflopSizingRule(
            position="BTN",
            raise_count=0,
            cold_callers=1,
            relation="NA",
            expressions=({"unit": "big-blinds", "value": 4},),
        )
        state = create_nplayer_preflop_root(
            _config(4, sizing_rules=(rule,))
        ).child(Action("DEAL", 0))

        state = state.child(Action("CALL", 2))

        assert state.current_player() == 3
        assert state.legal_actions() == (
            Action("FOLD"),
            Action("CALL", 2),
            Action("RAISE", 8),
            Action("RAISE", 100),
        )

    def test_small_blind_completion_counts_as_pre_raise_caller(self):
        """HU SB completion selects BB's unopened-pot cold_callers=1 rule."""
        rule = NPlayerPreflopSizingRule(
            position="BB",
            raise_count=0,
            cold_callers=1,
            relation="NA",
            expressions=({"unit": "big-blinds", "value": 3},),
        )
        state = create_nplayer_preflop_root(
            _config(2, sizing_rules=(rule,))
        ).child(Action("DEAL", 0))

        state = state.child(Action("CALL", 2))

        assert state.current_player() == 1
        assert state.legal_actions() == (
            Action("CHECK"),
            Action("RAISE", 6),
            Action("RAISE", 100),
        )


def test_completed_three_four_five_bet_sizing_key_trace() -> None:
    rules = (
        NPlayerPreflopSizingRule(
            "BTN/SB", 0, 0, "NA", ({"unit": "big-blinds", "value": 3},)
        ),
        NPlayerPreflopSizingRule(
            "BB", 1, 0, "OOP", ({"unit": "big-blinds", "value": 9},)
        ),
        NPlayerPreflopSizingRule(
            "BTN/SB", 2, 0, "IP", ({"unit": "big-blinds", "value": 27},)
        ),
        NPlayerPreflopSizingRule(
            "BB", 3, 0, "OOP", ({"unit": "big-blinds", "value": 45},)
        ),
    )
    state = create_nplayer_preflop_root(_config(2, sizing_rules=rules)).child(
        Action("DEAL", 0)
    )

    assert state.legal_actions() == (
        Action("FOLD"),
        Action("CALL", 2),
        Action("RAISE", 6),
        Action("RAISE", 100),
    )
    state = state.child(Action("RAISE", 6))
    assert state.legal_actions() == (
        Action("FOLD"),
        Action("CALL", 6),
        Action("RAISE", 18),
        Action("RAISE", 100),
    )
    state = state.child(Action("RAISE", 18))
    assert state.legal_actions() == (
        Action("FOLD"),
        Action("CALL", 18),
        Action("RAISE", 54),
        Action("RAISE", 100),
    )
    state = state.child(Action("RAISE", 54))
    assert state.legal_actions() == (
        Action("FOLD"),
        Action("CALL", 54),
        Action("RAISE", 90),
        Action("RAISE", 100),
    )
    state = state.child(Action("RAISE", 90))

    assert state.raise_count == 4
    assert tuple(item.action.amount for item in state.history) == (6, 18, 54, 90)


class TestFullRaiseReopening:
    """Full raise restores entitlement."""

    def test_full_raise_restores_entitlement(self):
        """After BTN 3-bets, CO can 4-bet."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=4,
            button=3,
            starting_stacks=(100,) * 4,
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=1),
                ForcedPost(seat=1, kind="big-blind", amount=2),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(4),
            sizing_rules=(
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=0,
                    cold_callers=0,
                    relation="NA",
                    expressions=({"unit": "big-blinds", "value": 3},),
                ),
                NPlayerPreflopSizingRule(
                    position="BTN",
                    raise_count=1,
                    cold_callers=0,
                    relation="IP",
                    expressions=({"unit": "big-blinds", "value": 9},),
                ),
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=2,
                    cold_callers=0,
                    relation="OOP",
                    expressions=({"unit": "big-blinds", "value": 27},),
                ),
            ),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        # CO raises to 6
        state = deal_state.child(Action("RAISE", 6))
        # BTN 3-bets to 18
        state = state.child(Action("RAISE", 18))
        # SB folds
        state = state.child(Action("FOLD", 0))
        # BB folds
        state = state.child(Action("FOLD", 0))
        # CO can 4-bet
        legal = [a for a in state.legal_actions() if a.kind == "RAISE"]
        assert any(a.amount == 54 for a in legal)


class TestMandatoryShortAllInTrace:
    """Mandatory CO30-BTNcall-SBcall-BB35 trace for reopens=False/True."""

    def test_short_all_in_no_reopen(self):
        """CO30, BTN call, SB call, BB35: pending=(2,3,0), no can_raise."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=4,
            button=3,
            starting_stacks=(500, 35, 500, 500),
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=5),
                ForcedPost(seat=1, kind="big-blind", amount=10),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(4),
            sizing_rules=(
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=0,
                    cold_callers=0,
                    relation="NA",
                    expressions=({"unit": "big-blinds", "value": 3},),
                ),
            ),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=False,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        # CO raises to 30
        state = deal_state.child(Action("RAISE", 30))
        # BTN calls 30
        state = state.child(Action("CALL", 30))
        # SB calls 30
        state = state.child(Action("CALL", 30))
        # BB goes all-in to 35 (increment 5 below previous 20)
        state = state.child(Action("RAISE", 35))
        # Pending should be (2, 3, 0)
        assert state.pending == (2, 3, 0)
        # Every responder owes a response, but no responder is re-entitled.
        assert state.can_raise == (False, False, False, False)
        legal = [a for a in state.legal_actions() if a.kind == "RAISE"]
        assert len(legal) == 0

    def test_short_all_in_with_reopen(self):
        """CO30, BTN call, SB call, BB35 with reopens=True: can_raise."""
        config = NPlayerPreflopConfig(
            version="nplayer-preflop-v1",
            num_players=4,
            button=3,
            starting_stacks=(500, 35, 500, 500),
            forced_posts=(
                ForcedPost(seat=0, kind="small-blind", amount=5),
                ForcedPost(seat=1, kind="big-blind", amount=10),
            ),
            straddle_variant="none",
            ranges=_make_tiny_ranges(4),
            sizing_rules=(
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=0,
                    cold_callers=0,
                    relation="NA",
                    expressions=({"unit": "big-blinds", "value": 3},),
                ),
                NPlayerPreflopSizingRule(
                    position="CO",
                    raise_count=2,
                    cold_callers=0,
                    relation="IP",
                    expressions=({"unit": "big-blinds", "value": 9},),
                ),
            ),
            max_raises=4,
            max_deals=10,
            max_nodes=10000,
            short_all_in_reopens=True,
            continuation=_terminal_table_continuation(),
        )
        root = create_nplayer_preflop_root(config)
        deal_state = root.child(root.chance_outcomes()[0][0])
        # CO raises to 30
        state = deal_state.child(Action("RAISE", 30))
        # BTN calls
        state = state.child(Action("CALL", 30))
        # SB calls
        state = state.child(Action("CALL", 30))
        # BB goes all-in short to 35
        state = state.child(Action("RAISE", 35))
        # With reopens=True, responders can raise
        assert state.pending == (2, 3, 0)
        assert state.can_raise == (True, False, True, True)
        legal = [a for a in state.legal_actions() if a.kind == "RAISE"]
        assert any(a.amount == 90 for a in legal)
