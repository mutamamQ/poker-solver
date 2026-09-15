"""Atomic structural tree-edit tests."""

from types import MappingProxyType

import pytest

from poker_solver.model import Action, TERMINAL
from poker_solver.tree_edit import (
    EditOperation,
    FiniteNode,
    FiniteTree,
    TreeEditError,
    apply_tree_edits,
)


A = Action("A")
B = Action("B")
C = Action("C")
X = Action("X")


def _terminal(node_id, value):
    return FiniteNode(node_id, TERMINAL, returns=(value, -value))


def _tree():
    return FiniteTree(
        "root",
        {
            "root": FiniteNode("root", 0, children=((A, "a"), (B, "b"))),
            "a": FiniteNode("a", 1, children=((X, "ax"),)),
            "ax": _terminal("ax", 1),
            "b": _terminal("b", 0),
        },
    )


def test_tree_is_immutable_reachable_and_deterministic():
    tree = _tree()
    assert tuple(tree.nodes) == ("root", "a", "ax", "b")
    assert isinstance(tree.nodes, MappingProxyType)
    with pytest.raises(TypeError):
        tree.nodes["x"] = _terminal("x", 0)  # type: ignore[index]


def test_add_action_subtree_is_atomic_and_invalidates_fresh_solver_state():
    tree = _tree()
    subtree = (_terminal("c", 2),)
    result = apply_tree_edits(tree, (EditOperation.add("root", C, "c", subtree),))
    assert result.tree.nodes["root"].children == ((A, "a"), (B, "b"), (C, "c"))
    assert tree.nodes["root"].children == ((A, "a"), (B, "b"))
    assert result.invalidation.requires_fresh_solver is True
    assert result.invalidation.ancestors == frozenset({"root"})
    assert result.invalidation.descendants == frozenset({"c"})
    assert result.invalidation.caches == frozenset({
        "root", "regrets", "average_policy", "iterations", "ev", "tables", "locks"
    })


def test_remove_action_removes_owned_descendants_and_marks_ancestors():
    result = apply_tree_edits(_tree(), (EditOperation.remove("root", A),))
    assert tuple(result.tree.nodes) == ("root", "b")
    assert result.tree.nodes["root"].children == ((B, "b"),)
    assert result.invalidation.descendants == frozenset({"a", "ax"})
    assert result.invalidation.ancestors == frozenset({"root"})


def test_replace_action_subtree_preserves_action_position():
    replacement = (
        FiniteNode("new", 1, children=((X, "new-x"),)),
        _terminal("new-x", 3),
    )
    result = apply_tree_edits(
        _tree(), (EditOperation.replace("root", A, "new", replacement),)
    )
    assert result.tree.nodes["root"].children == ((A, "new"), (B, "b"))
    assert "a" not in result.tree.nodes and "ax" not in result.tree.nodes
    assert result.invalidation.descendants == frozenset({"a", "ax", "new", "new-x"})


def test_multiple_edits_run_in_declared_order():
    operations = (
        EditOperation.add("root", C, "c", (_terminal("c", 2),)),
        EditOperation.remove("root", B),
    )
    result = apply_tree_edits(_tree(), operations)
    assert result.tree.nodes["root"].children == ((A, "a"), (C, "c"))


def test_failed_batch_leaves_original_unchanged():
    tree = _tree()
    operations = (
        EditOperation.add("root", C, "c", (_terminal("c", 2),)),
        EditOperation.remove("missing", A),
    )
    with pytest.raises(TreeEditError, match="missing"):
        apply_tree_edits(tree, operations)
    assert tuple(tree.nodes) == ("root", "a", "ax", "b")
    assert tree.nodes["root"].children == ((A, "a"), (B, "b"))


@pytest.mark.parametrize(
    "tree,match",
    [
        (lambda: FiniteTree("root", {"root": FiniteNode("root", 0, children=((A, "gone"),))}), "dangling"),
        (lambda: FiniteTree("root", {"root": FiniteNode("root", 0, children=((A, "root"),))}), "cycle"),
        (lambda: FiniteTree("root", {"root": _terminal("root", 0), "orphan": _terminal("orphan", 0)}), "unreachable"),
        (lambda: FiniteTree("root", {"root": FiniteNode("root", 0, children=((A, "a"), (A, "b"))), "a": _terminal("a", 0), "b": _terminal("b", 0)}), "duplicate"),
    ],
)
def test_tree_rejects_dangling_cycle_unreachable_and_duplicate_actions(tree, match):
    with pytest.raises((TreeEditError, ValueError), match=match):
        tree()


def test_edits_reject_unknown_nodes_actions_collisions_and_last_action():
    tree = _tree()
    with pytest.raises(TreeEditError, match="node"):
        apply_tree_edits(tree, (EditOperation.remove("missing", A),))
    with pytest.raises(TreeEditError, match="action"):
        apply_tree_edits(tree, (EditOperation.remove("root", X),))
    with pytest.raises(TreeEditError, match="already"):
        apply_tree_edits(tree, (EditOperation.add("root", A, "new", (_terminal("new", 0),)),))
    with pytest.raises(TreeEditError, match="last"):
        apply_tree_edits(tree, (EditOperation.remove("a", X),))
    with pytest.raises(TreeEditError, match="collides"):
        apply_tree_edits(tree, (EditOperation.add("root", C, "a", (_terminal("a", 0),)),))


def test_node_schema_rejects_bool_ids_bad_terminal_and_mutable_shapes():
    with pytest.raises((TypeError, ValueError)):
        FiniteNode(True, 0, children=((A, "x"),))
    with pytest.raises((TypeError, ValueError)):
        FiniteNode("x", True, children=((A, "y"),))
    with pytest.raises(ValueError, match="terminal"):
        FiniteNode("x", TERMINAL, children=((A, "y"),), returns=(0, 0))
    with pytest.raises(ValueError, match="returns"):
        FiniteNode("x", TERMINAL, returns=(True, 0))
