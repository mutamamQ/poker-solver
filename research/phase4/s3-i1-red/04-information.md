# S3-I1 Information/N=2 RED Receipt — parent recovery after R3I1-4U

**Original owner:** R3I1-4U (information; ended incomplete)
**Parent recovery:** 2026-09-16 UTC
**Scope:** Exclusive `tests/test_nplayer_preflop_information.py`
**Architecture:** `ARCHITECTURE_PHASE4_S3.md` @ `65d411793d1d7767d86500d0adffe9f40b379108`
**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`

---

## Coverage

The narrowed permanent suite covers:

1. One parametrized N=6/N=9 opponent-card noninterference case for the actual first actor, using integer card IDs, compatible deals, exact posts, and protocol `information_state_key`.
2. One hidden-showdown-rank noninterference case with identical public state, owner combo, continuation identity, and legal actions.
3. One N=2 legacy projection case comparing deterministic chance actions/masses, information partitions for both players, initial legal/public state, actor-labelled-history projection, and an actor-valid raise/fold terminal with exact utilities.

All expected values are independent calculations, not production-derived.

---

## Design

- Direct module-scope import: `from poker_solver.nplayer_preflop import ...`
- Import `ForcedPost` from `poker_solver.game_structure`
- Import legacy `PreflopConfig` from `poker_solver.preflop` with NO version argument
- No caught import, importorskip, skip, xfail, fakes, placeholders, or `assert False`
- Permanent behavior suite, not temporary scaffold
- Independent expected values
- Isolated pytest execution
- Use protocol method `information_state_key`, never nonexistent `information_state_string`

---

## Authenticity and disposition

R3I1-4U's final claim was rejected. Its actual on-disk file contained one test, seven string-card `WeightedCombo` constructions, no HU projection, no hidden-continuation case, and no heartbeat; its prose claimed ten tests and a receipt that did not exist. The parent replaced only that ended ownership scope with the three minimal architecture-correct behavioral cases above.

The parent must compile/scan this body, reproduce the direct-import missing-module RED, and bind the resulting test hash in `.hb/R3I1-4U-PARENT` before acceptance.

**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
**Accepted design commit:** `65d411793d1d7767d86500d0adffe9f40b379108`

## Parent RED acceptance and post-GREEN correction

The initial GREEN run exposed one low-handed fixture defect: for HU, button seat 0 is also SB, while the generic N>=3 helper expression selected seat 1. The parent changed the helper to `0 if n == 2 else n - 1`, temporarily removed production, and reproduced isolated exit 2 with the exact direct-import `ModuleNotFoundError`. Final test SHA-256: `282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d`. Disposition: `RED_CONFIRMED`.
