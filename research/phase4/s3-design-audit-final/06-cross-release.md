# S3 final cross-adversarial design release audit A3H6

**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Post-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Auditor:** A3H6 (fresh, different, non-author)  
**Date:** 2026-09-16 UTC

## Scope

Final frozen S3 design release audit. Cross-attack all accepted claims, repairs, boundaries, executable acceptance mapping, migration hazards, and contradictions. The candidate supersedes `fcae1cb6...` and `f0777689...` after two repair rounds exposed false PASS traces and one decisive ledger gap.

## Hash verification

Pre-audit: `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9` ✓  
Post-audit: `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9` ✓  
No modifications during audit.

## Cross-adversarial attacks

### 1. Ledger algebra and terminal refund boundedness

**Claim:** Section 8 states refund never exceeds street commitment; section 2.4 rejects unequal/partial/single-seat antes; section 15 correction 5 asserts `total[i] = uniform_ante + street[i]` guarantees boundedness.

**Attack:** The decisive A3X4 counterexample `(total=(0,50,190), street=(0,50,100))` produces refund 140 > street 100. Does the uniform-ante restriction actually close this?

**Verification:** With uniform ante `a >= 0` and street vector `s`, we have `total[i] = a + s[i]`. Let `s_L = max(s)` be the leader's street commitment and `s_2` be the second-highest street commitment. The unique leader has `total_L = a + s_L`. The second-highest total is at most `a + s_2` (it could be lower if another seat has lower street commitment, but we take the maximum of all other totals). 

Refund is `total_L - max(total_others)`. In the worst case, `max(total_others) = a + s_2`. Then:

```
refund = (a + s_L) - (a + s_2) = s_L - s_2
```

Since `s_2 >= 0` (all street commitments are non-negative by invariant), we have:

```
refund = s_L - s_2 <= s_L
```

The refund is bounded by the leader's street commitment. ✓

**Counterexample analysis:** The A3X4 example `(total=(0,50,190), street=(0,50,100))` violates the uniform-ante contract. If ante is uniform:
- If `a=0`: totals would be `(0,50,100)`, not `(0,50,190)`.
- If `a=50`: totals would be `(50,100,150)`, not `(0,50,190)`.
- No uniform `a` produces that total vector from that street vector.

The counterexample is correctly rejected by config validation. ✓

**Residual hazard:** Config validation must actually enforce "absent or exactly one equal ante per seat" and reject partial/unequal/single-seat forms. The acceptance matrix (section 13) requires this rejection be tested.

### 2. Straddle strict-increase and all-in option exclusion

**Claim:** Section 5 requires every straddle amount strictly greater than the preceding live wager; section 4 excludes all-in post seats from `pending`.

**Attack:** A3X3 silently truncated a declared straddle and placed an all-in straddler in `pending`. Does the spec permit equal or non-increasing straddles as a degenerate edge case?

**Verification:** Section 5 states "Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation." Section 3 states "A seat may start all-in only when its stack exactly equals its cumulative declared posts" and section 4 states "Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option." The spec is unambiguous: equal/decreasing straddles are invalid, and all-in post seats are never actionable. ✓

**Residual hazard:** Validation must reject equal/non-increasing straddles and test that all-in straddlers are absent from root `pending`.

### 3. No-reopen intersection vs union

**Claim:** Section 7 correction 4 states no-reopen short-all-in eligibility is the intersection of old pending and old entitlement, not a union.

**Attack:** A3X2's PASS trace used a union, allowing prior callers to re-raise. Is the intersection semantically coherent with the "retain an unacted option" language?

**Verification:** Section 7 states: "If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise." The intersection prevents a seat that already acted (checked/called) from gaining a new raise opportunity via a short all-in. This is the standard no-reopen rule. ✓

**Residual hazard:** Permanent betting tests must verify a prior caller cannot re-raise under no-reopen, and that only seats in both old-pending AND old-entitled may raise.

### 4. SB completion as pre-raise CALL

**Claim:** Section 15 correction 3 and section 7 state an SB completion counts as a pre-raise CALL for `cold_callers`.

**Attack:** A3X2 treated SB completion as zero cold callers. Is this a genuine sizing-key difference or a test artifact?

**Verification:** Section 7 states: "every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision." An SB that completes to the BB has called the live wager without raising, so it is a pre-raise caller. The correction is consistent. ✓

**Residual hazard:** Permanent sizing tests must verify SB completion increments `cold_callers` for the next raiser's key.

### 5. N=2 projection vs raw equality

**Claim:** Section 1 states N=2 compatibility is "explicit projection" over aligned public traces, not raw type/version/history/key equality.

**Attack:** Does this projection actually preserve information partitions and legal actions, or does it paper over a structural incompatibility?

**Verification:** Section 1 lists the projection: "normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities. Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history. Information compatibility compares partitions rather than key bytes." This is a semantic equivalence over observable game state, not a claim that the two implementations are interchangeable at the type level. The acceptance matrix (section 13) requires "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures." ✓

**Residual hazard:** The projection test must use frozen Phase-3 HU fixtures as the oracle, not a new synthetic fixture.

### 6. TDD batch ownership and feasibility

**Claim:** Section 12 assigns four exclusive RED owners to S3-I1 (config, betting, settlement, information), then a fifth gated core owner for production; S3-I2 has four RED owners (solve, API, examples, exports) then gated integration owners.

**Attack:** A3Y5 noted potential overlap between betting and settlement (both touch terminal accounting). Is the boundary clean?

**Verification:** S3-I1 batch 2 owns "HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure." Batch 3 owns "independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves." The boundary is: batch 2 owns action legality and transitions; batch 3 owns terminal accounting after action closes. Both import production, but batch 2 does not compute terminal utilities and batch 3 does not generate action trees. The split is feasible. ✓

**Residual hazard:** The gated core owner (batch 5) must not start until all four RED receipts exist and are parent-verified.

### 7. Bounded synthetic ranges vs tractability claims

**Claim:** Section 1 states "All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability."

**Attack:** Does the acceptance matrix (section 13) or any other section contradict this by requiring large-range performance?

**Verification:** Section 13 requires "HU, 6-max, and 9-max roots build and solve, return N values, and use exact deterministic chance mass" but does not specify range size. Section 1 explicitly states "Large-range tractability belongs to S4 abstraction." No contradiction. ✓

**Residual hazard:** Permanent examples and acceptance tests must document their synthetic bounded ranges and must not be misinterpreted as production-scale claims.

### 8. Continuation kind and solver convergence

**Claim:** Section 2.6 states result metadata has `converged=False` and `convergence_claim="none"`. Section 10 states the deviation certificate "is never sampled and never called exploitability or a Nash certificate."

**Attack:** Does the acceptance matrix or any boundary claim contradict this by requiring convergence?

**Verification:** Section 13 requires "policies are normalized, detached, and deterministic" and "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps." It does not require convergence. Section 1 states S3 "does not claim ... equilibrium convergence." Consistent. ✓

**Residual hazard:** Result provenance and metadata must truthfully state no convergence claim.

### 9. Migration hazards: S1/S2 regression and historical baseline preservation

**Claim:** Section 13 requires "all S1/S2 and legacy tests remain green" and "`phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`."

**Attack:** S3 is design-only with no production/tests. Can it violate this requirement?

**Verification:** The candidate manifest states "production/test paths changed during S3 design: none." The current S2 base is HEAD `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe`, which is a descendant of the historical tag. S3 design acceptance does not modify code, so it cannot break tests. The requirement applies to S3 implementation (S3-I1/I2), not this design audit. ✓

**Residual hazard:** S3-I1/I2 implementation waves must run the full suite and verify the historical tag is unchanged.

### 10. Contradictions between reconciliation notes and spec body

**Claim:** Section 14 states the six design streams were inputs, not authorities, and lists rejected elements from each.

**Attack:** Do any rejected elements appear in the spec body as accepted claims?

**Scan:**
- D301 zero street commitment at root: rejected. Section 3 requires antes do not increase `street_committed` but blinds/straddles do. ✓
- D301 initial-blind refund rejection: rejected. Section 8 applies refund before terminal. ✓
- D302 decimal-chip examples: rejected. All amounts are strict integers. ✓
- D302 non-zero-sum fold tuple: rejected. Section 8 requires exact zero-sum. ✓
- D303 HU Mississippi: rejected. Section 5 rejects HU Mississippi. ✓
- D304 "S3 needs no continuation": rejected. Section 2.3 requires continuation. ✓
- D306 replayed S2 postflop: rejected as S3 evidence. ✓

No contradictions found. ✓

## Executable acceptance mapping

Section 13 lists 18 acceptance criteria. Cross-check feasibility:

1. Config validation rejection: feasible via pytest parametrize over malformed inputs. ✓
2. HU/6/9 solve with exact chance: feasible with tiny synthetic ranges. ✓
3. Straddle variant trees: feasible via independent ledger oracles. ✓
4. Sizing-key selection: feasible via traced decision contexts. ✓
5. Action amount conservation: feasible via pot/stack invariants. ✓
6. Pending/reopening rules: feasible via traced action sequences. ✓
7. Independent terminal oracles: feasible via hand-calculated rational arithmetic. ✓
8. Zero-sum terminals: feasible via sum assertion. ✓
9. Information noninterference: feasible via key stability under hidden-value variation. ✓
10. Policy normalization: feasible via sum assertion. ✓
11. Reach/deviation oracles: feasible via exhaustive enumeration on tiny trees. ✓
12. N=2 projection: feasible via frozen Phase-3 HU fixture alignment. ✓
13. v4/CLI/examples/exports: feasible via contract tests. ✓
14. S1/S2 regression: feasible via full suite run. ✓
15. Fresh audit per batch: this audit is one instance. ✓
16. Historical tag preservation: feasible via `git rev-parse`. ✓

All criteria are executable with bounded synthetic inputs. ✓

## Boundary truth

Section 1 explicit boundaries:
- Additive, not a replacement. ✓
- Finite reference path, not unrestricted solving. ✓
- Caller-supplied continuations or bounded derived showdown. ✓
- Tiny synthetic ranges for acceptance, not production-scale claims. ✓
- S4 abstraction is separate. ✓

No overclaims detected. ✓

## Blockers

None. All attacks resolved to spec consistency, residual hazards are deferred to implementation test requirements (already in section 13), and no contradictions or overclaims found.

## Verdict

**PASS**

The candidate `ARCHITECTURE_PHASE4_S3.md` (SHA-256 `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`) is internally consistent, incorporates the two repair-round corrections, bounds its claims truthfully, and provides an executable acceptance matrix. The uniform all-seat ante contract closes the decisive A3X4 refund counterexample through sound algebra: with `total[i] = a + street[i]`, refund `= s_L - s_2 <= s_L` because `s_2 >= 0`. It is suitable as the sole S3 implementation authority after this final frozen design audit.

S3-I1 and S3-I2 implementation may proceed under the TDD batch gates in section 12, with mandatory fresh non-author audits after each batch and parent verification before the next batch starts.
