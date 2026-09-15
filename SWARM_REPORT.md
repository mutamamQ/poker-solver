# BryantGPT Swarm Report

## Executive summary

This mission used parallel BryantGPT subagents as researchers, designers, draft implementers, adversarial reviewers, and final gate reviewers while the parent orchestrator reconciled and executed every correctness claim.

The useful pattern was not "let ten writers merge code." It was:

1. fan out ten non-overlapping questions at once;
2. treat returns as untrusted proposals;
3. reconcile one authoritative architecture centrally;
4. preserve disjoint implementation ownership;
5. run an adversarial wave whose findings become executable regressions;
6. run a clean convergence wave only after fixes;
7. bind final claims to parent-executed receipts.

The largest operational failure was provider tool calling. BryantGPT repeatedly requested an unknown tool and the provider returned HTTP 502. Tool-enabled children therefore could not browse, write files, or run tests. Explicit tool-free prompts recovered useful analysis, but the orchestrator had to perform source verification, file writes, integration, execution, and reproduction. This limitation must be disclosed: reviewer reports were independent reasoning, not independently executed tests.

## Routing and concurrency

Verified route:

- provider: `bryant`
- model: `15d8cc8844/CLAUDE_V4_5_SONNET`
- configured concurrency: 10

All full waves were dispatched as one `delegate_task` call containing exactly ten tasks. This avoided accidental throttling and preserved a single batch identity.

## Wave 0: research

Original batch: `deleg_ebcc20be`, ten tasks.

Topics covered canonical single-street EVs, CFR variants, hand evaluation, validation strategy, equity fixtures, game modeling, Hold'em rules, open-source solvers, exploitability, and deterministic CLI design.

Failure: all original workers hit `HTTP 502: Model requested an unknown tool; no tools executed`. Tool-enabled retries failed identically.

Recovery: prompts explicitly prohibited tool calls and asked for final markdown reports. This produced usable drafts, but several contained confident errors:

- exploitability maximized independently at hidden histories;
- monotonic exploitability was proposed as an invariant;
- cumulative regrets were called zero-sum;
- fold utility and minimum-bet semantics were wrong;
- several remembered equity percentages were wrong;
- Pluribus was treated as though it had a public implementation repository;
- CLI scope expanded into timestamps, threading, multiplayer, and undeveloped shorthand.

The orchestrator rejected those claims, checked sources, used Treys to enumerate 16 exact fixtures, and wrote ten corrected reports under `research/`.

Lesson: use research agents to generate candidate claims and search directions, not to certify facts. Assign every numerical fixture an executable oracle before it enters tests.

## Wave 1: design

Batch: `deleg_31d9138a`, ten tool-free designers.

Ownership covered data model, CFR equations, evaluator/equity, validation, CLI, river rules, best response, packaging, architecture attack, and integration.

The drafts disagreed on APIs, dependencies, convergence assertions, Hold'em scope, and best-response algorithms. The orchestrator reconciled them into `ARCHITECTURE.md`, which became the only implementation authority.

Key reconciled choices:

- immutable game states and stable ordered actions;
- vanilla synchronous full-tree CFR;
- average strategy weighted by the acting player's own reach;
- exact information-set-consistent pure best response;
- explicit NashConv versus NashConv/2 naming;
- exact original evaluator plus exhaustive equity;
- standard Kuhn known answer `-1/18`;
- a finite heads-up river game rather than unverifiable full no-limit scope;
- standard-library runtime and deterministic argparse/JSON CLI.

Lesson: ten designers maximize option coverage but also contradiction. A central contract is mandatory before parallel implementation.

## Wave 2: implementation

Batch: `deleg_c0449eda`, ten disjoint ownership tasks:

1. model + tests
2. cards + tests
3. evaluator + tests
4. equity + tests
5. Kuhn + tests
6. river game + tests
7. CFR + tests
8. best response + tests
9. audit + tests
10. CLI + tests

The tool-free workers returned full code proposals in chat rather than editing files. Interfaces were often incompatible: one proposal expected Card objects while another used integers; one expected GameNode classes absent from the model; CFR and CLI proposals called nonexistent APIs; the river proposal used a knowingly simplified high-card evaluator. Direct merging would not have built.

The orchestrator retained useful local logic, rewrote integration around `ARCHITECTURE.md`, and exercised the actual package. Initial quick-suite failures were test expectation mistakes, fixed before the first full pass. The initial reconciled suite passed 68 tests, including exhaustive checks.

Lesson: non-overlapping filenames prevent write conflicts, not semantic conflicts. Every task needs the complete shared protocol, and a parent integration pass remains unavoidable. Tool-free code should be treated as pseudocode even when it looks complete.

## Wave 3: adversarial review and cross-check

Batch: `deleg_dfbb7f26`, ten reviewers.

Assignments separately attacked evaluator, equity, river rules, CFR, best response, audit, CLI, canonical Kuhn, oracle independence, and end-to-end compliance.

Reviewers over-labeled many hypothetical issues because they could not inspect or execute current code. Examples outside scope included multiway equity and commercial-scale BR performance. The orchestrator reproduced every applicable claim rather than accepting severity labels.

One blocking bug was confirmed: strict JSON spot configuration still used `float()`/`int()` coercion, accepting strings and booleans. The fix added explicit JSON number/integer validators, rejected booleans, and set `allow_nan=False`. Regression tests were added.

The review also drove stronger non-bug evidence:

- nine explicit seven-card evaluator edge cases;
- deterministic Kuhn CLI byte test;
- 100,000 random Treys category comparisons;
- 50,000 random Treys winner comparisons;
- documentation of external-library royal-flush class behavior;
- explicit disposition reports under `review/wave3-*`.

Post-fix suite: 79 tests passed in 128.25 seconds.

Lesson: adversarial prompts should demand concrete card/state reproductions. Severity without executable reproduction is a hypothesis. Cross-checkers are most valuable when forced to compare genuinely different implementations.

## Wave 4: clean convergence

Batch: `deleg_fd48bb37`, ten independent gates over evaluator, equity, river, CFR, best response, model/audit, CLI, Kuhn known answers, evidence independence, and integration.

Every gate reported PASS with zero blocking findings for the stated finite scope. The orchestrator corrected one reviewer wording error: average CFR strategy uses owner reach, not owner reach multiplied by chance reach. The code and architecture were already correct.

The final reports under `review/wave4-*` distinguish reviewer adjudication from parent-executed evidence. This avoids falsely claiming that BryantGPT ran commands during the tool outage.

Lesson: a clean final wave should receive fixed-state evidence and narrow pass/fail criteria. It should not be asked to redesign the system. The orchestrator must still sanity-check PASS rationales.

## Cross-check design that worked

Strong checks combined different failure modes:

- canonical exhaustive five-card frequencies detect evaluator category defects;
- direct seven-card logic versus Treys detects optimized-path defects;
- 16 exact integer equity fixtures detect enumeration/tie defects;
- analytical Kuhn counts detect state-tree defects;
- `-1/18` value plus exact NashConv detect CFR/metric defects;
- hidden-bit legal BR detects hidden-history cheating;
- deterministic repeated CLI output detects ordering/state leakage;
- tree audit detects structural violations independent of solver convergence.

A passing equilibrium value alone is weak: two offsetting bugs can preserve one scalar. The combination of structural, local, oracle, and equilibrium tests is substantially stronger.

## Recommendations for future ten-agent swarms

1. Preflight one tiny tool call through the target provider before launching a tool-dependent wave.
2. If tool calls fail systemically, stop retrying identical prompts. Switch explicitly to tool-free analysis and move execution responsibility to a capable parent or another verified worker route.
3. Put the complete shared protocol and invariants in every implementation prompt. File ownership alone is insufficient.
4. Make exactly one artifact authoritative after design reconciliation.
5. Separate algorithms by failure surface, not arbitrary file count: CFR, BR, evaluator, equity, game rules, and CLI each deserve an independent owner/reviewer.
6. Require reviewers to provide a concrete reproduction and expected result for every blocker.
7. Reject monotonic-convergence requirements for vanilla CFR.
8. Use a hidden-information trap for any best-response implementation.
9. Demand integer oracle counts, not rounded equity percentages.
10. Run a clean convergence wave only after all confirmed blockers have regression tests.
11. Record routing, batch IDs, failures, corrections, and execution ownership in PROGRESS.md.
12. Never describe tool-free reviewer analysis as an executed independent test.

## Phase 3 extension

Phase 3 reused the same untrusted-proposal model with implementation/audit gates split into smaller vertical batches. The parent implemented and executed the final engine-dispatch batch after observing production-facing RED tests. The shipped engine exposes only full finite-tree `classic` CFR and approximate check-only rollout; Fast/DDLS fails closed without a neural continuation model. Seven canonical synthetic fixtures and a four-workload semantic benchmark were added without strategy-data or throughput claims. Final C3 audit evidence is recorded in `PROGRESS.md`; this section does not pre-claim that gate before it executes.

The parent route separately experienced OpenAI-Codex HTTP 429 usage limits. Those incidents were paused and logged rather than misclassified as BryantGPT failures or used to reduce the BryantGPT width.

## Final assessment

BryantGPT was effective at breadth, candidate design generation, edge-case brainstorming, and independent conceptual review. It was ineffective as an autonomous coding swarm under the observed tool-envelope failure. The best result came from combining ten-way conceptual breadth with strict central reconciliation and executable parent-side verification.

The experiment supports ten-agent parallel waves when work is partitioned by independent reasoning surface. It does not support blind code aggregation. Correctness came from explicit protocols, adversarial reproduction, independent oracles, and a single orchestrator accountable for real test receipts.
