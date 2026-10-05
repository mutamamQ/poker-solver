# Design Report 05 — Minimal web UI, HTTP server, and tests

Status: design proposal for the practice-mode implementation wave. The authoritative requirements are in `PRACTICE_MODE_DESIGN.md`; this report specifies the thin HTTP/UI layer and its verification plan without changing that contract.

## Repository check

- Searched `docs/`, `src/poker_solver/`, and `examples/` for `.html` and `.js` files: none found.
- Searched the repository for `http.server` and `ThreadingHTTPServer`: no prior server implementation found; only the authoritative design mentions the intended server.
- The existing exported API entry point is `poker_solver.api_v4.dispatch_v4`. Practice operations are specified in the design, but the repository search did not find their implementation. Treat this report as a plan, not evidence that the practice API or UI already exists.

## Minimal server: `src/poker_solver/practice/server.py`

Use only the standard library: `http.server.ThreadingHTTPServer`, `BaseHTTPRequestHandler`, `json`, and `pathlib`. Keep request handling thin; route `/api/v4` to `dispatch_v4` and let the API/service own practice behavior.

- Bind to `127.0.0.1` by default. Expose a CLI `--port` option; port `0` should be accepted for tests and reported through the bound server address.
- `GET /` serves `web/index.html`; `GET /app.js` and `GET /style.css` serve the two sibling assets. Set explicit UTF-8 content types and `Content-Length`. Return 404 for other paths and 405 for unsupported methods; do not expose arbitrary filesystem paths.
- `POST /api/v4` reads one JSON request body and calls `dispatch_v4(data)`. Serialize the returned JSON-safe response as UTF-8 JSON. Convert `ValueError` to a 400 JSON error response; do not leak a traceback or internal filesystem path.
- Enforce a documented finite body limit (suggested initial limit: 1 MiB). Reject missing, malformed, negative, or over-limit `Content-Length` before reading an unbounded body; return 413 for a body over the limit. Reject malformed JSON with a 400 JSON error.
- Use an explicit static-path allow-list rather than joining an untrusted URL path to the web root. If path resolution is used internally, verify the resolved file remains beneath the resolved `web/` directory. This prevents traversal, including encoded traversal and symlink escapes.
- Run `serve_forever()` in normal operation; tests start and stop the server explicitly. Ensure `server_close()` runs after `shutdown()`.

The request envelope remains the v4 envelope in the authoritative design: integer `version: 4`, an `operation`, and a `payload`. Do not create a second practice-specific wire protocol.

## UI flow: API-driven only

`index.html` supplies semantic containers and controls; `app.js` performs `fetch` calls to `/api/v4`; `style.css` provides a compact, responsive practice layout. No solver answer, strategy probability, optimal size, example EV, or fixed spot answer belongs in JavaScript. Derive every displayed strategy value from the API response.

1. On load, call `practice-list-spots`; render selectable spots and a clear loading, empty, and error state.
2. On selection, call `practice-solve-spot` for the selected spot. Render the board, pot, stacks, public action history, and hero hand. Format cards as rank plus suit glyph using card data returned by the API; do not encode a sample deal in the client.
3. Build available action controls and the size input from the returned legal action set. A size control is relevant only where the legal set includes a size-bearing action; submit only an action/amount represented by that set.
4. On submit, call `practice-submit-play` with the selected `spot_id` and play. Render score, grade, EV loss, optimal mix bar, and the whole-range strategy table from the response. Keep displayed values labeled with their units where applicable.
5. Show solve provenance from the response: canonical solve parameters, iterations, `nash_conv` when present, and `params_hash` (plus other provenance fields supplied by the API). Handle absent optional values explicitly rather than inventing them.
6. Disable duplicate submission while a request is pending; surface HTTP/API errors accessibly and allow retry. Keep navigation back to the spot list available.

The implementation should agree with the service/API serializer on exact JSON property names. This report intentionally specifies displayed data and operations rather than guessing unverified response keys.

## Static DOM contract

Use these stable IDs in `index.html`; `test_practice_server.py` can assert their presence by parsing or simple exact-ID checks. IDs are test hooks and should not be renamed casually.

| ID | Required purpose |
|---|---|
| `practice-app` | Root application landmark |
| `spot-list` | Spot choices populated from the list response |
| `spot-status` | Loading, empty, and list error status |
| `spot-details` | Selected spot context |
| `board-cards` | Board card glyphs |
| `pot-value` | Pot display |
| `stacks-list` | Seat stacks |
| `action-history` | Public action history |
| `hero-hand` | Hero hand card glyphs |
| `action-controls` | Controls generated from returned legal actions |
| `action-size` | Size input, shown/used only when applicable |
| `submit-play` | Submit the selected play |
| `result-panel` | Submission result region |
| `score-value`, `grade-value`, `ev-loss-value` | Score, grade, and EV loss |
| `optimal-mix` | Optimal mix visualization |
| `range-strategy` | Whole-range strategy table |
| `provenance` | Solver provenance details |
| `error-message` | Accessible request/validation error |

Use labels and `aria-live` on status/result/error regions. Static HTML checks assert structure and accessibility hooks only; behavioral tests verify data and state transitions through the API rather than brittle CSS details.

## HTTP server tests: `tests/test_practice_server.py`

Use a fixture that creates the server on `("127.0.0.1", 0)`, starts `serve_forever` in a thread, yields its actual address, then calls `shutdown()`, joins the thread, and calls `server_close()` in `finally`.

- Real `urllib.request` round trip: POST a valid v4 practice request to `/api/v4`; assert HTTP status, JSON content type, parseable response, and operation result. Use a deterministic, small-tree fixture so the request exercises the real dispatch path without a long solve.
- GET `/`, `/app.js`, and `/style.css`; assert success, non-empty bodies, and expected content types. Check the HTML contains the stable DOM IDs above.
- POST a request that causes `ValueError`; assert 400 and a JSON error body.
- Verify unknown static paths and traversal attempts (including percent-encoded `..`) are rejected and do not return file contents. Assert path handling never serves a file outside `web/`.
- Verify oversized request bodies are rejected before dispatch. Test unsupported methods and malformed JSON if included in the handler contract.
- Keep test cleanup robust on assertion failures; no fixed port, sleeps, or external network dependency.

## Consolidated practice test plan and runtime budget

Run the permanent practice tests from section 9 of `PRACTICE_MODE_DESIGN.md`: spot validation/hash/immutability; adapter and provenance; scorer metrics/off-tree mapping; deterministic catalog and no literal strategy data; required no-hardcode sensitivity to iterations/range/pot/stack and `params_hash`; progress persistence/corruption; API; CLI; server; and solver-evaluation fast checks.

Budget target: all practice tests add **less than 60 seconds** to the full suite. Keep routine tests on tiny deterministic trees, bound iteration counts, avoid repeated expensive solves by sharing only safe test fixtures, and keep benchmarks/timing sweeps out of the default fast suite. Measure the practice subset and full suite in CI; if the budget is exceeded, identify slow tests by duration and reduce fixture cost without weakening the required sensitivity and end-to-end checks. This is a target, not a measured runtime claim.

## Loopback socket probe

Temporary probe created under `/tmp`, run, then removed. The exact invocation and observed output were:

```sh
python /tmp/practice_loopback_probe.py; status=$?; rm -f /tmp/practice_loopback_probe.py; exit $status
```

```text
200 loopback-ok
```

Probe source (10 lines):

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen
from threading import Thread
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"loopback-ok")
    def log_message(self, *args): pass
server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
with urlopen(f"http://127.0.0.1:{server.server_port}/") as response: print(response.status, response.read().decode())
server.shutdown(); server.server_close()
```

The successful response confirms this environment permits a loopback `ThreadingHTTPServer` bound to port 0 and a `urllib` round trip.
