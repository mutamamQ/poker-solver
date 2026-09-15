# Canonical spot presets and Phase 3 validation catalogue

## Evidence status and rejected draft claims

The tool-enabled and restricted-tool BryantGPT attempts failed before tool execution. A tool-free draft was used only as a checklist. Parent verification rejected its invented application URLs/API endpoint, unproven equilibrium ranges, arbitrary rake and ICM assumptions, unsupported cross-solver tolerances, and claim that Fast/DDLS could be validated as “10x faster and within 5% exploitability.” None of those claims or fixtures is accepted here.

The preset library is an **example-input library**, not a presolved strategy library. Position labels and stack depths make the examples recognizable; all numeric ranges, boards, runout subsets, sizes, and profiles are declared test fixtures rather than attributed to GTO Wizard.

## Verified product-semantics sources

The parent fetched each source below and checked that it supports the adjacent feature claim.

1. Dynamic sizing chooses a requested number of high-EV sizes, optionally from a user candidate list: https://blog.gtowizard.com/dynamic-sizing-a-gto-breakthrough/
2. Dynamic Sizing 2.0 evaluates action subsets in small depth-limited trees and compares their EV; GTO Wizard does not claim absolute optimality for the earlier pruning approach: https://blog.gtowizard.com/introducing_dynamic_sizing_2/
3. Fixed solutions retain configured sizes, while Automatic is described as selecting one highest-EV size in the cited comparison: https://blog.gtowizard.com/do-multiple-sizes-matter/
4. Nodelocking can specify strategies by combo, hand category, or action frequency: https://blog.gtowizard.com/introducing-nodelocking/
5. Custom rake is described as percentage of final pot capped at a maximum and composes with ranges, stack depth, bet sizes, and nodelocking: https://blog.gtowizard.com/customizable-raked-solutions-with-gto-wizard-ai/
6. Three-way postflop product scope includes custom ranges, mixed stacks, arbitrary sizes, rake, nodelocking, side pots, and bunching; the dated article also states then-current limitations: https://blog.gtowizard.com/now_live_3_way_solving_nodelocking_2_0_and_50k_icm_ft_sims/
7. Multiway preflop product scope reaches nine players and lists per-player/total/BB antes, standard/double/Mississippi straddles, custom stacks, raise sizes, limping, rake, locks, and profiles: https://blog.gtowizard.com/introducing-multiway-preflop-solving/
8. Classic solves one street at a time; Fast/DDLS searches a few moves and re-resolves, using more neural approximation: https://blog.gtowizard.com/gto-wizard-ai-custom-multiway-solving/
9. The AI explainer states that learned expected values replace computation of future streets: https://blog.gtowizard.com/gto-wizard-ai-explained/
10. The bounty article distinguishes KO, PKO, and Mystery bounties and explains that future-bounty value is modeled rather than exactly derived from the current hand alone: https://blog.gtowizard.com/bounty-models-explained-solving-knockout-tournaments/
11. The Range Builder article documents the product’s range-training use, but it is not a formal import/export grammar: https://blog.gtowizard.com/how-to-use-range-builder-in-gto-wizard-to-improve-your-game/

Mathematical correctness must come from executable analytical or exhaustive oracles, not from reproducing screenshots or undocumented commercial outputs.

## Preset file contract

Preset files use strict JSON. The Phase 3 API must reject unknown keys, booleans in numeric fields, non-finite numbers, duplicate player IDs, duplicate cards/actions, inconsistent stack and contribution values, and references to missing named ranges. Existing version-1 and version-2 APIs remain unchanged.

A Phase 3 preset has these top-level fields:

- `version`: integer `3`;
- `preset_id`: stable lowercase ASCII identifier;
- `description`: human-readable text, never parsed as rules;
- `kind`: `preflop-heads-up`, `postflop-heads-up`, or `postflop-three-way`;
- `game`: the complete game structure in integer chip units;
- `ranges`: explicit combo weights or references to named ranges shipped in the same file;
- `tree`: sizing mode, candidate sizes, and node edits;
- `rake`: explicit disabled/enabled accounting rule;
- `engine`: explicit bounded engine mode and solver algorithm;
- `provenance`: `origin`, `accuracy_claim`, and `notes` strings.

Amounts use integer chips in the executable game state. Human sizing expressions remain strings until converted by the sizing module. A preset stores both the expression and the deterministic integer target after conversion so fixtures can detect rounding changes.

No preset contains a `gto_wizard_url` or claims copied equilibrium ranges unless a separately licensed, machine-readable source is actually bundled and verified. The Phase 3 canonical examples use `origin: "poker-solver synthetic validation fixture"` and `accuracy_claim: "none; input example only"`.

## Required canonical examples

### 1. `examples/phase3_btn_vs_bb_25bb.json`

A two-player preflop tree with BTN/SB player 0 and BB player 1. Use a 100-chip big blind, 50-chip small blind, zero ante, and equal 2,500-chip starting stacks **before forced contributions**. The root posts 50 and 100, so remaining stacks are 2,450 and 2,400 and the initial pot is 150. BTN acts first preflop. Include a deliberately tiny explicit combo range per player so exhaustive tests remain tractable. Configure Fixed open/raise-to targets and a small maximum raise count. This preset demonstrates positions, blind accounting, range loading, and a finite raise tree; it is not a 25bb equilibrium chart.

### 2. `examples/phase3_sb_vs_bb_15bb.json`

A two-player preflop tree with a 100-chip BB, 50-chip SB, configurable per-player ante of 10 chips, and equal 1,500-chip starting stacks before forced contributions. Both players post the ante; SB posts the additional blind and acts first. Use a tiny synthetic range and include limp, raise, fold, call, and all-in paths within a bounded raise tree. This fixture is chip-EV only. It must not smuggle a three-player payout vector into a heads-up game or claim ICM.

### 3. `examples/phase3_three_way_river.json`

A bounded three-player river fixture with a fixed five-card board, one exact noncolliding combo per player, unequal remaining stacks, a declared pot/contribution ledger, fixed legal wager targets, and rake disabled. It must exercise one fold followed by a two-player showdown and one three-way showdown. An optional sibling fixture enables a percentage-plus-cap rake rule. This is the primary side-pot/payoff-conservation example, not a broad multiway parity claim.

### 4. Named range library example

`examples/phase3_ranges.json` contains at least two synthetic named ranges with explicit two-card combos and weights in `[0,1]`. Import, export, save, and reload must be lossless under canonical ordering. Names are identifiers, not paths.

### 5. Node lock/profile example

`examples/phase3_exploitative.json` references one canonical node ID, provides a complete locked action distribution, and includes one explicit profile constraint set. Labels such as `calling-station` are display names only; the executable payload contains numerical action constraints/incentives.

## Validation catalogue

Unless otherwise noted, deterministic arithmetic and probability comparisons use absolute tolerance `1e-12`. Iterative solver tolerances must be fixture-specific and committed with a named exact/reference strategy; no universal commercial-solver tolerance is asserted.

| # | Mission feature | Independent correctness oracle | Acceptance gate | Boundary |
|---|---|---|---|---|
| 1 | Heads-up preflop | Exhaustive enumeration of all compatible ordered deals in the tiny preset; independent chip ledger and legal-action state machine | Chance mass is 1; no card collisions; blind/ante conservation exact; every raise/call/all-in target matches hand calculation; information keys omit opponent cards | Bounded ranges/tree only, not unrestricted 1,326-combo solving |
| 2 | Fixed/Dynamic/Automatic sizing and `%`/`e`/`x`/`bb` | Pure formula fixtures plus exhaustive subset enumeration on a tiny normal-form decision game | Unit conversion and rounding exact; Fixed preserves legal requested sizes; Dynamic/Automatic selected subset EV equals brute-force best subset under the project’s declared tie-break | Product’s proprietary ML/heuristics are not reproduced |
| 3 | Range editor | Combinatorial expansion: pairs 6 combos, suited 4, offsuit 12; canonical parser/serializer round trip | Duplicate-combo rejection, weights in `[0,1]`, blocker filtering, save/load and text round trip exact | One documented project grammar, not every third-party syntax |
| 4 | Tree/node editing | Clone a tiny tree, apply one edit, exhaustively compare node/action sets and reachable terminals | Stable node ID resolves exactly once; illegal removal fails; only the selected subtree changes | Finite immutable edits only |
| 5 | Nodelocking | Hand-built two-action zero-sum game with an exact locked mixture | Locked policy is preserved exactly; unlocked opponent best response and value equal brute-force enumeration | Complete/partial locks as documented; no claim to proprietary “minimally exploitable locking” |
| 6 | Player profiles | Translate profile constraints to explicit per-node bounds/incentives and compare with direct constraints on a tiny game | Label-free constraints produce the same policy/value as the named profile; infeasible constraints fail | Small declared profile language |
| 7 | Game structure | Independent forced-bet ledger and exhaustive legal-action traces | Stack + committed + awarded chips conserved; action order, limps, cold calls, and configured straddle examples match declared rules | Full-ring scale may be config-only/documented |
| 8 | Rake | For each terminal pot, independently compute `min(floor_or_round(rule.percent * eligible_pot), cap)` using the declared rounding and eligibility rule | Operator rake plus player awards equals pot exactly; disabled rake reproduces chip-EV byte-for-byte; min/max edge cases exact | One explicit percentage/cap/min/no-flop-no-drop model; site-specific schedules not implied |
| 9 | Multiway | Exhaustive tiny three-player terminal allocation including folds, ties, unequal contributions, side pots, and odd-chip policy | Sum of returns plus rake is zero under the declared baseline; symmetric permutations preserve values when odd-chip order is irrelevant | Three-way postflop bounded; nine-way preflop documented/scaffold boundary |
| 10 | ICM and bounties | Recursive exact ICM for 2–5 players compared with independently enumerated finish-order probabilities; tiny KO/PKO cash-transfer ledgers | ICM equities sum to payout pool; equal stacks are symmetric; chip scaling invariant; bounty transfers conserve declared bounty pool | Full strategic tournament solve, future PKO EV, TKO ambiguity, and Mystery distributions are documented boundaries unless explicitly modeled |
| 11 | Classic vs Fast/DDLS | Direct existing full-tree CFR path; checkdown cutoff identity and a counterexample where equity rollout differs from strategic continuation | Classic equals legacy results; unsupported Fast fails closed; heuristic outputs are labeled and do not claim original-game NashConv | Neural DDLS is not implemented |
| 12 | Own/opponent range tables | Independently condition chance reach by private hand and evaluate each action continuation from raw strategy/tree | Per-hand action probabilities sum to 1; weighted hand EVs aggregate to root EV for each player; both player views agree with raw policies | Only reachable explicit combos |
| 13 | Opponent range inference | Manual Bayes fixture, e.g. prior masses `1/4, 3/4` and likelihoods `1, 1/3` yield posterior `1/2, 1/2` | Exact normalized posterior, sequential-update identity, blocker removal, and impossible-evidence failure | Conditional on supplied strategy/profile likelihoods; not mind reading |
| 14 | Prefill and spot library | Strict loader plus direct construction equality | Every shipped example loads, canonicalizes deterministically, audits, and reaches all intended action kinds; provenance disclaims solved output | Small examples, not a presolved library |
| 15 | Accuracy method | Mutation tests against each oracle: alter a sign, denominator, rounding edge, hidden-information key, or action target | Every mutation is caught by at least one focused test; review report names oracle, fixture, expected value, and tolerance | Commercial screenshots are supporting semantics evidence, never sole numeric oracle |

## Product parity matrix for the preset layer

| Item | Status |
|---|---|
| Strict example configuration loading | Implement |
| BTN vs BB 25bb and SB vs BB 15bb examples | Implement as synthetic bounded fixtures |
| Tiny three-way postflop example | Implement |
| Named range and exploitative examples | Implement |
| Embedded equilibrium charts | Not included |
| Authenticated/private GTO Wizard API use | Not included; no verified public endpoint was found |
| Full presolved spot library | Tier 3 documented boundary |
| Numeric parity with proprietary GTO Wizard outputs | Not claimed |

## Review requirements

Every example must be exercised through both the strict programmatic loader and its CLI command. A preset is accepted only after a non-author reviewer runs its focused tests, checks its declared stack/pot arithmetic independently, cross-checks old version-1/version-2 inputs, and writes a sign-off under `review/phase3/`. Example files are executable acceptance fixtures, not documentation decoration.
