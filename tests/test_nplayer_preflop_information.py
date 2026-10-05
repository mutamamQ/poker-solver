"""Information noninterference and projected HU compatibility contracts."""

from __future__ import annotations

from fractions import Fraction

import pytest

from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, TERMINAL
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopPublicAction,
    NPlayerPreflopSizingRule,
    NPlayerPreflopState,
    create_nplayer_preflop_root,
)
from poker_solver.preflop import (
    Continuation,
    PreflopConfig,
    PreflopState,
    WeightedCombo,
    create_preflop_root,
)


def _combo(cards: tuple[int, int]) -> WeightedCombo:
    return WeightedCombo(cards, Fraction(1))


def _rank_continuation(
    deal: tuple[tuple[int, int], ...],
    ranks: tuple[int, ...],
) -> NPlayerPreflopContinuation:
    return NPlayerPreflopContinuation(
        kind="showdown-ranks",
        provenance="information-fixture",
        source="supplied",
        payoff_table={},
        showdown_ranks={deal: ranks},
        odd_chip_order=tuple(range(len(deal))),
    )


def _nplayer_config(
    deal: tuple[tuple[int, int], ...],
    ranks: tuple[int, ...],
) -> NPlayerPreflopConfig:
    n = len(deal)
    return NPlayerPreflopConfig(
        version="nplayer-preflop-v1",
        num_players=n,
        button=0 if n == 2 else n - 1,
        starting_stacks=(100,) * n,
        forced_posts=(
            ForcedPost(seat=0, kind="small-blind", amount=1),
            ForcedPost(seat=1, kind="big-blind", amount=2),
        ),
        straddle_variant="none",
        ranges=tuple((_combo(cards),) for cards in deal),
        sizing_rules=(),
        max_raises=2,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=_rank_continuation(deal, ranks),
    )


def _dealt(config: NPlayerPreflopConfig):
    root = create_nplayer_preflop_root(config)
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1
    return root.child(outcomes[0][0])


@pytest.mark.parametrize("n", (6, 9))
def test_information_key_excludes_opponent_cards_for_first_actor(n: int) -> None:
    first_deal = tuple((2 * seat, 2 * seat + 1) for seat in range(n))
    second_deal = list(first_deal)
    second_deal[3] = (40, 41)
    ranks = tuple(range(n, 0, -1))

    first = _dealt(_nplayer_config(first_deal, ranks))
    second = _dealt(_nplayer_config(tuple(second_deal), ranks))

    assert first.current_player() == second.current_player() == 2
    assert first.legal_actions() == second.legal_actions()
    assert first.information_state_key(2) == second.information_state_key(2)

    owner_deal = list(first_deal)
    owner_deal[2] = (42, 43)
    owner_changed = _dealt(_nplayer_config(tuple(owner_deal), ranks))
    assert first.information_state_key(2) != owner_changed.information_state_key(2)


@pytest.mark.parametrize("n", (2, 6, 9))
def test_information_key_excludes_hidden_showdown_ranks(n: int) -> None:
    deal = tuple((2 * seat, 2 * seat + 1) for seat in range(n))
    first = _dealt(_nplayer_config(deal, tuple(range(n))))
    second = _dealt(_nplayer_config(deal, tuple(reversed(range(n)))))
    actor = 0 if n == 2 else 2

    assert first.current_player() == second.current_player() == actor
    assert first.legal_actions() == second.legal_actions()
    assert first.information_state_key(actor) == second.information_state_key(actor)


def test_projected_hu_fold_terminal_refund_and_information_partitions() -> None:
    ranges = (
        (_combo((0, 1)), _combo((2, 3))),
        (_combo((4, 5)), _combo((6, 7))),
    )
    expressions = (
        {"unit": "big-blinds", "value": 3},
        {"unit": "all-in"},
    )
    legacy = PreflopConfig(
        starting_stacks=(20, 20),
        forced_posts=(1, 2),
        ranges=ranges,
        sizing_expressions=expressions,
        max_raises=2,
        max_deals=4,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=Continuation("terminal-table", {}, "hu-projection"),
    )
    generic = NPlayerPreflopConfig(
        version="nplayer-preflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(20, 20),
        forced_posts=(
            ForcedPost(seat=0, kind="small-blind", amount=1),
            ForcedPost(seat=1, kind="big-blind", amount=2),
        ),
        straddle_variant="none",
        ranges=ranges,
        sizing_rules=(
            NPlayerPreflopSizingRule(
                position="BTN/SB",
                raise_count=0,
                cold_callers=0,
                relation="NA",
                expressions=expressions,
            ),
        ),
        max_raises=2,
        max_deals=4,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(
            kind="terminal-table",
            provenance="hu-projection",
            source="supplied",
            payoff_table={},
            showdown_ranks={},
            odd_chip_order=(),
        ),
    )

    old_root = create_preflop_root(legacy)
    new_root = create_nplayer_preflop_root(generic)
    old_outcomes = old_root.chance_outcomes()
    new_outcomes = new_root.chance_outcomes()
    assert tuple(action for action, _ in new_outcomes) == tuple(action for action, _ in old_outcomes)
    assert tuple(float(probability) for _, probability in new_outcomes) == tuple(
        float(probability) for _, probability in old_outcomes
    )

    old_states = tuple(old_root.child(action) for action, _ in old_outcomes)
    new_states = tuple(new_root.child(action) for action, _ in new_outcomes)
    for player in (0, 1):
        old_keys = tuple(state.information_state_key(player) for state in old_states)
        new_keys = tuple(state.information_state_key(player) for state in new_states)
        old_partition = tuple(left == right for left in old_keys for right in old_keys)
        new_partition = tuple(left == right for left in new_keys for right in new_keys)
        assert new_partition == old_partition

    old_state = old_states[0]
    new_state = new_states[0]
    assert new_state.current_player() == old_state.current_player() == 0
    assert new_state.legal_actions() == old_state.legal_actions()
    assert new_state.pot == old_state.pot
    assert new_state.street_committed == old_state.committed
    assert new_state.total_contributed == old_state.total_contributed
    assert new_state.remaining == old_state.remaining

    for action in (Action("RAISE", 6), Action("FOLD")):
        assert action in old_state.legal_actions()
        assert action in new_state.legal_actions()
        old_state = old_state.child(action)
        new_state = new_state.child(action)
        assert tuple(entry.action for entry in new_state.history) == old_state.history

    assert new_state.current_player() == old_state.current_player() == TERMINAL
    assert new_state.returns() == old_state.returns() == (2.0, -2.0)

    # Legacy preserves the raw pre-refund terminal ledger even though its fold
    # utilities account for the four unmatched chips.  The N-player state stores
    # the canonical section-8 ledger.  Compatibility therefore compares raw
    # ledgers only at decisions and independently canonicalized ledgers here.
    assert old_state.pot == 8
    assert old_state.committed == (6, 2)
    assert old_state.total_contributed == (6, 2)
    assert old_state.remaining == (14, 18)
    assert new_state.pot == 4
    assert new_state.street_committed == (2, 2)
    assert new_state.total_contributed == (2, 2)
    assert new_state.remaining == (18, 18)

    legacy_refund = old_state.total_contributed[0] - old_state.total_contributed[1]
    canonical_legacy = (
        old_state.pot - legacy_refund,
        (old_state.committed[0] - legacy_refund, old_state.committed[1]),
        (
            old_state.total_contributed[0] - legacy_refund,
            old_state.total_contributed[1],
        ),
        (old_state.remaining[0] + legacy_refund, old_state.remaining[1]),
    )
    assert canonical_legacy == (
        new_state.pot,
        new_state.street_committed,
        new_state.total_contributed,
        new_state.remaining,
    )


def test_projected_hu_call_raise_reraise_traces_match_legacy() -> None:
    deal = ((0, 1), (2, 3))
    ranges = ((_combo(deal[0]),), (_combo(deal[1]),))
    expressions = (
        {"unit": "big-blinds", "value": 3},
        {"unit": "big-blinds", "value": 9},
        {"unit": "all-in"},
    )
    closed_traces = (
        ((Action("CALL", 2), Action("CHECK")), (Fraction(-1), Fraction(1))),
        ((Action("RAISE", 6), Action("CALL", 6)), (Fraction(-2), Fraction(2))),
        (
            (Action("RAISE", 6), Action("RAISE", 18), Action("CALL", 18)),
            (Fraction(-3), Fraction(3)),
        ),
    )
    legacy_table = {(deal, trace): values for trace, values in closed_traces}
    generic_table = {
        (
            deal,
            tuple(
                NPlayerPreflopPublicAction(index % 2, action)
                for index, action in enumerate(trace)
            ),
        ): values
        for trace, values in closed_traces
    }
    legacy = PreflopConfig(
        starting_stacks=(20, 20),
        forced_posts=(1, 2),
        ranges=ranges,
        sizing_expressions=expressions,
        max_raises=3,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=Continuation("terminal-table", legacy_table, "hu-traces"),
    )
    generic = NPlayerPreflopConfig(
        version="nplayer-preflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(20, 20),
        forced_posts=(
            ForcedPost(0, "small-blind", 1),
            ForcedPost(1, "big-blind", 2),
        ),
        straddle_variant="none",
        ranges=ranges,
        sizing_rules=(
            NPlayerPreflopSizingRule("BTN/SB", 0, 0, "NA", expressions),
            NPlayerPreflopSizingRule("BB", 0, 1, "NA", expressions),
            NPlayerPreflopSizingRule("BB", 1, 0, "OOP", expressions),
            NPlayerPreflopSizingRule("BTN/SB", 2, 0, "IP", expressions),
        ),
        max_raises=3,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(
            kind="terminal-table",
            provenance="hu-traces",
            source="supplied",
            payoff_table=generic_table,
            showdown_ranks={},
            odd_chip_order=(),
        ),
    )

    traces = tuple(trace for trace, _values in closed_traces) + (
        (Action("RAISE", 6), Action("FOLD")),
    )
    aligned_decisions: list[tuple[PreflopState, NPlayerPreflopState]] = []
    for trace in traces:
        old_state = create_preflop_root(legacy).child(Action("DEAL", 0))
        new_state = create_nplayer_preflop_root(generic).child(Action("DEAL", 0))
        for action in trace:
            assert new_state.current_player() == old_state.current_player()
            assert new_state.legal_actions() == old_state.legal_actions()
            assert new_state.pot == old_state.pot
            assert new_state.street_committed == old_state.committed
            assert new_state.total_contributed == old_state.total_contributed
            assert new_state.remaining == old_state.remaining
            assert tuple(item.action for item in new_state.history) == old_state.history
            aligned_decisions.append((old_state, new_state))
            old_state = old_state.child(action)
            new_state = new_state.child(action)
        assert new_state.current_player() == old_state.current_player() == TERMINAL
        assert new_state.returns() == old_state.returns()

    for player in (0, 1):
        old_keys = tuple(
            state.information_state_key(player) for state, _new in aligned_decisions
        )
        new_keys = tuple(
            state.information_state_key(player) for _old, state in aligned_decisions
        )
        assert tuple(left == right for left in old_keys for right in old_keys) == tuple(
            left == right for left in new_keys for right in new_keys
        )


def test_hu_projection_excludes_legacy_chipless_responder_suffix() -> None:
    """The N-player path closes correctly where legacy leaves a chipless actor."""

    deal = ((0, 1), (2, 3))
    ranges = ((_combo(deal[0]),), (_combo(deal[1]),))
    actions = (
        Action("CALL", 2),
        Action("RAISE", 7),
        Action("RAISE", 20),
    )
    values = (Fraction(7), Fraction(-7))
    expressions = ({"unit": "all-in"},)

    legacy_config = PreflopConfig(
        starting_stacks=(20, 7),
        forced_posts=(1, 2),
        ranges=ranges,
        sizing_expressions=expressions,
        max_raises=3,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=Continuation(
            kind="terminal-table",
            payoff_table={(deal, actions): values},
            provenance="known legacy chipless-responder suffix",
        ),
    )
    public_history = tuple(
        NPlayerPreflopPublicAction(actor=index % 2, action=action)
        for index, action in enumerate(actions)
    )
    generic_config = NPlayerPreflopConfig(
        version="nplayer-preflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(20, 7),
        forced_posts=(
            ForcedPost(0, "small-blind", 1),
            ForcedPost(1, "big-blind", 2),
        ),
        straddle_variant="none",
        ranges=ranges,
        sizing_rules=(
            NPlayerPreflopSizingRule("BTN/SB", 0, 0, "NA", expressions),
            NPlayerPreflopSizingRule("BB", 1, 0, "OOP", expressions),
            NPlayerPreflopSizingRule("BTN/SB", 2, 0, "IP", expressions),
        ),
        max_raises=3,
        max_deals=1,
        max_nodes=1_000,
        short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(
            kind="terminal-table",
            provenance="correct unequal-stack closure",
            source="supplied",
            payoff_table={(deal, public_history): values},
            showdown_ranks={},
            odd_chip_order=(),
        ),
    )

    legacy = create_preflop_root(legacy_config).child(Action("DEAL", 0))
    generic = create_nplayer_preflop_root(generic_config).child(Action("DEAL", 0))
    for action in actions:
        assert legacy.current_player() == generic.current_player()
        assert legacy.legal_actions() == generic.legal_actions()
        legacy = legacy.child(action)
        generic = generic.child(action)

    # Preserve the legacy module's historical invalid suffix without treating it
    # as the compatibility oracle for the new finite N-player state machine.
    assert legacy.current_player() == 1
    assert legacy.remaining == (0, 0)
    assert legacy.legal_actions() == (Action("FOLD"), Action("CALL", 7))

    assert generic.current_player() == TERMINAL
    assert generic.pending == ()
    assert generic.pot == 14
    assert generic.street_committed == (7, 7)
    assert generic.total_contributed == (7, 7)
    assert generic.remaining == (13, 0)
    assert generic.terminal_values == values