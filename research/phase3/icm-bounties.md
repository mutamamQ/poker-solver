# ICM tournaments and bounties: tractable evaluators and boundaries

## Evidence status

The restricted-tool BryantGPT worker claimed it wrote this file, but parent read-back found no file. Its summary was treated as untrusted. Parent verification rejected a universal “bounty power” conversion, universal 50/50 PKO split, fixed `O(n!)` implementation requirement, unsupported risk-premium example, and claim that full optimal PKO strategy is straightforwardly tractable.

## Verified sources

1. GTO Wizard ICM Basics defines ICM as converting stacks to tournament equity using stack sizes and payouts, with first-place probability equal to stack share, and lists assumptions/limitations: https://blog.gtowizard.com/icm-basics/
2. GTO Wizard on when ICM matters identifies the traditional method as Harville/Malmuth-Harville and notes alternatives and omitted future-game effects: https://blog.gtowizard.com/when-does-icm-become-significant-in-mtts/
3. GTO Wizard's bounty-model article distinguishes KO, PKO, and Mystery formats and explains that its future-bounty EV uses a proportional model plus learned prediction: https://blog.gtowizard.com/bounty-models-explained-solving-knockout-tournaments/
4. GTO Wizard's bounty prize-pool article separates regular placement prizes (ICM-modeled) from bounty value and gives an average-value approximation for Mystery bounties: https://blog.gtowizard.com/the-theory-of-bounty-tournaments-part-1-prize-pool-fundamentals/
5. GTO Wizard's ICM/equity-drop article explains that current and future bounty value interacts with, rather than being identical to, regular-prize ICM: https://blog.gtowizard.com/the-theory-of-bounty-tournaments-part-2-icm-and-equity-drops/
6. PokerStars' format guide uses TKO for Total Knockout, where the buy-in value is allocated to bounties rather than a regular placement prize pool: https://www.pokerstars.com/poker/learn/news/the-complete-guide-to-knock-out-poker/
7. Melcher's tournament-equity thesis is linked by GTO Wizard as an independent comparison of tournament equity models: https://repositum.tuwien.at/handle/20.500.12708/79991

Product articles describe defaults and approximations, not universal tournament rules. Every bounty fraction, prize pool, tie allocation, and Mystery distribution must therefore be explicit input.

## Tiered Phase 3 target

### Implement exactly: standalone ICM equity evaluator

Given positive player stacks and nonincreasing nonnegative placement payouts, compute each player's expected placement prize under the Harville/Malmuth ICM assumptions. This is a utility evaluator, not by itself a poker strategy solver.

### Implement exactly: immediate bounty transition/accounting

Given explicit eliminations, bounty ownership, recipient shares, and a declared KO/PKO/TKO/Mystery rule, compute immediate cash awards and new bounty heads/distribution state. This isolates auditable accounting from speculative future strategy.

### Bounded integration

A tiny terminal poker tree may replace chip-EV terminal utility with:

`post_hand_ICM_equity - pre_hand_ICM_equity + immediate_bounty_cash + explicitly_modeled_mystery_award`.

This is exact for the declared one-hand terminal model and ICM assumptions. Full-field future play, future bounty capture EV, field skill, blind growth, and GTO Wizard's learned continuation model are not included.

### Documented boundaries

- unrestricted postflop/preflop ICM strategy solving;
- full-field optimal PKO/TKO/Mystery strategy;
- GTO Wizard neural future-bounty EV parity;
- Future Game Simulation;
- site-specific hidden Mystery-bounty assignment rules unless explicitly modeled;
- claiming ICM is ground truth rather than an assumption-based model.

## ICM definition

For remaining players `N`, stacks `s_i > 0`, and total `S`, ICM gives first-place probability:

`P(i first) = s_i / S`.

Conditioned on player `i` taking first, remove `i`; among remaining players, the next-place probability is proportional to their unchanged stacks. For complete finish order `(i1,...,in)`:

`P(order) = product_{k=1..n} s_ik / (S - sum_{j<k} s_ij)`.

Player `i`'s equity is the sum over finish places of `P(i finishes place k) * payout_k`.

Assumptions include equal skill/future opportunity, stack-only finish chances, fixed payout schedule, and no position/blind-growth/future strategic dynamics. Scaling every stack by the same positive factor leaves equity unchanged. Equities sum to the sum of remaining payouts.

## Pure-Python algorithm

A permutation enumerator is the independent oracle for small `n`, not the production algorithm. Production uses subset dynamic programming over eliminated/placed-player masks and paid positions, with deterministic player order. Equivalent remaining-stack totals are reused. Time and memory bounds are stated from the implementation's actual mask/state count; the architectural input limit is measured and tested rather than asserting that all ten-player cases are cheap.

Use `fractions.Fraction` in known-answer tests and finite floats in the API implementation. Payouts and stacks reject booleans, NaN/infinity, negatives, zero total stack, too many paid positions, and increasing payouts. Busted players may be excluded before evaluation or represented with zero stack only in a separate post-hand wrapper; the core evaluator requires strictly positive stacks.

## Exact ICM fixtures

Parent-generated independent permutation enumeration produced:

1. stacks `(1,1)`, payouts `(100,0)` → equities `(50,50)`.
2. stacks `(1,1,1)`, payouts `(100,60,30)` → each `190/3`; total `190`.
3. stacks `(50,30,20)`, payouts `(100,60,0)` → `(985/14, 105/2, 260/7)` = approximately `(70.3571428571,52.5,37.1428571429)`; total `160`.
4. stacks `(2,1,1)`, payouts `(100,60,20)` → `(220/3,160/3,160/3)`; total `180`.

Production float output must agree with the Fraction permutation oracle within `1e-12`. Additional exhaustive tests compare subset DP with permutation enumeration for deterministic stack/payout grids up to a tractable fixture size.

## Immediate bounty formats

All monetary quantities are nonnegative finite values in one declared currency unit. Rounding is not implicit; integer minor units are preferred.

### Standard knockout (KO/SKO)

An eliminated player's current bounty is paid immediately to the declared recipient(s). The regular placement prize pool remains separate. If several players jointly eliminate a player, recipient shares are explicit and sum to one; the engine does not invent a house rule.

### Progressive knockout (PKO)

For eliminated player bounty `b` and configured immediate fraction `f in [0,1]`:

- `f*b` is immediate cash split by declared recipient shares;
- `(1-f)*b` is added to recipients' bounty heads using the same explicit shares, unless a separately declared rule says otherwise;
- the eliminated player's bounty becomes zero.

Many events use one half, but Phase 3 does not hard-code `f=0.5`. Winner self-bounty treatment is an explicit terminal rule.

### Total knockout (TKO)

`TKO` means the regular placement payout vector is empty/zero and tournament value is allocated through bounties. It is an economic format flag, not enough to determine progressive versus fixed transfer mechanics. The schema therefore requires an explicit bounty transfer rule (`standard` or `progressive`) and its parameters. This resolves terminology without guessing operator-specific rules.

### Mystery bounty

A Mystery bounty is a random award drawn under an explicitly supplied finite distribution or remaining multiset. Two bounded modes are valid:

- `expected-value`: immediate award is the exact distribution mean;
- `enumerated-chance`: create one chance outcome per distinct award with exact probability and update the remaining multiset when modeling draws without replacement.

No external probability library is needed. Replacing the full distribution by its mean preserves one-draw expected cash but not risk-sensitive utilities, future draw composition, or strategy when nonlinear utility is modeled. Full hidden-assignment tournament dynamics are a boundary.

## Bounty conservation fixtures

1. **KO:** bounty 100, one recipient → immediate cash 100, eliminated head 0, total bounty/cash value conserved.
2. **KO split:** bounty 101, shares `(1/2,1/2)` with integer minor units requires an explicit odd-unit recipient; no floating loss.
3. **PKO half example:** `b=80`, `f=1/2` → cash 40 and recipient head increase 40.
4. **PKO configurable:** `b=100`, `f=1/4`, shares `(3/4,1/4)` → total immediate cash 25 and head increases 75, each apportioned exactly by shares.
5. **PKO winner:** winner-self-bounty unlock is applied only when explicit; otherwise no implicit final cash appears.
6. **TKO:** zero placement payouts plus KO awards; total declared tournament value equals cumulative bounty cash plus live bounty heads under the declared transfer model.
7. **Mystery mean:** awards `(10,10,80)` with equal probabilities have expected award `100/3`; exact Fraction oracle and float differ by at most `1e-12`.
8. **Mystery without replacement:** after drawing 80, remaining distribution is `(10,10)` with mean 10; probabilities and value conserved exactly.
9. **Multiple eliminations:** each eliminated player maps to an independently validated recipient-share vector; no bounty is awarded twice.

## One-hand tournament utility integration

Inputs include pre-hand stacks, post-hand stacks, payout vector, and explicit eliminations. Verify chip conservation independently before applying ICM. Compute:

`u_i = ICM(post)_i - ICM(pre)_i + immediate_cash_i`.

Busted players have zero post-hand placement equity unless the payout schedule wrapper assigns a placement prize determined by simultaneous-elimination rules. Simultaneous bust order and ties are tournament rules and must be explicit; Phase 3's simplest integration rejects ambiguous simultaneous eliminations.

The sum of `ICM(post)-ICM(pre)` is zero when the same remaining payout pool is represented on both sides. Immediate bounty cash comes from a separately tracked bounty pool; conservation tests include that pool rather than expecting player utilities alone to sum to zero.

## Strict JSON and CLI

New standalone subcommands/endpoints:

- `icm-equity`: strict stacks/payouts → equity and finish probabilities;
- `bounty-transition`: strict format/rule/current heads/eliminations/distribution → cash awards and next state;
- bounded tournament terminal evaluation through the Phase 3 game API.

Every request has integer `version:3`, exact allowed fields, deterministic ordering, explicit units, and structural limits. Reject duplicate JSON keys, bool-as-number, malformed shares, ambiguous eliminators, unknown `TKO` transfer mode, impossible Mystery distributions, and unsupported future-EV requests. Existing Phase 1/2 schemas remain unchanged.

## Acceptance gates

- subset-DP ICM agrees with independent Fraction permutation enumeration within `1e-12` on all small fixtures;
- equities sum to payout pool within `1e-12`;
- equal stacks produce equal equities and seat permutation only permutes output;
- common stack scaling leaves output unchanged within `1e-12`;
- bounty cash + live heads + consumed/declared terminal value conserves the configured bounty pool exactly in integer-unit fixtures;
- PKO immediate fraction and recipient shares are never defaulted silently;
- Mystery enumeration probabilities sum to one and without-replacement updates exact counts;
- one-hand tournament utilities match hand-calculated pre/post ICM differences;
- oversized ICM inputs fail at the documented mask/state limit;
- requests for full strategic ICM/bounty or neural future-bounty parity fail closed with a documented-boundary message.

## Implemented-versus-boundary matrix

| Capability | Phase 3 disposition |
|---|---|
| Small-field exact ICM equity | Implement |
| Independent permutation oracle | Implement in tests |
| KO/SKO immediate bounty accounting | Implement |
| Configurable PKO immediate/head transfer | Implement |
| TKO as zero regular pool plus explicit bounty rule | Implement accounting |
| Finite Mystery expected/enumerated one-draw model | Implement |
| Tiny one-hand terminal utility integration | Implement bounded version |
| Full tournament strategic solving | Documented boundary |
| Future bounty capture EV | Documented boundary |
| Neural continuation/value approximation | Tier 3 boundary |
| Universal site/house bounty rules | Not claimed |

Every implementation sub-batch requires a fresh non-author adversarial wave under `review/phase3/` before the next feature batch starts.
