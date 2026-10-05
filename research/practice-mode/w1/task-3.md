# W1 task-3 — Practice HTTP server + API/server tests

Files (owned): `src/poker_solver/practice/server.py`, `tests/test_practice_api.py`, this note.

## Run

```bash
.venv/bin/python -m poker_solver.practice.server --port 7777            # serves repo-root web/
.venv/bin/python -m poker_solver.practice.server --port 0 --web-dir web # any free port
POKER_PRACTICE_WEB=/path/to/web POKER_PRACTICE_TIMEOUT=30 .venv/bin/python -m poker_solver.practice.server
.venv/bin/python -m pytest tests/test_practice_api.py -q
```

Stdlib only (`ThreadingHTTPServer`, `BaseHTTPRequestHandler`, `json`, `pathlib`). Binds `127.0.0.1` by default.
Public API: `DEFAULT_WEB_DIR` (repo-root `web/`), `make_server(host, port, web_dir=None, dispatch=None)`,
`serve(host, port, web_dir)` (serve_forever + server_close in finally), `main(argv)` (`--host`, `--port`=7777, `--web-dir`).
Web dir precedence: argument > `POKER_PRACTICE_WEB` > `DEFAULT_WEB_DIR`. `dispatch` defaults to the real
`poker_solver.api_v4.dispatch_v4` (imported lazily); tests inject a stub only for error/timeout cases.

## Routes

| Method | Path | Result |
|---|---|---|
| GET/HEAD | `/`, `/index.html` | `index.html`, `text/html; charset=utf-8` |
| GET/HEAD | `/app.js` | `text/javascript; charset=utf-8` |
| GET/HEAD | `/style.css` | `text/css; charset=utf-8` |
| GET | `/api/health` | 200 `{"ok": true}` |
| POST | `/api/v4` | 200 dispatch_v4 response JSON |
| any | anything else (incl. traversal, `%2e%2e`, `/web/../x`) | 404 JSON |
| non-allowed method on a known path (PUT/DELETE/PATCH/OPTIONS anywhere known, POST on static/health, GET on `/api/v4`) | 405 JSON + `Allow` |

Static files are resolved only from a fixed allow-list map (URL path -> file name); the URL is never joined onto
the filesystem. Missing allow-listed file -> 404 JSON. Query strings are ignored.

## POST /api/v4 status codes

| Condition | Status |
|---|---|
| Missing / non-integer / negative `Content-Length` | 400 |
| `Content-Length` > 1 MiB (checked before reading) | 413 |
| Body not UTF-8 JSON, duplicate keys, NaN/Infinity, non-object top level | 400 |
| dispatch raises `ValueError`/`TypeError`/`KeyError` (bad version like `"4"`, `4.0`, `true`; unknown op; bad payload) | 400 `{"error": msg}` (no traceback) |
| dispatch exceeds timeout (default 90 s, env `POKER_PRACTICE_TIMEOUT`) | 504 |
| other exception | 500 `{"error": "internal server error"}` (logged) |
| success | 200 |

All JSON responses: `application/json; charset=utf-8`, `Content-Length`, `Cache-Control: no-store`,
`json.dumps(allow_nan=False)` (non-serializable result -> 500). Request logging goes to the `logging` module (DEBUG), not stderr.
Dispatch runs in a daemon worker thread joined with the timeout; on timeout the solve thread is abandoned (Python
cannot kill it) but the client gets 504 promptly.

## Tests (`tests/test_practice_api.py`)

- Server (always run): static assets + content types/length, missing asset 404, traversal/unknown 404 (raw
  `HTTPConnection` so paths aren't normalised; asserts no secret/pyproject content), health, 405s, malformed JSON,
  duplicate keys, NaN, non-object, 413, missing/negative Content-Length, strict version (`"4"`, `4.0`, `true`),
  unknown op, injected-dispatch KeyError -> 400, injected success, timeout -> 504, env web-dir override, default web dir.
- Practice round trip over HTTP (list spots; solve kuhn/river spot -> strategy sums to 1 + params_hash/iterations;
  submit optimal_action -> score in [0,100] + grade; R1: same spot_id, iterations 5 vs 300 -> different params_hash and
  strategy/range_strategy). Guarded by a single `skipif`: a probe `dispatch_v4(practice-list-spots)` raising `ValueError`.
  They un-skip automatically once `practice.api.handle_practice` exists (dispatch_v4 already routes `practice-*`).

## Decisions

- `make_server` takes an extra optional `dispatch=` parameter (test hook); production default is the real dispatch_v4.
- 405 vs 404: unknown paths are 404 for every method; known paths with the wrong method are 405.
- HEAD supported for static/health routes (same headers, no body).
- R1 test uses the same `solve.seed` for both runs so only iterations differ; asserts `result.spot` is identical.
