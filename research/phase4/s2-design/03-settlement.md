# D203 exact N-player settlement — parent-normalized

Status: accepted design input, corrected against production primitives.

Settlement pipeline

1. `refund_uncalled_excess(total_contributed)` returns matched contributions and per-seat refunds.
2. Add refunds to remaining stacks and subtract them from street commitment; reject a negative street commitment.
3. `build_pot_layers(matched, folded=...)` constructs exact integer layers.
4. Determine per-layer winners using higher integer showdown rank among `layer.eligible`; a lone live player wins every layer without showdown lookup.
5. `calculate_rake(..., flop_seen=True)` and `allocate_rake` apply one hand-level integer rake.
6. `award_pot_layers` awards each net layer by the declared odd-chip order.
7. Pad the returned awards tuple with zeros to N seats because zero-contribution trailing seats may not appear in any layer.
8. Final stack is refunded remaining plus awards. Utility is final minus starting stack. Require `sum(utilities)+rake==0` and `sum(final)+rake==sum(starting_stacks)`.

Independent ledger fixtures

- Four players: asymmetric all-ins create at least two layers; one folded contributor funds but cannot win; exact layer amounts, refunds, awards, and utilities are hand-derived.
- Five players: three contribution levels and a tie create deterministic odd chips. Rotate `odd_chip_order` and assert only the declared remainder recipients change.
- Nine players: all-in cascade with one combo per player produces several layers and a distinct eligible winner set per layer; assert exact integer conservation.
- Rake matrix: floor/ceiling/nearest, cap, minimum, NFND, and top-down/bottom-up allocation use existing pure primitives and compare to direct integer arithmetic.

Required attacks

Reject missing showdown coverage, rank vectors of the wrong dimension, bool ranks, invalid winner eligibility, all-folded/dead layers, excess rake, and caller mutation. Every terminal is checked before float conversion; player utilities may sum to `-house_rake`, while player-plus-house utility is exactly zero.

No new reach tracker or settlement primitive is needed. The existing `game_structure.py` functions remain the implementation under test, not the independent expected-value oracle.
