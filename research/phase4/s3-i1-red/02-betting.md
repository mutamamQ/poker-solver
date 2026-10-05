# S3-I1 Betting/Reopening RED Receipt — R3I1-2S

**Owner:** R3I1-2S (betting/reopening corrective)
**Parent verification timestamp:** 2026-09-16T04:14Z
**Scope:** Exclusive `tests/test_nplayer_preflop_betting.py`
**Architecture:** `ARCHITECTURE_PHASE4_S3.md` @ `65d411793d1d7767d86500d0adffe9f40b379108`
**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`

---

## Coverage

The narrowed permanent suite covers:

1. **HU/6/9 initial action order** — exact first actors and HU pending queue.
2. **Standard-straddle boundary** — exact 6-player first actor after the operational UTG straddle.
3. **Exact sizing-key selection** — one CO raise/BTN call/SB squeeze verifies `cold_callers=1` and OOP lookup.
4. **Full-raise reopening** — a CO open, BTN 3-bet, and CO 4-bet verify the exact raise-count/relation keys.
5. **Mandatory legal short-all-in trace** — CO raises to 30, BTN and SB call, BB is truly all-in at 35. Both policies assert `pending == (2, 3, 0)` and exact `can_raise` vectors; the reopening case uses the exact `(CO, raise_count=2, cold_callers=0, IP)` key.

All expected vectors are independent integer/rational calculations, not production-derived.

---

## Design

- Direct module-scope import: `from poker_solver.nplayer_preflop import ...`
- No caught import, importorskip, skip, xfail, fakes, or placeholders
- Permanent behavior suite, not temporary scaffold
- Independent expected values and amounts
- Isolated pytest execution

---

## Parent RED verification

The parent compiled the permanent test body and scanned it for caught imports, skips, xfails, `assert False`, vacuous root assertions, invented `apply_action` methods, and sizing expressions outside the strict `sizing.py` schema. The worker's invented `{kind: fixed, amount: ...}` expressions were replaced by exact equivalent `big-blinds` expressions before final acceptance. It directly imports `poker_solver.nplayer_preflop`; the isolated command below fails only because that production module is intentionally absent.

```text
uv run pytest -q tests/test_nplayer_preflop_betting.py
exit: 2
error: ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'
```

The worker did not execute its promised receipt commands; this receipt records the parent's actual run rather than the worker's unsupported claim. After the parent's exact reopening correction, the final test hash is recorded in the completion heartbeat.

**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
**Accepted design commit:** `65d411793d1d7767d86500d0adffe9f40b379108`

**Disposition:** `RED_CONFIRMED` subject to hash-bound heartbeat.

## Post-GREEN protocol correction and RED revalidation

The first GREEN run exposed that eight fixture setup lines treated the first `chance_outcomes()` entry as a state. The architecture and `NPlayerGameState` protocol define it as `(Action("DEAL", index), probability)`. The parent corrected only those lines to call `root.child(action)`, temporarily removed production, and reproduced isolated exit 2 with the exact missing-module cause. Final test SHA-256: `d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69`.
