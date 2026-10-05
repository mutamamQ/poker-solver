VERDICT: FINDINGS

# W3 re-audit round 4: R2/R4 final verification (commit 40a520c)

Auditor: fresh adversarial agent. No repo edits apart from this file, and no commits. I probed my own server, `PYTHONPATH=src .venv/bin/python -m poker_solver.practice.server --port 7841`, which has since been stopped. `r3_more.py` uses in-process `make_server(port=0)`. The live :7777 server was not touched and returned 200 on `/api/health` at the end.

## Suite (R4)
`cd /home/genomix-node/poker-solver && .venv/bin/python -m pytest -q` gives **1025 passed in 319.37s**, which matches the expected count.

## Round-3 repairs

| # | Repair | Result |
|---|---|---|
| N1 | Request-line parse errors | **Fixed.** `hello\r\n\r\n` returns `HTTP/1.1 400`. `GET / HTTP/2.0` and `HTTP/3.1` return `HTTP/1.1 505`. `GET / HTTP/1.1 extra`, `HTTP/x.y` and `\x00\xff junk` return `HTTP/1.1 400`. Every one carries application/json, nosniff, CSP, X-Frame-Options, Referrer-Policy and `Connection: close`, with a `{error}` body. |
| N4 | A leading CRLF before the request line | **Fixed.** A single `\r\n` prefix returns 200 `{"ok":true}`, and so does a run of up to 8 blank lines. See F-R4-1 for a side effect of this change. |
| N2 / N3 | Accepted, not repaired | Still present: a header trickle held the connection for 27.5 s with the timeout scaled to 2 s, and the allstreet body is still flat. Neither produced a crash or a 500, so I am not re-reporting them. |

## Fuzz
- **`/tmp/r2r4/fuzz.py`:** 428 cases gave 396 × 400 and 32 × 200, with **0 problems**.
  - There were no 5xx responses, no dropped connections and no non-JSON bodies.
  - Every 400 is exactly `{error}` and carries nosniff and CSP.
  - Every 200 has exactly the keys `{version, operation, result, provenance}`. They are the same legitimate inputs as in round 3: big seeds and limits, size snapping, and `user="\ud800"`.
- **HTTP level (`r3_verify.py` and `r3_more.py`):**
  - The F1 weights return 400.
  - F2: every closing error sends `Connection: close`, and reuse then gets 200.
  - F4: M-SEARCH and FOO return 405, and 414 and 431 return JSON with headers. TE chunked without a CL returns 400 with close, a huge CL returns 413, and `Expect: 100-continue` returns 100 then a response.
  - A body trickle gets 400 after 6.0 s. A forced 504 returns JSON with nosniff and CSP, and reuse then gets 200.
- **Totals:** no 500 anywhere, and health returned 200 after every batch.

## Findings

### F-R4-1: MINOR. The new leading-blank-line loop skips the stdlib request-line length check, so an over-long request line is silently truncated at 65537 bytes
- **Location:** `src/poker_solver/practice/server.py:316-322` (`parse_request` override, line 320 `self.raw_requestline = self.rfile.readline(65537)`).
- **Cause:** stdlib `handle_one_request` checks `len(raw_requestline) > 65536` and sends 414, but only for the *first* line it reads. The override re-reads the request line after a blank line and never repeats that check. The first 65537 bytes are parsed as the request line, and the rest of that line is read as header data.
- **Repro 1 (regresses the N1 class: response with no status line or headers):**
  ```
  python3 -c 'import sys; sys.stdout.buffer.write(b"\r\nGET /"+b"a"*70000+b" HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")' | nc -q3 127.0.0.1 PORT
  ```
  - **Result:** the server writes only `{"error":"not found"}`, with no `HTTP/1.1` status line, no Content-Type, no nosniff and no CSP. The truncated two-token line is handled as an HTTP/0.9 request.
  - **Control:** the same bytes without the leading `\r\n` return `HTTP/1.1 414` JSON with all headers.
- **Repro 2 (the overflow bytes become headers):**
  - **Setup:** build `first = b"POST /api/v4?" + b"a"*N + b" HTTP/1.1"`, with N chosen so that `len(first) == 65537`.
  - **Request:** send `b"\r\n" + first + b"Content-Length: 70\r\nHost: x\r\nConnection: close\r\n\r\n" + <70-byte practice-list-spots body>`.
  - **Result:** **200** with a full practice-list-spots result. The `Content-Length` that sat on the same line as the request was honoured as a header.
  - **Control:** without the leading CRLF, the same request returns 414.
  - A GET variant (`...HTTP/1.1X-Injected: 1\r\n...`) also returns 200 instead of 414.
- **Impact:** low. The server is loopback-only with no front proxy, so I could not show any smuggling against another component. The real problems are a 414 bypass and bytes from inside the request line being read as headers. The HTTP/0.9-style body with no headers is exactly the output N1 was meant to remove.
- **Fix suggestion:** inside the loop, after each re-read, apply the same check: `if len(self.raw_requestline) > 65536: self.requestline = ''; self.request_version = ''; self.command = ''; self.send_error(414); return False`.

### Observed, not counted
- Nine or more leading blank lines still cause a silent close. The loop stops after 8, and the stdlib then sees an empty line and returns no response. RFC 9112 only requires tolerating one CRLF, so I have not counted this.
- A lone `\r\n` or `\n` followed by EOF or a timeout gets no response. This is expected, because no request was sent.
- The server stderr shows a `BrokenPipeError` traceback from `server.py:279`, then `_error`, then `_send_json:188`, when a client disconnects before the "incomplete request body" 400 is written. No response is lost, because the peer has already gone, and nothing returns a 500. Only the log is noisy.
- `Content-Length` leniency (`+2`, `1_0`, duplicate CL) and raw HTTP/0.9 `GET /` behave as in round 3.
