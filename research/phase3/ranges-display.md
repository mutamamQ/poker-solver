# Range editor and range/strategy display

## Evidence status

The restricted-tool BryantGPT researcher fetched sources but could not write its report. Parent verification rejected several summary claims: there is no accepted universal “PioSOLVER text grammar” matching the proposed `22+`/`AKo:0.5` syntax; case-insensitive normalization conflicts with this repository's strict card parsing; action frequencies must not use a loose `±0.01` normalization tolerance; and fold EV is not generally less than every alternative action EV.

## Verified references

1. GTO Wizard custom solution builder documents range text import, export in “standard UPI format,” range changes, and prefill: https://help.gtowizard.com/how-to-build-custom-solutions/
2. GTO Wizard Study Mode documents strategy, range, breakdown, and report tabs plus EV, equity, equity realization, and range weights: https://help.gtowizard.com/study-mode
3. GTO Wizard nodelocking documents per-combo, hand-category, and action-frequency controls: https://blog.gtowizard.com/introducing-nodelocking/
4. PioSOLVER UPI commands define a stable order of all 1,326 explicit starting hands and vector-valued range/strategy interfaces: https://piosolver.com/docs/upi/commands/
5. PioSOLVER's explanation of displayed numbers distinguishes range weights, strategies, EV, and matchup weighting: https://piosolver.com/docs/viewer/numbers_in_piosolver/
6. PioSOLVER's GTO FAQ explains that mixed actions approach equal EV at equilibrium and that aggregate hand EV must be matchup-weighted: https://piosolver.com/docs/faq/gto_concept/
7. Python `poker` library range notation is an independent example of shorthand parsing, but is not adopted wholesale: https://poker.readthedocs.io/en/latest/range.html

“UPI” in source 1 is a product interoperability statement, not enough by itself to infer a complete public grammar. Phase 3 therefore defines and versions its own strict, lossless grammar.

## Canonical range representation

### Explicit combinations

The source of truth is a mapping from a sorted two-card tuple to a finite weight in `[0,1]`. Cards use the repository's strict two-character grammar and canonical integer order. `(As,Kd)` and `(Kd,As)` are the same combo and duplicates are rejected unless an editor operation explicitly replaces an existing weight.

Hold'em has:

- 13 pair classes × 6 suit combinations = 78 combos;
- 78 distinct-rank suited classes × 4 = 312 combos;
- 78 distinct-rank offsuit classes × 12 = 936 combos;
- total 1,326 explicit combos and `13 + 78 + 78 = 169` canonical classes.

Zero weight is retained only when requested for round-trip/display purposes; solver conversion may omit it while preserving editor data.

### Canonical classes

A class token is exactly:

- pair: `AA` through `22`;
- suited distinct ranks: `AKs`, `A2s`, etc.;
- offsuit distinct ranks: `AKo`, `A2o`, etc.

Ranks must be descending in a distinct-rank class. `KAs`, lowercase ranks, missing `s/o`, and exact-card strings masquerading as classes fail. Expansion order is the global lexicographic order of canonical explicit combo card integers, not UI matrix order.

### Weight model

Weights are inclusion frequencies, not a probability distribution and need not sum to one. They must be finite JSON numbers in `[0,1]`; booleans fail. Chance construction later normalizes compatible joint mass after blockers. This preserves existing `WeightedCombo` semantics while adding the upper bound needed by the editor.

## Versioned range-text grammar

Phase 3 text format `poker-solver-range-v1` is intentionally small:

`document := entry ("," entry)*`

`entry := token [":" decimal_weight]`

`token := class | explicit_combo`

`explicit_combo := card card`

Whitespace is permitted only around commas, never inside tokens. Default weight is `1`. Decimal weights use plain base-10 notation without exponent, sign, NaN, or infinity. Examples:

- `AA,AKs:0.5,AsKd:0.25`
- `2c2d:0,AhKh`

No `+`, `-`, bracket, percentage, random, or third-party shorthand is accepted in v1. Import expands classes to combos. Overlap between entries is rejected rather than added, maximized, or last-write-wins. Export emits explicit canonical combos and weights so it is lossless; it does not attempt class compression. Weights use deterministic shortest decimal text that round-trips through the API's decimal parser.

This is a documented-boundary choice: broad Pio/GTO+/Flopzilla syntax compatibility is not claimed.

## Editor operations

`RangeEditor` is immutable from the caller's perspective: each operation returns a new canonical range.

- `add(token, weight=1)`: all expanded combos must be absent; otherwise fail atomically.
- `set_weight(token, weight)`: all expanded combos must already exist; otherwise fail atomically.
- `remove(token)`: all expanded combos must exist; otherwise fail atomically.
- `include_or_replace(token, weight)`: explicit upsert operation; never the implicit behavior of `add`.
- `blocked(dead_cards)`: returns the conditional compatible range without mutating the saved source.

Class operations are atomic. Removing `AKs` cannot silently remove only three of four combos if one is absent.

## Named save/load

A strict library file has:

- `format: "poker-solver-range-library-v1"`;
- `ranges`: an object keyed by validated names;
- each value: ordered entries `{cards:[c1,c2], weight:number}`.

Names match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` and are identifiers only; separators and `..` cannot become paths. Unknown top-level/entry fields, duplicate names after JSON decoding, duplicate combos, malformed cards, or invalid weights fail. Because Python's default JSON decoder loses duplicate object-key evidence, strict loading must use an `object_pairs_hook` that rejects duplicate keys.

Save uses canonical ordering, sorted keys, compact deterministic JSON, `allow_nan=False`, and atomic replace (`temporary file`, flush/fsync where supported, then `os.replace`). Loading never evaluates Python representations.

## Blockers and conditional mass

A combo is compatible iff neither card appears on the public board, known dead cards, or another already conditioned player's explicit hand. Filtering occurs before normalization.

Exact blocker fixture: with hero `AsKd`, villain source `AA,AKs,AKo` contains `6+4+12=22` combos. Compatible counts are:

- `AA`: 3;
- `AKs`: 2 (`AcKc`, `AhKh` under `cdhs` suits);
- `AKo`: 7;
- total: 12.

The 10 removed combos must be enumerated in the test rather than trusted as prose. Weighted mass uses original combo weights. Empty positive compatible mass is an error.

## Strategy/range table semantics

A range table is derived from the exact game tree, chance reach, a validated complete strategy, a selected public node/history, and a player. It never invents EVs from only a serialized display row.

For each compatible explicit hand `h`, report:

- source range weight;
- conditional reach/matchup mass at the selected public node;
- normalized conditional probability within the displayed player's range;
- if the player acts at this information set, every legal action's strategy probability and conditional action EV;
- mixed hand EV `sum_a strategy(h,a) * action_ev(h,a)`;
- optional 169-class aggregate generated only after explicit-combo rows.

For a fixed hand and selected information set, action EV is obtained by forcing that action at the information set while following the supplied profile afterward, averaging over compatible hidden opponent hands/chance outcomes with their conditional counterfactual reach. The player's own probability of choosing the forced action is not multiplied into that action EV. The mixed hand EV then applies the player's strategy probabilities.

A current-node opponent-range view reports the opponent's posterior compatible combo masses conditioned on the public history. If the opponent is the actor, it also reports their action breakdown. If not, action fields are absent rather than guessed from a later node.

### Aggregation identities

- Each displayed acting-hand action distribution sums to one within `1e-12`.
- Each hand mixed EV equals the dot product of its action probabilities and action EVs within `1e-12`.
- Aggregate frequency for action `a` is `sum_h reach(h)*sigma(h,a) / sum_h reach(h)`, not an unweighted average of hand rows.
- Aggregate EV is matchup/reach-weighted. Source 6 explicitly warns that a plain average of hand EVs is wrong when matchup counts differ.
- When the selected node is the root and the same payoff baseline is used, aggregating per-hand EVs for each player reproduces raw `expected_values` within `1e-12`.
- Class rows equal the weighted aggregation of their explicit child combos; they are display reductions, never solver inputs after blockers.

EV may be positive, zero, or negative for any action. The only ordering rule at exact equilibrium is that positive-probability actions are best responses/equal-valued up to solution error; finite-iteration strategies need not satisfy exact equality.

## Strict JSON API

Range editing requests use explicit operations and exactly versioned fields. Strategy-table requests identify a loaded game/preset, canonical public history/node ID, strategy document, and player. Successful output sorts explicit combos and actions canonically and includes:

- payoff baseline and units;
- conditioning node/history;
- player and whether they act;
- total compatible mass;
- explicit rows;
- optional class rows;
- aggregate frequencies and EV;
- unreachable/zero-mass status where applicable.

Unknown nodes, wrong-player information keys, incomplete strategies, zero conditional mass, NaN/infinity, probability sums outside `1e-10` input validation, and incompatible cards fail. Output computations target `1e-12`; the wider `1e-10` accepts serialization noise consistently with existing strategy validation.

## Independent acceptance fixtures

1. **Combinatorics:** expanding every 169 class yields exactly 1,326 unique combos: pair 78, suited 312, offsuit 936.
2. **Single classes:** `AA` yields 6, `AKs` yields 4, `AKo` yields 12, with exact expected cards.
3. **Parser rejection:** duplicate/overlapping entries, lowercase, shorthand, malformed decimal, bool JSON weights, and out-of-range weights fail.
4. **Round trip:** text import → canonical explicit export → import is exactly equal, including zero and fractional weights.
5. **Library round trip:** save/load is object-equal and byte-deterministic; duplicate JSON keys and traversal-like names fail.
6. **Blocker fixture:** `AsKd` against `AA,AKs,AKo` leaves exactly the 12 independently enumerated combos above.
7. **Bayes/action split:** prior combo masses multiplied by observed action probabilities produce the expected action-specific range; sums match the inference module.
8. **Tiny tree table:** enumerate every terminal manually; compare each hand/action EV and mixed EV within `1e-12`.
9. **Raw-strategy identity:** per-hand action rows exactly reproduce the corresponding raw information-set policy.
10. **Aggregation:** own and opponent explicit rows independently aggregate to raw root EV and action frequencies within `1e-12`.
11. **Noninterference:** changing only an opponent hidden hand may change terminal strength but never the acting player's information key or legal action tuple.
12. **Unreachable node:** zero conditional mass fails clearly; it must not emit NaN rows.

## Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| Explicit 1,326-combo weighted ranges | Implement |
| Strict 169-class expansion | Implement |
| Add/remove/set/upsert | Implement |
| Named JSON library save/load | Implement |
| Lossless project text import/export | Implement |
| Broad third-party shorthand/UPI compatibility | Documented boundary |
| Per-combo own and opponent range views | Implement for bounded explicit trees |
| Per-action and mixed hand EV | Implement by exact conditional traversal |
| Aggregate class/frequency/EV tables | Implement as explicit-row reductions |
| GUI matrix/editor | Out of backend scope |
| Unrestricted large-game tables/neural EV | Documented boundary |

Every implementation sub-batch requires a fresh non-author adversarial sign-off under `review/phase3/` before the next feature batch starts.
