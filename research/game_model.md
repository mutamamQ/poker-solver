# Game and information-set model

Use a small protocol rather than one universal mutable poker state. A finite game exposes: `initial_state()`, `current_player()` (`CHANCE=-1`, `TERMINAL=-2`, or 0/1), deterministic `legal_actions()`, normalized `chance_outcomes()`, immutable `child(action)`, `information_state_key(player)`, and `returns()` at terminals.

## Invariants

- Exactly one node kind applies. Terminal nodes have no actions; chance nodes have outcomes; player nodes have legal actions.
- Chance outcomes are deterministic in order, unique, nonnegative, and sum to one.
- An information-set key contains game/version, acting player, that player's observations/private cards, and the complete sequence of that player's remembered observations/actions. It excludes hidden opponent cards.
- All histories sharing a key have the same acting player and same ordered legal-action tuple. Check this globally during tree audit.
- Immutable states make traversals reproducible and prevent sibling-branch contamination.
- Action identities encode semantics and amounts without delimiter ambiguity. Prefer tuples/dataclasses as dictionary keys; JSON is presentation, not identity.
- Terminal returns use one fixed baseline and satisfy u0+u1=0.

## Proposed types

`Action(kind: Enum, amount: int|None)` is frozen and ordered. Game-specific states are frozen dataclasses. The generic solver depends only on the protocol. Kuhn state stores dealt cards plus action-history string. A Hold'em river state stores board, private combo (when traversing the full state), initial pot, per-player street contributions, actor, public action tuple, last full raise size, remaining stacks and terminal result.

Do not sort the board during serialization: card order can encode the public reveal sequence in multi-street games. Do sort unordered hole-card pairs canonically. Avoid `assert` for user validation because optimized Python can remove assertions.

## Limited Hold'em boundary

This reference supports one already-dealt river, two players, explicit combo-weighted ranges, no rake, equal or explicit remaining stacks, and a finite configured set of legal raise-to amounts. No blinds, side pots, multiway play, earlier streets, card abstraction, or automatic off-tree sizing are claimed. Chance at the root enumerates compatible ordered private-hand pairs with conditional normalized weight.

## Audit tests

Traverse the complete game and verify state immutability/hash stability, deterministic child ordering, card uniqueness, one chance-probability mass, one owner/legal-action signature per infoset key, no cycles, reachable terminal nodes, finite zero-sum utilities, and no hidden-card component in a player's key. Construct two histories differing only in opponent cards and require the same key; construct two distinct public action histories and require different keys.

## Common failures

Hidden-card leakage; key delimiter collision; omitting bet size from history; losing perfect recall; different legal actions under one key; pot/contribution double counting; treating a short all-in as a full raise; per-history instead of per-infoset best responses; mutable deck reuse; unordered set traversal; and utility measured from inconsistent baselines.

## Sources

- OpenSpiel game/algorithm framework: https://github.com/google-deepmind/open_spiel
- OpenSpiel Kuhn implementation: https://github.com/google-deepmind/open_spiel/tree/master/open_spiel/games
- ACPC infrastructure/game definitions: https://github.com/ethansbrown/acpc
- Original CFR assumptions and information sets: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
