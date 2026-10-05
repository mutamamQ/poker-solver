# W4 task B — persistent practice solve cache

## Files (exclusive ownership)
- `src/poker_solver/practice/solve_cache.py` (new)
- `tests/test_practice_solve_cache.py` (new, 36 tests)

No edits to models.py / adapter.py / api.py. No cache files committed (a test asserts no
`<sha256>.json` exists anywhere in the repo tree). Not committed to git.

## Design
- `DiskSolveCache(directory, memory_items=256)` — `MutableMapping[str, SolvedSpot]`, keyed by the full
  `PracticeSpot.params_hash()`. `DiskSolveCache.from_env()` -> `$POKER_PRACTICE_CACHE_DIR` (if non-empty)
  else `~/.cache/poker-solver/practice`. Also `default_cache_dir()`.
- Keys must match `^[0-9a-f]{64}$` (get/set/del raise `ValueError` otherwise) -> no path traversal.
  `__setitem__` also requires `value.spot.params_hash() == key == value.provenance.params_hash`.
- One file `<key>.json`: `{schema: "practice-solve-cache-v1", solver_version, key, created_at,
  solved: SolvedSpot.to_json(), info_key: <tagged encoding>}`. Atomic write: `mkstemp` in the same dir
  (`.tmp-*`), fsync, `os.replace`; temp removed on failure.
- Deserializer lives in solve_cache.py (`solved_from_record`; models has no `SolvedSpot.from_json`).
  The spot is rebuilt from its canonical params (generic: iterates `dataclasses.fields(PracticeSpot)`,
  converters only for structured fields — ranges/actions/solve/tuples), so any backend/game_type that
  PracticeSpot itself accepts (nplayer-preflop 2/3 players, allstreet flop, multistreet turn) loads
  without changes here. Never re-solves. Rebuilt `params_hash`/`spot_id` must equal the stored ones and
  the file key.
- `info_key` (arbitrary hashable solver infoset key) uses a tagged JSON codec: primitives as-is;
  tuple/list/frozenset/mapping/`Action`/`Fraction` tagged (covers kuhn, river, multistreet/allstreet,
  nplayer_preflop key shapes). Unknown types -> not persisted.
- Before writing, the record is decoded back in memory and must be `==` the original SolvedSpot;
  otherwise it is kept in memory only (logged). This guarantees disk hits are exact for future families.
- Load rejection (treated as miss, file removed, warning logged, `discarded` counter): invalid JSON,
  truncated, schema mismatch, solver_version mismatch (vs `adapter.solver_version()`), record key ≠
  filename, rebuilt hash mismatch, invalid SolvedSpot fields, file > 64 MiB. Symlinks are ignored.
- Thread-safe (RLock around memory + disk ops); LRU memory layer (`OrderedDict`) in front.
- Fail-soft: if the dir can't be created/written (probe temp file at init) -> warning, `disk_ok=False`,
  memory-only with unbounded memory so no solve is lost; write OSErrors also degrade to memory.
- `clear()` removes entry files + stale `.tmp-*` files only (unrelated files untouched), returns count;
  `stats()` -> `{dir, disk_ok, count, bytes, memory_items, schema, solver_version}`.

## CLI
`python -m poker_solver.practice.solve_cache [--dir D] warm [--families a,b] [--limit N] [--iterations N] [--seed S] [--timeout SEC]`
— real `SolverAdapter(cache=DiskSolveCache)`; per-spot `hit|miss|error  <sec>s <spot_id> <hash12>` +
summary; exit 1 if any spot errored, 2 for bad args (e.g. unknown family). `stats`, `clear`.
`--iterations` omitted -> catalog/family default solve params. Manual run (tmp dir): 24 kuhn+river-ip
spots at 30 its cold 2.98 s, warm rerun 24/24 hits 0.01 s; stats/clear verified.

## Tests (`tests/test_practice_solve_cache.py`, all use `tmp_path`)
Exact round trip (field-by-field, floats compared by `.hex()`, `to_json` equal) for real kuhn, river and
allstreet solves, via record and via a fresh disk instance; fresh adapter + fresh cache instance on same dir
-> hit with `solve_count == 0` and equal result; iterations 30 vs 31 -> different key -> miss/solve;
7 corrupt/mismatch variants -> miss + file removed + re-solve re-persists; file renamed to a wrong key ->
rejected; 10 traversal/malformed keys rejected, nothing written; key/value mismatch rejected; atomic write
(os.replace from same dir, no temp leftovers, replace failure -> memory only); unwritable dir ->
memory-only; LRU bound vs disk persistence; from_env/default dir; delete/clear/stats; 8-thread concurrency
smoke (shared + separate instances on one dir); CLI warm/stats/clear and env dir; no pre-solved files in repo.

Result: `36 passed in 2.70s`. Full suite `.venv/bin/python -m pytest -q`: **1094 passed, 0 failed**
(396.7 s). Baseline was 1026; 36 are from this task, and the remaining +32 come from tests other W4 tasks
added at the same time in the shared worktree.

## Notes for integrators
- Task C: `SolverAdapter(cache=DiskSolveCache.from_env())`; construction never raises for an unusable
  dir (degrades to memory) — only a bad `memory_items` raises.
- A solver package version bump invalidates (and deletes on read) all old entries.
- `wall_time_s` in a cache hit is the original solve's time (provenance is preserved exactly).
