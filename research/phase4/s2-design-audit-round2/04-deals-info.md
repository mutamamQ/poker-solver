# F204 — Deals and information design audit

**Auditor:** F204  
**Frozen hash:** 770a25ab95381da7b38e1e0d2604ad513a202daa8b9a54c79f7b762e990c4eba  
**Scope:** ARCHITECTURE_PHASE4_S2.md §4 (deals), §7 (information)  
**Verdict:** PASS

## §4 Deterministic bounded private deals

**Iterative candidate-product bounding (§4 para 2, §2.1 max_deals):**  
PASS. The spec requires `prod(len(range_i)) <= max_deals` before enumeration and forbids recursive retry-until-compatible enumeration. This bounds work even when all candidates collide. The existing three-player implementation in `multiway.py:365–378` (`_deals`) walks the Cartesian product iteratively in seat/range tuple order with a board-seeded used-card set, prunes collisions immediately, and enforces the bound after enumeration (`len(results) > config.max_deals` raises). The bound check is post-enumeration rather than pre-check, but the iterative walk with immediate pruning satisfies the no-recursive-retry constraint and the final bound enforcement prevents silent truncation. For S2, the spec's pre-check `prod(len(range_i)) <= max_deals` is a stricter real work bound that can be validated before enumeration begins.

**Fraction(str(weight)) conversion and post-float validation (§4 para 1):**  
PASS. `preflop.py:36–58` (`WeightedCombo.__post_init__`) demonstrates the required pattern: line 52 converts `Fraction(self.weight)` (the public float) deterministically, and lines 53–56 validate the result is positive and finite. `multiway.py` line 373 multiplies `first.weight * second.weight * third.weight` where each weight is already a validated `Fraction` from `WeightedCombo`, preserving exact rational arithmetic. Line 195 converts the summed total to float for public probabilities. The spec's requirement for `Fraction(str(weight))` conversion of validated public floats plus required post-conversion validation is feasible and matches the existing pattern.

**Initially-live showdown coverage (§4 para 4, §2.1 showdown_ranks):**  
PASS. The spec requires exact showdown-rank coverage when more than one player can reach showdown, checked at root construction, with missing/duplicate/malformed/extra records failing before solving. `multiway.py:99–108` validates the showdown mapping structure and detaches it into `MappingProxyType`. Line 304–305 enforces coverage at settlement: `if self.private_deal not in self.config.showdown_ranks: raise ValueError("missing showdown rank coverage for deal")`. The check occurs at showdown (when `len(live) > 1`), not at root construction. For S2, moving this validation to root construction (after `_deals` enumeration, before solving) is feasible: enumerate compatible deals, filter to those where `>1` initially-live player exists, and require exact coverage of that set.

## §7 Information and strategy integrity

**Information/rank noninterference (§7 para 1–2):**  
PASS. The spec requires the information key to include all public fields affecting legal actions or settlement, and to exclude opponent private cards, deal index, iterator position, and hidden showdown ranks. `multiway.py:337–352` (`information_state_key`) includes version, owner, owner combo, board, button, all ledgers/fold flags, history, and wager targets. It excludes opponent combos (line 343 includes only `self.private_deal[player]`) and does not include deal index or showdown ranks. `nplayer.py:116–124` enforces owner/action consistency across all infoset occurrences. The existing three-player implementation satisfies the noninterference requirement.

**Detached strategy (§7 para 3):**  
PASS. The spec requires strategies returned by the solve facade to be detached nested mappings with finite nonnegative probabilities summing to one. `nplayer.py:156–167` (`average_strategy`) returns a freshly constructed `dict[Hashable, dict[Action, float]]` with normalized probabilities. The inner dicts are new objects, not references to the solver's internal `strategy_sum`. Repeated deterministic runs produce equal values/diagnostics/serialized strategy because CFR is deterministic and the strategy is computed from accumulated sums.

## §2 Feasibility against existing source

**2-9 player feasibility:**  
PASS. `nplayer.py:36–40` (`_player_count`) validates `2 <= count <= 9`. `collect_nplayer_infosets` (line 52) and `NPlayerCFRSolver.__init__` (line 144) both call `_player_count`, enforcing the 2–9 range. The generic solver already supports N players; S2 adds a typed 2–9-player postflop config and state that implement the `NPlayerGameState` protocol. The existing `multiway.py` three-player implementation demonstrates feasibility for N=3; extending to 2–9 with per-seat tuples of length N and clockwise order logic is a bounded generalization of the existing pattern.

## Summary

All audited design elements are internally consistent, feasible against existing source, and adequately gated by the specified acceptance matrix (§11). No defects found in the frozen specification.
