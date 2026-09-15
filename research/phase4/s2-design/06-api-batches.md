# D206 public surface, TDD batches, and release matrix — parent-normalized

Status: recovered from the failed worker's two unauthorized draft documents and corrected against current S1 interfaces.

Public surface

- Typed exports: `NPlayerPostflopConfig`, `NPlayerPostflopState`, `NPlayerPostflopSolveResult`, `create_nplayer_postflop_root`, and `solve_nplayer_postflop`.
- Strict v4 operation: `solve-nplayer-postflop`, using the existing direct request envelope and rejecting unknown/missing fields, bool numerics, malformed N-length arrays, nonfinite weights, unsupported algorithms, and any caller mutation alias.
- The existing generic `phase4 REQUEST --json` CLI already forwards to `dispatch_v4`; adding the operation should require no new subcommand or CLI parser shape.
- Only after typed/API gates pass, update v3 capability `multiway-postflop` from exactly `3` players to `[2, 9]`, retain `one-betting-round`, and add truthful typed/json-v4/cli-phase4 interfaces.
- Legacy `MultiwayConfig`, `ThreePlayerPostflopState`, `create_three_player_root`, v1-v3 operations, and old tests remain unchanged.

Implementation batches

S2-I1 — typed core, then fresh non-author audit and commit:
- Permanent RED suites own config/deals, betting transitions, settlement/odd chips/rake, information noninterference, and old/new three-player equivalence.
- One production owner adds `nplayer_postflop.py` only after all RED receipts. Parent resolves shared integration.
- Required 4/5/9 fixtures and exact ledgers pass; legacy three-player suite and full baseline pass.

S2-I2 — solve facade, exact diagnostics, strict API/examples, then fresh non-author audit and commit:
- RED suites own N-player solve/reach/deviation, strict v4, canonical 4/5/9 examples, package exports, capability truth, and generic CLI invocation.
- Production owners have nonoverlapping `nplayer_postflop.py` facade and `api_v4.py` parsing paths; parent owns `__init__.py`/capability shared integration.
- Five-plus-player exact diagnostic executes below its explicit pure-strategy cap; no sampled or convergence claim.

Release matrix

S2 passes only when 4-, 5-, and 9-player spots solve; all terminal player utilities plus rake conserve exactly; hand-derived side pots and odd chips match; chance mass and information noninterference hold; deterministic repeated solves agree; a 5+ exact deviation diagnostic matches an independent enumeration; every old three-player test and the complete prior suite pass; fresh non-author audits verify each batch; accepted batches are committed; and `phase3-398-green` remains present.

Boundaries: one betting round, finite caller-supplied weighted ranges/showdown ranks, bounded vanilla CFR, exact but bounded exhaustive deviation diagnostic, no multi-street multiway, no convergence certificate, no abstraction, no preflop tree.
