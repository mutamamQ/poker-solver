"""S2-I1 RED: NPlayerPostflopConfig validation, defensive copy, bounded deterministic deals.

Permanent test owner for config construction, strict validation, deal enumeration,
blocker filtering, exact rational mass arithmetic, deterministic ordering, and max_deals
fail-closed behavior.
"""

import pytest
from fractions import Fraction
from math import isfinite
from poker_solver.preflop import WeightedCombo
from poker_solver.game_structure import RakePolicy
from poker_solver.nplayer_postflop import (
    NPlayerPostflopConfig,
    create_nplayer_postflop_root,
    enumerate_deals,
    DealN,
)


def test_config_validation_rejects_wrong_version():
    """Config must have exactly 'nplayer-postflop-v1' version string."""
    with pytest.raises(ValueError, match="version"):
        NPlayerPostflopConfig(
            version="wrong-version",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50, 100),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_rejects_bool_as_int():
    """Config validation must reject bool masquerading as int in num_players, button, etc."""
    with pytest.raises((ValueError, TypeError), match="bool|int"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=True,  # bool as int
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_num_players_range():
    """num_players must be strict int in [2, 9]."""
    with pytest.raises(ValueError, match="num_players"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=1,  # below minimum
            button=0,
            starting_stacks=(1000,),
            contributions=(10,),
            folded=(False,),
            board=(0, 1, 2),
            ranges=((WeightedCombo((3, 4), Fraction(1)),),),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0,),
            showdown_ranks={((3, 4),): (0,)},
        )

    with pytest.raises(ValueError, match="num_players"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=10,  # above maximum
            button=0,
            starting_stacks=(1000,) * 10,
            contributions=(10,) * 10,
            folded=(False,) * 10,
            board=(0, 1, 2),
            ranges=tuple((WeightedCombo((i * 2 + 3, i * 2 + 4), Fraction(1)),) for i in range(10)),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=tuple(range(10)),
            showdown_ranks={},
        )


def test_config_validation_enforces_tuple_lengths():
    """All per-seat tuples must have length exactly num_players."""
    with pytest.raises(ValueError, match="length|num_players"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000, 1000),  # wrong length
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_positive_stacks():
    """starting_stacks must all be positive strict integers."""
    with pytest.raises(ValueError, match="stack|positive"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 0),  # zero stack
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_nonnegative_contributions():
    """contributions must be nonnegative and not exceed stacks."""
    with pytest.raises(ValueError, match="contribution"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 2000),  # exceeds stack
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_positive_initial_pot():
    """sum(contributions) must be positive."""
    with pytest.raises(ValueError, match="pot|contribution"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(0, 0),  # zero pot
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_at_least_two_live():
    """At least two seats must be initially live (not folded)."""
    with pytest.raises(ValueError, match="live|fold"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(True, False),  # only one live
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_board_size_and_uniqueness():
    """board must be exactly 3, 4, or 5 unique card integers in 0..51."""
    with pytest.raises(ValueError, match="board"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1),  # too few cards
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )

    with pytest.raises(ValueError, match="board|unique"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 0, 2),  # duplicate card
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_nonempty_unique_ranges():
    """Each range must be nonempty tuple of unique WeightedCombo with finite positive weights."""
    with pytest.raises(ValueError, match="range|empty"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (),  # empty range
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={},
        )


def test_config_validation_enforces_increasing_unique_targets():
    """wager_targets must be positive, unique, and increasing."""
    with pytest.raises(ValueError, match="target|increasing"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(100, 50),  # not increasing
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_positive_bounds():
    """max_raises, max_deals, max_nodes must be positive strict integers."""
    with pytest.raises(ValueError, match="max_raises|positive"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=0,  # not positive
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_enforces_odd_chip_order_permutation():
    """odd_chip_order must be exactly a permutation of range(num_players)."""
    with pytest.raises(ValueError, match="odd_chip_order|permutation"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 0),  # not a permutation
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_validation_rejects_unmatched_root_excess():
    """Config must reject pre-existing unmatched excess in initial contributions."""
    # This test requires understanding of refund_uncalled_excess behavior
    # Unmatched excess exists when contributions are not matched (e.g., one player contributed more)
    with pytest.raises(ValueError, match="unmatched|excess|refund"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(100, 20),  # unmatched: player 0 has 80 excess
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=1000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
        )


def test_config_defensive_copy_showdown_ranks():
    """Config must detach caller's showdown_ranks mapping and expose via MappingProxyType."""
    original_ranks = {((3, 4), (5, 6)): (1, 0)}
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((3, 4), Fraction(1)),),
            (WeightedCombo((5, 6), Fraction(1)),),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=1000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks=original_ranks,
    )
    # Mutate original
    original_ranks[((7, 8), (9, 10))] = (0, 1)
    # Config should be unaffected
    assert len(config.showdown_ranks) == 1
    assert ((7, 8), (9, 10)) not in config.showdown_ranks


def test_deal_enumeration_deterministic_order():
    """Deal enumeration must walk Cartesian product in seat/range tuple order."""
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((3, 4), Fraction(1)), WeightedCombo((5, 6), Fraction(1))),
            (WeightedCombo((7, 8), Fraction(1)), WeightedCombo((9, 10), Fraction(1))),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=10000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks={
            ((3, 4), (7, 8)): (1, 0),
            ((3, 4), (9, 10)): (1, 0),
            ((5, 6), (7, 8)): (0, 1),
            ((5, 6), (9, 10)): (0, 1),
        },
    )
    deals = enumerate_deals(config)
    # First deal should be (3,4) x (7,8), then (3,4) x (9,10), etc.
    assert deals[0][0] == ((3, 4), (7, 8))
    assert deals[1][0] == ((3, 4), (9, 10))
    assert deals[2][0] == ((5, 6), (7, 8))
    assert deals[3][0] == ((5, 6), (9, 10))


def test_deal_enumeration_blocker_filtering():
    """Deal enumeration must prune collisions immediately with board and prior seats."""
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((0, 3), Fraction(1)), WeightedCombo((4, 5), Fraction(1))),  # (0,3) collides with board
            (WeightedCombo((6, 7), Fraction(1)),),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=10000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks={
            ((4, 5), (6, 7)): (1, 0),
        },
    )
    deals = enumerate_deals(config)
    # Only (4,5) x (6,7) should be valid; (0,3) x (6,7) is blocked
    assert len(deals) == 1
    assert deals[0][0] == ((4, 5), (6, 7))


def test_deal_enumeration_exact_rational_mass():
    """Deal weights must use exact Fraction arithmetic until final probability conversion."""
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((3, 4), Fraction(1, 3)),),
            (WeightedCombo((5, 6), Fraction(2, 5)),),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=10000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks={
            ((3, 4), (5, 6)): (1, 0),
        },
    )
    deals = enumerate_deals(config)
    # Raw deal mass stays exact; chance normalization happens at the root.
    assert len(deals) == 1
    assert deals[0][1] == Fraction(2, 15)


def test_deal_enumeration_max_deals_bound():
    """max_deals must bound candidate Cartesian products before enumeration."""
    with pytest.raises(ValueError, match="max_deals"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                tuple(WeightedCombo((i * 2 + 3, i * 2 + 4), Fraction(1)) for i in range(10)),  # 10 combos
                tuple(WeightedCombo((i * 2 + 23, i * 2 + 24), Fraction(1)) for i in range(10)),  # 10 combos
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=50,  # 10 * 10 = 100 > 50, should fail
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={},  # Will fail on showdown coverage, but max_deals should fail first
        )


def test_deal_enumeration_no_silent_truncation():
    """Compatible results must never be silently truncated."""
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((3, 4), Fraction(1)), WeightedCombo((5, 6), Fraction(1))),
            (WeightedCombo((7, 8), Fraction(1)), WeightedCombo((9, 10), Fraction(1))),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=10000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks={
            ((3, 4), (7, 8)): (1, 0),
            ((3, 4), (9, 10)): (1, 0),
            ((5, 6), (7, 8)): (0, 1),
            ((5, 6), (9, 10)): (0, 1),
        },
    )
    deals = enumerate_deals(config)
    # All 4 compatible deals should be present
    assert len(deals) == 4


def test_deal_enumeration_fail_closed_on_zero_mass():
    """Zero total mass or no compatible deals must fail closed."""
    with pytest.raises(ValueError, match="mass|deal"):
        config = NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2, 3, 4),  # full board
            ranges=(
                (WeightedCombo((0, 1), Fraction(1)),),  # collides with board
                (WeightedCombo((2, 3), Fraction(1)),),  # collides with board
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=10000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={},
        )
        enumerate_deals(config)


def test_deal_enumeration_probabilities_sum_to_one():
    """Public float probabilities must be finite, nonnegative, sum to 1 within 1e-12."""
    config = NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=2,
        button=0,
        starting_stacks=(1000, 1000),
        contributions=(10, 10),
        folded=(False, False),
        board=(0, 1, 2),
        ranges=(
            (WeightedCombo((3, 4), Fraction(1)), WeightedCombo((5, 6), Fraction(2))),
            (WeightedCombo((7, 8), Fraction(3)),),
        ),
        wager_targets=(50,),
        max_raises=3,
        max_deals=10000,
        max_nodes=10000,
        odd_chip_order=(0, 1),
        showdown_ranks={
            ((3, 4), (7, 8)): (1, 0),
            ((5, 6), (7, 8)): (0, 1),
        },
    )
    outcomes = create_nplayer_postflop_root(config).chance_outcomes()
    total_prob = sum(prob for _, prob in outcomes)
    assert abs(total_prob - 1.0) < 1e-12
    assert all(prob >= 0 and isfinite(prob) for _, prob in outcomes)


def test_deal_enumeration_showdown_coverage_at_root():
    """Every compatible deal must have exact showdown-rank coverage at root construction."""
    with pytest.raises(ValueError, match="showdown|coverage|rank"):
        config = NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=10000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={},  # missing coverage for (3,4) x (5,6)
        )
        create_nplayer_postflop_root(config)


def test_config_accepts_all_num_players_2_through_9():
    """Config must accept every N from 2 through 9 with valid inputs."""
    for n in range(2, 10):
        config = NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=n,
            button=0,
            starting_stacks=(1000,) * n,
            contributions=(10,) * n,
            folded=(False,) * n,
            board=(0, 1, 2),
            ranges=tuple((WeightedCombo((i * 2 + 3, i * 2 + 4), Fraction(1)),) for i in range(n)),
            wager_targets=(50,),
            max_raises=3,
            max_deals=10000,
            max_nodes=10000,
            odd_chip_order=tuple(range(n)),
            showdown_ranks={
                tuple((i * 2 + 3, i * 2 + 4) for i in range(n)): tuple(range(n))
            },
        )
        assert config.num_players == n


def test_config_rejects_malformed_rake_policy():
    """Config must validate optional RakePolicy structure."""
    with pytest.raises((ValueError, TypeError), match="rake"):
        NPlayerPostflopConfig(
            version="nplayer-postflop-v1",
            num_players=2,
            button=0,
            starting_stacks=(1000, 1000),
            contributions=(10, 10),
            folded=(False, False),
            board=(0, 1, 2),
            ranges=(
                (WeightedCombo((3, 4), Fraction(1)),),
                (WeightedCombo((5, 6), Fraction(1)),),
            ),
            wager_targets=(50,),
            max_raises=3,
            max_deals=10000,
            max_nodes=10000,
            odd_chip_order=(0, 1),
            showdown_ranks={((3, 4), (5, 6)): (1, 0)},
            rake_policy="invalid",  # should be RakePolicy or None
        )
