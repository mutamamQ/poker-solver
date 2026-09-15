# Heads-up preflop solving: bounded exact contract

## Evidence status and corrections

A restricted-tool BryantGPT worker wrote the first draft. Parent read it in full and rejected unsupported solver-agreement tolerances, invented “known GTO” range percentages, arbitrary fixed raise-depth limits, incorrect geometric sizing, an incorrect all-in pot example that double-counted blinds, and the claim that ordinary non-all-in preflop solving is exact without a postflop continuation model.

## Verified references

1. GTO Wizard's HU preflop release documents customized trees, stack depths, antes, limps, Dynamic sizing, nodelocking, and product support up to 250bb: https://blog.gtowizard.com/introducing-gto-wizard-ai-heads-up-preflop-solver/
2. GTO Wizard's solution-builder documentation defines per-player, total, and BB ante modes; preflop tree controls; blind-relative stacks; limps/cold calls; and size units: https://help.gtowizard.com/how-to-build-custom-solutions/
3. GTO Wizard's multiway preflop release documents broader product structures and explicitly says its engine is a CFR/neural hybrid: https://blog.gtowizard.com/introducing-multiway-preflop-solving/
4. Upswing's rules summary confirms that heads-up BTN posts the small blind and acts first preflop, while BB acts first postflop: https://upswingpoker.com/who-goes-first-in-texas-holdem-poker/
5. GTO Wizard's raise calculation gives the simple heads-up pot-percentage raise formula: https://blog.gtowizard.com/how-to-calculate-raises-in-poker/
6. OpenSpiel provides an independent procedural extensive-form poker implementation suitable for tiny action/chance/payoff cross-checks: https://github.com/google-deepmind/open_spiel
7. CFR correctness for a declared finite two-player zero-sum tree follows Zinkevich et al.: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf

Commercial outputs are feature-semantics evidence, not accepted numeric strategy oracles without identical machine-readable trees/payoff continuations.

## Critical continuation-value boundary

A preflop betting round does not normally end the poker hand. When a limp, raise, or call leaves chips behind, its value depends on all later boards and postflop strategies. GTO Wizard publicly says its preflop engine combines CFR with neural value estimation. This dependency-free project does not have that model.

Phase 3 therefore supports three explicit terminal-continuation modes:

1. `all-in-runout`: after matched all-ins, enumerate declared or complete legal five-card boards and use exact showdown value. This is real Hold'em utility for the bounded explicit ranges/runouts.
2. `table`: for every compatible private deal and preflop-closing public history, the caller supplies a finite zero-sum continuation payoff. Solving is exact for that declared finite game. The table's provenance is mandatory; it is not represented as independently solved Hold'em unless it is.
3. `checkdown-equity`: use exact board enumeration and no-further-betting payoff after a non-all-in close. This is a working approximation, labeled `continuation_model: checkdown-equity`; no unrestricted-game NashConv claim is allowed.

A request with non-all-in closing paths and no continuation mode fails. This is the honest bounded implementation of “preflop solving”; unrestricted postflop continuation parity is a Tier 3/neural boundary.

## Heads-up setup

Seats are fixed as player 0 `BTN_SB` and player 1 `BB`.

- Stacks are integer chips **before** forced postings.
- BTN posts the small blind and BB posts the big blind, each capped by their remaining stack in short-stack boundary cases.
- BTN acts first preflop if able to act.
- If a matched non-all-in preflop round transitions postflop, BB is first postflop; this fact is included in continuation metadata even when later streets are not expanded.
- Deal order has no strategic effect to the chance distribution. Chance identity is canonical ordered `(BTN hand, BB hand)` regardless of physical card-delivery order.

### Ante modes

- `none`: no ante.
- `per-player`: each seat posts the configured amount.
- `total`: configured total ante is spread equally across both seats; the integer amount must be divisible by two in the HU helper. Callers needing an odd/custom allocation use explicit postings.
- `bb-ante`: BB alone posts the configured amount.
- `explicit`: an exact two-item ante-posting vector.

Antes are forced player contributions, not ownerless dead money. Total starting pot equals the exact sum of blind and ante postings. Remaining stack equals starting stack minus that player's postings. Invalid negative amounts and total forced postings above a stack fail; short blind rules, if supported, are explicit rather than silently clipped.

“Effective stack” metadata is the maximum matched contribution still contestable between the two players under the selected baseline; it is derived from each player's starting stack/contribution ledger. It is not used to erase unmatched chips or to double-count posted blinds.

## Private-deal chance

Each player's source range is a finite tuple of explicit weighted combos. Root chance:

1. removes combos colliding with any declared dead/public card;
2. enumerates compatible ordered hand pairs;
3. assigns unnormalized mass `w0*w1`;
4. rejects zero total mass;
5. normalizes once in deterministic combo order.

Chance mass sums to one within `1e-12`. The acting player's information key contains only their own cards, seats, forced contributions, stacks/commitments, public action history, and immutable rules/tree/continuation identity. It excludes opponent cards and unobserved future boards.

## Betting state and legal actions

State includes current commitments, total contributions, remaining stacks, highest commitment, last full-raise increment, actor, whether each player has acted since the last full raise, public history, and terminal/continuation reason.

At the root, the live BB establishes the initial amount to call and the initial full-raise increment. BTN may:

- fold;
- call/limp to the BB (or call all-in if short);
- choose any configured legal raise-to target.

After a limp, BB may check to close preflop or raise. Facing a wager, a player may fold, call up to the lesser of the live target and their total available chips, or make a legal configured raise.

A full raise increases the highest commitment by at least the previous full-raise increment and reopens action. A short all-in may increase the call target but does not reopen raising for a player who already acted unless the cumulative rule is explicitly implemented and tested. Heads-up unmatched excess is returned before payoff/continuation evaluation.

Preflop closes when both live contributions are matched and both players have completed the required response cycle, or when only one player remains. A maximum-raises/tree-node limit is explicit input and audited; there is no universal “five or six actions” rule.

Sizing conversion and Fixed/Dynamic/Automatic selection use the authoritative contract in `research/phase3/bet-sizing.md`; this module cannot redefine geometric or pot-percentage formulas.

## Payoffs

The payoff baseline is each player's wealth before forced postings. For a fold:

`u_i = award_i - total_contribution_i`,

where awards sum to all contributions after any separately configured rake. With no rake, returns sum exactly to zero. Posted blinds/antes are already included in contributions and are never added again as “dead money.”

For a matched all-in, enumerate legal boards, rank both seven-card hands with the existing evaluator, split ties under the declared integer odd-chip policy, and average terminal returns by exact runout probability.

For a table continuation, validate one finite two-value payoff per compatible deal/closing history and require the pair to sum to zero within `1e-12` (or to negative declared rake where composed). For checkdown approximation, payoff uses exact showdowns under the no-further-betting assumption and output metadata forbids an unrestricted-game accuracy label.

## Strict configuration/API

A version-3 preflop request includes exactly:

- `version`, `game: "holdem-preflop-heads-up"`;
- two starting stacks and position IDs;
- blinds and one explicit ante mode;
- two explicit weighted ranges;
- finite tree/sizing specification;
- continuation mode and its required payload;
- solver algorithm, iterations, and seed where applicable;
- structural limits.

Unknown fields, duplicate JSON keys, bool-as-number, noninteger chips, invalid ranges, missing continuation leaves, inconsistent payoff tables, illegal sizes, and oversized deal/tree/runout products fail with status 2. Existing version-1/version-2 APIs remain unchanged.

## Independent acceptance oracles

Integer ledgers/actions compare exactly; probability/value arithmetic uses absolute tolerance `1e-12` unless an iterative fixture declares a measured threshold.

1. **Blind/action order:** with stacks `(2500,2500)`, SB 50, BB 100, no ante, root pot is 150, remaining stacks `(2450,2400)`, commitments `(50,100)`, and BTN acts first.
2. **Ante ledgers:** per-player 10 produces postings `(60,110)` and pot 170; total ante 20 produces the same; BB ante 20 produces `(50,120)` and pot 170. Explicit postings reproduce their exact vector.
3. **Limp/check:** BTN call-to 100 pays 50; BB check closes with total contributions `(100,100)` and pot 200 before continuation. No chip appears twice.
4. **Fold:** BTN folds immediately in the no-ante setup. Awards `(0,150)` and returns `(-50,+50)` under the pre-posting wealth baseline.
5. **Raise increments:** BTN raise-to 300 has increment 200 over BB 100. BB's next full raise target is at least 500. One chip below fails unless it is the exact permitted short all-in.
6. **Unmatched all-in:** starting stacks `(5000,10000)` include forced postings. After both commit, at most 5000 from each is contested; any BB excess is returned. Final no-rake player returns sum exactly zero. The rejected `2*effective_stack + blinds` formula is forbidden.
7. **Chance enumeration:** compare root pair identities/weights with an independent `itertools.product` blocker oracle.
8. **All-in equity:** tiny exact-combo all-in games compare integer win/tie/loss runout counts against the existing Treys fixtures/oracle where applicable, not rounded chart percentages.
9. **Information noninterference:** changing only BB's hidden hand leaves BTN's key/actions unchanged; changing a public raise changes the key.
10. **Continuation completeness:** omit one deal/history table leaf and assert fail-closed; exact table values reproduce a hand-solved tiny normal-form game.
11. **Checkdown identity:** where the supplied table is independently generated by exact checkdown equity, table and checkdown modes agree within `1e-12`.
12. **Approximation disclosure:** checkdown output has `approximation:true`; table output names provenance; all-in-runout is exact for declared runouts. None says GTO Wizard parity.
13. **Solver oracle:** vanilla CFR on a deliberately tiny preflop/table game is compared with exhaustive infoset-consistent best response; the committed fixture sets its convergence threshold from an independently solved game.
14. **Sizing integration:** generated legal actions match the sizing module's targets exactly; Dynamic with all candidates equals Fixed.
15. **Determinism/limits:** input ordering cannot change canonical output; limit and limit+1 cases are tested.

## Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| HU BTN/SB versus BB positions and forced postings | Implement |
| Per-player, total, BB, and explicit antes | Implement with exact chip ledger |
| Limp/fold/call/raise/all-in finite tree | Implement |
| Fixed/Dynamic/Automatic sizing integration | Implement per bounded sizing contract |
| Exact explicit-range all-in runouts | Implement within structural limits |
| Caller-supplied continuation table | Implement; exact for declared finite game |
| Checkdown-equity continuation | Implement and label approximation |
| Full unrestricted postflop continuation | Documented boundary |
| GTO Wizard neural preflop parity | Not claimed |
| Arbitrary 1,326-combo × full-board scale | Reject beyond tested limits |
| Ring-game bunching | Not part of HU model |

Every implementation sub-batch requires a fresh non-author adversarial wave under `review/phase3/` before the next feature batch starts.
