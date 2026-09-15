# Bet sizing modes and units

## Evidence status

The restricted-tool BryantGPT researcher fetched sources but failed to write its artifact and returned only a summary. The parent independently fetched the cited GTO Wizard help/blog pages and rejected unsupported details from the summary: there is no documented 5–10% deduplication threshold, no documented 95–99% automatic all-in threshold, no basis for a universal `min 2x`, and the reported “99.95% EV capture” is a dated aggregate benchmark rather than the semantics of Dynamic mode.

## Verified GTO Wizard semantics

- **Fixed:** the user specifies exactly which bet/raise sizes are allowed; the tree is not simplified.
- **Dynamic:** the user chooses how many bet/raise sizes to retain and may provide the candidate list; the system searches for high-EV size subsets at each decision point.
- **Automatic:** the system chooses both the number of sizes and a candidate list adjusted using stack-to-pot ratio, then simplifies to high-EV sizes.
- The supported product input forms are pot percentage (`%`), geometric (`e`), multiple of the previous bet (`x`), and, in the current preflop builder documentation, big blinds (`bb`).
- Dynamic Sizing 2.0 is described as solving small depth-limited trees for action subsets and comparing their EV with the all-actions tree. The underlying production procedure is proprietary and is not reproduced here.

Verified product sources:

1. GTO Wizard Custom Solving FAQ: https://help.gtowizard.com/custom-solving-faq/
2. GTO Wizard, “How To Build Custom Solutions”: https://help.gtowizard.com/how-to-build-custom-solutions/
3. GTO Wizard, “Dynamic Sizing: A GTO Breakthrough”: https://blog.gtowizard.com/dynamic-sizing-a-gto-breakthrough/
4. GTO Wizard, “Introducing Dynamic Sizing 2.0”: https://blog.gtowizard.com/introducing_dynamic_sizing_2/
5. GTO Wizard, “Dynamic Sizing Benchmarks”: https://blog.gtowizard.com/dynamic-sizing-benchmarks/
6. GTO Wizard, “How to Calculate Raises in Poker”: https://blog.gtowizard.com/how-to-calculate-raises-in-poker/
7. GTO Wizard, “Pot Geometry”: https://blog.gtowizard.com/pot-geometry/

Source 6 gives `X% pot raise-to = previous bet + X% * (street-starting pot + 2 * previous bet)` for the simple heads-up, previously-uncommitted case. Source 7 defines geometric sizing as using the same fraction of the pot at each remaining betting opportunity so stacks are committed by the last one.

## Bounded project contract

All Phase 3 sizing is exact relative to a declared finite candidate set and game tree. “Best EV” means the value of a fully re-solved bounded game, not a local hand-strength heuristic and not parity with GTO Wizard's proprietary model.

### Strict size expression

A size is a JSON object, not a permissive string:

- `{"unit":"pot-percent","value":75}`
- `{"unit":"geometric","streets":2,"scale":1}`
- `{"unit":"previous-bet-multiple","value":3}`
- `{"unit":"big-blinds","value":2.5}`
- `{"unit":"all-in"}`

Fields are exact per variant. Unknown fields, booleans, non-finite values, nonpositive scales/multipliers, zero streets, and unsupported context fail. Decimal JSON numbers are parsed through their decimal text representation, not binary-float arithmetic.

Converted `Action.amount` is the actor's integer **raise-to commitment for the current street**, matching `multistreet.py`.

### Rounding

The project uses decimal round-half-up to the nearest chip after the complete formula is evaluated. It does not round intermediate pot fractions. The unrounded amount and rounding rule are metadata when a user-facing Phase 3 endpoint explains a conversion.

After conversion:

1. clamp is forbidden;
2. an amount above stack is illegal unless the expression was `all-in`, which converts exactly to the actor's maximum raise-to;
3. an amount below the minimum legal full raise is illegal unless it is the actor's exact short all-in and the poker state permits it;
4. equal integer targets produced by distinct expressions are deduplicated by target, retaining the first expression in input order as provenance;
5. no “near all-in” threshold rewrites a legal target to all-in.

## Unit formulas

Let:

- `P` be the pot immediately before the action, including all current-street commitments;
- `h` be the highest current-street commitment;
- `c = h - own` be the actor's call amount;
- `P_call = P + c` be the pot after the actor hypothetically calls;
- `own_call = own + c`;
- `R` be chips remaining after that call;
- `BB` be the big-blind chip value.

### Pot percentage

For fraction `q = value / 100`:

- when not facing a wager (`c = 0`), target is `own + q * P`;
- when facing a wager, target is `own_call + q * P_call`.

The second formula means “call, then raise by q of the pot after calling.” In the simple heads-up case with street-starting pot `P0`, a bet `B`, and no prior actor commitment, the pot before response is `P0+B`; a pot-size raise gives `B + (P0+2B) = P0+3B`, agreeing with source 6.

### Previous-bet multiple

For multiplier `m`, the bounded project defines target as `m * h`, rounded once. This common raise-to convention is simple and deterministic for preflop opens and one prior postflop bet. It is an explicit project convention because the product documentation says only “multiple of the previous bet” and does not fully specify every multi-raise commitment context. The resolved target must still satisfy call, minimum-raise, pot-limit, and stack rules.

### Big blinds

Target is `value * BB`, rounded once. It is a current-street raise-to amount, not additional chips. This makes `2.5bb` a preflop open to 2.5 big blinds. A postflop use is allowed only where the schema permits it and has the same raise-to meaning.

### Geometric

At an unopened betting node with equal effective remaining stack `S`, current pot `P > 0`, and `n` intended equal-fraction bet/call opportunities including the current bet, the geometric fraction is:

`g = ((1 + 2*S/P) ** (1/n) - 1) / 2`.

Proof: after each bet and call the pot is multiplied by `1+2g`. One player's total contribution after `n` opportunities is `P/2 * ((1+2g)^n - 1)`, which equals `S` by construction.

`scale` multiplies `g` before conversion; the ordinary geometric size has `scale = 1`. At a facing-wager node, compute geometry after the hypothetical call using `P_call`, the effective matched stack remaining after the call, and the explicitly supplied number of opportunities. If stack asymmetry makes the requested equal-bet construction impossible, reject it rather than silently substituting all-in.

The project never infers `n` from prose. API callers provide `streets`; preset builders may derive it deterministically from starting street and record the resolved number.

## Sizing modes

### Fixed

Input: ordered size expressions at a declared node or node pattern. Convert, validate, and deduplicate. Every surviving legal target becomes an action. Fixed never removes a target based on EV.

Acceptance oracle: the output action tuple equals the hand-converted legal targets exactly, in canonical increasing-target order after fold/check/call base actions.

### Dynamic

Input: an ordered finite candidate list, exact retained count `N`, selecting player, solver algorithm/budget, and deterministic tie tolerance.

For the bounded reference algorithm:

1. enumerate every size subset of cardinality `N`;
2. materialize and solve a fresh edited tree for each subset using the same algorithm/budget;
3. measure the selecting player's root EV under the solved profile;
4. choose maximum EV; values within `tie_tolerance` tie, resolved by lexicographically increasing integer targets;
5. return every candidate subset and measured EV as evidence.

This exhaustive algorithm is exponential in candidate count and therefore accepts at most a small architecture-defined limit. It is exact with respect to the enumerated subsets and measured finite-iteration solver outputs. It does not claim that “the top N sizes individually” equals the best joint subset; interactions require subset evaluation.

### Automatic

GTO Wizard's automatic candidate generation and size-count rule are proprietary. The bounded project uses a transparent substitute:

1. generate a documented finite candidate grid from the current pot, stack, legal bounds, and allowed units;
2. solve the all-candidate tree to obtain reference EV `V_full`;
3. exhaustively evaluate subsets from size 1 through `max_sizes`;
4. choose the smallest-cardinality subset whose selecting-player EV is within caller-declared `ev_tolerance` of `V_full`;
5. among equal-cardinality qualifying subsets, maximize EV and use the Dynamic lexicographic tie-break.

If no subset qualifies, use the best `max_sizes` subset and report the measured EV gap. This is an explainable bounded Automatic mode, not GTO Wizard algorithm parity. Without an EV tolerance or complexity objective, “automatically choose N” is under-specified and adding actions generally makes a player's action set no worse in the exact zero-sum game.

## Accuracy oracles and tests

1. **Formula fixtures:** hand-calculate `%`, `x`, `bb`, and `e` targets using decimal arithmetic. Assert integer targets exactly.
2. **Raise identity:** street-starting pot 100, opponent bet 50, actor committed 0: a 100% pot raise-to is 250. This follows both the general project formula and source 6's `3B+P0` identity.
3. **Geometric conservation:** for several integer-friendly `P,S,n` fixtures, simulate all bet/call rounds and assert final remaining stack and pot against the formula. For irrational targets, test the unrounded Decimal value separately and the declared one-time rounding exactly.
4. **Legality boundaries:** exact min raise accepted, one chip below rejected unless exact short all-in, exact stack target accepted, one chip above rejected, pot-limit cap enforced by the game state.
5. **Deduplication:** distinct expressions resolving to the same integer target produce one action; targets one chip apart remain distinct.
6. **Fixed invariant:** no legal configured target is pruned.
7. **Dynamic oracle:** on a tiny game with at most five candidates, compare selected subset and EV to an independent brute-force enumerator; tolerance `1e-12` for exact expected-value games and a fixture-specific predeclared tolerance for iterative CFR.
8. **Cross-mode identities:** Dynamic with `N == candidate_count` equals Fixed on the same candidates; Automatic with `max_sizes == candidate_count` and zero EV tolerance may choose a smaller exactly equivalent subset but must match full-tree EV within the declared solver tolerance.
9. **Order/determinism:** candidate input permutation cannot change selected integer targets, measured EVs, or canonical JSON.
10. **API rejection:** malformed units, booleans, NaN/infinity, unsupported geometric context, impossible retained counts, and combinatorial limits fail with status 2.

## Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| `%`, `e`, `x`, and `bb` conversion | Implement with formulas and explicit rounding above |
| Fixed sizing | Implement fully for bounded trees |
| Dynamic sizing | Implement exhaustive best-subset selection for small candidate sets |
| Automatic sizing | Implement transparent EV-tolerance subset selection over a documented generated grid |
| GTO Wizard proprietary ML sizing selection | Documented boundary |
| Continuous bet-size optimization | Documented boundary |
| Magic near-size merging or all-in thresholds | Not implemented |
| Large candidate sets | Reject at a tested limit |

Every implementation batch for this module requires a fresh non-author review under `review/phase3/` before another feature batch begins.
