# Range editor and named range persistence/import/export: design specification

## 1. Scope and ownership

This design specifies the Phase 3 weighted range editor, deterministic versioned serialization, named range persistence, import/export, and strict JSON API. It implements the canonical range representation, versioned text grammar, editor operations, library save/load, and blocker-aware conditional mass defined in `research/phase3/ranges-display.md`.

**Module ownership:**

- `src/poker_solver/range_editor.py`: core editor, parser, serializer
- `tests/test_range_editor.py`: acceptance fixtures and round-trip oracles

**Dependencies:**

- `cards.py`: strict two-character card grammar, canonical integer order, validation
- `equity.py`: `WeightedCombo` frozen dataclass, blocker-aware range filtering

No other modules are modified. The editor is a pure data-transformation layer; it does not import solver, game, or CLI modules.

## 2. Canonical range representation

### 2.1 Internal model

A range is an immutable mapping from a sorted two-card tuple to a finite weight in `[0,1]`:

```python
@dataclass(frozen=True, slots=True)
class Range:
    combos: dict[tuple[int, int], float]
```

Internal invariants enforced at construction:

1. Every key is a sorted two-card tuple of distinct canonical card integers.
2. Every weight is a finite JSON-compatible number in `[0,1]`.
3. No duplicate combos (enforced by dict identity).
4. Zero weights are retained only when explicitly requested for round-trip/display purposes.

Cards use the repository's strict two-character grammar (`23456789TJQKA` ranks, `cdhs` suits) and canonical integer order from `cards.py`. `(As,Kd)` and `(Kd,As)` are the same combo; the constructor normalizes to `(min, max)` and rejects duplicates.

### 2.2 Combinatorics

Hold'em has exactly 1,326 explicit combos:

- 13 pair classes × 6 suit combinations = 78 combos
- 78 distinct-rank suited classes × 4 = 312 combos
- 78 distinct-rank offsuit classes × 12 = 936 combos
- Total: 1,326 combos, 169 canonical classes

Acceptance test: expanding every 169 class yields exactly 1,326 unique combos with the expected distribution.

### 2.3 Canonical class tokens

A class token is exactly:

- Pair: `AA` through `22`
- Suited distinct ranks: `AKs`, `A2s`, etc.
- Offsuit distinct ranks: `AKo`, `A2o`, etc.

Ranks must be descending in a distinct-rank class. Validation rejects:

- Lowercase ranks
- Missing `s`/`o` suffix
- Ascending rank order (`KAs`)
- Exact-card strings masquerading as classes

Expansion order is the global lexicographic order of canonical explicit combo card integers, not UI matrix order.

### 2.4 Weight model

Weights are inclusion frequencies, not a probability distribution. They need not sum to one. Validation:

- Must be finite JSON numbers in `[0,1]`
- Booleans fail (strict type checking)
- NaN, infinity, negative values fail

This preserves existing `WeightedCombo` semantics from `equity.py` while adding the upper bound needed by the editor. Chance construction later normalizes compatible joint mass after blockers.

## 3. Versioned range-text grammar

### 3.1 Grammar specification

Phase 3 text format `poker-solver-range-v1` is intentionally small:

```
document := entry ("," entry)*
entry := token [":" decimal_weight]
token := class | explicit_combo
explicit_combo := card card
class := pair | suited | offsuit
pair := rank rank
suited := rank rank "s"
offsuit := rank rank "o"
rank := "A" | "K" | "Q" | "J" | "T" | "9" | "8" | "7" | "6" | "5" | "4" | "3" | "2"
card := rank suit
suit := "c" | "d" | "h" | "s"
decimal_weight := ["0"] "." digit+ | "1" ["." "0"*] | "0"
```

**Whitespace:** permitted only around commas, never inside tokens.

**Default weight:** `1` when omitted.

**Decimal weights:** plain base-10 notation without exponent, sign, NaN, or infinity.

**Examples:**

- `AA,AKs:0.5,AsKd:0.25`
- `2c2d:0,AhKh`

**Explicitly rejected:**

- `+`, `-`, bracket, percentage, random, or third-party shorthand
- Overlap between entries (rejected rather than added, maximized, or last-write-wins)

This is a documented-boundary choice: broad Pio/GTO+/Flopzilla syntax compatibility is not claimed.

### 3.2 Parser implementation

**Module:** `range_editor.py`

**Function:** `parse_range_text(text: str, version: str = "poker-solver-range-v1") -> Range`

**Algorithm:**

1. Validate version string exactly.
2. Split on commas, strip whitespace around each entry.
3. For each entry:
   - Split on `:` to separate token and optional weight.
   - Parse token as class or explicit combo.
   - Parse weight as decimal (default `1`).
   - Expand class to explicit combos if needed.
   - Validate weight in `[0,1]`, finite, not boolean.
4. Accumulate all expanded combos.
5. Reject duplicate/overlapping combos atomically.
6. Return frozen `Range`.

**Validation failures (raise `ValueError` with specific message):**

- Unknown version
- Lowercase ranks
- Missing `s`/`o` suffix
- Malformed decimal
- Boolean JSON weights
- Out-of-range weights
- Duplicate combos
- Invalid card strings

### 3.3 Serializer implementation

**Function:** `export_range_text(range: Range, version: str = "poker-solver-range-v1") -> str`

**Algorithm:**

1. Validate version string exactly.
2. Sort combos by canonical card integer order.
3. For each combo:
   - Format as explicit two-card string.
   - Format weight using deterministic shortest decimal text that round-trips.
   - Emit `card1card2:weight` or `card1card2` if weight is exactly `1`.
4. Join with `,`.
5. Return string.

**Deterministic weight formatting:**

- Use Python's `Decimal` for exact decimal representation.
- Format with minimum precision that round-trips through the parser.
- No exponent notation.
- `1.0` serializes as `1`.
- `0.5` serializes as `0.5`.
- `0.333333...` uses sufficient precision to round-trip within `1e-15`.

**Export is lossless:** it emits explicit canonical combos and weights. It does not attempt class compression.

## 4. Editor operations

`RangeEditor` is immutable from the caller's perspective: each operation returns a new canonical `Range`.

### 4.1 Operations

**Function signatures:**

```python
def add(range: Range, token: str, weight: float = 1.0) -> Range:
    """All expanded combos must be absent; otherwise fail atomically."""

def set_weight(range: Range, token: str, weight: float) -> Range:
    """All expanded combos must already exist; otherwise fail atomically."""

def remove(range: Range, token: str) -> Range:
    """All expanded combos must exist; otherwise fail atomically."""

def include_or_replace(range: Range, token: str, weight: float) -> Range:
    """Explicit upsert operation; never the implicit behavior of add."""

def blocked(range: Range, dead_cards: tuple[int, ...]) -> Range:
    """Returns the conditional compatible range without mutating the saved source."""
```

### 4.2 Atomicity

Class operations are atomic. Removing `AKs` cannot silently remove only three of four combos if one is absent. Validation:

1. Expand token to explicit combos.
2. Check precondition for all combos.
3. If any combo fails, raise `ValueError` with specific message.
4. If all pass, apply operation and return new `Range`.

### 4.3 Blocker semantics

A combo is compatible iff neither card appears in `dead_cards`. Filtering occurs before normalization.

**Exact blocker fixture (from `ranges-display.md`):**

With hero `AsKd`, villain source `AA,AKs,AKo` contains `6+4+12=22` combos. Compatible counts:

- `AA`: 3 (remove `AsAx`, `AdAx`)
- `AKs`: 2 (`AcKc`, `AhKh` under `cdhs` suits)
- `AKo`: 7 (remove `AsKx`, `AxKd`)
- Total: 12

The 10 removed combos must be enumerated in the test rather than trusted as prose. Weighted mass uses original combo weights. Empty positive compatible mass is an error.

## 5. Named save/load

### 5.1 Library file format

A strict library file has:

```json
{
  "format": "poker-solver-range-library-v1",
  "ranges": {
    "BTN_open": [
      {"cards": ["As", "Ah"], "weight": 1.0},
      {"cards": ["As", "Kd"], "weight": 0.5}
    ],
    "BB_3bet": [
      {"cards": ["Ac", "Ad"], "weight": 1.0}
    ]
  }
}
```

**Fields:**

- `format`: exactly `"poker-solver-range-library-v1"`
- `ranges`: object keyed by validated names
- Each value: ordered entries `{"cards": [c1, c2], "weight": number}`

**Name validation:**

- Match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`
- Identifiers only; separators and `..` cannot become paths
- No leading/trailing whitespace

**Entry validation:**

- `cards`: array of exactly two strict card strings
- `weight`: finite JSON number in `[0,1]`, not boolean
- Unknown fields fail
- Duplicate combos within a range fail
- Malformed cards fail

**Duplicate key detection:**

Because Python's default JSON decoder loses duplicate object-key evidence, strict loading must use an `object_pairs_hook` that rejects duplicate keys:

```python
def reject_duplicate_keys(pairs):
    seen = set()
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
    return dict(pairs)

json.loads(text, object_pairs_hook=reject_duplicate_keys)
```

### 5.2 Save implementation

**Function:** `save_range_library(path: str, ranges: dict[str, Range]) -> None`

**Algorithm:**

1. Validate all range names.
2. Build canonical JSON structure:
   - `format`: `"poker-solver-range-library-v1"`
   - `ranges`: sorted by name
   - Each range: sorted combos, each as `{"cards": [c1, c2], "weight": w}`
3. Serialize with:
   - Sorted keys
   - Compact deterministic JSON (no extra whitespace)
   - `allow_nan=False`
   - Canonical card order
4. Atomic replace:
   - Write to temporary file in same directory
   - Flush/fsync where supported
   - `os.replace(temp, path)`

**Deterministic output:**

- Same input produces byte-identical output.
- Canonical ordering: names sorted, combos sorted, keys sorted.
- No floating-point non-determinism.

### 5.3 Load implementation

**Function:** `load_range_library(path: str) -> dict[str, Range]`

**Algorithm:**

1. Read file.
2. Parse JSON with `object_pairs_hook=reject_duplicate_keys`.
3. Validate `format` exactly.
4. Validate all range names.
5. For each range:
   - Validate each entry.
   - Parse cards.
   - Validate weight.
   - Reject duplicate combos.
   - Build `Range`.
6. Return dict.

**Validation failures (raise `ValueError`):**

- Unknown top-level fields
- Duplicate names after JSON decoding
- Duplicate combos within a range
- Malformed cards
- Invalid weights
- Unknown entry fields

**Security:**

Loading never evaluates Python representations. Only JSON parsing is used.

## 6. Strict JSON API

### 6.1 Range editing requests

Range editing requests use explicit operations and exactly versioned fields.

**Request schema:**

```json
{
  "version": 3,
  "operation": "add" | "set_weight" | "remove" | "include_or_replace" | "blocked",
  "range": "<range-text-v1>" | {"format": "poker-solver-range-library-v1", "name": "..."} | {"combos": [{"cards": [...], "weight": ...}]},
  "token": "AA" | "AKs" | "AsKd",
  "weight": 0.5,
  "dead_cards": ["As", "Kd"]
}
```

**Response schema:**

```json
{
  "format": "poker-solver-range-v1",
  "combos": [
    {"cards": ["As", "Ah"], "weight": 1.0}
  ],
  "total_combos": 1326,
  "total_weight": 1326.0
}
```

### 6.2 Validation

**Unknown nodes, wrong-player information keys, incomplete strategies, zero conditional mass, NaN/infinity, probability sums outside `1e-10` input validation, and incompatible cards fail.**

Output computations target `1e-12`; the wider `1e-10` accepts serialization noise consistently with existing strategy validation.

### 6.3 CLI integration

**New subcommands:**

```bash
poker-solver range parse <text> --json
poker-solver range export <library-file> <name> --json
poker-solver range add <library-file> <name> <text>
poker-solver range blocked <text> --dead As,Kd --json
```

**Exit codes:**

- 0: success
- 1: internal runtime failure
- 2: invalid input/config

**JSON output:**

- Sorted keys
- Deterministic fields only
- `allow_nan=False`

## 7. Independent acceptance fixtures

All fixtures from `research/phase3/ranges-display.md` section "Independent acceptance fixtures":

1. **Combinatorics:** expanding every 169 class yields exactly 1,326 unique combos: pair 78, suited 312, offsuit 936.
2. **Single classes:** `AA` yields 6, `AKs` yields 4, `AKo` yields 12, with exact expected cards.
3. **Parser rejection:** duplicate/overlapping entries, lowercase, shorthand, malformed decimal, bool JSON weights, and out-of-range weights fail.
4. **Round trip:** text import → canonical explicit export → import is exactly equal, including zero and fractional weights.
5. **Library round trip:** save/load is object-equal and byte-deterministic; duplicate JSON keys and traversal-like names fail.
6. **Blocker fixture:** `AsKd` against `AA,AKs,AKo` leaves exactly the 12 independently enumerated combos above.

Additional editor-specific fixtures:

7. **Add atomicity:** adding `AKs` to a range containing `AcKc` fails atomically; no partial state.
8. **Set_weight atomicity:** setting weight for `AKs` when only 3 of 4 combos exist fails atomically.
9. **Remove atomicity:** removing `AKs` when only 3 of 4 combos exist fails atomically.
10. **Include_or_replace idempotence:** calling twice with same token/weight produces identical result.
11. **Blocked empty mass:** blocking all combos raises specific error, not NaN.
12. **Name validation:** names with leading digits, `..`, `/`, and length > 64 fail.

## 8. Round-trip oracles

### 8.1 Text round-trip

**Oracle:** `parse_range_text(export_range_text(range)) == range`

**Test cases:**

- Full 1,326-combo range
- Single combo with weight `0.5`
- Zero-weight combo (explicit retention)
- Mixed classes and explicit combos

**Tolerance:** exact object equality after normalization.

### 8.2 Library round-trip

**Oracle:** `load_range_library(path) == ranges` after `save_range_library(path, ranges)`

**Byte-determinism:** saving the same ranges twice produces byte-identical files.

**Test cases:**

- Empty library
- Single range
- Multiple ranges with overlapping combos (different ranges)
- Names with `_`, `.`, `-`

### 8.3 Blocker round-trip

**Oracle:** `blocked(blocked(range, dead1), dead2) == blocked(range, dead1 + dead2)`

**Test cases:**

- Sequential blocking
- Commutative blocking (order independence)
- Blocking with empty dead cards (identity)

## 9. Module ownership and boundaries

### 9.1 Exclusive ownership

**Worker 11 (new):**

- `src/poker_solver/range_editor.py`
- `tests/test_range_editor.py`

**No other workers edit these files.**

### 9.2 Dependencies

**Read-only imports:**

- `cards.py`: `validate_unique`, `format_card`, `parse_card`, `FULL_DECK`
- `equity.py`: `WeightedCombo`

**No imports from:**

- `cfr.py`, `mccfr.py`, `best_response.py`, `audit.py`, `api.py`, `cli.py`

The editor is a pure data-transformation layer.

### 9.3 Integration points

**Future integration (not in this batch):**

- `api.py`: add range-editing endpoints
- `cli.py`: add range subcommands
- `multistreet.py`: use `Range` for initial combo weights

**Integration is orchestrator responsibility, not worker 11.**

## 10. Backward compatibility

### 10.1 Versioning

**Text format:** `poker-solver-range-v1`

**Library format:** `poker-solver-range-library-v1`

**Future versions:**

- `v2` may add class compression, shorthand, or third-party compatibility.
- `v1` parsers must reject unknown versions explicitly.
- `v1` serializers must never emit `v2` format.

### 10.2 Existing code

**No changes to:**

- `equity.py`: `WeightedCombo` remains unchanged.
- `cards.py`: no new card grammar.
- All Phase 1+2 tests remain green.

**New code:**

- `range_editor.py`: new module, no existing dependencies.
- `test_range_editor.py`: new test file.

### 10.3 API stability

**Phase 3 range API is additive:**

- No changes to existing `solve-spot`, `solve-kuhn`, `equity`, `evaluate` endpoints.
- New `range` subcommands are opt-in.

## 11. Tests and oracles

### 11.1 Test organization

**File:** `tests/test_range_editor.py`

**Sections:**

1. Combinatorics (fixtures 1-2)
2. Parser validation (fixture 3)
3. Round-trip oracles (fixtures 4-5)
4. Blocker fixtures (fixture 6)
5. Editor atomicity (fixtures 7-9)
6. Name validation (fixture 12)
7. Edge cases (empty range, zero weights, etc.)

### 11.2 Slow tests

**Mark with `@pytest.mark.slow`:**

- Full 1,326-combo expansion
- Exhaustive blocker enumeration
- Large library save/load

**Fast tests (default suite):**

- Single class expansion
- Small blocker fixture
- Parser rejection
- Round-trip on small ranges

### 11.3 Determinism tests

**Byte-determinism:**

- Save same ranges twice → byte-identical files
- Export same range twice → identical text

**Order independence:**

- Permute input combo order → same canonical output
- Permute library name order → same canonical JSON (after sorting)

### 11.4 Failure tests

**Strictly reject:**

- Lowercase ranks
- Missing `s`/`o` suffix
- Malformed decimal
- Boolean JSON weights
- Out-of-range weights
- Duplicate combos
- Invalid card strings
- Duplicate JSON keys
- Traversal-like names (`..`, `/`)
- Names > 64 chars
- Unknown version strings
- Unknown top-level fields
- Partial atomicity violations

## 12. Acceptance gates

Before merging:

1. All 185 Phase 1+2 tests remain green.
2. All 12 range-editor fixtures pass.
3. Round-trip oracles pass with exact equality.
4. Blocker fixture enumerates exactly 12 combos.
5. Library save/load is byte-deterministic.
6. Parser rejects all invalid inputs with specific errors.
7. Editor operations are atomic (no partial state).
8. No new dependencies added to `pyproject.toml`.
9. Fresh non-author adversarial review under `review/phase3/range-editor.md` signs off.

## 13. Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| Explicit 1,326-combo weighted ranges | Implement |
| Strict 169-class expansion | Implement |
| Add/remove/set/upsert | Implement |
| Named JSON library save/load | Implement |
| Lossless project text import/export | Implement |
| Blocker-aware conditional mass | Implement |
| Deterministic versioned serialization | Implement |
| Strict JSON API | Implement |
| CLI subcommands | Implement |
| Round-trip oracles | Implement |
| Broad third-party shorthand/UPI compatibility | Documented boundary |
| Class compression in export | Documented boundary (future `v2`) |
| GUI matrix/editor | Out of backend scope |
| Unrestricted large-game tables/neural EV | Documented boundary |

Every implementation sub-batch requires a fresh non-author adversarial sign-off under `review/phase3/` before the next feature batch starts.
