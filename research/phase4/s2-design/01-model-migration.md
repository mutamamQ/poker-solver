# D201 generic 2–9-player model — parent-normalized

Status: accepted design input, not implementation authority.

Decision

S2 adds `src/poker_solver/nplayer_postflop.py`; it does not refactor or adapt the frozen `multiway.py` path. Existing `MultiwayConfig`, `ThreePlayerPostflopState`, and `create_three_player_root` remain byte-for-byte compatible through S2-I1.

New typed contracts

- `NPlayerPostflopConfig`, frozen and slotted, with exact `version="nplayer-postflop-v1"`, strict integer `num_players` from 2 through 9, contiguous seat indices `0..N-1`, and N-length stacks/contributions/folded/ranges/odd-chip order/showdown ranks.
- `NPlayerPostflopState`, frozen and slotted, implementing the existing `NPlayerGameState` protocol.
- `create_nplayer_postflop_root` and a deterministic bounded deal enumerator.

Config invariants

- Reject bool-as-int everywhere; require positive starting stacks and positive total initial pot, nonnegative contributions not exceeding stacks, at least two initially live seats, and a button in range.
- Board has 3/4/5 unique nonnegative cards; each range is a nonempty tuple of unique `WeightedCombo` values.
- Wager targets are positive, unique, increasing integers; bounds are positive integers; odd-chip order is exactly a permutation of all seats.
- Every showdown key is an N-tuple of disjoint two-card combos and every rank vector has length N; detach the caller mapping with `MappingProxyType`.

State invariants

- Every per-seat tuple has length N; `pot == sum(total_contributed)`; `remaining[i]+total_contributed[i]==starting_stacks[i]`; and `street_committed[i] <= total_contributed[i]`.
- Pending seats are unique/in-range/live/actionable; `can_raise` is N booleans; action/history/phase fields are strict.
- Chance root has no private deal or history. Dealt states use a configured compatible deal. Terminal values are N integers and satisfy `sum(values)+house_rake==0`; nonterminals carry neither settlement nor rake.
- Information keys include only the requesting seat's private combo plus public state; opponent combos and deal index are absent.

Compatibility oracle

A permanent regression constructs equivalent singleton 3-player old/new configs, enumerates every bounded action path, and compares legal actions, terminal ledgers, information partitions, and deterministic solve values. Existing Phase-3 tests remain unchanged.
