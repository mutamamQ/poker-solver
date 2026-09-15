# D204 deterministic deals and information noninterference — parent-normalized

Status: accepted design input; unauthorized skipped-test skeleton excluded.

Deal enumeration

- Traverse the Cartesian product of per-seat range tuples in seat/range order, carrying a used-card set seeded by the board. Prune a branch immediately when a combo collides.
- Each valid deal is an N-tuple of two-card tuples. Its exact weight is the product of `Fraction` weights. Reject zero total mass.
- Stop and fail as soon as valid deals exceed `max_deals`; never silently truncate or renormalize a prefix. The implementation may also use the declared node/work bound to fail closed on excessive enumeration work, but must document that disposition.
- Chance actions are `Action("DEAL", index)` in deterministic enumeration order. Normalize only at the public chance boundary; sum must be one within `1e-12`.

Information contract

The key contains version, N, owner, owner private combo, board, button, public commitments/contributions/remaining/folded state, public action history, and wager targets. It excludes every opponent combo, a deal index, iterator order, and hidden rank-table values.

Permanent noninterference tests

- Build four- and nine-player states whose opponent deals differ while the owner's cards and public state are identical; the owner's keys must be equal.
- Change only the owner's private combo; its key must differ.
- Different chance outcomes mapping to one infoset must expose identical owner/action signatures through `collect_nplayer_infosets`.
- Caller mutation of range lists or showdown mappings after config creation cannot alter deals or keys.

Bounded fixtures

Use one or two combos per seat and explicitly enumerate compatible expected deals for 4/5/9 seats. Tests assert order, exact weights before float conversion, chance mass, blocker filtering, deterministic repeats, `max_deals` failure, and no compatible-deal failure. No skipped or placeholder permanent tests are permitted.
