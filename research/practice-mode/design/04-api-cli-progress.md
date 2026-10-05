### Report 04 — Practice API, CLI, and progress persistence

Status: proposed implementation contract, not implemented behavior. New wire/storage field names below are design proposals for parent reconciliation, not claims about existing code.
Authority: `PRACTICE_MODE_DESIGN.md`, especially sections 2, 7, 9, 10, read in full; also `api_v4.py`, `cli.py`, `pyproject.toml`, `model.py`, `kuhn.py`, and `river.py`.
Verified baseline: branch `feat/practice-mode`; `git status --short` produced no entries before this report. No practice package existed at inspection time.
Ownership: parent integrates shared dispatch/parser files; practice workers implement their modules and permanent tests. This report changes neither source nor tests.

### 1. Strict wire conventions

Every request has exactly `{version, operation, payload}`. `version` is JSON integer `4`; floats and booleans fail before operation routing.
Every response has exactly `{version, operation, result, provenance}`, with integer `4` and the requested operation. This new response wrapper applies ONLY to practice operations.
Below, braces enumerate the complete allowed field set; `?` means optional input field, not an output field. Unspecified additional properties are forbidden recursively except explicitly keyed maps.
An omitted optional input uses its documented default; explicit null is rejected unless its type includes null. Arrays must be JSON lists, not tuples accepted by convenience coercion.
All integers reject bool and floats; all numeric values reject bool, NaN, and infinities. Strings are not coerced, trimmed, or case-normalized.
Unknown/missing fields, invalid types, unsupported backend combinations, illegal actions, unknown IDs, failed reconstruction, and corrupt stores raise `ValueError`; do not return a success-shaped error object.
JSON ingress rejects duplicate object keys and nonstandard numeric constants. The in-process dispatcher validates the already-decoded object; duplicate keys cannot be recovered after decoding.
Output contains only dict/list/string/int/finite float/bool/null, with string map keys. Serialize with `allow_nan=False`; never stringify arbitrary Action/InfoKey objects as a serialization shortcut.
Identifiers: `spot_id` is the derived family/hash-prefix ID from section 3; retain full `params_hash` and reject prefix collisions. User is a nonempty string, default `local`, preserved exactly.
User labels are local identities, NOT authentication. Do not expose the local service publicly as a trustworthy competitive leaderboard.

#### Shared types and provenance

`SolveParams = {algorithm, iterations, seed}`: algorithm is `vanilla-cfr` or `external-sampling-mccfr`; iterations is positive int; seed is int|null.
Vanilla uses null; external sampling requires an integer seed and a supporting backend. Catalog sampling seed is a separate integer.
`Action = {kind, amount}` on output; kind is the exact backend action token, amount is nonnegative int. On pure-action input amount may be omitted, meaning zero.
Do not uppercase/lowercase tokens: inspected Kuhn/river use lowercase, while existing preflop API history uses uppercase. Membership is checked against the solved legal actions.
`Play = Action | {mix:[{action:Action, probability:number}, ...]}`; reject both forms together, empty mixes, duplicate input actions, negative probabilities, and sums outside absolute tolerance 1e-9.
Mixed entries permit no additional keys; their Action objects require both fields. Zero probabilities are allowed; no silent renormalization.
Only wager amounts may snap, within the same legal action kind, to the nearest solved size; ties select smaller size. Never snap an illegal kind or invent an EV.
If distinct requested mix entries snap to one legal action, sum their probabilities for evaluation while preserving the original play and mapping report.
`Policy = [{action:Action, probability:number}, ...]`; `ActionValues = [{action:Action, q:number}, ...]`. Entries use identical deterministic legal-action order.
`Provenance = {backend, entrypoint, params, params_hash, algorithm, iterations, seed, nash_conv, wall_time_s, solver_version}`.
Here `params` is the complete canonical solve specification from `spot.py`, not a partial CLI argument list; `params_hash` is its SHA-256 canonical-JSON hash.
`backend`, algorithm, iterations and seed match the solve; entrypoint and solver_version are actual recorded strings; wall_time_s is finite/nonnegative; nash_conv is finite/nonnegative|null when unavailable.
Never synthesize provenance for an unsolved listing. List response provenance is null. Solve/submit provenance is one Provenance object.
Progress/leaderboard provenance is a deduplicated array of historical Provenance objects referenced by their returned attempts/best results; empty data yields `[]`.
Deduplicate by complete provenance content, not only params_hash: separate runs can share parameters but differ in timing/version. Sort by canonical JSON for deterministic output.

#### Spot serialization and cross-report boundary

`Spot = {spot_id, family, backend, game_type, street, board, hero_seat, villain_seats, ranges, pot, stacks, action_history, bet_sizes, hero_hand, solve, backend_extra}`.
These fields correspond to authoritative PracticeSpot; `solve` is SolveParams; ranges are per-seat lists of exact `{cards:[int,int], weight:number}` objects.
Hold'em cards are distinct integers 0..51; weights are finite and positive; validate compatible deals, hero membership and board collisions in `spot.py` before solving.
Seat fields and stacks have backend-correct cardinality; seats are unique/in-range; stacks are positive integers; pot is finite/nonnegative and decision pot must support the authoritative scoring denominator.
Action history uses complete Action objects; bet_sizes are positive integer sizes; hero_hand is a concrete two-card array or null where the adapter explicitly supports sampling.
Backend enum: kuhn, river, allstreet, nplayer-preflop. Game type: heads-up or 3-max. Street: preflop, flop, turn, river, subject to actual backend support.
Board length follows supported backend/street, not an assumption that the solver supports arbitrary turn starts. Unsupported turn spots fail explicitly.
`backend_extra` is NOT an arbitrary pass-through bag: use backend-specific closed schemas owned by report 03/spot.py and report 02/adapter.py.
For allstreet and preflop, existing strict dispatch payloads are the verified reference for backend-specific fields; do not duplicate them with inconsistent defaults in service.py.
Parent reconciliation required before coding the inline Spot parser: authoritative section 3 says two-card hero_hand, while section 4 requires a Kuhn J/Q/K hand; backend_extra has no enumerated schema yet.
Until those contracts are reconciled, the exact inline-Spot nested schema is blocked; reject unsupported inline shapes rather than accepting unchecked extension keys. The API payload/envelope contracts below are otherwise closed.
No new service-owned hand encoding, backend parameter aliases, or invented defaults should silently override the parent design.

### 2. Operation contracts

#### practice-list-spots

Payload: `{families?:[string,...], seed?:int, limit?:int}`. Omitted families means all supported families, seed defaults to 0, omitted limit means all matching spots; supplied limit must be positive.
Reject empty/duplicate/unknown supplied families. Generate metadata only, sort by spot_id, then apply limit; never solve to list.
Result: `{spots:[Spot,...], total:int, returned:int}`. Total counts all matching spots before limit; returned equals the array length. Provenance: null.
Catalog SolveParams defaults must be one shared, versioned catalog policy, explicitly finalized by parent/report 03; list and ID reconstruction must use precisely the same policy.

#### practice-solve-spot

Payload is exactly one variant: `{spot:Spot}` OR `{spot_id:string, families?:[string,...], seed?:int}`.
The ID branch regenerates the same catalog using list defaults; no limit is accepted because it could hide the target. Reject both/neither selectors and mismatched derived IDs.
Result: `{spot:Spot, decision:{hero_seat:int, pot:number, legal_actions:[Action,...]}, strategy:Policy, action_values:ActionValues, range_strategy:[{hand:string, strategy:Policy},...], optimal_action:Action, optimal_size:int|null}`.
Hand is the adapter's documented display serialization, not an InfoKey parser. All action probabilities, Q values, optimal action/size and provenance originate in the real solve/cache.
Successful solve registers the canonical Spot specification durably for subsequent ID-only submission; this adds no attempt or leaderboard credit.
Cache hits must validate the complete canonical hash and artifact compatibility. Default solve cache remains in-memory; a progress registry is not a disk solve cache.

#### practice-submit-play

Payload: `{spot_id:string, play:Play, user?:string}`; no client score, Q, strategy, provenance, store path, or solver override fields.
Resolve the canonical Spot from the durable registry, with deterministic default-catalog lookup allowed if absent. An unknown ID raises ValueError; never guess nondefault seed/solve parameters from a hash prefix.
Solve that specification again or use a validated content-addressed artifact, score the supplied play, then atomically append exactly one attempt. Report success only after persistence succeeds.
Result: `{spot_id:string, user:string, score:Score, progress:SpotProgress}`.
`Score = {ev_loss_chips, ev_loss_pct_pot, score, grade, chosen_q, best_q, solver_mix_q, solver_self_loss, feedback, mapped_action, size_mapped, mapped_play, provenance}`.
Numeric fields are finite; losses and self-loss are nonnegative; score is in [0,100]; grade uses exactly Perfect/Good/Inaccuracy/Mistake/Blunder and authoritative thresholds.
Feedback is a string generated from computed values. mapped_action is Action|null for a snapped pure play, otherwise null; size_mapped is bool; mapped_play is the evaluated canonical Play for either variant.
Nested score provenance equals the response provenance. Preserve original play in the attempt. No automatic retry of submit: identical resubmission intentionally creates another attempt.

#### practice-progress

Payload: `{user?:string}`. Result: `{user:string, attempts:int, spots_attempted:int, spots:{spot_id:SpotProgress}}`.
Return only this user's attempts, not every user's history. Sort spot keys; absent user returns zero counts and an empty map without creating a file.
`SpotProgress = {attempts:int, best:Attempt, last:Attempt, history:[Attempt,...]}` for attempted spots only; do not manufacture null best/last records for unattempted spots.
Attempts is history length, last is its last entry, best is selected by descending score, ascending EV loss in chips, then earliest sequence.

#### practice-leaderboard

Payload: exactly `{}`. Result: `{entries:[{rank:int, user:string, spots_attempted:int, attempts:int, mean_best_score:number, total_best_ev_loss_chips:number},...]}`.
Only users with at least one attempt qualify. Compute mean_best_score from one best attempt per distinct spot, not from all attempts; sum those best EV losses for the displayed total.
Order by descending mean_best_score, descending spots_attempted, then exact user string lexically; assign consecutive ranks starting at 1. Empty store returns no entries.
This is a practice summary across potentially different spot sets, not an equal-difficulty tournament ranking. Display that caveat; repeated easy attempts do not receive extra weight.
Provenance covers the best attempts used by the aggregate. Read one consistent store snapshot; never solve or rewrite during aggregation.

### 3. Minimal parent integration

In `api_v4.py`, leave imports, strict envelope/version validation, helpers, existing three operation branches and allstreet fall-through intact.
Extend the explicit allowed-operation set with the five named practice operations. Immediately after operation validation, recognize those exact names and lazy-import the service router from `practice/service.py`.
Use an explicitly agreed service callable, taking operation and raw payload; service owns payload parsing and dependencies. Do not claim an existing function signature for this not-yet-created module.
Do not route arbitrary `practice-*` strings; do not broaden accepted Mapping types, numeric coercion, exception handling, or old response schemas.
Service may import existing strict helpers lazily; adapter must not import service. Avoid import-time recursive calls when preflop adapter invokes the original v4 operation.
Do not change dispatch_v4's public one-argument signature merely to carry a store. Default dispatch resolves environment/default path; CLI and server inject an explicit ProgressStore at their service boundary.
For HTTP, bind the configured store in the handler and reuse identical strict envelope validation/routing. Never use per-request global environment mutation, and never accept a filesystem path from JSON.
Parent should reconcile this injection seam with report 05: shared parsing/routing must not let HTTP accept shapes rejected by dispatch_v4.
Old-op successful outputs and representative errors must remain unchanged; new allowed-operation error text necessarily enumerates more names.

### 4. CLI contract

Parent adds one `practice` argparse subtree and delegates registration/execution to `practice/cli.py`; existing eight top-level subcommands and behavior remain unchanged.
Syntax: `poker-solver practice [--store PATH] COMMAND ...`. Also accept --store after the leaf command; reject conflicting duplicate values rather than silently overriding.
Store precedence: explicit --store, nonempty `$POKER_PRACTICE_STORE`, then `~/.local/share/poker-solver/practice.json`; expand `~`. Empty explicit/env paths fail instead of selecting the working directory.
Resolve once per invocation; list need not open the store. No store selection field is accepted by v4 payloads.
- `list [--family NAME ...] [--seed INT] [--limit INT] [--json]`: repeated --family builds families; defaults match list API.
- `solve (--spot FILE | --spot-id ID) [--family NAME ...] [--seed INT] [--json]`: --spot reads exactly Spot, with `-` for stdin; catalog flags only with --spot-id.
- `submit --spot-id ID (--play FILE | --action KIND [--amount INT]) [--user NAME] [--json]`: --play reads exact Play, `-` for stdin; amount is valid only with --action.
- `progress [--user NAME] [--json]` and `leaderboard [--json]` map directly to their operations.
- `serve [--host ADDRESS] [--port INT]`: defaults host 127.0.0.1 and port 8787; allow port 0 for tests and print actual bound address to stderr. No --json success document for the long-running server.
Solve overrides live in explicit Spot.solve, not hidden CLI defaults; changing them changes canonical identity. Do not offer --iterations overrides that retain the old spot_id.
--json emits one complete API response, compact sorted JSON with allow_nan=False and a trailing newline; diagnostics go only to stderr.
Default text: list rows show ID/family/street; solve shows legal actions, mix, Q, optimal size and full provenance; submit shows grade, score, EV losses, mapping, solver noise and provenance.
Progress text shows attempts/best/last per spot; leaderboard shows rank/user/coverage/mean best score and the unequal-coverage caveat. Historical provenance remains available with --json.
Keep existing CLI convention: success 0, validation/I/O failure 2 with `error: ...` on stderr and no success JSON; argparse errors also exit 2. No traceback for expected bad input.

### 5. ProgressStore contract

Proposed exact root: `{version:1, spots:{spot_id:Spot}, users:{user:{spots:{spot_id:SpotProgress}}}}`; version is a JSON integer, never bool/float.
`Attempt = {sequence:int, recorded_at:string, params_hash:string, play:Play, score:Score}`. Sequence is positive and contiguous per user/spot; recorded_at is UTC ISO-8601 ending Z.
Keep complete unbounded history initially; truncating history would invalidate attempts/best reconstruction and requires a new explicit policy/version.
Registry stores full canonical Spot inputs, never hand-authored answers. Reject ID/hash mismatch, hash-prefix collisions, missing registry references, duplicate keys, inconsistent score provenance and unsupported versions.
On read validate the whole document, including attempts/history equality, best/last equality to recomputed selections, sequence order, numeric bounds and provenance hashes. Do not silently repair persisted derived fields.
A nonexistent file means empty version-1 state. Empty/truncated/malformed JSON, invalid UTF-8, wrong types, unknown fields, unsupported versions and unreadable existing files fail closed with contextual ValueError.
Never rename away, reset or overwrite a corrupt file automatically; preserve its bytes. Catch specific decoding/Unicode/I/O exceptions, never bare Exception.
Read-only progress/leaderboard calls do not mkdir or create files. Successful solve registers a spot; submit commits registration and attempt together if reconstructing a default-catalog spot.
Write algorithm: validate new state; serialize fully with allow_nan=False; create parent directory if needed; create unique tempfile in the destination directory; write UTF-8, flush, fsync, close; os.replace onto destination.
Use restrictive permissions for newly created store/temp files. A temp in /tmp is NOT sufficient for atomic replacement of a store on another filesystem.
Finally remove leftover tempfiles on failure. Before-replace failures preserve the original file. After-replace directory-fsync failure is an uncertain durability outcome, not proof of rollback; do not automatically retry submission.
Fsync the parent directory where supported for crash durability; distinguish atomic visibility from persistence after power loss.
Atomic replacement alone does not prevent lost updates. Proposed Linux baseline: adjacent advisory lock file plus flock around reload/validate/mutate/replace, shared by all writer processes; reads see old or new complete snapshots.
A persistent runtime lock sidecar is an explicit implementation proposal, not a file created by this report. If cross-platform locking is deferred, reject unsupported concurrent-writer deployment rather than claim safety.
Do the expensive solve outside the write lock; reload under lock before append and check canonical registry compatibility. Concurrent solves must not overwrite newer attempts.
Frozen dataclasses and tuple/MappingProxyType defensive copies at domain boundaries; serialization produces fresh mutable JSON containers, never aliases into store internals.

### 6. Executed baseline probe — verbatim commands and output

Working directory was `/tmp`. Used the existing `.venv` directly, which the task permits, to avoid uv synchronization/lockfile writes. `-B` prevented bytecode creation. No probe file was created, so none required deletion.
Commands:
```bash
PYTHONPATH=/home/genomix-node/poker-solver/src /home/genomix-node/poker-solver/.venv/bin/python -B -c 'from poker_solver.api_v4 import dispatch_v4
for version in (4.0, True):
    try:
        dispatch_v4({"version": version, "operation": "solve-allstreet-postflop", "payload": {}})
    except ValueError as exc:
        print(f"version={version!r}: {type(exc).__name__}: {exc}")
    else:
        raise AssertionError(f"accepted invalid version: {version!r}")'
PYTHONPATH=/home/genomix-node/poker-solver/src /home/genomix-node/poker-solver/.venv/bin/python -B -m poker_solver.cli --help
```
Combined stdout, exit code 0:
```text
version=4.0: ValueError: version must be JSON integer 4
version=True: ValueError: version must be JSON integer 4
usage: poker-solver [-h]
                    {evaluate,equity,solve-kuhn,solve-spot,solve-multistreet,exploitability,phase3,phase4}
                    ...

Finite-game poker solver reference

positional arguments:
  {evaluate,equity,solve-kuhn,solve-spot,solve-multistreet,exploitability,phase3,phase4}
    evaluate            evaluate exactly five or seven cards
    equity              enumerate exact heads-up equity
    solve-kuhn          solve standard Kuhn poker
    solve-spot          solve a compact river spot JSON file
    solve-multistreet   solve a multi-street game (version 2)
    exploitability      compute exploitability of a multi-street strategy
    phase3              run a strict bounded version-3 JSON operation
    phase4              run a strict bounded version-4 JSON operation

options:
  -h, --help            show this help message and exit
```

### 7. Permanent test lists

`tests/test_practice_api.py`:
- Parametrize all five operations through production dispatch_v4; test integer 4 acceptance, 4.0/True rejection, unknown operation, missing/extra envelope and recursively invalid payload fields.
- Test optional omission versus null, duplicate-key ingress, bool-as-number rejection, nonfinite values, limits, families, IDs, mutually exclusive selectors and mixed-play invariants.
- Exercise list -> solve -> submit -> progress -> leaderboard using real small solves; validate every response's JSON serialization, provenance, hash and legal-action correspondence.
- Test nondefault catalog seed and inline spot registration across fresh service instances, unknown IDs, collision detection, rejected client scores/store paths and unchanged state after invalid submit.
- Verify pure/mixed off-tree mapping, original-play preservation, canonical mapped play, deterministic ordering and no fabricated provenance on listings.
- Regression-test all three old operations with their existing production tests and representative valid/invalid requests; no new fallback parsing or changed old response fields.

`tests/test_practice_cli.py`:
- Production parser/help exposes practice and six leaves while retaining the eight old commands; required flags, mutual exclusion and unknown arguments behave correctly.
- End-to-end subprocess list/solve/submit/progress/leaderboard with isolated --store; JSON stdout parses exactly once and text mode exposes scores/provenance.
- Test --store placement/conflicts, environment/default precedence, tilde expansion, empty paths, file/stdin input, malformed JSON and no stdout success on errors.
- Verify separate CLI invocations can submit a previously registered nondefault spot; no implicit iterations override or user normalization.
- Start serve on loopback port 0, discover bound address, exercise /api/v4 with the configured store, then stop/join the server; coordinate HTTP detail ownership with test_practice_server.py.

`tests/test_practice_progress.py`:
- Missing-file empty read without writes; register-only solve gives no attempt; persistence/reopen, user/spot isolation, defensive copies and exact hash/provenance preservation.
- Attempts/last/history/best tie rules; leaderboard weighting, deterministic ties, empty users and provenance aggregation from exactly the selected attempts.
- Fail closed on corrupt/truncated/empty/invalid-UTF8 input, duplicate keys, NaN, bool/float version, future version, unknown nested fields, inconsistent summaries and registry/hash mismatch; original bytes unchanged.
- Inject serialization/write/fsync/replace failures; verify original-or-new complete JSON, no leftover tempfiles, same-directory temp placement and permission behavior.
- Separate-process concurrent submissions preserve every attempt under the lock; readers never see partial JSON; test crash-before-replace recovery and after-replace durability reporting.
Use production imports and tiny solver trees, no literal strategy tables. Keep combined practice additions under the authoritative <60 s budget; tests above are planned, not executed here.

### 8. Parent decisions still required

Exact inline Spot/backend_extra schemas and Kuhn hand representation, shared catalog SolveParams defaults, and HTTP store injection require reconciliation across reports 02/03/05 before implementation.
The baseline probes passed; new practice functionality was neither implemented nor tested. This report does not claim a complete executable JSON Schema while those authoritative model gaps remain open.
