# S4 R2 Design Audit: Information Safety, Solver Compatibility, and Exact Strategy Lift

**Auditor:** R2A3 (non-author, wholly fresh)
**Candidate:** ARCHITECTURE_PHASE4_S4.md SHA-256 `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`
**Manifest:** research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md SHA-256 `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed`
**Base HEAD:** `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`
**Date:** 2026-09-16

---

## Executive Summary

**VERDICT: PASS with substantive evidence**

The S4 R2 architecture specification correctly addresses all three R1 findings (incomplete wire schema, ambiguous bounds, integer weight parsing) and establishes a sound foundation for exact-signature hand abstraction with:

1. **Information safety:** Fixed-bucket perfect recall with complete own-information keys and verified noninterference
2. **Solver compatibility:** Exact wire fidelity to current `information_state_key` structure in multistreet.py
3. **Exact strategy lift:** Complete ordered-action coverage with certified twin policy equality

No production/test code exists yet (expected for design audit). Current source files (model.py, cfr.py, best_response.py, api.py, multistreet.py) provide the authoritative baseline for integration.

---

## 1. Verification of Candidate Integrity

### 1.1 Hash Verification

```
✓ ARCHITECTURE_PHASE4_S4.md: 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2
✓ CANDIDATE_MANIFEST.md: f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed
✓ 02-engine-integration-codex.md: 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d
```

All three document hashes match manifest declarations exactly.

### 1.2 Base Repository State

- HEAD commit: `149780bf` (matches manifest)
- Tag `phase3-398-green` → `feba8222` (preserved, matches manifest)
- No S4 implementation code present (expected)
- Source files located under `src/poker_solver/` (not root)

---

## 2. Information Safety Analysis

### 2.1 Fixed-Bucket Perfect Recall (§3.3)

**Design commitment:**
> "A hand receives one private bucket at root and retains it through every street. No street-local rebucketing may merge distinct prior buckets."

**Abstract information key structure (§3.3, lines 71-77):**
- Policy version and canonical semantic config digest
- Acting player
- **Own fixed bucket ID** (not opponent bucket)
- Full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, terminal marker

**Excluded from key (§3.3, line 78):**
> "opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, and representative cards"

**Finding:** The abstract key correctly implements perfect recall by:
1. Including complete public observation history (board progression, betting sequence)
2. Preserving own bucket identity across streets (no rebucketing)
3. Excluding opponent private information and latent world details

**Verification requirement (§3.3, line 78):**
> "Compile-time recall and noninterference checks are required in addition to `validate_bounded_tree`."

This mandates explicit validation beyond tree structure checks.

### 2.2 Own-Information Noninterference

**Key property (§3.3, lines 71-72):**
> "Same abstract key therefore implies the same own observation/action sequence and ordered legal actions."

The abstract key contains:
- Own bucket (own cards abstracted)
- Public frame (observable to both players)
- Acting player

It excludes opponent bucket, ensuring that two histories with identical own observations and public events map to the same abstract key regardless of opponent's hidden cards.

**Signature certificate (§3.2, lines 64-66):**
> "Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand."

Hands in the same bucket have identical strategic continuations against all opponent hands, making them behaviorally indistinguishable from the owning player's perspective.

**Finding:** The design satisfies own-information noninterference. The abstract key depends only on own bucket and public observations, never on opponent's private bucket or exact cards.

### 2.3 Ordered Actions and Deterministic Signatures

**Action ordering (§3.1, line 47):**
> "source legal-action tuple order is preserved exactly"

**Bucket assignment (§3.1, line 48):**
> "bucket IDs are assigned by lexicographically sorted distinct complete signatures"

**Public transition validation (§4.3, lines 147-150):**
> "All members of a pair must have identical actor and ordered legal actions at a public frame. [...] Any disagreement fails instead of intersecting actions or dropping members."

The compiler verifies that all hands in a bucket produce identical ordered legal actions at every reachable public frame.

**Finding:** Action ordering is preserved from source through abstract policy. The design enforces deterministic action signatures per bucket-public-frame pair.

---

## 3. Solver Compatibility Analysis

### 3.1 Current `information_state_key` Wire Format

**Examined:** `src/poker_solver/multistreet.py` lines 439-456

```python
def information_state_key(self, player: int) -> InfoKey:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    if self.private_deal is None:
        raise ValueError("information key requires a private deal")
    own_cards = tuple(sorted(self.private_deal[player]))
    public_history = tuple(action for action in self.history if action.kind != "DEAL")
    return (
        self.config.version,
        player,
        own_cards,
        self.board,
        public_history,
        self.pot,
        self.committed,
        self.remaining,
        self.config.betting_mode,
    )
```

**Current exact key structure:**
1. `config.version` ("multistreet-v1")
2. `player` (0 or 1)
3. `own_cards` (sorted tuple of two card IDs)
4. `board` (tuple of card IDs)
5. `public_history` (tuple of Action, excluding DEAL)
6. `pot` (integer)
7. `committed` (tuple of two integers)
8. `remaining` (tuple of two integers)
9. `betting_mode` ("no-limit" or "pot-limit")

### 3.2 Abstract Key Mapping (§3.3)

**Specified abstract key (lines 71-77):**
- Policy version and canonical semantic config digest
- Acting player
- Own fixed bucket ID
- Full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, terminal marker

**Mapping correspondence:**

| Exact Key Component | Abstract Key Component | Transformation |
|---------------------|------------------------|----------------|
| `config.version` | policy version + config digest | Semantic digest replaces literal version |
| `player` | acting player | Direct |
| `own_cards` | own bucket ID | Abstraction: cards → bucket |
| `board` | public frame: board | Direct |
| `public_history` | public frame: history + RUNOUT history | Separated betting/chance |
| `pot` | public frame: pot | Direct |
| `committed` | public frame: committed | Direct |
| `remaining` | public frame: remaining | Direct |
| `betting_mode` | (in config digest) | Moved to digest |
| — | public frame: street | Added (derivable from board length) |
| — | public frame: total_contributed | Added (tracked in MultiStreetState) |
| — | public frame: last_raise_increment | Added (tracked in MultiStreetState) |
| — | public frame: terminal_reason | Added (tracked in MultiStreetState) |

**Finding:** The abstract key is a **superset** of the exact key's public information:
- All public components from exact key are preserved in abstract public frame
- Additional public fields (street, total_contributed, last_raise_increment, terminal_reason) are already tracked in `MultiStreetState` (lines 107-115)
- Own cards are replaced by own bucket (the abstraction)
- Config digest replaces version string (semantic equivalence)

### 3.3 Lift Function Specification (§4.1, lines 120-122)

```python
def abstract_key_for_exact(state: MultiStreetState, player: int,
                           plan: ReducedPlan) -> AbstractInfoKey: ...
```

**Lift traversal (§6, lines 229-231):**
> "Lifting traverses an explicitly bounded exact root only when requested. Every reachable exact key maps through its own hand's certified bucket and complete abstract policy. Ordered actions must match."

**Coverage requirement (§6, line 231):**
> "Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap."

**Twin policy equality (§6, line 231):**
> "Certified twin hands receive the same copied float values exactly, while each original exact key remains separately addressable."

**Finding:** The lift function design ensures:
1. Every exact key maps to exactly one abstract key via its hand's bucket
2. Ordered actions match between exact and abstract (enforced by bucket construction)
3. Twin hands (same bucket) receive identical policy values
4. Complete coverage is verified (no silent gaps)

### 3.4 Solver Integration Points

**Examined source files:**
- `cfr.py` lines 45, 67, 141: Uses `state.information_state_key(player)` for regret/strategy tables
- `best_response.py` lines 51, 108, 154: Uses `information_state_key` for response computation
- `api.py` lines 312-319: `complete_strategy` fills unvisited infosets uniformly

**Abstract solve result (§6, lines 196-203):**
```python
@dataclass(frozen=True, slots=True)
class AbstractSolveResult:
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    reduced_metric: NashConvResult
    exact_metric: NashConvResult | None
    strategy: Mapping[InfoKey, Mapping[Action, float]]
    lifted_strategy: Mapping[InfoKey, Mapping[Action, float]] | None
    plan: ReducedPlan
    ...
```

The `strategy` field uses the same `InfoKey` type as existing solvers, ensuring type compatibility.

**Finding:** The abstract solver produces strategies in the same `Mapping[InfoKey, Mapping[Action, float]]` format as existing CFR/MCCFR solvers, enabling reuse of:
- `complete_strategy` (api.py line 312)
- `nash_conv` (best_response.py line 206)
- `expected_values` (cfr.py line 58)

---

## 4. Exact Strategy Lift Analysis

### 4.1 Lift Traversal Bounds (§6, lines 227-232)

**Explicit bounds:**
> "Lifting traverses an explicitly bounded exact root only when requested. [...] Requested diagnostics that exceed them fail rather than returning silently missing fields."

**ExactEvaluationConfig (§6, lines 182-185):**
```python
@dataclass(frozen=True, slots=True)
class ExactEvaluationConfig:
    max_nodes: int
    max_depth: int
```

Lift is optional and independently bounded, preventing forced traversal of large exact trees during result construction.

### 4.2 Complete Coverage Verification (§6, line 231)

**Coverage requirement:**
> "Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap."

The lift function must:
1. Visit every reachable exact information set
2. Map each to its abstract policy via bucket membership
3. Detect and fail on:
   - Missing abstract policies (bucket without policy)
   - Duplicate exact keys mapping to different policies (corruption)
   - Config mismatches (wrong game)
   - Coverage gaps (unreachable exact keys)

**Finding:** The design explicitly forbids silent gap-filling. `complete_strategy` (which adds uniform policies to unvisited infosets) is prohibited from masking lift coverage failures.

### 4.3 Ordered Action Matching (§6, line 230)

**Action order preservation (§3.1, line 47):**
> "source legal-action tuple order is preserved exactly"

**Bucket construction validation (§4.3, lines 147-150):**
> "All members of a pair must have identical actor and ordered legal actions at a public frame. [...] Any disagreement fails instead of intersecting actions or dropping members."

**Lift requirement (§6, line 230):**
> "Ordered actions must match."

The lift function verifies that:
- Exact state legal actions match abstract policy actions
- Action order is identical
- No actions are added or removed

**Finding:** Three-layer validation ensures action consistency:
1. Bucket construction verifies identical actions for all members
2. Abstract policy preserves source action order
3. Lift verifies exact-to-abstract action matching

### 4.4 Twin Policy Equality (§6, line 231)

**Certified twins (§3.2, lines 64-66):**
> "Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand. [...] These are behavioural twins for the configured game."

**Lift policy copying (§6, line 231):**
> "Certified twin hands receive the same copied float values exactly, while each original exact key remains separately addressable."

**Wire schema (§9.1, lines 392-393):**
```
AbstractPolicyEntry = {"key": AbstractKeyRecord, "policy": [PolicyItem, ...]}
ExactPolicyEntry = {"key": ExactKeyRecord, "policy": [PolicyItem, ...]}
```

Both use `PolicyItem = {"action": ActionRecord, "probability": finite float}`.

**Finding:** Twin hands (same bucket) receive:
1. Identical abstract policy (single bucket policy)
2. Bit-identical float probability values (copied, not recomputed)
3. Separate exact key entries (each hand addressable)
4. No mutable aliasing (§9.1, line 454: "detached and deeply immutable")

### 4.5 Immutability and Isolation (§9.1, lines 454-455)

**Result immutability:**
> "Returned Python mappings and all nested containers are detached and deeply immutable; JSON conversion creates fresh lists/objects with no mutable alias to the result."

**Structured records (§9.1, line 455):**
> "Structured records, never `str(key)` dictionaries, preserve key/action identity."

**Finding:** The lifted strategy is:
- Deeply immutable (no mutable aliases)
- Detached from solver state
- Structured (preserves Action identity, not string keys)
- Safe for concurrent access and serialization

---

## 5. Uniform Repair Prohibition

### 5.1 Explicit Prohibition (§6, line 231)

**Coverage gap handling:**
> "Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap."

The design explicitly forbids using `complete_strategy` (which adds uniform policies to unvisited infosets) to hide lift coverage failures.

### 5.2 Complete vs. Lift Coverage

**`complete_strategy` usage (api.py lines 312-319):**
```python
def complete_strategy(root: GameState, strategy: Strategy) -> Strategy:
    """Fill lazily unvisited infosets with explicit uniform policies."""
    complete = {key: dict(policy) for key, policy in strategy.items()}
    for key, (_, actions) in collect_infosets(root).items():
        if key not in complete:
            probability = 1.0 / len(actions)
            complete[key] = {action: probability for action in actions}
    return complete
```

This function is appropriate for:
- MCCFR (which samples and may not visit all infosets)
- Lazy exact solvers

It is **inappropriate** for lift coverage gaps because:
- Lift should visit all reachable exact keys (bounded traversal)
- Missing abstract policy indicates bucket construction or solver bug
- Uniform fill would hide the bug

**Finding:** The prohibition is correct. Lift coverage gaps are structural errors, not lazy-visit artifacts.

---

## 6. Deep Immutability Verification

### 6.1 Immutable Records (§4.1, lines 82-90)

**Record specification:**
```python
@dataclass(frozen=True, slots=True)
class AbstractionConfig: ...

@dataclass(frozen=True, slots=True)
class Bucket: ...

@dataclass(frozen=True, slots=True)
class World: ...
```

All records use `frozen=True, slots=True` for:
- Immutability (frozen)
- Memory efficiency (slots)
- Hashability (frozen dataclasses are hashable if all fields are)

### 6.2 Defensive Detachment (§4.1, line 83)

**Specification:**
> "frozen/slotted, defensively detached records"

**Canonical inputs (§3.1, line 42):**
> "Construction first validates and defensively copies the source config."

The compiler must:
1. Copy input data structures (no mutable aliases to user data)
2. Freeze internal structures (no mutation after construction)
3. Return detached results (no mutable aliases to internal state)

### 6.3 Result Immutability (§9.1, lines 454-455)

**Wire schema immutability:**
> "Returned Python mappings and all nested containers are detached and deeply immutable; JSON conversion creates fresh lists/objects with no mutable alias to the result."

**Finding:** Three-layer immutability:
1. Input: Defensive copy on construction
2. Internal: Frozen dataclasses with slots
3. Output: Detached, deeply immutable results

---

## 7. Reduced vs. Exact Metric Scope

### 7.1 Explicit Scope Labeling (§6, lines 200, 202)

**AbstractSolveResult fields:**
```python
reduced_metric: NashConvResult
exact_metric: NashConvResult | None
...
metric_scope: Literal["reduced-game"]
```

**Wire schema (§9.1, lines 347-350):**
```
reduced_nashconv: finite nonnegative float
reduced_exploitability: finite nonnegative float
exact_nashconv: finite nonnegative float | null
exact_exploitability: finite nonnegative float | null
```

Metrics are explicitly labeled as reduced or exact, never ambiguous.

### 7.2 Diagnostic Status (§6, lines 201, 203)

**Status field:**
```python
exact_evaluation_status: Literal["not-requested", "completed"]
```

**Wire schema (§9.1, line 351):**
```
exact_evaluation_status: "not-requested" | "completed"
```

**Null semantics (§9.1, lines 362-363):**
> "When `exact_evaluation_status` is `not-requested`, both exact metrics and `lifted_strategy` are null. When it is `completed`, both exact metrics are finite and `lifted_strategy` is a non-null complete list."

No ambiguous partial results: either all exact diagnostics are present or all are null.

### 7.3 Metadata Distinction (§9.1, lines 418-437)

**Metadata fields:**
```
physical_node_count: positive integer
physical_terminal_count: positive integer
physical_chance_count: nonnegative integer
physical_decision_count: nonnegative integer
physical_max_depth: nonnegative integer
...
exact_node_count_analytic: positive integer | null
exact_node_count_status: "not-derived" | "derived-not-traversed" | "executed"
```

**Physical vs. exact distinction (§5, lines 162-163):**
> "`node_count` is exactly the history occurrence count produced by `validate_bounded_tree`: root, chance, decision, and terminal nodes. It is not bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size."

**Finding:** Metadata clearly distinguishes:
- Physical reduced counts (always present)
- Exact analytic counts (derived from formula, not traversed)
- Exact executed counts (from bounded traversal)
- Latent world counts (preprocessing)
- Infoset counts (not conflated with physical nodes)

---

## 8. Solver Compatibility with Current Codebase

### 8.1 GameState Protocol Compliance

**Examined:** `src/poker_solver/model.py` lines 29-36

```python
@runtime_checkable
class GameState(Protocol):
    def current_player(self) -> int: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> GameState: ...
    def information_state_key(self, player: int) -> InfoKey: ...
    def returns(self) -> tuple[float, float]: ...
```

**ReducedState specification (§4.1, lines 125-126):**
> "`ReducedState.child` is an O(1) validated node lookup and never materializes member subtrees. Root chance actions are deterministic `Action(\"ABSTRACT_DEAL\", k)` values for sorted nonempty bucket pairs."

ReducedState must implement the GameState protocol, making it compatible with:
- `CFRSolver` (cfr.py line 80)
- `MCCFRSolver` (mccfr.py)
- `best_response` (best_response.py line 199)
- `nash_conv` (best_response.py line 206)
- `validate_bounded_tree` (bounded_tree.py line 20)

**Finding:** ReducedState is a drop-in replacement for exact states in solver APIs.

### 8.2 Action Type Compatibility

**Examined:** `src/poker_solver/model.py` lines 12-22

```python
@dataclass(frozen=True, order=True, slots=True)
class Action:
    kind: str
    amount: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("action kind must be a non-empty string")
        if not isinstance(self.amount, int) or isinstance(self.amount, bool):
            raise ValueError("action amount must be an integer")
```

**Abstract deal actions (§4.1, line 125):**
> "Root chance actions are deterministic `Action(\"ABSTRACT_DEAL\", k)` values for sorted nonempty bucket pairs."

**Public chance actions (§4.1, line 125):**
> "Public chance retains `Action(\"RUNOUT\", card)`."

Both use the existing `Action` dataclass with string kind and integer amount.

**Finding:** No new action types or formats. Abstract actions use existing `Action` class.

### 8.3 Strategy Type Compatibility

**Examined:** `src/poker_solver/model.py` lines 24-26

```python
InfoKey = Hashable
ActionPolicy = Mapping[Action, float]
Strategy = Mapping[InfoKey, ActionPolicy]
```

**Abstract strategy (§6, line 197):**
```python
strategy: Mapping[InfoKey, Mapping[Action, float]]
```

**Lifted strategy (§6, line 198):**
```python
lifted_strategy: Mapping[InfoKey, Mapping[Action, float]] | None
```

Both use the same `Strategy` type alias.

**Finding:** Abstract and lifted strategies are type-compatible with existing solver outputs.

---

## 9. Diagnostics Caps and Fail-Closed Behavior

### 9.1 Independent Diagnostic Bounds (§6, lines 227-228)

**Specification:**
> "Exact diagnostics are absent by default and have independent explicit bounds; requested diagnostics that exceed them fail rather than returning silently missing fields."

**ExactEvaluationConfig (§6, lines 182-185):**
```python
@dataclass(frozen=True, slots=True)
class ExactEvaluationConfig:
    max_nodes: int
    max_depth: int
```

Diagnostic bounds are separate from reduced game bounds, allowing:
- Small reduced game (e.g., 161 nodes)
- Large exact game (e.g., 348,481 nodes)
- Optional bounded exact traversal (e.g., 10,000 node cap)

### 9.2 Fail-Closed on Exceeded Bounds (§9.1, line 362)

**Wire schema behavior:**
> "A requested diagnostic that exceeds a bound returns an error, never a successful response with `not-requested`."

If exact evaluation is requested but exceeds bounds:
- **Correct:** Return error
- **Incorrect:** Return success with `exact_evaluation_status: "not-requested"`

This prevents silent diagnostic failures.

### 9.3 All-or-Nothing Diagnostics (§9.1, lines 362-363)

**Specification:**
> "When `exact_evaluation_status` is `not-requested`, both exact metrics and `lifted_strategy` are null. When it is `completed`, both exact metrics are finite and `lifted_strategy` is a non-null complete list."

No partial diagnostics:
- Either all exact metrics + lifted strategy are present
- Or all are null

No mixed states like "exact metrics present but lifted strategy null".

**Finding:** Diagnostics are fail-closed and all-or-nothing, preventing ambiguous partial results.

---

## 10. R1 Finding Repairs

### 10.1 Finding 1: Incomplete Exact Response Schema

**R1 issue:** Earlier architecture had incomplete nested wire schema for exact keys, policies, and metadata.

**R2 repair (§9.1, lines 364-448):**

Exhaustive nested schemas:
```
ActionRecord = {"kind": string, "amount": integer}
RationalRecord = {"numerator": decimal integer string,
                  "denominator": positive decimal integer string}
PublicFrameRecord = { ... 10 required fields ... }
AbstractKeyRecord = { ... 4 required fields ... }
ExactKeyRecord = { ... 8 required fields ... }
PolicyItem = {"action": ActionRecord, "probability": finite float}
AbstractPolicyEntry = {"key": AbstractKeyRecord, "policy": [PolicyItem, ...]}
ExactPolicyEntry = {"key": ExactKeyRecord, "policy": [PolicyItem, ...]}
BucketRecord = { ... 4 required fields ... }
BucketPairRecord = { ... 4 required fields ... }
AbstractionMetadata = { ... 48 required fields ... }
```

**Verification:** §9.1 lines 336-448 provide complete, exhaustive schemas for all nested records. Every field is specified with exact type and constraints.

**Status:** ✓ REPAIRED

### 10.2 Finding 2: Ambiguous Optional vs. Required Base Bounds

**R1 issue:** Unclear whether `max_nodes` and `max_depth` are required or optional for the new abstraction operation.

**R2 repair (§9, lines 308-314):**
> "For this new operation only, `payload` has exactly these required fields: [...] `max_nodes` and `max_depth`, which are newly mandatory for this operation even though they remain optional with unchanged defaults for `solve-allstreet-postflop`."

> "`payload.max_nodes` must equal `abstraction.max_abstract_nodes`, and `payload.max_depth` must equal `abstraction.max_depth`; omission of either base bound fails before equality checking."

**Verification:** 
- New operation: `max_nodes` and `max_depth` are **required** in payload
- New operation: Must equal abstraction bounds (no ambiguity)
- Old operations: Retain optional behavior (backward compatible)

**Status:** ✓ REPAIRED

### 10.3 Finding 3: Integer Weight Parsing Above 2^53

**R1 issue:** Inherited `_float` helper coerces all numbers to float, losing exactness for integers above 2^53.

**R2 repair (§9, lines 332-333):**
> "For this operation, range-entry `weight` parsing does NOT call the existing `_float` helper. A non-bool JSON integer remains an integer through positivity/bit-cap validation and is converted with `Fraction(value)`; a finite JSON float remains a float through validation and is converted with `Fraction.from_float(value)`."

**Verification:**
- JSON integer → `Fraction(value)` (exact, no float conversion)
- JSON float → `Fraction.from_float(value)` (preserves binary float exactly)
- Bit cap validation (§3.1, line 52): Excessive numerator/denominator bit lengths fail
- Old operations retain `_float` behavior (backward compatible)

**Status:** ✓ REPAIRED

---

## 11. Exact Key Wire Fidelity

### 11.1 ExactKeyRecord Schema (§9.1, lines 384-390)

```
ExactKeyRecord = {
  "game_version": "multistreet-v1", "player": 0 | 1,
  "own_cards": [integer, integer], "board": [integer, ...],
  "history": [ActionRecord, ...], "pot": integer,
  "committed": [integer, integer], "remaining": [integer, integer],
  "betting_mode": "no-limit" | "pot-limit"
}
```

### 11.2 Comparison with Current `information_state_key`

**Current implementation (multistreet.py lines 446-456):**
```python
return (
    self.config.version,           # "multistreet-v1"
    player,                        # 0 | 1
    own_cards,                     # tuple(sorted(...))
    self.board,                    # tuple of card IDs
    public_history,                # tuple of Action (no DEAL)
    self.pot,                      # integer
    self.committed,                # tuple of two integers
    self.remaining,                # tuple of two integers
    self.config.betting_mode,      # "no-limit" | "pot-limit"
)
```

**Wire schema mapping:**

| Current Tuple Position | Wire Schema Field | Type Match |
|------------------------|-------------------|------------|
| 0: `config.version` | `game_version` | ✓ ("multistreet-v1") |
| 1: `player` | `player` | ✓ (0 or 1) |
| 2: `own_cards` | `own_cards` | ✓ (two integers) |
| 3: `board` | `board` | ✓ (integer array) |
| 4: `public_history` | `history` | ✓ (ActionRecord array) |
| 5: `pot` | `pot` | ✓ (integer) |
| 6: `committed` | `committed` | ✓ (two integers) |
| 7: `remaining` | `remaining` | ✓ (two integers) |
| 8: `betting_mode` | `betting_mode` | ✓ ("no-limit" or "pot-limit") |

**Finding:** The wire schema is an **exact serialization** of the current `information_state_key` tuple. All nine components are present with matching types and semantics.

### 11.3 ActionRecord Fidelity (§9.1, line 367)

```
ActionRecord = {"kind": string, "amount": integer}
```

**Current Action dataclass (model.py lines 12-15):**
```python
@dataclass(frozen=True, order=True, slots=True)
class Action:
    kind: str
    amount: int = 0
```

**Finding:** ActionRecord is an exact JSON representation of the Action dataclass.

---

## 12. Preregistered Fixture Verification

### 12.1 Small Fixture (§8.1, lines 259-278)

**Configuration:**
- Flop: Ah Kh Qh
- Runouts: (Jh,9h), (Jh,8h)
- Dead pot: 2, stack: 1
- No-limit, target (1,), river betting enabled
- P0: 2c3c, 2d3d (weights 1.0)
- P1: 2s3s, Th4s (weights 1.0)

**Expected exact stats:**
- 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12

**Expected abstract stats:**
- P0: 1 bucket
- P1: 2 buckets
- 161 physical nodes
- 4 exact worlds → 2 abstract deals (mass 1/2 each)

**Quality gate (§8.1, lines 273-275):**
> "Parent reference receipt at 1,000 exact vanilla iterations is values `(-0.9993335546875001, 0.9993335546875001)`, best responses `(-0.9993333333333333, 1.0000625)`, incentives `(2.2135416677393494e-07, 0.0007289453125000067)`, and NashConv `0.0007291666666667806`."

Both exact and abstract must achieve NashConv ≤ 0.02 chips after 1,000 iterations.

**Blocker companions (§8.1, lines 276-278):**
- Opponent-blocker: Equal showdown, three compatible deals, signatures stay separate
- Runout-blocker: One P0 hand blocks a runout, signatures stay separate

**Finding:** Small fixture tests:
1. Exact node count (321)
2. Reduced node count (161)
3. Bucket separation (P0: 1, P1: 2)
4. Quality convergence (NashConv ≤ 0.02)
5. Blocker safety (no incorrect merging)

### 12.2 Large Fixture (§8.2, lines 280-301)

**Configuration:**
- Same public game as small fixture
- P0: All pairs from {2c,3c,4c,5c,6c,7c,2d,3d,4d,5d,6d,7d} (66 hands)
- P1: All pairs from {2s,3s,4s,5s,6s,7s,2h,3h,4h,5h,6h,Th} (66 hands)
- All 4,356 pairs compatible

**Expected stats:**
- P0: 1 bucket (66 hands)
- P1: 2 buckets (55 no-Th, 11 with-Th)
- Pair masses: 5/6, 1/6
- Single-world tree: 81 nodes (34 terminals, 15 chance, 32 decisions, depth 12)
- Exact physical nodes: 1 + 4,356 * 80 = 348,481
- Reduced physical nodes: 1 + 2 * 80 = 161
- Charged signature slots: 17,424
- Belief entries: 17,424

**Acceptance criteria (§8.2, lines 299-301):**
> "Acceptance requires the complete reduced path — preflight, 1,000-iteration vanilla training, completion, reduced NashConv, frozen result, and strict serialization — under 10,000 physical nodes and depth 32. The same exact config with 10,000 nodes must fail before training."

**Finding:** Large fixture tests:
1. Exact count certificate: 348,481 (analytic, not traversed)
2. Reduced solve: 161 nodes (under 10,000 cap)
3. Exact preflight failure: Same config with 10,000 cap fails before training
4. Bucket separation: P1 Th-blocker creates distinct bucket
5. Scalability: 4,356 worlds → 2 abstract deals

---

## 13. Mathematical Certificates

### 13.1 Value-Gap Bound (§7, lines 237-251)

**Theorem (lines 247-249):**
> "For a lifted abstract profile `a` and independently trained exact reference `r`:
> `|v(a)-v(r)| <= max(e1(a)+e0(r), e0(a)+e1(r)) <= C(a)+C(r)`."

Where:
- `v(x)` = expected value of profile x
- `e0(x)` = P0 incentive to deviate
- `e1(x)` = P1 incentive to deviate
- `C(x)` = NashConv = e0(x) + e1(x)

**Preregistered bound (§7, lines 250-252):**
> "On the preregistered small fixture, both profiles must have exact-tree NashConv at most 0.02 chips after 1,000 vanilla iterations, giving a preregistered loose value-gap bound of 0.04 chips and the tighter observed incentive expression above."

**Finding:** The value-gap bound is a **finite-iteration comparison**, not a convergence claim. It bounds the difference between two finite profiles without assuming either is equilibrium.

### 13.2 Zero Model Error (§7, lines 253-256)

**Theorem (lines 253-256):**
> "The exact-signature quotient has terminal diameter zero and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value. [...] Therefore the v1 model-error term is exactly zero."

**Proof sketch:**
1. Hands in same bucket have identical labelled continuations (§3.2, lines 64-66)
2. Terminal diameter zero: Twins have identical payoffs against all opponent hands
3. Identical observable kernels: Twins have identical public chance laws
4. Rational value equality: Reduced value (bucket mixture) = exact value (hand mixture)
5. Model error = 0 (no approximation in abstraction)

**Clarification (§7, line 256):**
> "This is a certificate, not a claim that float CFR has converged."

The zero model error is a property of the abstraction, not the solver.

**Finding:** The mathematical certificate correctly distinguishes:
- Model error (abstraction quality): 0 for exact-signature
- Approximation error (solver convergence): Non-zero for finite-iteration CFR

### 13.3 Rational Certificate Tests (§10, lines 488-493)

**S4-I3 test requirements:**
> "Required cases cover [...] arbitrary nonuniform bucket-profile rational simulation equality, [...] rational incentive theorem, small 1,000-iteration quality gates."

**Small-fixture rational tests (§7, lines 254-256):**
> "Small-fixture tests rationalize returned policy probabilities with `Fraction.from_float`, normalize each policy exactly, and replay exact chance/utility. They independently compute rational best-response incentives over the bounded 321-node tree and compare ordinary float metrics within `1e-10` chips."

**Finding:** Rational certificate tests verify:
1. Rational value equality (reduced = exact lifted)
2. Rational best-response computation
3. Float metric agreement within tolerance
4. Arbitrary nonuniform bucket profiles (not just uniform)

---

## 14. No Uniform Repair in Lift

Reiteration of §5 findings:

**Explicit prohibition (§6, line 231):**
> "Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap."

**Rationale:**
- `complete_strategy` is for lazy-visit solvers (MCCFR)
- Lift is bounded exhaustive traversal
- Missing abstract policy = structural bug
- Uniform fill would hide the bug

**Finding:** The design correctly prohibits uniform repair in lift. Coverage gaps must fail, not be silently filled.

---

## 15. Implementation Batch Structure

### 15.1 RED-First Discipline (§10, lines 458-470)

**Requirement (line 458):**
> "No production bytes may precede each batch's behavioral RED."

**Test ownership:**
- S4-I1: `tests/test_abstraction_signatures.py` (RED owns)
- S4-I2: `tests/test_abstraction_reduced_game.py` (RED owns)
- S4-I3: `tests/test_abstraction_solve.py` (RED owns)
- S4-I4: `tests/test_api_v4_abstraction.py`, `test_phase4_s4_examples.py`, `test_phase4_s4_exports.py` (RED owns)

**GREEN ownership:**
- S4-I1: `src/poker_solver/abstraction.py` up through `build_buckets` only
- S4-I2: Complete `abstraction.py` compiler and `ReducedState`
- S4-I3: `src/poker_solver/abstraction_solve.py` and lift functions
- S4-I4: Additive edits to `api_v4.py`, `__init__.py`, examples, docs

**Finding:** Batch structure enforces:
1. Tests written before production code
2. No stubs that falsely pass later gates
3. Incremental integration (signatures → compiler → solver → API)
4. Focused scope per batch

### 15.2 Audit Cadence (§11, lines 513-528)

**Per-batch gates:**
1. Prove RED is genuine pre-production
2. Record literal test/source/report hashes
3. Run focused tests (no skipped/xfail)
4. Run S1/API compatibility tests
5. Run compileall and full pytest
6. Run git diff --check
7. Freeze candidate manifest
8. **Dispatch exactly six fresh BryantGPT non-authors**
9. Parent-authenticate transcripts, hashes, receipts
10. Repair every reproduced finding via new RED
11. Repeat wholly fresh audit of changed bytes
12. Commit accepted batch before next

**Finding:** Each batch receives a fresh exact-six non-author audit. Repairs trigger new audits of changed bytes only.

---

## 16. Compatibility with Existing Codebase

### 16.1 No Breaking Changes to Existing Operations

**API compatibility (§10, lines 507-510):**
> "GREEN owns additive edits to `api_v4.py`, `__init__.py`, canonical examples, and only S4-specific README/docs text. It may not rename or relax prior operations."

**Bound compatibility (§9, lines 312-314):**
> "For this new operation only, [...] `max_nodes` and `max_depth`, which are newly mandatory for this operation even though they remain optional with unchanged defaults for `solve-allstreet-postflop`."

**Weight parsing compatibility (§9, line 333):**
> "This rule [...] is local to the new operation. Direct-Python and decoded-JSON requests have identical behavior. Prior operations retain their existing float-coercion behavior."

**Finding:** S4 is strictly additive:
- New operation: `solve-allstreet-abstracted`
- New modules: `abstraction.py`, `abstraction_solve.py`
- Existing operations unchanged
- Existing tests unchanged (817 must pass)

### 16.2 Preserved Historical Baseline

**Tag preservation (§1, line 20):**
> "Historical tag `phase3-398-green` must remain exactly `feba8222a0b614b0c64eca59402403ce733195ea`."

**Regression baseline (§1, line 20):**
> "The live pre-S4 regression is 817 tests; 398 is the preserved historical baseline, not the current expected total."

**S4 completion gate (§12, line 548):**
> "`phase3-398-green` remains unchanged."

**Finding:** Historical baseline is frozen and verified. Current 817 tests must pass; 398 is historical reference only.

---

## 17. Findings Summary

### 17.1 Design Strengths

1. **Information safety:**
   - Fixed-bucket perfect recall (no rebucketing)
   - Own-information noninterference (abstract key excludes opponent bucket)
   - Ordered action preservation (source → abstract → lift)
   - Compile-time recall and noninterference checks

2. **Solver compatibility:**
   - ReducedState implements GameState protocol
   - Abstract strategies use existing Strategy type
   - Actions use existing Action dataclass
   - Drop-in replacement for CFR/MCCFR/best_response

3. **Exact strategy lift:**
   - Complete coverage verification (no silent gaps)
   - Ordered action matching (exact = abstract)
   - Twin policy equality (bit-identical floats)
   - Deep immutability (no mutable aliases)
   - Fail-closed on coverage gaps (no uniform repair)

4. **Wire fidelity:**
   - ExactKeyRecord is exact serialization of current `information_state_key`
   - All nine tuple components present with matching types
   - ActionRecord matches Action dataclass

5. **R1 repairs:**
   - Complete exhaustive nested wire schemas (§9.1)
   - Mandatory base bounds for new operation, optional for old (§9)
   - Integer weight preservation via Fraction(value) (§9)

6. **Metric scope:**
   - Explicit reduced vs. exact labeling
   - All-or-nothing diagnostics (no partial results)
   - Fail-closed on exceeded bounds
   - Physical vs. infoset vs. latent distinction

7. **Mathematical rigor:**
   - Zero model error certificate (exact-signature property)
   - Finite-iteration value-gap bound (no convergence claim)
   - Rational certificate tests (Fraction arithmetic)
   - Preregistered fixtures with quality gates

8. **Implementation discipline:**
   - RED-first per batch (tests before production)
   - Fresh exact-six non-author audit per batch
   - Strictly additive (no breaking changes)
   - Preserved historical baseline

### 17.2 No Blocking Issues Found

No design flaws, ambiguities, or incompatibilities that would prevent correct implementation.

---

## 18. Recommendations

### 18.1 Implementation Priorities

1. **S4-I1 (signatures):** Focus on:
   - Fraction conversion and bit-cap validation
   - Duplicate/zero/blocked support rejection
   - Opponent and runout blocker separation tests
   - Deterministic bucket ID assignment

2. **S4-I2 (compiler):** Focus on:
   - Generalized posterior arithmetic (§4.2, lines 131-143)
   - Public transition differential validation (§4.3, lines 147-150)
   - Exact odd-tie settlement (§4.4, lines 153-160)
   - Instrumented no-exact-subtree tests

3. **S4-I3 (solver):** Focus on:
   - Lift coverage verification (no silent gaps)
   - Twin policy bit-identical copying
   - Rational certificate helpers (Fraction arithmetic)
   - Exact diagnostic cap failures

4. **S4-I4 (API):** Focus on:
   - Exhaustive nested schema validation
   - Integer weight preservation (Fraction(value))
   - Mandatory base bounds for new operation
   - Deterministic list ordering

### 18.2 Test Coverage Priorities

1. **Blocker safety:**
   - Opponent-blocker fixture (equal showdown, different compatibility)
   - Runout-blocker fixture (one hand blocks a runout)
   - Equal-equity separation (same equity, different blockers)

2. **Lift coverage:**
   - Missing abstract policy (must fail)
   - Duplicate exact key disagreement (must fail)
   - Coverage gaps (must fail, not uniform-filled)
   - Twin policy bit-identical equality

3. **Rational certificates:**
   - Arbitrary nonuniform bucket profiles
   - Rational value equality (reduced = exact lifted)
   - Rational best-response computation
   - Float metric agreement within tolerance

4. **Diagnostics:**
   - Exact evaluation requested but exceeds bounds (must fail)
   - All-or-nothing diagnostics (no partial results)
   - Analytic vs. executed exact counts

---

## 19. Conclusion

**VERDICT: PASS**

The S4 R2 architecture specification is **sound, complete, and implementable**. It correctly addresses all three R1 findings and establishes a rigorous foundation for exact-signature hand abstraction with:

1. **Information safety:** Fixed-bucket perfect recall, own-information noninterference, ordered actions, compile-time validation
2. **Solver compatibility:** GameState protocol compliance, existing Strategy/Action types, drop-in replacement for CFR/MCCFR
3. **Exact strategy lift:** Complete coverage verification, ordered action matching, twin policy equality, fail-closed on gaps
4. **Wire fidelity:** ExactKeyRecord is exact serialization of current `information_state_key`
5. **Mathematical rigor:** Zero model error certificate, finite-iteration value-gap bound, rational tests
6. **Implementation discipline:** RED-first batches, fresh audits, strictly additive, preserved baseline

No blocking issues found. The specification is ready for S4-I1 implementation.

---

## Appendix A: Source File Inventory

**Examined files:**
- `src/poker_solver/model.py` (42 lines): GameState protocol, Action dataclass, CHANCE/TERMINAL constants
- `src/poker_solver/cfr.py` (162 lines): Vanilla CFR solver, regret matching, expected values
- `src/poker_solver/best_response.py` (215 lines): Scalable best response, NashConv, validation
- `src/poker_solver/api.py` (393 lines): Version-2 API, config loading, solve_multistreet, complete_strategy
- `src/poker_solver/multistreet.py` (500 lines): MultiStreetConfig, MultiStreetState, information_state_key (lines 439-456)
- `src/poker_solver/bounded_tree.py` (247 lines): validate_bounded_tree, BoundedTreeStats
- `src/poker_solver/api_v4.py` (708 lines): Version-4 API, strict validation helpers
- `src/poker_solver/allstreet.py` (partial): AllStreetPostflopConfig, S1 facade

**No S4 implementation files exist** (expected for design audit).

---

## Appendix B: Key Architecture Sections

- §3.2 (lines 54-68): Complete labelled signatures
- §3.3 (lines 69-79): Fixed buckets and perfect recall
- §4.1 (lines 82-126): Immutable records and public functions
- §4.2 (lines 127-146): Root mass and beliefs
- §4.3 (lines 147-152): Public betting transitions
- §4.4 (lines 153-160): Terminal utility
- §6 (lines 178-236): Strategy solve, lift, and truthful result
- §7 (lines 237-256): Mathematical certificates
- §8.1 (lines 259-278): Small comparable fixture
- §8.2 (lines 280-301): Large bounded fixture
- §9 (lines 302-456): Strict v4 API and serialization
- §10 (lines 458-511): RED-first implementation and audit batches
- §11 (lines 513-528): Per-batch parent gates
- §12 (lines 534-550): S4 completion gate

---

**Report hash:** (to be computed after file write)
**Auditor:** R2A3
**Status:** COMPLETED
