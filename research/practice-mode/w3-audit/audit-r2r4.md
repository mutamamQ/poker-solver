# W3 audit-2: R2 envelope fidelity, server robustness, R4 suite

Auditor: fresh adversarial agent. Repo HEAD 67c421f. No source edits.

**Manifest:** I checked all 21 sha256 entries in `CANDIDATE_MANIFEST.md` with `sha256sum -c`. All 21 are **OK**. `git diff HEAD` is clean.

## VERDICT: FINDINGS

There are 2 MAJOR and 2 MINOR findings, all reproduced. They cover the never-500 and always-a-JSON-400 rules and the 405 rule. The envelope, the suite and the CLI are otherwise clean.

---

### F1 — MAJOR — huge integer probability raises OverflowError, which becomes HTTP 500
- **File:** `src/poker_solver/practice/scoring.py:68` (`_finite`: `float(value)` on an unbounded int). The 500 comes from `server.py:270-273`.
- **Reproduce (in-process):**
  ```
  cd /home/genomix-node/poker-solver && .venv/bin/python -c "
  from poker_solver.api_v4 import dispatch_v4
  dispatch_v4({'version':4,'operation':'practice-submit-play','payload':{'spot_id':'kuhn-intro/820b58289136',
   'play':{'mix':[{'action':{'kind':'check','amount':0},'probability':10**400}]},'solve':{'iterations':5}}})"
  ```
  → `OverflowError: int too large to convert to float`
- **Reproduce (HTTP):** start `PYTHONPATH=src .venv/bin/python -m poker_solver.practice.server --port 7802`. POST the same envelope with the literal `1` followed by 400 zeros as the probability. My script was `/tmp/probe_overflow.py`.
- **Expected:** ValueError, then HTTP 400 `{"error": ...}`.
- **Actual:** `500 {"error":"internal server error"}`. The fuzz found this to be the only non-ValueError escape from `dispatch_v4`. It also triggers on the river spot.

### F2 — MAJOR — deeply nested JSON makes the server drop the connection with no response (RecursionError)
- **File:** `src/poker_solver/practice/server.py:253-257`. `parse_json_strict` is guarded only by `except (ValueError, UnicodeDecodeError)`. `RecursionError` escapes the handler, and socketserver prints a traceback.
- **Reproduce:**
  ```
  .venv/bin/python -c "
  import socket; b=b'['*1000+b']'*1000
  s=socket.create_connection(('127.0.0.1',7802)); s.sendall(b'POST /api/v4 HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n'%len(b)+b)
  print(repr(s.recv(1000)))"
  ```
- **Expected:** HTTP 400 with a JSON body ("Reject malformed JSON with a 400 JSON error", 05-web-ui-tests.md:18).
- **Actual:** `b''`. The connection closes with no HTTP response, and the server log shows `RecursionError: maximum recursion depth exceeded while decoding a JSON array`. Depth 500 gives 400. Depth 990 and above gives an empty reply. The server process survives and `/api/health` stays 200.

### F3 — MINOR — TRACE and unknown methods return the stdlib 501 HTML page, not 405 JSON
- **File:** `src/poker_solver/practice/server.py:276-281`. Only PUT, DELETE, PATCH and OPTIONS are mapped to `_method_not_allowed`.
- **Reproduce:** `curl -si -X TRACE http://127.0.0.1:7802/` (`-X FOO` behaves the same).
- **Expected:** "405 for unsupported methods" (05-web-ui-tests.md:16), with a JSON error.
- **Actual:** `501 Unsupported method ('TRACE')` with a `text/html` body. The response has no CSP, nosniff or X-Frame-Options headers.

### F4 — MINOR — a short body under a declared Content-Length holds a handler thread with no socket timeout
- **File:** `src/poker_solver/practice/server.py:248`. `self.rfile.read(length)` runs, and `PracticeHandler.timeout` is unset.
- **Reproduce:** send `POST /api/v4` with `Content-Length: 75` and only 10 body bytes, then keep the socket open. My probe was in `/tmp/probe_http.py`, case "short body".
- **Expected:** a bounded read timeout, then 400 "incomplete request body".
- **Actual:** no response for as long as the client holds the socket (my client gave up at 10 s). The 400 branch at line 249 is reached only when the client closes. This is a slowloris-style thread leak; impact is limited because the server is loopback-only.

---

## R2 envelope checks (all pass unless listed above)
- **Version:** `'4'`, `4.0`, `true`, `5`, a missing version and `4e0` over HTTP all give ValueError, then 400 "version must be JSON integer 4".
- **Top-level keys:** an extra key, a missing payload, an unknown operation and a wrong-case operation all give ValueError.
- **Payload validation:** an unknown payload key, payload `[]` or `null`, bool seed or limit, `limit:0`, `limit:2.0`, empty, duplicate or unknown families, and `solve:null` all give ValueError. So do `solve` extra keys, bad algorithm, MCCFR without a seed, vanilla with a seed, and bool `solve.seed`.
- **Iterations:** `0`, `-1`, `20001`, `1e9`, `true`, `10.0` and `null` all give ValueError.
- **spot_id:** `"nope"`, `5` and `""` all give ValueError.
- **Plays:** an illegal kind, an unlisted `raise`, a mix summing to 0.9, duplicate mix actions, NaN, inf, negative and bool probabilities all give ValueError. So do an empty mix, mix plus kind, a mix action missing amount, bool or float amount, null or list play, an empty or int user, and extra play keys. A mix sum of 1+1e-10 is accepted (within the 1e-9 tolerance).
- **Fuzz:** about 700 weird-value substitutions across every payload field. The only non-ValueError was F1.
- **Success shape:** list, solve and submit each return exactly `{version, operation, provenance, result}`. List provenance is `null`. Solve and submit provenance has all 10 fields: backend, entrypoint, params, params_hash, algorithm, iterations, seed, nash_conv, wall_time_s and solver_version. Every response passes `json.dumps(allow_nan=False)`.
- **Operation names:** exactly `practice-list-spots`, `practice-solve-spot` and `practice-submit-play`. The non-practice operations are unchanged: the diff 98d6992 only adds the routing branch. `tests/test_api_v4*.py`, `test_api.py` and `test_api_v3.py` give **125 passed**.

## Server checks (pass)
- **Path traversal:** `/../../etc/passwd`, `%2f` and `%2e%2e` encoded, `%252e` double-encoded, `/app.js/../..`, `//etc`, `%00`, `/./app.js`, case variants, backslashes and `/%2fapp.js` all return 404 JSON. Static files are served from an allow-list dict only.
- **Content-Length:** a huge value (99999999999) or 1 MiB+1 gives 413 before any read. A negative or non-numeric value gives 400. A missing Content-Length gives 400. `Transfer-Encoding: chunked` without Content-Length gives 400 "Content-Length required".
- **JSON ingress:** duplicate keys (top-level and nested) give 400. `NaN` and `Infinity` literals give 400. Invalid UTF-8 and a BOM give 400. A 5000-digit int gives 400.
- **Concurrency:** 8 parallel distinct solves at 200-207 iterations all returned 200 in about 21.7 s wall time, with the correct iterations echoed and strategies summing to 1. 8 parallel identical solves returned identical results and the same provenance (cache coherent).
- **Timeout:** with `POKER_PRACTICE_TIMEOUT=1`, 20000-iteration solves give 504 `{"error":"solve timed out"}` in about 1.0 s, with `no-store`. The server stays responsive (list returns in 0.15 s). The abandoned worker keeps burning CPU after the 504 (documented in w1/task-3.md:49).
- **Security headers:** static and 204 responses carry nosniff, a strict CSP, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`. JSON responses carry nosniff and `no-store`.
- **Binding:** the default bind is 127.0.0.1 (`make_server`, `serve` and argparse all default to it). `ss` shows `127.0.0.1:7802` and `127.0.0.1:7777`.

## R4 suite
- `.venv/bin/python -m pytest -q` gives **1007 passed in 315.81s**.
- `.venv/bin/python -m pytest -q tests/test_practice_*.py -p no:randomly`, run twice: **190 passed in 28.94s**, then **190 passed in 27.54s**. No flakes, and the time is under the 60 s budget.

## CLI smoke (pass)
- `python -m poker_solver.practice.api list --limit 2` returns rc 0 with a valid envelope.
- `solve <river> --iterations 50` returns an envelope with iterations=50.
- `submit <river> bet 30` returns Perfect 100.0, with `size_mapped` true and the bet mapped to bet[33].
- The bad inputs (illegal `raise`, unknown spot, `--iterations 0`, `--limit 0`) each return rc 2 with an `error:` message on stderr.
- `scripts/practice_smoke.sh 7803` gives **SMOKE PASS (7 checks)**, and the port is released afterwards.

## NOTES (observed, not findings)
- **Duplicate Content-Length:** `Content-Length: N` followed by `Content-Length: 5` is accepted; the first value is used. `Content-Length: +5` parses as 5. Both are harmless on loopback but lenient.
- **Chunked plus Content-Length:** the server honors Content-Length and ignores Transfer-Encoding. The result is 400 on the leftover chunk framing, not a request-smuggling success.
- **Absolute-form request target:** `GET http://evil/app.js` serves app.js. This is RFC-allowed, with no traversal.
- **List result shape:** the list result is `{spots, families}` per w1/task-2.md. That differs from design 04's `{spots, total, returned}`, which is a design-level reconciliation question.
- **Unbounded list inputs:** `seed` and `limit` accept any magnitude int (e.g. 10**30, -1). Both are bounded ints in effect, so this is harmless.
- **Ports:** the server on 7777 was never touched. My 7802 servers were killed, and 7803 was cleaned up by the script.
