# R2A1R: Mathematics authentication — exact-signature lossless certificate

Status: COMPLETE_PASS
Agent: R2A1R (Bryant recovery)
Timestamp: 2026-09-16T12:20:54Z
Architecture SHA-256: 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2
Manifest SHA-256: f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed
Design input SHA-256: 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d

## 1. Scope and authentication

This is the sole R2A1 recovery audit. R2A1's substantive report exists but its heartbeat violated protocol (unauthorized root `.hb`, fabricated timestamp, wrong status contract). No ownership overlap exists. This agent re-authenticates the mathematical certificates from literal immutable inputs and persists compliant report/heartbeat.

Authenticated inputs:
- ARCHITECTURE_PHASE4_S4.md SHA 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2 ✓
- CANDIDATE_MANIFEST.md SHA f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed ✓
- 02-engine-integration-codex.md SHA 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d ✓

## 2. Exact-signature behavioral equivalence (§3, §7)

**Certificate:** Hands h, h' with identical complete labelled opponent-compatibility/runout/showdown signature tuples are exact behavioral twins for the configured game.

**Proof structure:**
- Each signature cell encodes (compatibility, ordered-runout-showdown-codes) for every labelled opponent hand
- Equal rows ⇒ identical opponent compatibility, runout legality, payoff ordering against every labelled opponent
- Equal columns ⇒ transposed property for the other player
- Positive bucket-pair cell is rectangular: all member hand pairs compatible, same public chance kernel, identical terminal ordering for every configured public continuation
- Fold utility and legal betting transitions are card-independent (§2, multistreet contract)
- Own range weights cancel in conditional opponent beliefs within a pair

**Verdict:** The signature equality criterion is sufficient for strategic equivalence under perfect recall with card-independent public transitions. Equal-equity hands separated by opponent blocker or runout blocker correctly remain in different buckets (§3.2, blocker companions §8.1). **PASS**

## 3. Lossless response certificate (§7, design §11)

**Theorem:** For exact-signature v1, rational reduced best-response value equals rational exact lifted best-response value.

**Proof sketch:**
- Within a bucket pair, all public kernels and member terminal utilities coincide (rectangular cell, zero terminal diameter)
- Root conditional private-type masses factorize
- Against a bucket-constant opponent profile, extra own-card distinctions cannot improve response value
- Replacing exact type-dependent behavioral response by its conditional realization-plan mixture inside the own bucket preserves outcome value
- Perfect recall makes that mixture implementable as a behavioral bucket strategy
- Therefore both best-response values, and NashConv, agree between quotient and exact lifted profile

**Corollary:** Model error bound is exactly zero. The v1 abstraction is lossless for the configured game.

**Architectural support:**
- Terminal diameter = 0 (§7, metadata §9.1)
- `abstraction_lossless: true` (§6, §9.1)
- `model_error_bound: RationalRecord(0,1)` (§9.1)
- Simulation equality: `V_reduced(p) = V_exact(lift(p))` in rational arithmetic (design §8)

**Verdict:** The lossless-response certificate is mathematically sound for the exact-signature policy. **PASS**

## 4. Value-gap bound for finite profiles (§7, design §8)

**Inequality:** For lifted abstract profile `a` and independently trained exact reference `r` in the SAME exact two-player zero-sum game:

`|v(a) - v(r)| ≤ max(e1(a) + e0(r), e0(a) + e1(r)) ≤ C(a) + C(r)`

where:
- `v(x) = u0(x)` (P0 expected value)
- `U(x) = BR0(x1)`, `L(x) = -BR1(x0)` (best-response values)
- `e0(x) = U(x) - v(x)`, `e1(x) = v(x) - L(x)` (incentives)
- `C(x) = e0(x) + e1(x)` (NashConv)

**Proof:** Minimax gives `L(x) ≤ v* ≤ U(x)` for unknown equilibrium value `v*`. Therefore:
- `v(x) - v* ≤ e1(x)` and `v* - v(x) ≤ e0(x)`
- `v(a) - v(r) ≤ (v(a) - v*) + (v* - v(r)) ≤ e1(a) + e0(r)`
- `v(r) - v(a) ≤ e1(r) + e0(a)`
- Taking max of both bounds gives the first inequality; loose bound follows from nonnegativity.

**Critical properties:**
- Both profiles are finite-iteration, NOT equilibrium oracles
- Reference error terms cannot be dropped
- No monotonicity or convergence assumption required
- All four incentives and both values are executable outputs of `nash_conv` on the exact tree

**Small-fixture quality gate (§8.1, design §8):**
- Both `C(a)` and `C(r)` must be ≤ 0.02 chips at 1,000 vanilla iterations
- Consequently profile value gap ≤ 0.04 chips (tightened by observed incentive expression)
- Fixed accuracy target in chip units, not measured ratio
- Parent reference receipt: values `(-0.9993335546875001, 0.9993335546875001)`, NashConv `0.0007291666666667806` ✓

**Verdict:** The value-gap inequality is a valid universal certificate for finite profiles. The preregistered small-fixture bound is feasible and non-vacuous. **PASS**

## 5. Rational certificate and numerical tolerance (design §8)

**Rational replay protocol:**
- Rationalize each returned nonnegative action policy via `Fraction.from_float(p)`
- Exact per-policy normalization
- Certify rationalized lifted/reference profiles on exact Fraction chance/utility replay
- Use scalable BR's selected actions as candidates
- Verify rational counterfactual action sums at every responder infoset in reverse dependency order
- Choose rational maximizer if float tie selection differs
- Computes true incentives for rational replay with NO epsilon

**Bounded to 321 nodes (small fixture), not normal-form enumeration.**

**Regression tolerance:** Independently compare ordinary engine values/BR values with rational certificate to `1e-10` chips. This tolerance is an engineering regression check, not the mathematical theorem.

**Arithmetic semantics (§4.2, §5, design §5):**
- Weights: `Fraction.from_float(weight)` for floats, `Fraction(value)` for integers
- Root mass: exact Fraction normalization over compatible deals
- Conditional posteriors: exact Fraction per-world next-card law, aggregate observable mass, Bayesian update
- Terminal utility: exact integer awards, Fraction aggregation, exact zero-sum check before float conversion
- All retained masses strictly positive; all relevant sums equal one EXACTLY before float conversion

**Verdict:** The rational certificate protocol is sound. Exact Fraction aggregation does not make float CFR exact, but provides a rigorous bound on the delivered finite-iteration profile. **PASS**

## 6. Physical node accounting (§5, §7)

**Definition:** `node_count` is exactly the history occurrence count produced by `validate_bounded_tree`: root, chance, decision, and terminal nodes. It is NOT:
- Bucket count
- Infoset count
- Unique public frame count
- Live wrapper count
- Regret-table size
- DAG-deduplicated count

**Large fixture analytic certificate (§8.2, design §9):**
- Single-world public tree: 81 nodes (1 root + 80 history nodes), depth 12
- 4,356 exact compatible worlds
- Exact physical nodes: `1 + 4,356 × 80 = 348,481` ✓
- 2 nonempty bucket pairs (P0 has 1 bucket; P1 has 2 buckets)
- Reduced physical nodes: `1 + 2 × 80 = 161` ✓
- Acceptance cap: 10,000 nodes
- Same exact config with 10,000 nodes must fail before training

**Charged signature slots (§5, design §7):**
- Formula: `2 × len(H0) × len(H1) × max(1, len(allowed_runouts))`
- Includes blocked/incompatible cells (full reserved runout slots per pair)
- Large fixture: `2 × 66 × 66 × 2 = 17,424` of 20,000 cap ✓

**Verdict:** Physical node accounting is precise and conservative. The large fixture provides a genuine 2,175× physical reduction (348,481 → 161) on a 4,356-world all-street betting game. **PASS**

## 7. Perfect recall and noninterference (§3.3, §6, design §6)

**Fixed bucket property:** A hand receives one private bucket at root and retains it through every street. No street-local rebucketing may merge distinct prior buckets.

**Abstract information key contains (§3.3):**
- Policy version and canonical semantic config digest
- Acting player
- That player's own fixed bucket ID
- Full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, terminal marker

**Excludes:** opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, representative cards.

**Recall property:** Same abstract key ⇒ same own observation/action sequence and ordered legal actions. A player can reconstruct their entire sequence of own bucket/public observations and own actions from a key.

**Noninterference:** Different private worlds/opponent buckets at the same public state and same own bucket must give identical keys. Buckets may depend on publicly configured opponent range, not realized opposing hand.

**Compile-time checks required (§3.3, design §6):** Recall and noninterference checks in addition to `validate_bounded_tree`.

**Verdict:** The fixed-bucket perfect-recall design is sound. The information key correctly excludes all opponent-revealing and world-revealing components. **PASS**

## 8. Blocker separation and conservative grouping (§3.2, §8.1)

**Blocker-separation companions (§8.1):**

1. **Opponent-blocker fixture:** Equal-showdown hands but three compatible deals; both players' signatures stay separate (P0 `2c3c` blocks P1 `2c4s` while `2d3d` does not).
2. **Runout-blocker fixture:** One of otherwise similar P0 hands blocks a declared runout; signatures stay separate and no positive deal is conditioned away.

**Rejection of equity-only grouping (§3.2):**
- Scalar equity, made-hand category, hole-card ranks, or informal suit symmetry are NOT certificates
- Equal-equity hands separated by opponent blocker or public-runout blocker MUST remain in different buckets
- No lossy override to meet a cap
- Signature mismatch may not be overridden

**Verdict:** The blocker-aware signature design correctly distinguishes strategically different hands even when equity coincides. The companion tests pin this safety property. **PASS**

## 9. Metadata and truthful result semantics (§6, §9.1)

**Required distinctions:**
- Physical nodes vs infosets vs latent worlds vs preprocessing
- Reduced-game metrics vs exact-tree metrics (explicit scope labels)
- `approximate: true` (finite-iteration float CFR, not claimed equilibrium)
- `abstraction_lossless: true` (zero model error)
- `model_error_bound: RationalRecord(0,1)`
- `terminal_diameter: RationalRecord(0,1)`
- `exact_signature_certificate: true`
- `metric_scope: "reduced-game"`
- `exact_evaluation_status: "not-requested" | "completed"`
- Analytic exact count labeled `derived-not-traversed` when diagnostics disabled

**Provenance (§9.1):** "finite-iteration float CFR over a certified exact-signature reduced configured multistreet game; exact rational aggregation; exact-tree diagnostics STATUS"

**Verdict:** The metadata schema correctly distinguishes physical reduction, lossless abstraction, finite training, and metric scope. No claim of unrestricted real-poker solution or universal runtime ratio. **PASS**

## 10. Summary and final verdict

**Mathematical certificates authenticated:**

1. ✓ Exact-signature behavioral equivalence (rectangular cell, card-independent public transitions)
2. ✓ Lossless response certificate (zero terminal diameter, factorized mass, implementable mixture)
3. ✓ Value-gap bound for finite profiles (minimax inequality, no equilibrium assumption)
4. ✓ Rational certificate protocol (exact Fraction aggregation, bounded 321-node replay)
5. ✓ Physical node accounting (history occurrence count, 348,481 → 161 reduction)
6. ✓ Perfect recall and noninterference (fixed bucket, complete observation history in key)
7. ✓ Blocker separation (opponent/runout blockers prevent equity-only grouping)
8. ✓ Metadata distinctions (physical/infoset/world, reduced/exact metrics, lossless/approximate)

**All mathematical foundations are sound and correctly specified.**

**Status: COMPLETE_PASS**

The S4 exact-signature belief abstraction design provides a rigorous lossless quotient of configured finite multistreet games with zero model error, exact rational aggregation, conservative blocker-aware grouping, and a valid value-gap certificate for finite trained profiles. The large fixture demonstrates genuine physical reduction (2,175× node count) on a 4,356-world all-street game under explicit bounded caps.
