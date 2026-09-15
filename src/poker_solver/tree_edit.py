"""Immutable bounded finite trees and atomic structural edits."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from .model import Action, CHANCE, TERMINAL


class TreeEditError(ValueError):
    """Raised when a tree or atomic edit batch is invalid."""


def _node_id(value: object, label: str = "node id") -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class FiniteNode:
    node_id: str
    player: int
    children: tuple[tuple[Action, str], ...] = ()
    returns: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        _node_id(self.node_id)
        if isinstance(self.player, bool) or not isinstance(self.player, int):
            raise ValueError("player must be an integer")
        if not isinstance(self.children, tuple) or any(
            not isinstance(edge, tuple)
            or len(edge) != 2
            or not isinstance(edge[0], Action)
            or not isinstance(edge[1], str)
            or not edge[1]
            for edge in self.children
        ):
            raise ValueError("children must be an immutable tuple of Action/node-id edges")
        actions = tuple(action for action, _ in self.children)
        if len(set(actions)) != len(actions):
            raise TreeEditError("duplicate actions at node")
        if self.player == TERMINAL:
            if self.children:
                raise ValueError("terminal node cannot have children")
            if len(self.returns) < 2:
                raise ValueError("terminal returns must contain at least two values")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                for value in self.returns
            ):
                raise ValueError("terminal returns must be finite numbers")
        else:
            if self.player < CHANCE:
                raise ValueError("invalid player identifier")
            if not self.children:
                raise ValueError("non-terminal node must have children")
            if self.returns:
                raise ValueError("non-terminal node cannot have returns")


@dataclass(frozen=True, slots=True)
class FiniteTree:
    root_id: str
    nodes: Mapping[str, FiniteNode]

    def __post_init__(self) -> None:
        _node_id(self.root_id, "root id")
        if not isinstance(self.nodes, Mapping) or not self.nodes:
            raise TreeEditError("tree nodes must be a non-empty mapping")
        copied = dict(self.nodes)
        if self.root_id not in copied:
            raise TreeEditError("root node is missing")
        for key, node in copied.items():
            _node_id(key)
            if not isinstance(node, FiniteNode) or node.node_id != key:
                raise TreeEditError("node mapping key must equal stable node identity")
        parent_count = {node_id: 0 for node_id in copied}
        for node in copied.values():
            for _, child_id in node.children:
                if child_id not in copied:
                    raise TreeEditError(f"dangling child {child_id!r}")
                parent_count[child_id] += 1
        if parent_count[self.root_id] != 0:
            raise TreeEditError("cycle reaches the root")
        if any(
            count == 0 for node_id, count in parent_count.items() if node_id != self.root_id
        ):
            raise TreeEditError("unreachable nodes are not allowed")
        if any(
            count > 1 for node_id, count in parent_count.items() if node_id != self.root_id
        ):
            raise TreeEditError("finite structure must have one parent per non-root node")
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(node_id: str) -> None:
            if node_id in visiting:
                raise TreeEditError("cycle detected")
            if node_id in visited:
                return
            visiting.add(node_id)
            for _, child_id in copied[node_id].children:
                walk(child_id)
            visiting.remove(node_id)
            visited.add(node_id)

        walk(self.root_id)
        if visited != set(copied):
            raise TreeEditError("unreachable nodes are not allowed")
        object.__setattr__(self, "nodes", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class EditOperation:
    kind: str
    node_id: str
    action: Action
    child_id: str | None = None
    subtree: tuple[FiniteNode, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {"add", "remove", "replace"}:
            raise TreeEditError("unknown edit operation")
        _node_id(self.node_id)
        if not isinstance(self.action, Action):
            raise TreeEditError("edit action must be an Action")
        if self.kind == "remove":
            if self.child_id is not None or self.subtree:
                raise TreeEditError("remove cannot provide a subtree")
        else:
            _node_id(self.child_id, "child id")
            if not isinstance(self.subtree, tuple) or not self.subtree:
                raise TreeEditError("add/replace requires a non-empty immutable subtree")
            if any(not isinstance(node, FiniteNode) for node in self.subtree):
                raise TreeEditError("subtree must contain FiniteNode values")

    @classmethod
    def add(
        cls, node_id: str, action: Action, child_id: str,
        subtree: tuple[FiniteNode, ...],
    ) -> "EditOperation":
        return cls("add", node_id, action, child_id, subtree)

    @classmethod
    def remove(cls, node_id: str, action: Action) -> "EditOperation":
        return cls("remove", node_id, action)

    @classmethod
    def replace(
        cls, node_id: str, action: Action, child_id: str,
        subtree: tuple[FiniteNode, ...],
    ) -> "EditOperation":
        return cls("replace", node_id, action, child_id, subtree)


@dataclass(frozen=True, slots=True)
class InvalidationMetadata:
    ancestors: frozenset[str]
    descendants: frozenset[str]
    caches: frozenset[str]
    requires_fresh_solver: bool = True


@dataclass(frozen=True, slots=True)
class TreeEditResult:
    tree: FiniteTree
    invalidation: InvalidationMetadata


_ALL_CACHES = frozenset({
    "root", "regrets", "average_policy", "iterations", "ev", "tables", "locks"
})


def _descendants(nodes: Mapping[str, FiniteNode], root_id: str) -> set[str]:
    result: set[str] = set()
    pending = [root_id]
    while pending:
        node_id = pending.pop()
        if node_id in result:
            continue
        result.add(node_id)
        pending.extend(child for _, child in nodes[node_id].children)
    return result


def _ancestors(nodes: Mapping[str, FiniteNode], node_id: str) -> set[str]:
    parents = {
        child: parent.node_id
        for parent in nodes.values()
        for _, child in parent.children
    }
    result = {node_id}
    while node_id in parents:
        node_id = parents[node_id]
        result.add(node_id)
    return result


def _validated_subtree(operation: EditOperation) -> dict[str, FiniteNode]:
    subtree = {node.node_id: node for node in operation.subtree}
    if len(subtree) != len(operation.subtree):
        raise TreeEditError("duplicate subtree node identities")
    assert operation.child_id is not None
    if operation.child_id not in subtree:
        raise TreeEditError("subtree does not contain declared child root")
    FiniteTree(operation.child_id, subtree)
    return subtree


def apply_tree_edits(
    tree: FiniteTree,
    operations: tuple[EditOperation, ...],
) -> TreeEditResult:
    """Apply ordered structural edits atomically and invalidate all solver state."""
    if not isinstance(tree, FiniteTree):
        raise TypeError("tree must be a FiniteTree")
    if not isinstance(operations, tuple) or not operations:
        raise TreeEditError("operations must be a non-empty immutable tuple")
    if any(not isinstance(operation, EditOperation) for operation in operations):
        raise TreeEditError("operations must contain EditOperation values")
    nodes = dict(tree.nodes)
    all_ancestors: set[str] = set()
    all_descendants: set[str] = set()

    for operation in operations:
        if operation.node_id not in nodes:
            raise TreeEditError(f"node {operation.node_id!r} does not exist")
        parent = nodes[operation.node_id]
        if parent.player in {TERMINAL, CHANCE}:
            raise TreeEditError("edit target must be a decision node")
        matches = [index for index, (action, _) in enumerate(parent.children) if action == operation.action]
        all_ancestors.update(_ancestors(nodes, operation.node_id))

        if operation.kind == "add":
            if matches:
                raise TreeEditError("action already exists")
            subtree = _validated_subtree(operation)
            collision = set(subtree) & set(nodes)
            if collision:
                raise TreeEditError(f"subtree identity collides with existing nodes: {sorted(collision)!r}")
            nodes.update(subtree)
            assert operation.child_id is not None
            nodes[operation.node_id] = FiniteNode(
                parent.node_id, parent.player,
                parent.children + ((operation.action, operation.child_id),),
            )
            all_descendants.update(subtree)
        elif operation.kind == "remove":
            if not matches:
                raise TreeEditError("action does not exist")
            if len(parent.children) == 1:
                raise TreeEditError("cannot remove the last action")
            index = matches[0]
            old_root = parent.children[index][1]
            removed = _descendants(nodes, old_root)
            nodes[operation.node_id] = FiniteNode(
                parent.node_id, parent.player,
                parent.children[:index] + parent.children[index + 1:],
            )
            for node_id in removed:
                del nodes[node_id]
            all_descendants.update(removed)
        else:
            if not matches:
                raise TreeEditError("action does not exist")
            index = matches[0]
            old_root = parent.children[index][1]
            removed = _descendants(nodes, old_root)
            subtree = _validated_subtree(operation)
            collision = set(subtree) & (set(nodes) - removed)
            if collision:
                raise TreeEditError(f"subtree identity collides with existing nodes: {sorted(collision)!r}")
            for node_id in removed:
                del nodes[node_id]
            nodes.update(subtree)
            assert operation.child_id is not None
            replacement_children = list(parent.children)
            replacement_children[index] = (operation.action, operation.child_id)
            nodes[operation.node_id] = FiniteNode(
                parent.node_id, parent.player, tuple(replacement_children)
            )
            all_descendants.update(removed | set(subtree))
        FiniteTree(tree.root_id, nodes)

    edited = FiniteTree(tree.root_id, nodes)
    return TreeEditResult(
        edited,
        InvalidationMetadata(
            ancestors=frozenset(all_ancestors),
            descendants=frozenset(all_descendants),
            caches=_ALL_CACHES,
        ),
    )
