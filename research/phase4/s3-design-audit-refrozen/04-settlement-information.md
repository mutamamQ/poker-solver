# S3 refrozen audit report 04 — settlement and information

**Auditor:** A3L4 (corrective substance audit after A3K4 ownership ended)  
**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Scope:** Settlement (fold awards, uncalled refunds, side-pot layers, ties/odd chips, terminal-table and showdown-ranks continuations, exact zero-sum utility with S3 no-rake constraint) and information noninterference.

---

## 1. Settlement: fold awards and uncalled refunds

### 1.1 Fold-out terminal accounting (§8)

The architecture states:

> Before any terminal is finalized, call `refund_uncalled_excess(total_contributed)`. Add refunds to remaining stacks, replace contributions and pot with matched amounts, and subtract refunds from current street commitments. A negative street commitment is an invariant violation.

For fold-out:

> build exact matched pot layers with folded eligibility, award every layer to its sole eligible live winner, compute final stacks, and return exact utilities relative to starting stacks.

**Independent verification:**

- `refund_uncalled_excess` (game_structure.py:200–213) finds the unique highest contribution, computes `excess = highest - second`, refunds it to the leader, and returns matched contributions.
- The refund is bounded: `excess = highest - second ≤ highest` because `second ≥ 0`.
- After refund, `build_pot_layers` (game_structure.py:216–234) constructs layers from matched contributions with folded eligibility.
- For fold-out (one live seat), each layer awards to the sole eligible winner.
- Final stacks = `remaining + refunds + awards`.
- Utilities = `final_stacks - starting_stacks`.

**Refund boundedness proof (ante attack):**

The architecture claims:

> The all-seats-equal ante contract guarantees that every seat's total contribution is the same dead ante plus its live street commitment, so a unique leader's total-contribution excess equals its street-commitment excess and is bounded by that street commitment.

Independent calculation:

- Let `a` = uniform ante (all seats), `s[i]` = seat i's street commitment.
- Then `total[i] = a + s[i]`.
- Highest total: `H = a + s_max`.
- Second-highest total: `S = a + s_second` where `s_second` is the second-highest street commitment.
- Refund: `R = H - S = (a + s_max) - (a + s_second) = s_max - s_second`.
- Since `s_second ≥ 0`, we have `R ≤ s_max`.
- After refund, leader's street commitment becomes `s_max - R = s_max - (s_max - s_second) = s_second ≥ 0`.

**Conclusion:** Refund is bounded by street commitment; negative street commitment is impossible under the uniform-ante contract. ✓

**Partial/unequal/BB-only antes:** The architecture explicitly rejects these (§2.4, §3, §8):

> Unequal/per-seat-partial antes and a single-seat big-blind-ante representation are outside this ledger contract and fail validation.

Config validation (§2.4) enforces:

> Antes are either absent or exactly one identical positive ante is posted by every seat.

This is the "all-seats-equal ante contract." ✓

---

### 1.2 Uncalled refund in nplayer_postflop.py

Source inspection (nplayer_postflop.py:589–597):

```python
matched, refunds = refund_uncalled_excess(total_contributed)
remaining = tuple(
    current_remaining[seat] + refunds[seat] for seat in range(n)
)
street_committed = tuple(
    current_street[seat] - refunds[seat] for seat in range(n)
)
if any(value < 0 for value in street_committed):
    raise ValueError("uncalled refund exceeds street contribution")
```

This matches the architecture's refund protocol and enforces the non-negativity invariant. ✓

---

## 2. Settlement: side-pot layers, ties, odd chips

### 2.1 Side-pot layer construction (§8, game_structure.py)

`build_pot_layers` (game_structure.py:216–234):

- Sorts unique positive contribution levels.
- For each level, contributors are seats with `contribution ≥ level`.
- Layer amount = `(level - previous_level) * len(contributors)`.
- Eligible winners = `contributors - folded`.
- Layers are built bottom-up from matched contributions.

**Independent integer example (3 players, one folded):**

- Matched contributions: `(100, 50, 100)`.
- Folded: seat 1.
- Levels: `[50, 100]`.
- Layer 0: level 50, contributors {0,1,2}, amount = 50*3 = 150, eligible {0,2}.
- Layer 1: level 100, contributors {0,2}, amount = (100-50)*2 = 100, eligible {0,2}.
- Total pot: 150 + 100 = 250 = sum(matched). ✓

---

### 2.2 Tie handling and odd-chip assignment (§2.3, game_structure.py)

`award_pot_layers` (game_structure.py:277–311):

- For each layer, winners are a non-empty subset of eligible seats.
- **S3 no-rake constraint:** The architecture (§8) states "The S3 path has no house-rake field." S3 settlement uses `rake = 0` exactly.
- Post-rake layer amount is divided: `quotient, remainder = divmod(layer.amount - rake, len(winners))`.
- Every winner receives `quotient`.
- The first `remainder` winners in `odd_chip_order` receive +1.

**Independent integer example (tie, 3-way split with remainder):**

- Layer amount: 100, rake: 0, winners: {0, 2, 5}.
- `odd_chip_order`: (5, 0, 2, ...).
- `quotient = 100 // 3 = 33`, `remainder = 100 % 3 = 1`.
- Ordered winners in odd_chip_order: [5, 0, 2].
- Awards: seat 5 gets 33+1=34, seat 0 gets 33, seat 2 gets 33.
- Total: 34+33+33 = 100. ✓

The architecture (§2.3) specifies:

> `odd_chip_order: tuple[int, ...]` for `showdown-ranks`, exactly a seat permutation.

Config validation (NPlayerPostflopConfig.__post_init__, nplayer_postflop.py:184–188) enforces this:

```python
if (
    not isinstance(self.odd_chip_order, tuple)
    or len(self.odd_chip_order) != n
    or set(self.odd_chip_order) != set(range(n))
):
    raise ValueError("odd_chip_order must be a permutation of all seats")
```

✓

---

## 3. Settlement: terminal-table and showdown-ranks continuations

### 3.1 Terminal-table continuation (§2.3, §8)

Architecture:

> For `terminal-table`, every value is an exact finite N-tuple that sums to zero. Values are complete hand utilities relative to starting stacks; production must not add current contributions a second time. Missing keys fail when their leaf is reached.

Implementation (nplayer_postflop.py:571–658, specifically the `_settle` method):

- For fold-out (len(live) == 1), no terminal-table lookup; awards computed from layers.
- For showdown (len(live) > 1), uses `showdown_ranks` (see §3.2).
- Terminal-table is **not implemented** in the current nplayer_postflop.py.

**Architecture scope (§1):**

> S3 is a finite reference path. ... Closed non-fold leaves use caller-supplied exact continuation values or caller-supplied ranks for a bounded derived showdown continuation.

The architecture describes terminal-table as a continuation kind (§2.3), but the **current S2 postflop implementation** (nplayer_postflop.py) only implements `showdown_ranks`. The architecture is **design-only** (CANDIDATE_MANIFEST.md:7):

> candidate type: design-only; S3 production and tests intentionally absent

Since this is an S3 **preflop** design audit and the S2 postflop implementation is the reference, terminal-table is a **future S3 preflop feature**. The architecture correctly specifies its zero-sum contract and relative-utility semantics. ✓ (design)

---

### 3.2 Showdown-ranks continuation (§2.3, §8)

Architecture:

> For `showdown-ranks`, every compatible deal has one strict integer rank per seat, larger wins. At every non-fold closed leaf, production refunds unmatched excess, builds exact side-pot layers from the current contributions, finds eligible winners per layer, awards ties with `odd_chip_order`, and derives exact zero-sum chip utilities.

Implementation (nplayer_postflop.py:603–647):

```python
if len(live) > 1:
    if private_deal not in self.config.showdown_ranks:
        raise ValueError("missing showdown rank coverage for deal")
    ranks = self.config.showdown_ranks[private_deal]
    winners = []
    for layer in layers:
        best = max(ranks[seat] for seat in layer.eligible)
        winners.append(
            frozenset(
                seat for seat in layer.eligible if ranks[seat] == best
            )
        )
else:
    winners = [frozenset(live) for _ in layers]
```

Then awards are computed via `award_pot_layers` with `odd_chip_order` (line 631–636).

Final utilities (line 644–647):

```python
utilities = tuple(
    final[seat] - self.config.starting_stacks[seat]
    for seat in range(n)
)
```

**Independent verification:**

- Ranks are caller-supplied (config.showdown_ranks).
- For each layer, the highest rank among eligible seats wins.
- Ties (multiple seats with best rank) split the layer via `award_pot_layers`.
- Utilities are relative to starting stacks. ✓

**Rank source:** Architecture (§2.3):

> Ranks are caller-supplied fixture/input data. Production never derives them from cards.

Config validation (nplayer_postflop.py:194–210) enforces:

- `showdown_ranks` is a mapping from `DealN` to `tuple[int, ...]`.
- Each deal has N integer ranks.
- No duplicate deals.

✓

---

## 4. Settlement: exact zero-sum utility (S3 no-rake)

### 4.1 Zero-sum enforcement with S3 no-rake constraint

Architecture (§8):

> Every terminal utility vector is an N-tuple of finite exact rationals summing to zero.

**Critical S3 constraint (§8):**

> The S3 path has no house-rake field.

This means S3 settlement must enforce **`sum(utilities) = 0` exactly**, not `sum(utilities) + rake = 0`.

Implementation (nplayer_postflop.py:639–643):

```python
verify_terminal_conservation(
    self.config.starting_stacks,
    final,
    house_rake=rake,
)
```

`verify_terminal_conservation` (game_structure.py:314–324):

```python
def verify_terminal_conservation(
    initial_stacks: tuple[int, ...], final_stacks: tuple[int, ...], *, house_rake: int
) -> None:
    """Raise unless final player chips plus house rake equal initial chips."""
    ...
    if final + rake != initial:
        raise ValueError("terminal chip conservation failed")
```

Utilities (nplayer_postflop.py:644–647):

```python
utilities = tuple(
    final[seat] - self.config.starting_stacks[seat]
    for seat in range(n)
)
```

**Independent proof for S3 no-rake:**

- `sum(final) + rake = sum(initial)` (enforced).
- `sum(utilities) = sum(final - initial) = sum(final) - sum(initial) = -rake`.
- **For S3, rake = 0 always**, so `sum(utilities) = 0`. ✓

State validation (nplayer_postflop.py:407–408):

```python
if sum(self.terminal_values) + self.house_rake != 0:
    raise ValueError("terminal utility and rake conservation failed")
```

**S3 interpretation:** When `house_rake = 0` (S3 constraint), this enforces `sum(utilities) = 0` exactly. ✓

**Reference helper discussion:** The shared `game_structure.py` helpers support an optional rake parameter for comparison with other ledger systems, but **S3 architecture fixes rake to zero**. Any S3 reference to these helpers must explicitly use `rake=0` or document that the rake parameter is non-authoritative for S3.

---

### 4.2 Integer arithmetic and exact rationals

All chip values are Python `int` (exact). Utilities are `int`. The architecture mentions "exact rationals" (§8), but the implementation uses integer utilities (nplayer_postflop.py:644–647, terminal_values are `int`). This is consistent: integer utilities are exact rationals with denominator 1. ✓

---

## 5. Deal coverage and rank source

### 5.1 Exact deal coverage (§2.3, §6)

Architecture (§2.3):

> For `showdown-ranks`, every compatible deal has one strict integer rank per seat.

Root construction (nplayer_postflop.py:713–727, `create_nplayer_postflop_root`):

```python
deals = enumerate_deals(config)
compatible = {deal for deal, _ in deals}
supplied = set(config.showdown_ranks)
if supplied != compatible:
    missing = compatible - supplied
    extra = supplied - compatible
    raise ValueError(
        f"showdown coverage must exactly match compatible deals "
        f"(missing={len(missing)}, extra={len(extra)})"
    )
```

This enforces **exact coverage**: every compatible deal must have ranks, and no extra deals are allowed. ✓

---

### 5.2 Rank source (§2.3)

Architecture:

> Ranks are caller-supplied fixture/input data. Production never derives them from cards. Permanent tests hand-declare tiny rank vectors and independently compute winners, layers, splits, and odd-chip recipients; no production evaluator is used as the expected-value oracle.

Config validation (nplayer_postflop.py:194–210) accepts `showdown_ranks` as a mapping input. No card evaluation logic exists in nplayer_postflop.py. ✓

---

## 6. Information noninterference

### 6.1 Information key specification (§9)

Architecture:

> An acting player's information key includes only:
> - version/rule identity and N;
> - owner seat and owner's private combo;
> - button, starting stacks, forced posts, straddle variant, and immutable sizing-rule identity;
> - pot, public commitments/contributions/remaining/fold flags;
> - pending order, raise entitlements, last increment, raise count, and acting seat;
> - actor-labelled public history;
> - continuation kind, source, and provenance.
>
> It excludes opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, and traversal state.

Implementation (nplayer_postflop.py:660–687, `information_state_key`):

```python
def information_state_key(self, player: int):
    n = self.config.num_players
    if (
        isinstance(player, bool)
        or not isinstance(player, int)
        or not 0 <= player < n
        or self.private_deal is None
    ):
        raise ValueError("information key requires dealt state and valid player")
    return (
        self.config.version,
        n,
        player,
        self.private_deal[player],
        self.config.board,
        self.config.button,
        self.street_committed,
        self.total_contributed,
        self.remaining,
        self.folded,
        self.pending,
        self.can_raise,
        self.last_raise_increment,
        self.raise_count,
        self.acting_player,
        self.config.wager_targets,
        self.history,
    )
```

**Verification against architecture:**

- ✓ version, N, player (owner seat), owner's private combo.
- ✓ button (via config.button).
- ✗ **starting stacks not included** (only current remaining/contributed).
- ✗ **forced posts not included** (postflop has no forced posts; contributions are initial state).
- ✗ **straddle variant not included** (postflop has no straddles).
- ✗ **sizing-rule identity not included** (postflop uses wager_targets, which IS included).
- ✓ pot (implicitly via total_contributed, since pot = sum(total_contributed)).
- ✓ public commitments/contributions/remaining/fold flags.
- ✓ pending order, raise entitlements, last increment, raise count, acting seat.
- ✓ actor-labelled public history.
- ✗ **continuation kind/source/provenance not included**.

**Analysis:**

The architecture's §9 information key specification is written for **S3 preflop**, not S2 postflop. The current implementation (nplayer_postflop.py) is **S2 postflop**, which has:

- No forced posts (initial contributions are given).
- No straddle variant.
- No sizing rules (uses wager_targets).
- No continuation kind/source/provenance in the key (showdown_ranks are in config, but their identity is not in the key).

The postflop information key is **correct for postflop**: it includes all public state and the owner's private cards, and excludes opponent cards and hidden ranks. ✓ (for postflop)

The architecture's §9 specification is a **preflop design requirement**, not a postflop audit target. Since this audit is for the S3 **preflop design** (CANDIDATE_MANIFEST.md), and the design correctly specifies the preflop information key, this is ✓ (design).

---

### 6.2 Opponent-card noninterference

Architecture (§9):

> It excludes opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, and traversal state.

Implementation (nplayer_postflop.py:673):

```python
self.private_deal[player],
```

Only the owner's combo is included. Opponent combos (`private_deal[other]` for `other != player`) are excluded. ✓

---

### 6.3 Hidden continuation noninterference

Architecture (§9):

> It excludes ... hidden payoff-table values, hidden showdown ranks.

Implementation: `showdown_ranks` are in `config`, but the **mapping contents** (rank values) are not in the information key. The key includes `config.version`, `config.button`, `config.board`, `config.wager_targets`, but not `config.showdown_ranks`. ✓

(Note: The config object itself is not in the key tuple; only specific config fields are extracted.)

---

### 6.4 Legal action preservation (§9)

Architecture:

> Infosets must also preserve identical legal action tuples.

The information key includes all fields that determine legal actions:

- `acting_player` (who acts).
- `street_committed`, `remaining`, `folded` (stack state).
- `can_raise`, `last_raise_increment`, `raise_count` (raise eligibility).
- `wager_targets` (available sizes).
- `pending` (action order).

Two states with the same information key will have the same legal actions. ✓

---

## 7. Hash verification

**Pre-audit hash:**

```
$ sha256sum ARCHITECTURE_PHASE4_S3.md
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6
```

Matches required SHA-256 in CANDIDATE_MANIFEST.md. ✓

**Post-audit hash:**

```
$ sha256sum ARCHITECTURE_PHASE4_S3.md
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6
```

Unchanged. ✓

---

## 8. Verdict

**PASS** — zero blockers.

### 8.1 Settlement

- ✓ Fold awards: exact layer construction, sole eligible winner per layer.
- ✓ Uncalled refunds: bounded by street commitment under uniform-ante contract; negative street commitment impossible.
- ✓ Ante contract: all-seats-equal enforced; partial/unequal/BB-only rejected.
- ✓ Side-pot layers: exact integer construction from matched contributions.
- ✓ Ties and odd chips: `odd_chip_order` permutation enforced, remainder distributed deterministically.
- ✓ Terminal-table continuation: design specifies zero-sum and relative-utility semantics (implementation deferred to S3 preflop).
- ✓ Showdown-ranks continuation: caller-supplied ranks, per-layer winner selection, exact awards.
- ✓ **Exact zero-sum utility with S3 no-rake:** `sum(utilities) = 0` enforced at every S3 terminal (rake fixed to zero).
- ✓ Deal coverage: exact match between compatible deals and supplied ranks enforced at root construction.
- ✓ Rank source: caller-supplied, no card evaluation in production.

### 8.2 Information

- ✓ Opponent-card noninterference: only owner's combo in key.
- ✓ Hidden continuation noninterference: rank values excluded from key.
- ✓ Legal action preservation: all action-determining fields in key.
- ✓ Preflop information key design (§9): correctly specifies all required fields for S3 preflop.

### 8.3 Independent calculations

- ✓ Refund boundedness: `R = s_max - s_second ≤ s_max` (ante attack proof).
- ✓ Side-pot layer example: 3-player fold-out, 250 total pot, two layers.
- ✓ Odd-chip example: 3-way tie, 100 chips, remainder 1, distributed per `odd_chip_order`.
- ✓ **S3 no-rake zero-sum proof:** `sum(final) + rake = sum(initial)` with `rake = 0` ⇒ `sum(utilities) = 0`.

### 8.4 Architecture integrity

- ✓ Pre-audit SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`.
- ✓ Post-audit SHA-256: unchanged.
- ✓ Design-only candidate: no implementation contradictions (S2 postflop is reference, S3 preflop is design).
- ✓ **S3 no-rake constraint:** Architecture §8 explicitly states "The S3 path has no house-rake field"; all S3 terminals enforce `sum(utilities) = 0` exactly.

---

**Signed:** A3L4, 2026-09-16 (corrective substance audit after A3K4 ownership ended)
