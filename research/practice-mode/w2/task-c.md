# W2 task-c — server integration, hardening, live UI e2e, smoke script

## Files
- `src/poker_solver/practice/server.py` (extended)
- `tests/test_practice_ui.py` (new, 17 tests)
- `scripts/practice_smoke.sh` (new, executable)

## Server changes
- `DEFAULT_WEB_DIR` already resolved to `<repo>/web` (`parents[3]`); kept, asserted by tests. Static allow-list unchanged (`/`, `/index.html`, `/app.js`, `/style.css`).
- `GET|HEAD /favicon.ico` -> 204, empty body, `Cache-Control: max-age=86400`, security headers. Added to `KNOWN_PATHS` so POST/PUT get 405 (not 404).
- Static responses now send `STATIC_SECURITY_HEADERS`: `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'`, plus `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` (cheap extra hardening). JSON responses keep nosniff + no-store and no CSP (not documents).
- Startup banner `Practice server on http://HOST:PORT/` (flush=True) was already in `serve()`; now covered by a subprocess test.

## Decisions
- Security-header test uses a throwaway web dir so it never skips; a second test checks headers on the real index (skips only without `web/index.html`).
- Static tests skip per-file (`index.html`, `app.js`, `style.css`) only if that file is missing. All API/e2e tests never skip.
- Extra CSP-compatibility checks (index has no inline `<script>` bodies, `on*=` handlers, `style=` attrs or `<style>`; app.js has no `setAttribute('style')`, no `style=` in HTML strings, no eval/new Function). Rationale: with `style-src 'self'` those would be silently blocked by the browser. CSSOM (`el.style.width = ...`) is allowed by CSP and is what the contract's mix-bar width needs.
- R1 grep: probability literals, EV/Q literals (`ev`, `ev_loss*`, `chosen_q`, `best_q`, `worst_q`), grade literal assignments (all 5 grades), quoted `kuhn-intro/` / `river-*/` prefixes, full spot_ids, 64-hex hashes. Bare `score:` was deliberately NOT banned (too likely in legit default/zero-state code).
- Hero-hand match in range_strategy is order-insensitive (`6d7d` vs `["6d","7d"]`); Kuhn uses the single rank.
- e2e also asserts submit re-solves deterministically (same params_hash/strategy as the solve call), optimal ev_loss ≈ 0, other action ev_loss ≥ optimal.
- R1 iteration test (5 vs 300) runs for both a Kuhn and a river spot; checks params_hash, strategy and range_strategy all differ.
- Smoke script default port 7787, uses `.venv/bin/python` (override via `PYTHON`), waits for the banner, checks health, favicon, list, solve (iterations 40), submit (optimal action), and `/` if web/ exists; exits 0/1.

## Verification
- `pytest -q tests/test_practice_api.py tests/test_practice_ui.py`: 54 passed (web/ files from workers a/b were present, so 0 skips).
- `scripts/practice_smoke.sh 7791`: SMOKE PASS (7 checks).
- Full suite `pytest -q`: 1007 passed (990 + 17 new) in 256 s.

## Findings for parent
- Current `web/index.html` + `web/app.js` + `web/style.css` pass all contract checks: all 25 IDs present, no duplicates, assets linked, viewport meta present, no inline script/style (CSP-safe), the three operations and `/api/v4` referenced, and no R1 hits. No contract violations found at test time.
- These files were still being written in parallel, so later edits could regress; `tests/test_practice_ui.py` will catch that.
