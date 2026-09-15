# Resource-bounds audit

**Manifest identity**: `research/phase4/s1-i1-audit/CANDIDATE_MANIFEST.md` frozen 2026-09-15T15:53:19Z, base commit `7a817e618a3c0898b531e88440b490323c62b49b`

**Artifact hashes**:
- `src/poker_solver/bounded_tree.py`: `52590d6bbadde602b6698ca7f5204851ed99b113dfee26e738cd85af67122afc`
- `src/poker_solver/allstreet.py`: `2d93dc2983fb4ec9bc499b2d025a109c34ae8437301c748d0be708a4e6b4f4d7`
- `src/poker_solver/multistreet.py`: `00b95824979bb894321dbb491746b9a97bf891b4682b6f1a5e58b70ab3fabebc`
- `tests/test_bounded_tree.py`: `e9ee79e85cf23499df6509e185f1345eacc22c1a54ecea593af10a7278cc85ea`

---

## Evidence

### 1. max_nodes enforcement

**Source**: `src/poker_solver/bounded_tree.py:42-45, 64-65`
```python
if not isinstance(max_nodes, int) or isinstance(max_nodes, bool) or max_nodes <= 0:
    raise ValueError("max_nodes must be a positive integer")

if node_count >= max_nodes:
    raise ValueError(f"max_nodes {max_nodes} exceeded")
```

**Test coverage**: `tests/test_bounded_tree.py:40-51, 532-536`
- Rejects `max_nodes=0`, `max_nodes=-1`, `max_nodes=True`
- Enforces bound during traversal with `WideTree(10)` vs `max_nodes=5`

**Runtime probe**:
```
PASS: max_nodes=0 rejected: max_nodes must be a positive integer
```

### 2. max_depth enforcement

**Source**: `src/poker_solver/bounded_tree.py:44-45, 60-61`
```python
if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth <= 0:
    raise ValueError("max_depth must be a positive integer")

if depth > max_depth:
    raise ValueError(f"max_depth {max_depth} exceeded")
```

**Test coverage**: `tests/test_bounded_tree.py:54-65, 505-509`
- Rejects `max_depth=0`, `max_depth=-1`, `max_depth=True`
- Enforces bound during traversal with `DeepTree(10)` vs `max_depth=5`

**Runtime probe**:
```
PASS: max_depth=0 rejected: max_depth must be a positive integer
```

### 3. Cycle detection

**Source**: `src/poker_solver/bounded_tree.py:67-71, 224`
```python
state_id = id(state)
if state_id in visited:
    raise ValueError("cycle detected")
visited.add(state_id)
# ... traversal ...
visited.remove(state_id)  # backtrack cleanup
```

**Test coverage**: `tests/test_bounded_tree.py:540-564`
- `CyclicTree` with `child(action) -> self` triggers cycle detection

**Runtime probe**:
```
PASS: cycle detected: cycle detected
```

### 4. Preflight invocation before training

**Source**: `src/poker_solver/allstreet.py:202-208`
```python
# Create root and validate bounded tree
root = create_allstreet_root(config)
stats = validate_bounded_tree(
    root,
    max_nodes=config.max_nodes,
    max_depth=config.max_depth,
)

# Train with appropriate algorithm
if algorithm == "vanilla-cfr":
    solver = CFRSolver(root)
```

**Evidence**: `validate_bounded_tree` called with `config.max_nodes` and `config.max_depth` before `CFRSolver(root)` or `MCCFRSolver(root, seed)` instantiation (lines 211-216).

**Config defaults**: `src/poker_solver/allstreet.py:31-32`
```python
max_nodes: int = 100_000
max_depth: int = 512
```

---

## Findings

1. **max_nodes bound**: Validated as positive integer at entry; enforced before each node expansion; tested with boundary rejection and traversal overflow.

2. **max_depth bound**: Validated as positive integer at entry; enforced before recursion; tested with boundary rejection and deep-tree overflow.

3. **Cycle detection**: Identity-based visited set with backtrack cleanup; tested with self-referential child.

4. **Preflight guarantee**: `solve_allstreet_postflop` invokes `validate_bounded_tree` with config bounds before solver instantiation; no code path bypasses validation.

---

## Verdict

**PASS**: Resource bounds are validated at entry, enforced during traversal, covered by RED/GREEN tests, and invoked as mandatory preflight before training. No RecursionError or unbounded-loop risk remains in the actual-tree path.