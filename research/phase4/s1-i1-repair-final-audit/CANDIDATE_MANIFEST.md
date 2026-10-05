# S1-I1 repaired candidate manifest

Frozen UTC: 2026-09-15T18:43:25Z
Base HEAD at freeze: `7a817e6`
Parent focused gate: `uv run pytest tests/test_allstreet_config.py tests/test_bounded_tree.py tests/test_api_v4.py -q` -> 116 passed in 2.31s
Parent full gate: `uv run pytest -q` -> 531 passed in 199.21s
Baseline tag present: `phase3-398-green`

Reviewers must verify every hash before testing and must not edit candidate source/tests.

```text
30d94c226a82375afa2a10f4e3c3b785e37009257023b65da296742bf7cbd1ea  src/poker_solver/allstreet.py
a695b0a91831f5764681caa8d3c461c29c8d9e663357f6796301a8c68c4a2047  src/poker_solver/api_v4.py
c221d77dffed3866b497acdef2ea039e93cd5b10e9ce387f1b6f0537df9b91f9  src/poker_solver/bounded_tree.py
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
a2765f7a3a6c538b38ea9d0c3471c4aade00e7c0db4ba0dda300eeb250437de4  tests/test_allstreet_config.py
b632e5d72c19679e591a1ef1e743af08c3ea50772c0712441d0703d925cd63da  tests/test_allstreet_state.py
fa1ec90e10dd11c44c730472f8502b797ed0eb0ef59d9c8e8d1994f72053540f  tests/test_api_v4.py
ed7184c00939dd8a847d7655f5cb60a1d696f1aacb3d143d3f3d286a6139936e  tests/test_bounded_tree.py
```
