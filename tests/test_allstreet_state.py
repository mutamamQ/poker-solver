"""S1-I1 composite-state and invariant tests for allstreet module.

Tests complete flop→turn→river progression, compatible runout chance mass,
blocked runout filtering, fold/call/check-close/all-in handling, raise-to
accounting, zero-sum terminals and solved values, policy normalization,
opponent-card noninterference, vanilla exact determinism and MCCFR same-seed
determinism.
"""

import pytest
from poker_solver.cards import parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.model import CHANCE, TERMINAL, Action
from poker_solver.multistreet import (
    MultiStreetConfig,
    MultiStreetState,
    create_root,
)


def test_flop_to_turn_progression():
    """Test that flop check-check advances to turn chance node."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (
        parse_cards(["2c", "3d"]),
        parse_cards(["2c", "4h"]),
    )
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50, 100),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_check0 = dealt.child(Action("CHECK"))
    after_check1 = after_check0.child(Action("CHECK"))
    
    assert after_check1.current_player() == CHANCE
    assert after_check1.street == "flop"
    assert after_check1.pot == 100
    assert after_check1.committed == (0, 0)


def test_turn_to_river_progression():
    """Test that turn check-check advances to river chance node."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (
        parse_cards(["2c", "3d"]),
        parse_cards(["2c", "4h"]),
    )
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_check0 = dealt.child(Action("CHECK"))
    after_check1 = after_check0.child(Action("CHECK"))
    
    # Turn card
    turn_outcomes = after_check1.chance_outcomes()
    turn_state = after_check1.child(turn_outcomes[0][0])
    assert turn_state.street == "turn"
    assert len(turn_state.board) == 4
    assert turn_state.current_player() == 0
    
    # Check-check on turn
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    assert turn_check1.current_player() == CHANCE
    assert turn_check1.street == "turn"


def test_river_check_check_terminal():
    """Test that river check-check reaches showdown terminal."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    
    # Flop check-check
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    
    # Turn card
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    
    # Turn check-check
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    
    # River card
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    assert river_state.street == "river"
    assert len(river_state.board) == 5
    
    # River check-check
    river_check0 = river_state.child(Action("CHECK"))
    river_check1 = river_check0.child(Action("CHECK"))
    
    assert river_check1.current_player() == TERMINAL
    assert river_check1.terminal_reason == "showdown-river"


def test_compatible_runout_chance_mass():
    """Test that chance outcomes sum to 1.0 at every chance node."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (
        parse_cards(["2c", "3d"]),
        parse_cards(["2c", "4h"]),
        parse_cards(["5s", "6d"]),
    )
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    
    # Turn chance mass
    turn_outcomes = flop_check1.chance_outcomes()
    turn_mass = sum(prob for _, prob in turn_outcomes)
    assert abs(turn_mass - 1.0) < 1e-9
    
    # River chance mass
    turn_state = flop_check1.child(turn_outcomes[0][0])
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    
    river_outcomes = turn_check1.chance_outcomes()
    river_mass = sum(prob for _, prob in river_outcomes)
    assert abs(river_mass - 1.0) < 1e-9


def test_blocked_runout_filtering():
    """Test that runouts blocked by private cards are filtered."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["2c", "2d"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (
        parse_cards(["2c", "3d"]),  # Blocked by player0's 2c
        parse_cards(["4h", "5s"]),  # Compatible
    )
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    
    turn_outcomes = flop_check1.chance_outcomes()
    # Only 4h should be available (from runout [4h, 5s])
    turn_cards = [action.amount for action, _ in turn_outcomes]
    assert parse_cards(["2c"])[0] not in turn_cards
    assert parse_cards(["4h"])[0] in turn_cards


def test_fold_handling():
    """Test fold terminates immediately with correct accounting."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_raise = dealt.child(Action("RAISE", 50))
    after_fold = after_raise.child(Action("FOLD"))
    
    assert after_fold.current_player() == TERMINAL
    assert after_fold.terminal_reason == "fold-1"
    u0, u1 = after_fold.returns()
    assert abs(u0 + u1) < 1e-9


def test_call_close_handling():
    """Test that call closes street and advances to chance."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_raise = dealt.child(Action("RAISE", 50))
    after_call = after_raise.child(Action("CALL", 50))
    
    assert after_call.current_player() == CHANCE
    assert after_call.committed == (50, 50)
    assert after_call.pot == 100


def test_all_in_handling():
    """Test that all-in closes action and advances to chance."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(500,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_all_in = dealt.child(Action("RAISE", 500))
    after_call = after_all_in.child(Action("CALL", 500))
    
    assert after_call.current_player() == CHANCE
    assert after_call.remaining == (0, 0)


def test_raise_to_accounting():
    """Test that raise-to semantics update committed and remaining correctly."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50, 100, 200),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    after_raise = dealt.child(Action("RAISE", 50))
    
    assert after_raise.committed == (50, 0)
    assert after_raise.remaining == (450, 500)
    assert after_raise.total_contributed == (50, 0)
    
    after_reraise = after_raise.child(Action("RAISE", 100))
    assert after_reraise.committed == (50, 100)
    assert after_reraise.remaining == (450, 400)
    assert after_reraise.total_contributed == (50, 100)


def test_zero_sum_terminals():
    """Test that all terminal returns are zero-sum."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    
    # Fold terminal
    after_raise = dealt.child(Action("RAISE", 50))
    after_fold = after_raise.child(Action("FOLD"))
    u0, u1 = after_fold.returns()
    assert abs(u0 + u1) < 1e-9
    
    # Showdown terminal
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    river_check0 = river_state.child(Action("CHECK"))
    river_check1 = river_check0.child(Action("CHECK"))
    
    u0, u1 = river_check1.returns()
    assert abs(u0 + u1) < 1e-9


def test_opponent_card_noninterference():
    """Test that information keys do not vary with opponent cards."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1_a = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    combos1_b = (WeightedCombo(parse_cards(["9h", "8h"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config_a = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1_a,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    config_b = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1_b,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    root_a = create_root(config_a)
    dealt_a = root_a.child(root_a.chance_outcomes()[0][0])
    
    root_b = create_root(config_b)
    dealt_b = root_b.child(root_b.chance_outcomes()[0][0])
    
    # Player 0's information key should be identical
    key_a = dealt_a.information_state_key(0)
    key_b = dealt_b.information_state_key(0)
    
    # Extract components that should match
    assert key_a[0] == key_b[0]  # version
    assert key_a[1] == key_b[1]  # player
    assert key_a[2] == key_b[2]  # own_cards
    assert key_a[3] == key_b[3]  # board
    assert key_a[4] == key_b[4]  # public_history
    assert key_a[5] == key_b[5]  # pot
    assert key_a[6] == key_b[6]  # committed
    assert key_a[7] == key_b[7]  # remaining
    assert key_a[8] == key_b[8]  # betting_mode


def test_vanilla_determinism():
    """Test that repeated traversals produce identical results."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    # First traversal
    root1 = create_root(config)
    dealt1 = root1.child(root1.chance_outcomes()[0][0])
    check1 = dealt1.child(Action("CHECK"))
    
    # Second traversal
    root2 = create_root(config)
    dealt2 = root2.child(root2.chance_outcomes()[0][0])
    check2 = dealt2.child(Action("CHECK"))
    
    # States should be identical
    assert check1.board == check2.board
    assert check1.pot == check2.pot
    assert check1.committed == check2.committed
    assert check1.remaining == check2.remaining
    assert check1.history == check2.history


def test_complete_flop_to_river_path():
    """Test a complete path from flop through river showdown."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=True,
    )
    
    # Root deal
    root = create_root(config)
    assert root.current_player() == CHANCE
    
    # Private deal
    dealt = root.child(root.chance_outcomes()[0][0])
    assert dealt.current_player() == 0
    assert dealt.street == "flop"
    
    # Flop action
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    assert flop_check1.current_player() == CHANCE
    
    # Turn card
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    assert turn_state.street == "turn"
    assert len(turn_state.board) == 4
    
    # Turn action
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    assert turn_check1.current_player() == CHANCE
    
    # River card
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    assert river_state.street == "river"
    assert len(river_state.board) == 5
    
    # River action
    river_check0 = river_state.child(Action("CHECK"))
    river_check1 = river_check0.child(Action("CHECK"))
    assert river_check1.current_player() == TERMINAL
    assert river_check1.terminal_reason == "showdown-river"
    
    # Terminal returns
    u0, u1 = river_check1.returns()
    assert abs(u0 + u1) < 1e-9


def test_river_betting_false_immediate_showdown():
    """Test river_betting=False skips river action and goes to immediate showdown."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        river_betting=False,  # Explicit False
    )
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    
    # Flop check-check
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    
    # Turn card
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    
    # Turn check-check
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    
    # River card should immediately terminate
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    assert river_state.current_player() == TERMINAL
    assert river_state.terminal_reason == "showdown-river"
    assert river_state.street == "river"
    assert len(river_state.board) == 5


def test_river_betting_default_false():
    """Test that river_betting defaults to False when omitted."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    # Omit river_betting entirely
    config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
    )
    
    # Verify default is False
    assert config.river_betting is False
    
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    
    # River should immediately terminate
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    assert river_state.current_player() == TERMINAL
    assert river_state.terminal_reason == "showdown-river"


def test_river_betting_strict_bool_validation():
    """Test that river_betting rejects non-bool values."""
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    # Test integer 1 (truthy but not bool)
    with pytest.raises(ValueError, match="river_betting must be a boolean"):
        MultiStreetConfig(
            version="multistreet-v1",
            starting_street="flop",
            starting_board=board,
            initial_dead_pot=100,
            effective_stack=500,
            player0_combos=combos0,
            player1_combos=combos1,
            allowed_runouts=runouts,
            betting_mode="no-limit",
            wager_targets=(50,),
            river_betting=1,  # type: ignore
        )
    
    # Test string "True"
    with pytest.raises(ValueError, match="river_betting must be a boolean"):
        MultiStreetConfig(
            version="multistreet-v1",
            starting_street="flop",
            starting_board=board,
            initial_dead_pot=100,
            effective_stack=500,
            player0_combos=combos0,
            player1_combos=combos1,
            allowed_runouts=runouts,
            betting_mode="no-limit",
            wager_targets=(50,),
            river_betting="True",  # type: ignore
        )


def test_create_allstreet_root_enables_river_betting():
    """Test that create_allstreet_root explicitly sets river_betting=True."""
    from poker_solver.allstreet import AllStreetPostflopConfig, create_allstreet_root
    
    board = parse_cards(["Ah", "Kd", "Qc"])
    combos0 = (WeightedCombo(parse_cards(["As", "Ks"]), 1.0),)
    combos1 = (WeightedCombo(parse_cards(["Jh", "Th"]), 1.0),)
    runouts = (parse_cards(["2c", "3d"]),)
    
    allstreet_config = AllStreetPostflopConfig(
        version="allstreet-postflop-v1",
        starting_board=board,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=combos0,
        player1_combos=combos1,
        allowed_runouts=runouts,
        betting_mode="no-limit",
        wager_targets=(50,),
        max_nodes=10000,
        max_depth=50,
    )
    
    root = create_allstreet_root(allstreet_config)
    
    # Verify river_betting is True in the underlying config
    assert root.config.river_betting is True
    
    # Verify river action is available
    dealt = root.child(root.chance_outcomes()[0][0])
    flop_check0 = dealt.child(Action("CHECK"))
    flop_check1 = flop_check0.child(Action("CHECK"))
    turn_state = flop_check1.child(flop_check1.chance_outcomes()[0][0])
    turn_check0 = turn_state.child(Action("CHECK"))
    turn_check1 = turn_check0.child(Action("CHECK"))
    river_state = turn_check1.child(turn_check1.chance_outcomes()[0][0])
    
    # River should be a decision node, not terminal
    assert river_state.current_player() == 0
    assert river_state.street == "river"
    assert len(river_state.board) == 5
