VERDICT: FINDINGS

# W3 re-audit round 2: R2/R4 (v4 envelope, server robustness, suite)

Auditor: fresh adversarial agent. Frozen scope: commit d37eec3 on feat/practice-mode. No repo edits apart from this file, and no commits.
Probes were run against my own server, `PYTHONPATH=src .venv/bin/python -m poker_solver.practice.server --port 7811`, which has since been stopped. The live :7777 server was not touched and still returns 200 on `/api/health`.
The probe scripts are in `/tmp/r2r4/` (probe1.py, probe2.py, probe3.py, fuzz.py, trickle.py).

## Round-1 repairs: all four verified fixed

| # | Repair | Result |
|---|---|---|
| 1 | Mix probability of `1` followed by 400 zeros (practice-submit-play) | **400** `{"error":"play.mix[0].probability must be finite"}` |
| 2 | Nested JSON at depths 990, 5000 and 50000, as arrays and as objects | **400** `{"error":"malformed JSON: nesting too deep"}` |
| 3 | TRACE, CONNECT, FOO, PROPFIND and lowercase `get` | **405** JSON with nosniff, CSP, XFO and Referrer-Policy. Known paths also send `Allow` (TRACE /nope gives 404). See F4 for the leftover gap. |
| 4 | Content-Length 75 with only 10 bytes sent, socket held open | Socket closed at **30.0 s**. 200 stalled sockets did not block `/api/health` (1 ms) or a list call. See F3 for the trickle bypass. |

## Suite (R4)
`cd /home/genomix-node/poker-solver && .venv/bin/python -m pytest -q` gives **1018 passed in 329.20s**, which matches the expected count.

## Fuzz summary
- **Envelopes and payloads:** 428 malformed cases in `/tmp/r2r4/fuzz.py`. They cover weird values for version, operation and payload on every op, every payload field, solve.*, pure and mix plays on the kuhn and river spots, huge ints and floats, lone surrogates and raw-byte bodies.
  - Results: 396 × 400 and 32 × 200. There were **0** 500s, 0 dropped connections and 0 non-JSON bodies. Every 400 is exactly `{error: str}` with nosniff and CSP. Every 200 has exactly the keys `{version, operation, result, provenance}`.
  - The 200s are all legitimate inputs: an int seed of any size, `limit` of 10**400, off-tree bet sizes that snap to a legal size, and `user` set to `"\ud800"`.
- **HTTP-level, clean:**
  - Pipelining (ok, bad, health, close) gave 4 ordered responses.
  - Keep-alive after a malformed-JSON 400 or a 404 GET kept working.
  - A missing Host header was served. HTTP/1.0 was served.
  - `Expect: 100-continue` gave 100 then 200.
  - Duplicate Content-Length, TE+CL and `+13`/`1_3` gave no smuggling, and each produced a single response.
  - Absolute-URI requests and non-UTF-8 headers were handled.
  - Every malformed client case gave a response or a deliberate close. Nothing silently dropped and the server process stayed up. Silent closes did occur, but only from the read timeout, from the F2 client-reuse case, and from the round-1 overflow on the legacy op (F1), which returns a 500.

## Findings

### F1: MAJOR. A huge integer weight on the legacy v4 op still gives HTTP 500
- **Location:** `src/poker_solver/api_v4.py:60`. `_float` calls `float(value)` on an unbounded int, and `OverflowError` is not converted to `ValueError`.
- The round-1 fix only patched `practice/scoring.py:_finite`. The same pattern remains in the shared `api_v4._float`, which is used at lines 138, 345, 372, 414 and 610. The server routes the error through `server.py:282-284` and returns a 500.
- **Repro (in-process):**
  ```
  cd /home/genomix-node/poker-solver && .venv/bin/python -c "
  from poker_solver.api_v4 import dispatch_v4
  p={'version':'allstreet-postflop-v1','starting_board':[0,1,2],'initial_dead_pot':10,'effective_stack':10,
     'player0_combos':[{'cards':[3,4],'weight':10**400}],'player1_combos':[{'cards':[5,6],'weight':1}],
     'allowed_runouts':[[7,8]],'betting_mode':'no-limit','wager_targets':[5],'algorithm':'vanilla-cfr','iterations':1,'seed':None}
  dispatch_v4({'version':4,'operation':'solve-allstreet-postflop','payload':p})"
  ```
  This raises `OverflowError: int too large to convert to float` at `api_v4.py:60`.
- **Repro (HTTP):** POST the same envelope to `/api/v4` with the weight written as the literal `1` followed by 400 zeros. The response is `500 {"error":"internal server error"}`.
- **Expected:** 400 `{error}`. The server's no-500 rule applies to everything on `/api/v4`.

### F2: MINOR. Error responses close the connection without sending `Connection: close`
- **Location:** `src/poker_solver/practice/server.py:195,198` (`_method_not_allowed`), `:240-259` (the Content-Length and body errors) and `:300,307` (`send_error`).
- These paths set `self.close_connection = True` but never send a `Connection: close` header. An HTTP/1.1 client therefore assumes keep-alive and writes into a socket the server has already closed.
- **Repro:**
  ```
  .venv/bin/python -c "
  import http.client; c=http.client.HTTPConnection('127.0.0.1',7811)
  c.request('PUT','/api/v4'); r=c.getresponse(); r.read(); print(r.status, r.will_close)
  c.request('POST','/api/v4',body='{}'); print(c.getresponse().status)"
  ```
  This prints `405 False`, then the second request fails with `BrokenPipeError`. POST /nope (404) and DELETE / (405) behave the same.
- **Expected:** any response the server closes after should carry `Connection: close`, as the stdlib `send_error` does. As it stands, the server drops the connection without telling the client.

### F3: MINOR. The 30 s socket timeout limits each recv, not the whole request, so a trickled body still holds a thread
- **Location:** `src/poker_solver/practice/server.py:144` (`timeout = 30`) and `:257` (`self.rfile.read(length)`).
- The timeout is applied per recv. Sending one byte every 29 s keeps a handler thread alive indefinitely, up to 1 MiB × 29 s.
- **Repro (timeout scaled to 2 s):** `.venv/bin/python /tmp/r2r4/trickle.py`. It sets `PracticeHandler.timeout = 2` and sends a 12-byte body one byte every 1.5 s. The request was **held for 18.0 s**, then answered with 400.
- **Expected:** a total deadline on the body read. The impact is limited because the server is loopback-only.

### F4: MINOR. Some error paths still miss the 405/JSON/security-header contract
- **(a) Unknown methods with non-letter names get 501, not 405.** Location: `server.py:299` (`self.command.isalpha()`).
  - Repro: `printf 'M-SEARCH /api/v4 HTTP/1.1\r\nHost: x\r\n\r\n' | nc 127.0.0.1 7811`
  - Result: `501 Not Implemented` `{"error":"Unsupported method ('M-SEARCH')"}`, with no `Allow` header. FOO on the same path gets 405 with Allow, so the two are inconsistent.
- **(b) Protocol-level errors return the stdlib HTML page with no nosniff or CSP.** Location: `server.py:304-306`, which hands codes 400, 408, 414 and 431, and any request without a parsed command, to `super().send_error`.
  - Repros:
    - 150 headers gives `431 Too many headers`.
    - A 70 kB header line gives `431 Line too long`.
    - A 70 kB request line gives `414`.
    - `hello\r\n\r\n` gives `400`.
    - `GET / HTTP/9.9` gives `505`.
  - All of these come back as `text/html;charset=utf-8` with no X-Content-Type-Options, CSP or XFO.
  - The contract says every client error is a JSON `{error}` with nosniff and the security headers.

### INFO (reproduced, no contract violation)
- **Host header is not validated.** `Host: evil.example` and requests with no Host are served normally. The server is therefore reachable by DNS rebinding from a browser. The design does not require a Host check, and the API holds no secrets.
- **BrokenPipe tracebacks on stderr.** When a stalled client disconnects, `server.py:260` (the incomplete-body 400) writes into the dead socket. socketserver then logs a `BrokenPipeError` traceback (196 of them during my 200-socket test). This is only log noise; the server stayed healthy.
