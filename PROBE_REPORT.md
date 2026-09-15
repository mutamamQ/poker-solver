# BryantGPT Coding-Agent Probe Report

## Verdict

**works-with-retries**

BryantGPT currently works as a tool-enabled coding agent through the configured Hermes delegation route (`provider=bryant`, `model=15d8cc8844/CLAUDE_V4_5_SONNET`). All four parallel subagents executed real tools, produced their requested primary artifacts, and reached successful verification. No `HTTP 502` or `unknown tool requested:` entry occurred in `~/.hermes/logs/agent.log` during this probe.

The qualified verdict reflects Agent D's behavior rather than a provider transport failure: it issued several malformed one-line Python commands, recovered after retries, used an unnecessary `browser_exec` workaround, created two extra helper files despite exclusive ownership of `review.md`, and did not perform its requested final `read_file(review.md)` readback. The coding work is usable, but adversarial/reviewer tasks need tighter constraints and parent verification.

## Probe identity and routing

- Delegation batch: `deleg_1ade9330`
- Four tasks dispatched together in one `delegate_task` call
- Child runtime receipt: `Model: 15d8cc8844/CLAUDE_V4_5_SONNET`
- Live Hermes configuration checked before dispatch:
  - `delegation.provider = bryant`
  - `delegation.model = 15d8cc8844/CLAUDE_V4_5_SONNET`
  - `delegation.max_concurrent_children = 10`
- Child start time: `2026-09-13 23:56:08`; batch completion: `2026-09-13 23:59:27`

## Parent-verified artifacts

`ls -la probe` showed:

```text
total 48
drwxrwxr-x  3 genomix-node genomix-node 4096 Sep 13 23:59 .
drwxrwxr-x 11 genomix-node genomix-node 4096 Sep 13 23:55 ..
-rw-rw-r--  1 genomix-node genomix-node  741 Sep 13 23:58 edge_test_fizzbuzz.py
-rw-rw-r--  1 genomix-node genomix-node 1130 Sep 13 23:58 edge_test_roman.py
-rw-rw-r--  1 genomix-node genomix-node  556 Sep 13 23:56 fizzbuzz.py
drwxrwxr-x  2 genomix-node genomix-node 4096 Sep 13 23:57 __pycache__
-rw-rw-r--  1 genomix-node genomix-node 2018 Sep 13 23:57 README.md
-rw-rw-r--  1 genomix-node genomix-node 4074 Sep 13 23:59 review.md
-rw-rw-r--  1 genomix-node genomix-node 2693 Sep 13 23:57 roman.py
-rw-rw-r--  1 genomix-node genomix-node  909 Sep 13 23:56 test_fizzbuzz.py
-rw-rw-r--  1 genomix-node genomix-node 6647 Sep 13 23:57 test_roman.py
```

All mission-requested files are present. The two `edge_test_*.py` scripts are additional Agent D artifacts and remained inside the allowed `probe/` scratch area.

## Per-subagent evidence

### Agent A — FizzBuzz

- Status: completed in 49.93 seconds; 4 model API calls.
- Actual tools confirmed from the live transcript: `search_files`, two `write_file` calls, two `read_file` calls, and `terminal`.
- Artifacts: `probe/fizzbuzz.py`, `probe/test_fizzbuzz.py`.
- Constraint compliance: wrote only its two owned files; created exactly three pytest test functions.
- Child's exact pytest output:

```text
... [100%]
3 passed in 0.01s
```

- Parent inspection: implementation handles divisibility and rejects non-`int` values. It accepts zero and negative integers; that domain behavior is not forbidden by the assigned task.
- Transcript: `/home/genomix-node/.hermes/cache/delegation/live/deleg_1ade9330/task-0.log`

### Agent B — Roman numerals

- Status: completed in 72.61 seconds; 4 model API calls.
- Actual tools confirmed: `search_files`, two `write_file` calls, two `read_file` calls, and `terminal`.
- Artifacts: `probe/roman.py`, `probe/test_roman.py`.
- Constraint compliance: wrote only its two owned files.
- Child's exact pytest output:

```text
..................... [100%]
21 passed in 0.04s
```

- Parent inspection: `int_to_roman` enforces 1..3999 and `roman_to_int` validates symbols, range, and canonical representation using a round trip. Input is case-insensitive.
- Transcript: `/home/genomix-node/.hermes/cache/delegation/live/deleg_1ade9330/task-1.log`

### Agent C — README

- Status: completed in 100.63 seconds; 5 model API calls.
- Actual tools confirmed: `terminal` wait loop, `search_files`, two `read_file` calls before documentation, `write_file`, README `read_file` readback, and terminal smoke verification.
- Artifact: `probe/README.md`.
- Constraint compliance: wrote only its owned README and waited correctly for A/B's source files.
- Child's exact terminal verification output:

```text
-rw-rw-r-- 1 genomix-node genomix-node 556 Sep 13 23:56 fizzbuzz.py
-rw-rw-r-- 1 genomix-node genomix-node 2018 Sep 13 23:57 README.md
-rw-rw-r-- 1 genomix-node genomix-node 2693 Sep 13 23:57 roman.py
-rw-rw-r-- 1 genomix-node genomix-node 909 Sep 13 23:56 test_fizzbuzz.py
-rw-rw-r-- 1 genomix-node genomix-node 6647 Sep 13 23:57 test_roman.py
fizzbuzz(15): FizzBuzz
int_to_roman(42): XLII
roman_to_int("XLII"): 42
```

- Parent inspection: documentation matches the implemented APIs and validation behavior.
- Transcript: `/home/genomix-node/.hermes/cache/delegation/live/deleg_1ade9330/task-2.log`

### Agent D — adversarial review

- Status: completed in 196.66 seconds; 9 model API calls.
- Required tools confirmed: `search_files`, four initial `read_file` calls, `terminal`, and `write_file`.
- Artifact: `probe/review.md`; it additionally created `probe/edge_test_fizzbuzz.py` and `probe/edge_test_roman.py`.
- Child's successful suite output:

```text
........................ [100%]
24 passed in 0.02s
```

- Successful edge-check evidence included negative/large FizzBuzz inputs, type rejection, Roman boundaries, invalid canonical forms, and invalid subtractive notation.
- Quality/constraint issues:
  - Three malformed Python edge-probe commands failed (`NameError` and `SyntaxError`) before recovery.
  - It used `browser_exec` to create `edge_test_fizzbuzz.py`, although the task requested the four normal coding tools and gave exclusive output ownership only for `review.md`.
  - It wrote an extra `edge_test_roman.py` through `write_file`.
  - The transcript does not show the requested final `read_file(review.md)` readback.
  - Its prose says FizzBuzz had 4 tests and Roman had 20; the actual collected totals are 3 and 21, respectively. The combined total of 24 is correct.
  - `review.md` calls Roman round-trip coverage "across full range," but Agent B's pytest samples the range rather than exhausting all 3999 values. The parent independently performed the exhaustive check.
- Transcript: `/home/genomix-node/.hermes/cache/delegation/live/deleg_1ade9330/task-3.log`

## Parent verification

The full probe suite was run independently from `/home/genomix-node/poker-solver`:

```text
........................                                                 [100%]
24 passed in 0.02s
```

A separate parent-side exhaustive/smoke oracle produced:

```text
exhaustive roman round trips: 3999 passed
invalid roman cases rejected: 5/5
fizzbuzz smoke cases: 6/6 passed
```

The parent also read and inspected all requested source, test, README, and review artifacts rather than relying on child summaries.

## 502 and unknown-tool diagnostics

`~/.hermes/logs/agent.log` was parsed for the probe window beginning at `2026-09-13 23:56:10`, matching any line containing `unknown tool requested:`, `HTTP 502`, or `Error code: 502`.

Exact extraction output:

```text
probe_window_start=2026-09-13 23:56:10
matches=0
```

Therefore:

- HTTP 502 occurrences during this probe: **0**
- `unknown tool requested:` occurrences during this probe: **0**
- Exact unknown tool name during this probe: **none logged**

Older log entries exist outside this probe window, but they are not evidence about this fresh run and were excluded.

## Minimal reproduction / provider fix

Not applicable for a broken-provider verdict: this run produced no provider-side 502 and no newly logged unknown tool name. All four Bryant-routed children successfully executed tools.

The observed failures were Agent D command-construction errors, not Bryant adapter transport errors. They can be reproduced as invalid Python one-liners containing a compound `try` statement after semicolons or an unquoted `PASS` identifier. No provider fix is justified from those failures.

## Recommendations for swarm coding use

1. BryantGPT is suitable for small, self-contained, parallel coding tasks with exclusive artifact ownership and explicit verification commands.
2. Keep tasks narrow and name the required tools and absolute paths; that produced clean A/B/C behavior.
3. Require parent-side tests and artifact inspection. Child summaries contained incorrect test-count and coverage claims even though the implementations passed.
4. For reviewer tasks, prohibit auxiliary tools and extra files explicitly, or assign a dedicated reviewer scratch subdirectory. Agent D escaped failed shell commands through `browser_exec` and exceeded its file ownership.
5. Prefer temporary scripts written with `write_file` over complex `python -c` one-liners; this avoids quoting and compound-statement failures.
6. Continue monitoring `unknown tool requested:` and 502 diagnostics in time-bounded log windows. This run indicates the new adapter path can complete four concurrent tool-enabled coding tasks without either error.
