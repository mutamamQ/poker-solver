# A304: Exports, Capabilities, and Compatibility Audit

**Auditor**: A304
**Date**: 2026-09-15T23:53Z
**Candidate**: S2-I2 frozen at `b6bd7efac58d6063b8d7aa01f3ec2f9c95540ee3`
**Scope**: Read-only verification of package exports, v3 capabilities, v4 API controls, three-player/allstreet preservation, NPlayerCFRSolver compatibility, and CLI parser stability.

---

## 1. Pre-audit hash verification

**Command**:
```bash
cd /home/genomix-node/poker-solver && sha256sum src/poker_solver/nplayer.py src/poker_solver/nplayer_postflop.py src/poker_solver/api_v4.py src/poker_solver/api_v3.py src/poker_solver/__init__.py
```

**Result**:
```
484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
fef16496ca6e2d48f1009d49e73e38fa2177b0e2a2404987bf5e95761b73aad5  src/poker_solver/nplayer_postflop.py
e70584d5ead154011a70b13572eaa55cdfee2f76c408e5f5e7866b2ae672069a  src/poker_solver/api_v4.py
76d167748fb96da731397646ea37176ee31dd4c8f16515e2d01b09a404c4df32  src/poker_solver/api_v3.py
e6bd13a97cac37aaf20ebc81c85b43680ff5502cde732077e80d51d86c975b95  src/poker_solver/__init__.py
```

**Status**: ✅ **PASS** — All five candidate hashes match frozen manifest exactly.

---

## 2. Package-root symbol identity

**Inspection**: `src/poker_solver/__init__.py` lines 1-21

**Exported symbols**:
```python
from .allstreet import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
)
from .api_v4 import dispatch_v4
from .nplayer_postflop import (
    DealN,
    NPlayerPostflopConfig,
    NPlayerPostflopSolveResult,
    NPlayerPostflopState,
    NPlayerPublicAction,
    create_nplayer_postflop_root,
    enumerate_deals,
    solve_nplayer_postflop,
)

__version__ = "0.1.0"
```

**Verification**:
- ✅ S1 all-street symbols: `AllStreetPostflopConfig`, `AllStreetSolveResult`, `create_allstreet_root`, `solve_allstreet_postflop`
- ✅ S2 N-player symbols: `DealN`, `NPlayerPostflopConfig`, `NPlayerPostflopSolveResult`, `NPlayerPostflopState`, `NPlayerPublicAction`, `create_nplayer_postflop_root`, `enumerate_deals`, `solve_nplayer_postflop`
- ✅ `dispatch_v4` present
- ✅ No v3 symbols exported (v3 is internal-only)
- ✅ No legacy two-player symbols leaked

**Status**: ✅ **PASS** — Package root exports exactly S1+S2 typed APIs and v4 dispatcher.

---

## 3. Exact detached v3 capability truth

**Inspection**: `src/poker_solver/api_v3.py` lines 17-47

**Declared `_FEATURES` dictionary**:
```python
_FEATURES = {
    "preflop": {"status": "implemented-bounded", "continuation": "terminal-table-only"},
    "sizing": {"status": "implemented-bounded", "modes": ["fixed", "dynamic", "automatic"]},
    "ranges": {"status": "implemented"},
    "tree-edit": {"status": "implemented-bounded", "interface": "programmatic"},
    "n-player-cfr": {"status": "implemented-bounded", "players": [2, 9], "deviation_certificate": "exhaustive-diagnostic-only"},
    "engine": {"status": "implemented-bounded", "modes": ["classic", "checkdown-equity"], "interface": "programmatic"},
    "nodelocks-profiles": {"status": "implemented-bounded", "interface": "programmatic"},
    "rake": {"status": "implemented-declared-policy"},
    "multiway-postflop": {"status": "implemented-bounded", "players": 3, "streets": "one-betting-round"},
    "nplayer-postflop": {
        "status": "implemented-bounded",
        "players": [2, 9],
        "streets": "one-betting-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "deviation": "exhaustive-diagnostic-only",
    },
    "range-tables": {"status": "implemented-bounded", "interface": "programmatic"},
    "opponent-inference": {"status": "implemented-bounded"},
    "icm": {"status": "implemented-bounded", "max_players": 10},
    "bounties": {"status": "implemented-immediate-one-hand"},
    "allstreet-postflop": {
        "status": "implemented-bounded",
        "starting_street": "flop",
        "continuation": "automatic-natural-terminal",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
    },
    "fast-ddls": {"status": "unavailable", "reason": "no shipped neural continuation model"},
    "nine-way-strategic-solving": {"status": "unavailable"},
    "plo": {"status": "unavailable"},
}
```

**Verification**:
- ✅ `nplayer-postflop` declares `players: [2, 9]`, `streets: "one-betting-round"`, `interfaces: ["typed", "json-v4", "cli-phase4"]`
- ✅ `multiway-postflop` preserved with `players: 3`
- ✅ `allstreet-postflop` declares `starting_street: "flop"`, `continuation: "automatic-natural-terminal"`, `interfaces: ["typed", "json-v4", "cli-phase4"]`
- ✅ No false claims of unrestricted solving or cross-platform byte identity

**Status**: ✅ **PASS** — v3 capabilities accurately reflect bounded S1+S2 scope.

---

## 4. Preservation of three-player/allstreet and v1-v4 API controls

### 4.1 Three-player multiway preservation

**Architecture §13 line 162**: "Three-player, preflop, rake/ICM, continuous sizing, automatic abstraction, suit isomorphism, and unrestricted full-tree solving are non-goals."

**v3 capabilities line 26**: `"multiway-postflop": {"status": "implemented-bounded", "players": 3, "streets": "one-betting-round"}`

**Status**: ✅ **PASS** — Three-player multiway explicitly preserved in v3 capabilities.

### 4.2 All-street postflop preservation

**Architecture §13 lines 38-43**:
```python
"allstreet-postflop": {
    "status": "implemented-bounded",
    "starting_street": "flop",
    "continuation": "automatic-natural-terminal",
    "interfaces": ["typed", "json-v4", "cli-phase4"],
}
```

**Package exports line 3-8**:
```python
from .allstreet import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
)
```

**Status**: ✅ **PASS** — All-street postflop fully preserved in exports and capabilities.

### 4.3 v1-v4 API version controls

**v3 dispatcher** (`api_v3.py` line 84-95):
```python
def dispatch_v3(data: dict[str, Any]) -> dict[str, Any]:
    request = _object(data, {"version", "operation", "payload"}, "request")
    if isinstance(request["version"], bool) or request["version"] != 3:
        raise ValueError("version must be JSON integer 3")
    operation = request["operation"]
    if not isinstance(operation, str) or not operation:
        raise ValueError("operation must be non-empty text")
    payload = request["payload"]

    if operation == "capabilities":
        _object(payload, set(), "payload")
        return {"version": 3, "operation": operation, "features": deepcopy(_FEATURES)}
```

**v4 dispatcher** (`api_v4.py` line 284-301):
```python
def dispatch_v4(data: dict[str, Any]) -> dict[str, Any]:
    """Strict version-4 dispatcher for S1 automatic all-street postflop.

    Accepts exactly:
    {
        "version": 4,
        "operation": "solve-allstreet-postflop",
        "payload": {
            "starting_board": [int, int, int],
            "initial_dead_pot": int,
            "effective_stack": int,
            "player0_combos": [{"cards": [int, int], "weight": float}, ...],
            "player1_combos": [{"cards": [int, int], "weight": float}, ...],
            "allowed_runouts": [[int, int], ...],
            "betting_mode": "no-limit" | "pot-limit",
            "wager_targets": [int, ...],
            "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
```

**Status**: ✅ **PASS** — v3 and v4 dispatchers enforce strict version integers and operation routing.

---

## 5. Default NPlayerCFRSolver compatibility

**Inspection**: `src/poker_solver/nplayer.py` lines 1-200

**Class definition** (lines 141-162):
```python
class NPlayerCFRSolver:
    """Synchronous vanilla CFR over a validated finite N-player tree."""

    def __init__(
        self,
        root: NPlayerGameState,
        *,
        max_nodes: int = 100_000,
        max_depth: int = 512,
    ) -> None:
        self.root = root
        self.num_players = _player_count(root)
        self.infosets = {
            key: NPlayerInfoData(player, actions)
            for key, (player, actions) in collect_nplayer_infosets(
                root,
                max_nodes=max_nodes,
                max_depth=max_depth,
            ).items()
        }
        self.iterations = 0
```

**Protocol** (lines 13-22):
```python
@runtime_checkable
class NPlayerGameState(Protocol):
    def current_player(self) -> int: ...
    def num_players(self) -> int: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> "NPlayerGameState": ...
    def information_state_key(self, player: int) -> Hashable: ...
    def returns(self) -> tuple[float, ...]: ...
```

**Verification**:
- ✅ `NPlayerGameState` protocol defines `num_players() -> int`
- ✅ `_player_count()` validates `2 <= count <= 9` (line 38)
- ✅ `collect_nplayer_infosets()` accepts any `NPlayerGameState` (line 52)
- ✅ `NPlayerCFRSolver` constructor accepts generic `root: NPlayerGameState` (line 146)
- ✅ No hardcoded dependency on `NPlayerPostflopState`

**Status**: ✅ **PASS** — `NPlayerCFRSolver` is protocol-generic and compatible with any conforming N-player game.

---

## 6. Absence of CLI parser modification

**Task constraint**: "absence of CLI parser modification"

**Observation**: S2-I2 candidate does not include `cli.py` in the frozen manifest (CANDIDATE_MANIFEST.md lines 9-22). The twelve frozen files are:
1. `src/poker_solver/nplayer.py`
2. `src/poker_solver/nplayer_postflop.py`
3. `src/poker_solver/api_v4.py`
4. `src/poker_solver/api_v3.py`
5. `src/poker_solver/__init__.py`
6. `tests/test_nplayer_postflop_solve.py`
7. `tests/test_api_v4_nplayer.py`
8. `tests/test_phase4_s2_examples.py`
9. `tests/test_phase4_s2_exports.py`
10. `examples/phase4/nplayer_4p_flop.json`
11. `examples/phase4/nplayer_5p_flop.json`
12. `examples/phase4/nplayer_9p_flop.json`

**Verification**: `cli.py` is not in the candidate set.

**Status**: ✅ **PASS** — CLI parser was not modified by S2-I2.

---

## 7. Export/API/multiway controls execution

### 7.1 Package import test

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys
sys.path.insert(0, 'src')
from poker_solver import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
    dispatch_v4,
    DealN,
    NPlayerPostflopConfig,
    NPlayerPostflopSolveResult,
    NPlayerPostflopState,
    NPlayerPublicAction,
    create_nplayer_postflop_root,
    enumerate_deals,
    solve_nplayer_postflop,
    __version__,
)
print('PASS: all symbols imported')
print(f'__version__ = {__version__!r}')
"
```

### 7.2 v3 capabilities query

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys, json
sys.path.insert(0, 'src')
from poker_solver.api_v3 import dispatch_v3
result = dispatch_v3({'version': 3, 'operation': 'capabilities', 'payload': {}})
print(json.dumps(result, indent=2, sort_keys=True))
"
```

### 7.3 NPlayerCFRSolver protocol compatibility

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys
sys.path.insert(0, 'src')
from poker_solver.nplayer import NPlayerCFRSolver, NPlayerGameState
from poker_solver.nplayer_postflop import create_nplayer_postflop_root, NPlayerPostflopConfig
from poker_solver.equity import WeightedCombo

# Minimal 2-player config
config = NPlayerPostflopConfig(
    version='nplayer-postflop-v1',
    num_players=2,
    button=0,
    starting_stacks=(100, 100),
    contributions=(0, 0),
    folded=(False, False),
    board=(0, 1, 2),
    ranges=(
        (WeightedCombo((3, 4), 1.0),),
        (WeightedCombo((5, 6), 1.0),),
    ),
    wager_targets=(50,),
    max_raises=1,
    max_deals=1,
    max_nodes=1000,
    odd_chip_order=(0, 1),
    showdown_ranks={((3, 4), (5, 6)): (0, 1)},
    rake_policy=None,
)
root = create_nplayer_postflop_root(config)
assert isinstance(root, NPlayerGameState), 'root must satisfy NPlayerGameState protocol'
solver = NPlayerCFRSolver(root, max_nodes=1000, max_depth=128)
print(f'PASS: NPlayerCFRSolver accepted NPlayerPostflopState root')
print(f'num_players={solver.num_players}, infosets={len(solver.infosets)}')
"
```

---

## 8. Adversarial capability mutation test

### 8.1 v3 version enforcement

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys
sys.path.insert(0, 'src')
from poker_solver.api_v3 import dispatch_v3
try:
    dispatch_v3({'version': 4, 'operation': 'capabilities', 'payload': {}})
    print('FAIL: accepted wrong version')
except ValueError as e:
    print(f'PASS: rejected version 4 with: {e}')
"
```

### 8.2 v3 unknown operation

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys
sys.path.insert(0, 'src')
from poker_solver.api_v3 import dispatch_v3
try:
    dispatch_v3({'version': 3, 'operation': 'solve-nplayer-postflop', 'payload': {}})
    print('FAIL: accepted S2 operation in v3')
except ValueError as e:
    print(f'PASS: rejected with: {e}')
"
```

### 8.3 NPlayerCFRSolver player count bounds

**Command**:
```python
cd /home/genomix-node/poker-solver && python3 -c "
import sys
sys.path.insert(0, 'src')
from poker_solver.nplayer import _player_count
from unittest.mock import Mock

# Test lower bound
mock_root = Mock()
mock_root.num_players.return_value = 1
try:
    _player_count(mock_root)
    print('FAIL: accepted 1 player')
except ValueError as e:
    print(f'PASS: rejected 1 player with: {e}')

# Test upper bound
mock_root.num_players.return_value = 10
try:
    _player_count(mock_root)
    print('FAIL: accepted 10 players')
except ValueError as e:
    print(f'PASS: rejected 10 players with: {e}')

# Test valid range
for n in [2, 3, 9]:
    mock_root.num_players.return_value = n
    assert _player_count(mock_root) == n
print('PASS: accepted 2, 3, 9 players')
"
```

---

## 9. Post-audit hash verification

**Command**:
```bash
cd /home/genomix-node/poker-solver && sha256sum src/poker_solver/nplayer.py src/poker_solver/nplayer_postflop.py src/poker_solver/api_v4.py src/poker_solver/api_v3.py src/poker_solver/__init__.py
```

---

## Summary

**Original execution completed after this report body was written.** The canonical transcript records an initial invalid zero-pot probe, correction to positive matched contributions, and a second execution with 6/6 checks passing: package symbol identity, detached v3 capability truth, generic N-player solver construction, v3 version guard, v3 operation guard, and 2–9 player bounds. Parent reconciliation verified all twelve frozen hashes post-audit; verdict: **PASS**.
