# I204 package exports and capability RED — parent recovery

Status: RED_READY.

The original I204 test introduced the five correct package-export requirements but incorrectly invented a package-root `get_capabilities` symbol. The sole correction worker read the file and then exhausted with HTTP 502 before writing. After its ownership cleared, parent replaced only that invalid capability path with the existing production v3 capability dispatcher.

Required package-root identities

- `AllStreetPostflopConfig`
- `AllStreetSolveResult`
- `create_allstreet_root`
- `solve_allstreet_postflop`
- `dispatch_v4`

Required capability path

`poker_solver.api_v3.dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}})` must retain existing features and add exactly:

    allstreet-postflop:
      status: implemented-bounded
      starting_street: flop
      continuation: automatic-natural-terminal
      interfaces: [typed, json-v4, cli-phase4]

The test also mutates the nested returned interface list, status, and top-level feature map, then requires a fresh dispatch to return the original data.

Parent RED command

    uv run pytest tests/test_phase4_s1_exports.py -q

Result: `6 failed in 0.24s`, expected exit 1. The five identity tests fail because package exports are absent. The capability test reaches the real v3 response and fails on missing `allstreet-postflop`. There are no syntax, collection, invented-function, or environment failures.

No production file was edited before this RED.
