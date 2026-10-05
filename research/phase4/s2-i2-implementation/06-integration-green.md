# I206 integration GREEN — parent recovery

The original integration worker failed with schema HTTP 502 during its gated wait. Its single retry correctly refused the stale non-status heartbeat and ended before CORE_GREEN_READY. After both ownerships ended and parent published genuine core readiness, parent implemented the exclusive integration scope.

Delivered:
- strict direct v4 `solve-nplayer-postflop` parser/dispatcher with exact fields, arrays, deterministic showdowns list conversion, duplicate/malformed/bool/nonfinite/algorithm/seed/bound rejection, detached response, certificate and truthful metadata;
- exact v3 `nplayer-postflop` capability;
- additive package-root exports;
- canonical complete 4/5/9 direct-request examples through the unchanged generic CLI.

Verification UTC: `2026-09-15T23:52:05Z`
- four S2-I2 modules: `51 passed in 3.39s`
- relevant legacy API/CLI/export/N-player/multiway: `96 passed in 3.03s`
- full regression: `653 passed in 229.45s`
- `git diff --check`: pass
- `phase3-398-green` identity preserved.

Source/example SHA-256:
- api_v4.py `e70584d5ead154011a70b13572eaa55cdfee2f76c408e5f5e7866b2ae672069a`
- api_v3.py `76d167748fb96da731397646ea37176ee31dd4c8f16515e2d01b09a404c4df32`
- __init__.py `e6bd13a97cac37aaf20ebc81c85b43680ff5502cde732077e80d51d86c975b95`
- 4p example `a119e0b08ad53efe99180ccfa714c28455c37f8577e1140747007cbaa2f86a4a`
- 5p example `8bae730f59db4f95ac4c7d91554189a81ae23f7bcad648a294b471bd291c80c5`
- 9p example `81c8437a0bd3cf20ee28beddff70424e4b83ae9f6c29e28442915a0a16d25338`

INTEGRATION_GREEN_READY
