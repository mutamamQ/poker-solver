"""Information noninterference and projected N=3 legacy-equivalence contracts."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from poker_solver.model import Action, TERMINAL
from poker_solver.multiway import MultiwayConfig, create_three_player_root
from poker_solver.preflop import WeightedCombo
from poker_solver.nplayer_postflop import (
    NPlayerPostflopConfig,
    create_nplayer_postflop_root,
)


def _combo(cards: tuple[int, int]) -> WeightedCombo:
    return WeightedCombo(cards, Fraction(1))


def _config(
    deal: tuple[tuple[int, int], ...],
    ranks: tuple[int, ...],
) -> NPlayerPostflopConfig:
    n = len(deal)
    return NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=n,
        button=0,
        starting_stacks=tuple(20 for _ in range(n)),
        contributions=tuple(2 for _ in range(n)),
        folded=tuple(False for _ in range(n)),
        board=(0, 1, 2),
        ranges=tuple((_combo(cards),) for cards in deal),
        wager_targets=(4, 8),
        max_raises=3,
        max_deals=20,
        max_nodes=500,
        odd_chip_order=tuple(range(n)),
        showdown_ranks={deal: ranks},
        rake_policy=None,
    )


def _dealt(config: NPlayerPostflopConfig):
    root = create_nplayer_postflop_root(config)
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1
    return root.child(outcomes[0][0])


def test_information_key_excludes_opponent_private_cards() -> None:
    first = _dealt(_config(((6, 7), (8, 9), (10, 11), (12, 13)), (4, 3, 2, 1)))
    second = _dealt(_config(((6, 7), (14, 15), (16, 17), (18, 19)), (4, 3, 2, 1)))
    assert first.information_state_string(0) == second.information_state_string(0)


def test_information_key_excludes_hidden_showdown_ranks_and_deal_index() -> None:
    deal = ((6, 7), (8, 9), (10, 11), (12, 13))
    first = _dealt(_config(deal, (4, 3, 2, 1)))
    second = _dealt(_config(deal, (1, 2, 3, 4)))
    assert first.information_state_string(0) == second.information_state_string(0)
    assert "deal" not in first.information_state_string(0).lower()


def test_information_key_includes_owner_combo_and_actor_labelled_history() -> None:
    first = _dealt(_config(((6, 7), (8, 9), (10, 11), (12, 13)), (4, 3, 2, 1)))
    second = _dealt(_config(((14, 15), (8, 9), (10, 11), (12, 13)), (4, 3, 2, 1)))
    assert first.information_state_string(0) != second.information_state_string(0)

    actor = first.current_player()
    checked = first.child(Action("CHECK"))
    key = checked.information_state_string(0)
    assert f"{actor}:CHECK" in key


def _three_player_pair(
    deal: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    ranks: tuple[int, int, int] = (3, 2, 1),
):
    ranges = ((_combo(deal[0]),), (_combo(deal[1]),), (_combo(deal[2]),))
    legacy_config = MultiwayConfig(
        button=0,
        starting_stacks=(20, 20, 20),
        contributions=(2, 2, 2),
        folded=(False, False, False),
        board=(0, 1, 2),
        ranges=ranges,
        wager_targets=(4, 8),
        max_raises=3,
        max_deals=20,
        max_nodes=500,
        odd_chip_order=(0, 1, 2),
        showdown_ranks={deal: ranks},
        rake_policy=None,
    )
    generic_config = _config(deal, ranks)
    old_root = create_three_player_root(legacy_config)
    new_root = create_nplayer_postflop_root(generic_config)

    old_outcomes = old_root.chance_outcomes()
    new_outcomes = new_root.chance_outcomes()
    assert len(old_outcomes) == len(new_outcomes) == 1
    assert old_outcomes[0][1] == new_outcomes[0][1] == Fraction(1)
    return (
        old_root.child(old_outcomes[0][0]),
        new_root.child(new_outcomes[0][0]),
    )


def _assert_public_projection(old_state, new_state) -> None:
    assert new_state.current_player() == old_state.current_player()
    assert new_state.legal_actions() == old_state.legal_actions()
    assert new_state.pot == old_state.pot
    assert new_state.total_contributed == old_state.total_contributed
    assert new_state.street_committed == old_state.street_committed
    assert new_state.remaining == old_state.remaining
    assert new_state.folded == old_state.folded
    assert frozenset(new_state.pending) == frozenset(old_state.pending)
    assert new_state.raise_count == old_state.raise_count
    assert new_state.last_raise_increment == old_state.last_raise_increment
    assert tuple(entry.action for entry in new_state.history) == old_state.history


@pytest.mark.parametrize(
    "actions",
    (
        (Action("CHECK"), Action("CHECK"), Action("CHECK")),
        (Action("RAISE", 4), Action("CALL", 4), Action("CALL", 4)),
        (Action("RAISE", 4), Action("FOLD"), Action("CALL", 4)),
        (Action("RAISE", 4), Action("CALL", 4), Action("FOLD")),
        (Action("RAISE", 4), Action("FOLD"), Action("FOLD")),
        (
            Action("RAISE", 4),
            Action("RAISE", 8),
            Action("CALL", 8),
            Action("CALL", 8),
        ),
    ),
    ids=("check", "raise-call-call", "raise-fold-call", "raise-call-fold", "fold-out", "reraise"),
)
def test_projected_three_player_representative_traces_match_legacy_engine(
    actions: tuple[Action, ...],
) -> None:
    old_state, new_state = _three_player_pair(((6, 7), (8, 9), (10, 11)))
    expected_history: list[tuple[int, Action]] = []

    for action in actions:
        _assert_public_projection(old_state, new_state)
        assert action in old_state.legal_actions()
        assert action in new_state.legal_actions()
        expected_history.append((old_state.current_player(), action))
        old_state = old_state.child(action)
        new_state = new_state.child(action)
        assert tuple((entry.actor, entry.action) for entry in new_state.history) == tuple(expected_history)

    _assert_public_projection(old_state, new_state)
    assert old_state.current_player() == new_state.current_player() == TERMINAL
    assert new_state.returns() == old_state.returns()
    assert sum(new_state.returns()) == 0.0


def test_projected_three_player_information_partitions_match_legacy_engine() -> None:
    deals = (
        ((6, 7), (8, 9), (10, 11)),
        ((12, 13), (8, 9), (10, 11)),
    )
    ranges = ((_combo(deals[0][0]), _combo(deals[1][0])), (_combo((8, 9)),), (_combo((10, 11)),))
    ranks = {deal: (3, 2, 1) for deal in deals}
    common: dict[str, Any] = dict(
        button=0,
        starting_stacks=(20, 20, 20),
        contributions=(2, 2, 2),
        folded=(False, False, False),
        board=(0, 1, 2),
        ranges=ranges,
        wager_targets=(4, 8),
        max_raises=3,
        max_deals=20,
        max_nodes=500,
        odd_chip_order=(0, 1, 2),
        showdown_ranks=ranks,
        rake_policy=None,
    )
    old_root = create_three_player_root(MultiwayConfig(**common))
    new_root = create_nplayer_postflop_root(
        NPlayerPostflopConfig(version="nplayer-postflop-v1", num_players=3, **common)
    )
    old_states = tuple(old_root.child(action) for action, _ in old_root.chance_outcomes())
    new_states = tuple(new_root.child(action) for action, _ in new_root.chance_outcomes())
    assert len(old_states) == len(new_states) == 2

    for player in range(3):
        old_keys = tuple(state.information_state_key(player) for state in old_states)
        new_keys = tuple(state.information_state_key(player) for state in new_states)
        old_partition = tuple(a == b for a in old_keys for b in old_keys)
        new_partition = tuple(a == b for a in new_keys for b in new_keys)
        assert new_partition == old_partition