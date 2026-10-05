"""Bounded two-player composite-tree preflight validation."""

from __future__ import annotations

from dataclasses import dataclass

from .model import GameState, TERMINAL, CHANCE


@dataclass(frozen=True, slots=True)
class BoundedTreeStats:
    """Immutable statistics from bounded tree validation."""
    node_count: int
    max_depth_reached: int
    terminal_count: int
    chance_count: int
    decision_count: int


def validate_bounded_tree(
    root: GameState,
    *,
    max_nodes: int,
    max_depth: int,
) -> BoundedTreeStats:
    """Exhaustively validate a two-player GameState tree with finite bounds.
    
    Validates:
    - Finite depth/node bounds before Python RecursionError
    - Cycle detection via identity
    - Actor values (TERMINAL, CHANCE, 0, 1)
    - Chance uniqueness/probabilities/mass
    - Legal-action uniqueness/nonempty
    - Deterministic action signatures per infoset
    - Finite exactly-two zero-sum terminal utilities
    - Strict bool rejection
    
    Raises ValueError with stable boundary messages on any violation.
    Returns BoundedTreeStats on success; no partial result.
    """
    # Validate bounds
    if not isinstance(max_nodes, int) or isinstance(max_nodes, bool) or max_nodes <= 0:
        raise ValueError("max_nodes must be a positive integer")
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth <= 0:
        raise ValueError("max_depth must be a positive integer")
    
    visited = set()
    infoset_signatures = {}  # infoset_key -> (player, frozenset(actions))
    
    node_count = 0
    terminal_count = 0
    chance_count = 0
    decision_count = 0
    max_depth_reached = 0
    
    def traverse(state: GameState, depth: int) -> None:
        nonlocal node_count, terminal_count, chance_count, decision_count, max_depth_reached
        
        # Check depth bound
        if depth > max_depth:
            raise ValueError(f"max_depth {max_depth} exceeded")
        
        # Check node count bound
        if node_count >= max_nodes:
            raise ValueError(f"max_nodes {max_nodes} exceeded")
        
        # Cycle detection
        state_id = id(state)
        if state_id in visited:
            raise ValueError("cycle detected")
        visited.add(state_id)
        
        node_count += 1
        max_depth_reached = max(max_depth_reached, depth)
        
        # Get actor
        try:
            actor = state.current_player()
        except Exception as e:
            raise ValueError(f"current_player() failed: {e}")
        
        # Validate actor type and value
        if isinstance(actor, bool) or not isinstance(actor, int):
            raise ValueError(f"actor must be int, got {type(actor).__name__}")
        if actor not in (TERMINAL, CHANCE, 0, 1):
            raise ValueError(f"actor must be TERMINAL, CHANCE, 0, or 1, got {actor}")
        
        if actor == TERMINAL:
            terminal_count += 1
            
            # Validate terminal has no actions
            try:
                legal = state.legal_actions()
            except Exception as e:
                raise ValueError(f"legal_actions() failed: {e}") from e
            if legal:
                raise ValueError("terminal node must have no legal actions")
            try:
                chance = state.chance_outcomes()
            except Exception as e:
                raise ValueError(f"chance_outcomes() failed: {e}") from e
            if chance:
                raise ValueError("terminal node must have no chance outcomes")
            
            # Validate returns
            try:
                returns = state.returns()
            except Exception as e:
                raise ValueError(f"returns() failed: {e}")
            
            if not isinstance(returns, tuple) or len(returns) != 2:
                raise ValueError("returns must be tuple of exactly two values")
            
            for i, val in enumerate(returns):
                if isinstance(val, bool):
                    raise ValueError(f"returns[{i}] must not be bool")
                if not isinstance(val, (int, float)):
                    raise ValueError(f"returns[{i}] must be numeric")
                if not (-float('inf') < val < float('inf')):
                    raise ValueError(f"returns[{i}] must be finite")
            
            # Validate zero-sum
            total = sum(returns)
            if abs(total) > 1e-9:
                raise ValueError(f"returns must sum to zero, got {total}")
        
        elif actor == CHANCE:
            chance_count += 1
            
            # Existing game implementations expose chance actions through
            # legal_actions(); when present they must match chance_outcomes().
            try:
                legal = state.legal_actions()
            except Exception as e:
                raise ValueError(f"legal_actions() failed: {e}") from e
            
            # Validate chance outcomes
            try:
                outcomes = state.chance_outcomes()
            except Exception as e:
                raise ValueError(f"chance_outcomes() failed: {e}")
            
            if not outcomes:
                raise ValueError("chance node must have nonempty outcomes")
            
            seen_actions = set()
            prob_sum = 0.0
            
            for outcome in outcomes:
                if not isinstance(outcome, tuple) or len(outcome) != 2:
                    raise ValueError("chance outcome must be (Action, probability) tuple")
                
                action, prob = outcome
                
                # Check action uniqueness
                if action in seen_actions:
                    raise ValueError(f"duplicate chance action {action}")
                seen_actions.add(action)
                
                # Validate probability
                if isinstance(prob, bool):
                    raise ValueError("chance probability must not be bool")
                if not isinstance(prob, (int, float)):
                    raise ValueError("chance probability must be numeric")
                if not (0 <= prob <= 1):
                    raise ValueError(f"chance probability must be in [0,1], got {prob}")
                if not (-float('inf') < prob < float('inf')):
                    raise ValueError("chance probability must be finite")
                
                prob_sum += prob
            
            if legal and (len(set(legal)) != len(legal) or set(legal) != seen_actions):
                raise ValueError("chance legal actions must match chance outcomes")
            
            # Validate probability mass sums to 1
            if abs(prob_sum - 1.0) > 1e-9:
                raise ValueError(f"chance probabilities must sum to 1, got {prob_sum}")
            
            # Traverse children
            for action, _ in outcomes:
                try:
                    child = state.child(action)
                except Exception as e:
                    raise ValueError(f"child({action}) failed: {e}")
                traverse(child, depth + 1)
        
        else:  # Decision node (actor in {0, 1})
            decision_count += 1
            
            # Validate decision has no chance outcomes
            try:
                chance = state.chance_outcomes()
            except Exception as e:
                raise ValueError(f"chance_outcomes() failed: {e}") from e
            if chance:
                raise ValueError("decision node must have no chance outcomes")
            
            # Validate legal actions
            try:
                legal = state.legal_actions()
            except Exception as e:
                raise ValueError(f"legal_actions() failed: {e}")
            
            if not legal:
                raise ValueError("decision node must have nonempty legal actions")
            
            # Check action uniqueness
            seen_actions = set()
            for action in legal:
                if action in seen_actions:
                    raise ValueError(f"duplicate legal action {action}")
                seen_actions.add(action)
            
            # Validate infoset signature consistency
            try:
                infoset_key = state.information_state_key(actor)
            except Exception as e:
                raise ValueError(f"information_state_key({actor}) failed: {e}")
            
            action_set = frozenset(legal)
            if infoset_key in infoset_signatures:
                prev_actor, prev_actions = infoset_signatures[infoset_key]
                if prev_actor != actor:
                    raise ValueError(f"infoset {infoset_key} has inconsistent actor")
                if prev_actions != action_set:
                    raise ValueError(f"infoset {infoset_key} has inconsistent action signature")
            else:
                infoset_signatures[infoset_key] = (actor, action_set)
            
            # Traverse children
            for action in legal:
                try:
                    child = state.child(action)
                except Exception as e:
                    raise ValueError(f"child({action}) failed: {e}")
                traverse(child, depth + 1)
        
        visited.remove(state_id)
    
    traverse(root, 0)
    
    return BoundedTreeStats(
        node_count=node_count,
        max_depth_reached=max_depth_reached,
        terminal_count=terminal_count,
        chance_count=chance_count,
        decision_count=decision_count,
    )