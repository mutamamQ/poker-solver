VERDICT: FINDINGS

# W3 re-audit round 3: R2/R4 (v4 envelope, server robustness, suite)

Auditor: fresh adversarial agent. Frozen scope: commit 13ddaa9. No repo edits apart from this file, and no commits.
Probes were run against my own server, `PYTHONPATH=src .venv/bin/python -m poker_solver.practice.server --port 7821`, which has since been stopped. Some scaled-timeout probes used in-process `make_server(port=0)`. The live :7777 server was not touched and still returns 200 on `/api/health`.
New probe scripts: `/tmp/r2r4/r3_verify.py` and `/tmp/r2r4/r3_more.py`. I also reused `/tmp/r2r4/fuzz.py`.

## Suite (R4)
`cd /home/genomix-node/poker-solver && .venv/bin/python -m pytest -q` gives **1022 passed in 278.77s**, which matches the expected count.

## Round-2 repairs

| # | Repair | Result |
|---|---|---|
| F1 | A combo weight of `1` followed by 400 zeros on `solve-allstreet-postflop` over HTTP | **Fixed.** Returns **400** `{"error":"player0_combos[0].weight must be finite"}` with nosniff and CSP. The negative 10**400, `1e400` and `1` followed by 309 zeros also return 400. |
| F2 | `Connection: close` on error responses that close the connection | **Fixed.** PUT, OPTIONS, M-SEARCH and FOO on /api/v4, POST /nope, DELETE /, bad or negative Content-Length, and 413 all send `Connection: close`. `will_close` is True, and the next `http.client` request reconnects and gets 200 with no BrokenPipe. Non-closing errors (malformed JSON 400, GET 404/405) keep the connection alive and reuse gives 200. |
| F3 | A trickled body is bounded by a whole-request deadline | **Fixed for the body.** With timeout scaled to 2 s and 1 byte sent every 1.5 s, the server returned 400 and closed after 6.0 s with 3 of 12 bytes received. The round-2 run held for 18 s. The request line and headers are still not bounded; see N2. |
| F4 | M-SEARCH, garbage request lines, 414, 431 and 505 | **Partly fixed.** M-SEARCH gives 405 JSON (Allow `POST` on /api/v4, no Allow on an unknown path). 414, 431 (too many headers) and 431 (line too long) give a JSON body plus nosniff, CSP and `Connection: close`. **Garbage request lines and 505 are still broken; see N1.** |

## Fuzz
- **Envelope and payload fuzz:** 428 cases from `/tmp/r2r4/fuzz.py` against :7821.
  - Results: 396 × 400 and 32 × 200. There were **0** problems: no 5xx, no dropped connections, no non-JSON bodies, nosniff and CSP on every 400, and every 400 has exactly the key `{error}`.
  - The 200s are the same legitimate inputs as in round 2: a big int seed or limit, off-tree sizes that snap to a legal size, and `user="\ud800"`. All 200s have exactly the keys `{version, operation, result, provenance}`.
- **HTTP-level:** about 40 raw and `http.client` cases.
  - TE chunked without CL gives 400 with close. A huge CL gives 413. `Expect: 100-continue` gives 100 then a response.
  - 504 path: with POKER_PRACTICE_TIMEOUT=0.01 and a slow dispatch, the server returns 504 JSON with nosniff and CSP, and connection reuse then gets 200.
  - No 500 in any case. The server stayed responsive throughout: health returned 200 after every batch.

## Findings

### N1: MINOR. Request-line parse errors (garbage lines, 400 "Bad request version" and 505) still send a bare body with no status line and no headers
- **Location:** `src/poker_solver/practice/server.py:316-328` (`send_error`), which goes through `_error`, then `_send_json:177`, then `send_response`.
- **Cause:** when stdlib `parse_request` fails before it has accepted a version, `self.request_version` is still the default `"HTTP/0.9"`. `send_response` and `end_headers` skip the status line and all headers for HTTP/0.9, so only the JSON body is written. For 505, the stdlib calls `send_error` before it assigns `request_version` (stdlib http/server.py:321 vs 324). The 414 and 431 paths work only because the stdlib sets `request_version='HTTP/1.1'` or has already parsed the line.
- **Repro** (any port running 13ddaa9):
  ```
  printf 'hello\r\n\r\n'                        | nc -q3 127.0.0.1 7821   # -> {"error":"Bad request syntax ('hello')"}
  printf 'GET / HTTP/2.0\r\nHost: x\r\n\r\n'      | nc -q3 127.0.0.1 7821   # -> {"error":"Invalid HTTP version (2.0)"}
  printf 'GET / HTTP/1.1 extra\r\n\r\n'           | nc -q3 127.0.0.1 7821   # -> {"error":"Bad request version ('extra')"}
  printf 'GET / HTTP/x.y\r\n\r\n'                 | nc -q3 127.0.0.1 7821   # same
  ```
  The `od -c` output starts directly with `{"error"...`. There is no `HTTP/1.1 4xx/505` line, no Content-Type, no nosniff and no CSP. A client gets an HTTP/0.9-style response with no status.
- **Expected:** a status line with 400 or 505, JSON, nosniff, CSP and `Connection: close`. A likely fix is to set `self.request_version = "HTTP/1.1"` in `send_error` when it is still `"HTTP/0.9"` and the request line was not a real HTTP/0.9 request.
- No regression test covers this; `test_practice_w3_regressions.py` tests only M-SEARCH.

### N2: MINOR. The whole-request deadline covers only the body, so a trickled request line or headers still holds a thread indefinitely
- **Location:** `server.py:146` (`timeout = 30`, applied per recv) and `server.py:190-203`. The deadline is set only in `_read_body`. The stdlib `handle_one_request` and `parse_headers` readlines have no total bound.
- **Repro (timeout scaled to 2 s):** in-process `S.PracticeHandler.timeout = 2; make_server(port=0)`. Send `GET /api/health HTTP/1.1\r\nHost: x\r\n\r\n` one byte per 1.0 s. The server read all **37 bytes over 37.0 s** and answered `HTTP/1.1 200 OK` with no deadline. At the real 30 s timeout, one byte every 29 s keeps a thread alive for up to about 64 KiB × 100 lines.
- **Impact:** low, because the server is loopback-only and threads are daemons. This is the same class as round-2 F3, but the round-3 fix covers only the body.

### N3: LOW (pre-existing, possibly out of contract). The legacy `solve-allstreet-postflop` success body is not `{version, operation, result, provenance}`
- **Location:** `src/poker_solver/api_v4.py:704-725`. The flat response shape has been unchanged since 149780b.
- **Repro:** POST a valid allstreet envelope (board [0,1,2], pot 10, stack 10, combos [3,4] and [5,6], runout [7,8], `vanilla-cfr`, 1 iteration). The response is 200 with 18 top-level keys: `algorithm, approximate, config_version, continuation, exploitability, game_version, iterations, max_depth, max_nodes, metadata, nashconv, operation, provenance, seed, starting_street, strategy, values, version`.
- This conflicts with the brief's statement that "a success body has exactly the keys version, operation, result and provenance". The practice ops comply. Flag it only if the contract is meant to cover the legacy ops.

### N4: LOW. A leading empty line before the request line causes a silent drop
- **Location:** stdlib `parse_request`, which returns False on an empty request line without sending an error. `server.py` does not override it.
- **Repro:** `printf '\r\nGET /api/health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n' | nc -q3 127.0.0.1 7821` gives an empty response, and the connection closes. RFC 9112 §2.2 says servers SHOULD ignore at least one leading CRLF. A bare `\r\n` also closes the connection silently.

### Observed, not counted
- `Content-Length` is parsed with `int(raw_len.strip())` at `server.py:263`, so `+2`, `1_0` (read as 10) and duplicate CL headers (the first one wins) are accepted. Each request still produces a single response, and there is no front proxy, so no smuggling impact was demonstrated.
- `GET /\r\n` with no version is a real HTTP/0.9 request. The stdlib serves raw index.html without headers or CSP.
