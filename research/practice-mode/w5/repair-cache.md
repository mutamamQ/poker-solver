# W5 repair-B — disk solve cache (audit F1, F2, F8, F9, F10)

Files (exclusive): `src/poker_solver/practice/solve_cache.py` (modified),
`tests/test_practice_w5_cache_repairs.py` (new, 50 tests). `tests/test_practice_solve_cache.py` is unchanged
and all 36 of its tests still pass. No models/catalog/adapter/evaluate edits. Not committed.

## Fixes
- **F1 — any corrupt record is a miss and its file is removed.** `_load` reads bytes (`read_bytes`). OSError
  on read is a transient miss and the file is kept. UTF-8 decode, `json.loads` and `solved_from_record` now
  all run inside one `try ... except Exception` that discards the file. This covers UnicodeDecodeError,
  RecursionError, ZeroDivisionError, OverflowError, TypeError, KeyError and AttributeError. `_store`'s
  round-trip check also catches `Exception`, so an unencodable value is kept in memory instead of raising.
- **F2 — invalidation tracks solver code.** New `code_fingerprint()` hashes the source bytes of
  `FINGERPRINT_MODULES` with sha256. It is computed lazily, once per process, under a lock. Each file adds its
  relative name, length and bytes, or a `missing` marker. Modules: model, cards, equity, evaluator, cfr,
  mccfr, kuhn, river, multistreet, allstreet, bounded_tree, game_structure, preflop, sizing, nplayer,
  nplayer_preflop, nplayer_postflop, best_response, api (complete_strategy), and practice/{adapter,
  evaluate, models, scoring, catalog, nplayer_metrics}. The record now has a `code_fingerprint` field.
  `solved_from_record(..., fingerprint=)` rejects a mismatch, and so does a missing field. `SCHEMA` is
  bumped to `practice-solve-cache-v2`, so v1 files are discarded on read. `stats()` and the CLI `stats`
  print the fingerprint. `DiskSolveCache(..., fingerprint=)` is an override, used only by tests to simulate
  "other code".
- **F8 — record consistency.** New `_check_provenance_matches_spot` is always run by `solved_from_record`
  (with or without `key`). It checks that `provenance.params_hash == spot.params_hash() == key`, that
  `provenance.backend == spot.backend`, that `(algorithm, iterations, seed) == spot.solve`, and that
  `provenance.params == spot.canonical()`. The params comparison checks dict equality and sorted-JSON
  equality, so `2` vs `2.0` is rejected. Not added: checking that `optimal_action` follows from `strategy`.
  `SolvedSpot` already checks `optimal_size`/legality, and argmax tie-breaking belongs to the adapter. A
  hand-edited strategy that keeps provenance intact can therefore still load (audit probe
  `tampered-wellformed-record`). The F2 fingerprint does not protect against this; the cache dir is
  user-local (0700).
- **F9 — memory_items=0 plus a failed write.** `__setitem__` now stores to disk first. If persisting fails,
  the key is marked volatile (`_volatile`) and the LRU never evicts it. `SolverAdapter.solve`'s read-back
  therefore returns the solve, and adapter.py needs no change. Persisted entries keep the old LRU bound.
  Re-setting a volatile key successfully makes it evictable again.
- **F10 — malformed keys.** `__contains__` returns `False` for non-str or non-sha256 keys. get/set/del
  still raise `ValueError`, as before.

## Verification
- Audit probe script `/tmp/w5a1/cache_probes.py` against the repaired code: invalid-utf8, deep-nesting and
  fraction-zero-den return a miss and the file is removed. The adapter path solves fine. contains-non-key
  gives `[(123, False), ('nothex', False)]`. memory_items0-write-failure gives `ok 21`. The
  provenance-inconsistent record is now rejected (miss). Multi-process and changed-params probes are
  unchanged and pass.
- New tests reproduce each repro:
  - F1: 13 corruption variants, each a miss with the file removed (checked twice), then re-solved and
    re-persisted; the audit restart-through-adapter loop; a transient read error keeps the file.
  - F2: the fingerprint is in the record and in stats; module coverage; editing or deleting
    cfr/kuhn/adapter/evaluate in a copied tree changes the hash; the mutant-writes / real-reads repro with
    the same `solver_version` is rejected and re-solved; a missing fingerprint and the v1 schema are
    rejected.
  - F8: 9 provenance tampers, including the audit's combined pot=999 / iterations=99999.
  - F9: memory_items=0 plus `os.replace` failure; volatile entries are kept while persisted ones are
    evicted.
  - F10: 9 malformed keys.
- `pytest tests/test_practice_solve_cache.py tests/test_practice_w5_cache_repairs.py`: **86 passed**.
- `pytest tests/test_practice_*.py` (with the concurrent repair agent's uncommitted work in the tree): **387 passed, 0 failed** (250 s).

## Notes for integrators
- Each new process recomputes the fingerprint once (~25 files, a few ms). Any edit to a listed module
  invalidates every cache entry on next read, including comment-only edits. This is intentional: it fails
  closed.
- If the adapter gains a dependency on a new solver module, add it to `FINGERPRINT_MODULES`.
  `test_f2_fingerprint_covers_required_modules` asserts that every listed file exists.
