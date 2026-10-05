# Solver evaluation results (full mode)

- generated: 2026-10-05T07:50:44+00:00 -> 2026-10-05T07:59:03+00:00 (499.3 s)
- git: `2a6f57ccadfa4ba2e60eb8131bb572b760d136cf` on `feat/practice-mode` (dirty=False)
- host: Linux-6.8.0-138-generic-x86_64-with-glibc2.39, Python 3.11.16, 2 CPUs, load [3.09521484375, 2.44580078125, 2.34521484375]
- **overall: FAIL** (correctness-only: PARTIAL)
- rule: Each criterion is graded from its THRESHOLDS entry. A capability's verdict is the worst of its evidence criteria and its documented scope cap. overall = worst(all criteria + all capabilities) with FAIL > PARTIAL > PASS. correctness_verdict = worst over the correctness criteria only (excludes timing, default-solve quality and scale).

## Criteria

| id | verdict | s | title |
|---|---|---|---|
| C1-kuhn-analytic | **PASS** | 5.2 | Kuhn poker: CFR vs analytic value -1/18 and alpha-family structure |
| C2-kuhn-mccfr | **PASS** | 1.5 | Kuhn poker: external-sampling MCCFR vs -1/18 |
| C3-river-closed-form | **PASS** | 10.6 | Polarized river toy vs closed-form frequencies/value (3 sizes) |
| C4-sizing-menu | **PASS** | 2.3 | Multi-size menu: solver picks the value-maximizing size |
| C5-convergence-river | **PASS** | 11.2 | NashConv vs iterations: river backend (catalog input) |
| C5-convergence-flop | **PASS** | 2.7 | NashConv vs iterations: allstreet flop backend |
| C5-convergence-turn | **PASS** | 1.9 | NashConv vs iterations: multistreet turn backend |
| C5-convergence-preflop-hu | **PASS** | 0.7 | NashConv vs iterations: nplayer_preflop heads-up |
| C5-convergence-preflop-3p | **PASS** | 3.8 | NashConv vs iterations: nplayer_preflop 3-player |
| C6-br-oracle-agreement | **PASS** | 0.0 | Repo best response / certificate vs independent oracle |
| C7-kuhn3-analytic | **PASS** | 40.4 | 3-player Kuhn vs analytic equilibrium family |
| C8-determinism | **PASS** | 1.5 | Same params -> identical strategy, values and params_hash |
| C9-param-sensitivity | **PASS** | 9.8 | R1: parameter changes change hash and solver output |
| C10-score-crosscheck | **PASS** | 339.8 | Practice Q/strategy/score/grade vs independent recomputation |
| C11-practice-solve-quality | **PARTIAL** | 0.0 | Exploitability of practice families at default solve |
| C12-practice-timing | **PASS** | 0.0 | Cold solve time of practice families at default solve |
| C13-equity-icm | **PASS** | 0.0 | Exact equity and ICM vs hand-derived / enumerated references |
| C14-scale | **FAIL** | 67.6 | Scaling to realistic range sizes (measured + projection) |
| C15-all-in | **PARTIAL** | 0.3 | All-in edge case: tree structure, zero-sum, convergence |
| C16-mixed-strategy | **PASS** | 0.0 | Strictly mixed equilibria reproduced where theory requires |

## Capabilities

| capability | verdict | scope cap | evidence | gaps |
|---|---|---|---|---|
| 2-player NL | **FAIL** | PARTIAL | C3-river-closed-form=PASS, C4-sizing-menu=PASS, C5-convergence-river=PASS, C5-convergence-flop=PASS, C5-convergence-turn=PASS, C5-convergence-preflop-hu=PASS, C6-br-oracle-agreement=PASS, C10-score-crosscheck=PASS, C14-scale=FAIL, C15-all-in=PARTIAL, C11-practice-solve-quality[river-oop-bet-or-check]=PASS, C11-practice-solve-quality[river-ip-facing-bet]=PASS, C11-practice-solve-quality[preflop-hu-open]=PASS, C11-practice-solve-quality[flop-cbet]=PARTIAL, C11-practice-solve-quality[turn-barrel]=PASS | bounded abstraction only: fixed wager menus, explicit tiny ranges (<= ~5 combos/side in the catalog), enumerated runout subsets; no full-range NLHE solve; C14-scale is FAIL; C15-all-in is PARTIAL; C11-practice-solve-quality[flop-cbet] is PARTIAL |
| 3-max | **PARTIAL** | PARTIAL | C5-convergence-preflop-3p=PASS, C6-br-oracle-agreement=PASS, C7-kuhn3-analytic=PASS, C11-practice-solve-quality[preflop-3max-open]=PASS, C12-practice-timing[preflop-3max-open]=PASS | 3-way only preflop (open/fold/call/jam trees, sampled-equity continuation); no multi-street 3-way postflop in practice; 3-max nash_conv is reported by practice/nplayer_metrics.py (W5) |
| preflop | **PARTIAL** | PARTIAL | C5-convergence-preflop-hu=PASS, C5-convergence-preflop-3p=PASS, C11-practice-solve-quality[preflop-hu-open]=PASS, C11-practice-solve-quality[preflop-3max-open]=PASS, C12-practice-timing[preflop-hu-open]=PASS, C12-practice-timing[preflop-3max-open]=PASS | preflop leaves are settled by sampled-board showdown equity (no postflop play), tiny ranges |
| postflop | **FAIL** | PARTIAL | C3-river-closed-form=PASS, C5-convergence-river=PASS, C5-convergence-flop=PASS, C5-convergence-turn=PASS, C10-score-crosscheck=PASS, C14-scale=FAIL, C11-practice-solve-quality[river-oop-bet-or-check]=PASS, C11-practice-solve-quality[river-ip-facing-bet]=PASS, C11-practice-solve-quality[flop-cbet]=PARTIAL, C11-practice-solve-quality[turn-barrel]=PASS, C12-practice-timing[river-oop-bet-or-check]=PASS, C12-practice-timing[river-ip-facing-bet]=PASS, C12-practice-timing[flop-cbet]=PASS, C12-practice-timing[turn-barrel]=PASS | single wager size per spot in the catalog, <= 4 enumerated runouts, tiny ranges; C14-scale is FAIL; C11-practice-solve-quality[flop-cbet] is PARTIAL |
| multi-street | **PARTIAL** | PARTIAL | C5-convergence-flop=PASS, C5-convergence-turn=PASS, C11-practice-solve-quality[flop-cbet]=PARTIAL, C11-practice-solve-quality[turn-barrel]=PASS, C12-practice-timing[flop-cbet]=PASS, C12-practice-timing[turn-barrel]=PASS | flop->river and turn->river only over an explicit runout subset (not all 49x48 runouts); C11-practice-solve-quality[flop-cbet] is PARTIAL |
| ICM | **PARTIAL** | PARTIAL | C13-equity-icm=PASS | icm.calculate_icm_equity is an evaluator only; no ICM-aware solve path in the solver facades or practice mode |
| mixed strategy | **PASS** | PASS | C1-kuhn-analytic=PASS, C3-river-closed-form=PASS, C16-mixed-strategy=PASS |  |
| sizing | **PARTIAL** | PARTIAL | C4-sizing-menu=PASS, C9-param-sensitivity=PASS | fixed menus; practice spots expose one size; off-tree user sizes are snapped, never solved |

## Key numbers

- C1-kuhn-analytic: NashConv by iterations 100:0.05135, 300:0.02708, 1000:0.01454, 3000:0.008389, 10000:0.004636
- C2-kuhn-mccfr: NashConv by iterations 1000:0.04872, 5000:0.03127, 20000:0.005511
- C3-river-closed-form: max_freq_error = 0.01496
- C4-sizing-menu: menu_value_error = 0.01873
- C5-convergence-river: NashConv by iterations 25:2.95, 100:0.8899, 400:0.4259, 1600:0.2009
- C5-convergence-flop: NashConv by iterations 10:36.19, 40:23.15, 160:7.969, 640:3.612
- C5-convergence-turn: NashConv by iterations 10:28.43, 40:11.34, 160:6.47, 640:3.022
- C5-convergence-preflop-hu: NashConv by iterations 10:0.8882, 40:0.4236, 160:0.1877, 640:0.08516, 2560:0.04109
- C5-convergence-preflop-3p: NashConv by iterations 10:3.095, 40:1.322, 160:0.241, 640:0.09818, 2560:0.05485
- C6-br-oracle-agreement: max_rel_error = 1.421e-14
- C7-kuhn3-analytic: NashConv by iterations 100:0.08952, 300:0.0316, 1000:0.01657, 3000:0.006463, 10000:0.002175
- C10-score-crosscheck: max_abs_error = 0
- C11-practice-solve-quality: exploitability_pct_pot = {'kuhn-intro': '0.8653', 'river-oop-bet-or-check': '0.2543', 'river-ip-facing-bet': '0.868', 'preflop-hu-open': '0.3396', 'preflop-3max-open': '0.143', 'flop-cbet': '1.122', 'turn-barrel': '0.5799'}
- C12-practice-timing: cold_solve_seconds = {'kuhn-intro': '0.3078', 'river-oop-bet-or-check': '2.109', 'river-ip-facing-bet': '1.648', 'preflop-hu-open': '0.4841', 'preflop-3max-open': '11.41', 'flop-cbet': '3.784', 'turn-barrel': '2.781'}
- C14-scale: projected_seconds_1000_iterations = 1.809e+05
