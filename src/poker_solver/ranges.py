"""Weighted Hold'em range editor and library.

Phase 3 Tier-1 module: strict 169-class parsing, explicit sorted combos,
finite weights [0,1], atomic operations, deterministic export/import.
"""

from typing import Dict, Tuple
from poker_solver.cards import parse_card, format_card, RANKS


class RangeEditor:
    """Immutable weighted range editor.
    
    Canonical representation: ordered map from sorted two-card combo to weight [0,1].
    Supports all 1,326 Hold'em combos and strict 169-class token expansion.
    """

    def __init__(self, combos: Dict[Tuple[int, int], float] = None):
        """Initialize with optional combo->weight mapping."""
        self._combos = dict(combos) if combos else {}
        # Validate all weights
        for combo, weight in self._combos.items():
            self._validate_combo(combo)
            self._validate_weight(weight)

    def combos(self) -> Dict[Tuple[int, int], float]:
        """Return canonical combo->weight mapping."""
        return dict(self._combos)

    def add(self, token: str, weight: float = 1.0) -> 'RangeEditor':
        """Add token with weight. All expanded combos must be absent.
        
        Args:
            token: Class token (AA, AKs, AKo) or explicit combo (AsKd)
            weight: Finite weight in [0,1], default 1.0
            
        Returns:
            New RangeEditor with added combos
            
        Raises:
            ValueError: If any expanded combo already exists or weight invalid
        """
        self._validate_weight(weight)
        expanded = self._expand_token(token)
        
        # Check for duplicates/overlap - atomic rejection
        for combo in expanded:
            if combo in self._combos:
                raise ValueError(f"combo {self._format_combo(combo)} already exists")
        
        # All clear - create new editor
        new_combos = dict(self._combos)
        for combo in expanded:
            new_combos[combo] = weight
        
        return RangeEditor(new_combos)

    def set_weight(self, token: str, weight: float) -> 'RangeEditor':
        """Set weight for token. All expanded combos must exist.
        
        Args:
            token: Class token or explicit combo
            weight: New finite weight in [0,1]
            
        Returns:
            New RangeEditor with updated weights
            
        Raises:
            ValueError: If any expanded combo doesn't exist or weight invalid
        """
        self._validate_weight(weight)
        expanded = self._expand_token(token)
        
        # Check all combos exist - atomic requirement
        for combo in expanded:
            if combo not in self._combos:
                raise ValueError(f"combo {self._format_combo(combo)} not in range")
        
        # All exist - create new editor
        new_combos = dict(self._combos)
        for combo in expanded:
            new_combos[combo] = weight
        
        return RangeEditor(new_combos)

    def remove(self, token: str) -> 'RangeEditor':
        """Remove token. All expanded combos must exist.
        
        Args:
            token: Class token or explicit combo
            
        Returns:
            New RangeEditor without removed combos
            
        Raises:
            ValueError: If any expanded combo doesn't exist
        """
        expanded = self._expand_token(token)
        
        # Check all combos exist - atomic requirement
        for combo in expanded:
            if combo not in self._combos:
                raise ValueError(f"combo {self._format_combo(combo)} not in range")
        
        # All exist - create new editor
        new_combos = dict(self._combos)
        for combo in expanded:
            del new_combos[combo]
        
        return RangeEditor(new_combos)

    def include_or_replace(self, token: str, weight: float = 1.0) -> 'RangeEditor':
        """Atomically add or replace every combo expanded from ``token``."""
        self._validate_weight(weight)
        new_combos = dict(self._combos)
        for combo in self._expand_token(token):
            new_combos[combo] = weight
        return RangeEditor(new_combos)

    def blocked(self, dead_cards: list[int]) -> 'RangeEditor':
        """Return a new editor with every dead-card combo removed."""
        if not isinstance(dead_cards, list):
            raise ValueError("dead_cards must be a list")
        dead: set[int] = set()
        for card in dead_cards:
            if isinstance(card, bool) or not isinstance(card, int) or not 0 <= card < 52:
                raise ValueError("dead cards must be card integers")
            if card in dead:
                raise ValueError("dead cards must be unique")
            dead.add(card)
        return RangeEditor(
            {combo: weight for combo, weight in self._combos.items() if not dead.intersection(combo)}
        )

    def _expand_token(self, token: str) -> list[Tuple[int, int]]:
        """Expand class token or explicit combo to canonical sorted combos.
        
        Returns:
            List of (card1, card2) tuples where card1 <= card2
        """
        if not isinstance(token, str):
            raise ValueError(f"token must be string, got {type(token).__name__}")
        
        token = token.strip()
        
        # Try explicit combo first: two cards like AsKd
        if len(token) == 4:
            try:
                c1 = parse_card(token[:2])
                c2 = parse_card(token[2:])
                if c1 == c2:
                    raise ValueError(f"explicit combo cannot have duplicate cards: {token}")
                return [self._canonical_combo(c1, c2)]
            except ValueError:
                pass  # Not a valid explicit combo, try class
        
        # Try class token: AA, AKs, AKo
        if len(token) in (2, 3):
            return self._expand_class(token)
        
        raise ValueError(f"invalid token: {token!r}")

    def _expand_class(self, token: str) -> list[Tuple[int, int]]:
        """Expand 169-class token to combos.
        
        Args:
            token: AA (pair), AKs (suited), AKo (offsuit)
            
        Returns:
            List of canonical combos
        """
        if len(token) == 2:
            # Pair: AA through 22
            if token[0] != token[1] or token[0] not in RANKS:
                raise ValueError(f"invalid pair class: {token!r}")
            return self._expand_pair(token[0])
        
        elif len(token) == 3:
            # Suited or offsuit: AKs, AKo
            r1, r2, suffix = token[0], token[1], token[2]
            
            if r1 not in RANKS or r2 not in RANKS:
                raise ValueError(f"invalid ranks in class: {token!r}")
            
            if r1 == r2:
                raise ValueError(f"pair class must be 2 chars, not {token!r}")
            
            # Ranks must be descending
            if RANKS.index(r1) < RANKS.index(r2):
                raise ValueError(f"ranks must be descending: {token!r}")
            
            if suffix == 's':
                return self._expand_suited(r1, r2)
            elif suffix == 'o':
                return self._expand_offsuit(r1, r2)
            else:
                raise ValueError(f"suffix must be 's' or 'o', got {suffix!r}")
        
        raise ValueError(f"invalid class token: {token!r}")

    def _expand_pair(self, rank: str) -> list[Tuple[int, int]]:
        """Expand pair to 6 suit combinations."""
        rank_idx = RANKS.index(rank)
        combos = []
        suits = 'cdhs'
        
        for i in range(4):
            for j in range(i + 1, 4):
                c1 = rank_idx * 4 + i
                c2 = rank_idx * 4 + j
                combos.append(self._canonical_combo(c1, c2))
        
        return combos

    def _expand_suited(self, rank1: str, rank2: str) -> list[Tuple[int, int]]:
        """Expand suited class to 4 combinations."""
        r1_idx = RANKS.index(rank1)
        r2_idx = RANKS.index(rank2)
        combos = []
        
        for suit in range(4):
            c1 = r1_idx * 4 + suit
            c2 = r2_idx * 4 + suit
            combos.append(self._canonical_combo(c1, c2))
        
        return combos

    def _expand_offsuit(self, rank1: str, rank2: str) -> list[Tuple[int, int]]:
        """Expand offsuit class to 12 combinations."""
        r1_idx = RANKS.index(rank1)
        r2_idx = RANKS.index(rank2)
        combos = []
        
        for s1 in range(4):
            for s2 in range(4):
                if s1 != s2:
                    c1 = r1_idx * 4 + s1
                    c2 = r2_idx * 4 + s2
                    combos.append(self._canonical_combo(c1, c2))
        
        return combos

    def _canonical_combo(self, c1: int, c2: int) -> Tuple[int, int]:
        """Return sorted canonical combo tuple."""
        return (c1, c2) if c1 <= c2 else (c2, c1)

    def _format_combo(self, combo: Tuple[int, int]) -> str:
        """Format combo as text."""
        return format_card(combo[0]) + format_card(combo[1])

    def _validate_combo(self, combo: Tuple[int, int]) -> None:
        """Validate combo tuple."""
        if not isinstance(combo, tuple) or len(combo) != 2:
            raise ValueError(f"combo must be 2-tuple, got {combo!r}")
        
        c1, c2 = combo
        if not isinstance(c1, int) or not isinstance(c2, int):
            raise ValueError(f"combo cards must be int, got {combo!r}")
        
        if not (0 <= c1 < 52 and 0 <= c2 < 52):
            raise ValueError(f"combo cards out of range: {combo!r}")
        
        if c1 == c2:
            raise ValueError(f"combo cannot have duplicate cards: {combo!r}")
        
        if c1 > c2:
            raise ValueError(f"combo must be sorted: {combo!r}")

    def _validate_weight(self, weight: float) -> None:
        """Validate weight is finite in [0,1]."""
        if isinstance(weight, bool):
            raise ValueError(f"weight cannot be boolean")
        
        if not isinstance(weight, (int, float)):
            raise ValueError(f"weight must be number, got {type(weight).__name__}")
        
        # Check finite BEFORE range check
        if weight != weight:  # NaN check
            raise ValueError("weight cannot be NaN")
        
        if weight == float('inf') or weight == float('-inf'):
            raise ValueError("weight cannot be infinite")
        
        if not (0 <= weight <= 1):
            raise ValueError(f"weight must be in [0,1], got {weight}")


# Text format functions

def export_range_text(editor: RangeEditor) -> str:
    """Export range to poker-solver-range-v1 text format.
    
    Exports explicit combos with weights, not class shorthand.
    Format: card1card2:weight,card3card4:weight,...
    
    Args:
        editor: RangeEditor to export
        
    Returns:
        Comma-separated explicit combo text
    """
    combos = editor.combos()
    if not combos:
        return ""
    
    # Sort by combo for deterministic output
    sorted_combos = sorted(combos.items())
    
    entries = []
    for combo, weight in sorted_combos:
        cards = format_card(combo[0]) + format_card(combo[1])
        # Use shortest decimal representation
        weight_str = _format_weight(weight)
        entries.append(f"{cards}:{weight_str}")
    
    return ",".join(entries)


def import_range_text(text: str) -> RangeEditor:
    """Import range from poker-solver-range-v1 text format.
    
    Accepts class tokens (AA, AKs, AKo) and explicit combos.
    Rejects overlapping entries atomically.
    
    Args:
        text: Comma-separated range text
        
    Returns:
        RangeEditor with imported combos
        
    Raises:
        ValueError: If entries overlap or format is invalid
    """
    if not isinstance(text, str):
        raise ValueError(f"text must be string, got {type(text).__name__}")
    
    text = text.strip()
    if not text:
        return RangeEditor()
    
    # Parse all entries first to check for overlaps
    entries = []
    for entry in text.split(","):
        entry = entry.strip()
        if not entry:
            continue
        
        if ":" in entry:
            token, weight_str = entry.split(":", 1)
            token = token.strip()
            weight = _parse_weight(weight_str.strip())
        else:
            token = entry
            weight = 1.0
        
        entries.append((token, weight))
    
    # Build editor, checking for overlaps
    editor = RangeEditor()
    seen_combos = set()
    
    for token, weight in entries:
        # Expand token
        expanded = editor._expand_token(token)
        
        # Check for overlap with previously seen combos
        for combo in expanded:
            if combo in seen_combos:
                raise ValueError(f"overlap: combo {editor._format_combo(combo)} appears multiple times")
            seen_combos.add(combo)
        
        # Add to editor
        editor = editor.add(token, weight)
    
    return editor


def _format_weight(weight: float) -> str:
    """Format weight as shortest decimal string."""
    # Use repr for shortest representation, strip trailing zeros
    if weight == int(weight):
        return str(int(weight))
    s = str(weight)
    # Remove trailing zeros after decimal point
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


def _parse_weight(text: str) -> float:
    """Parse weight from decimal text."""
    try:
        weight = float(text)
    except (ValueError, TypeError) as e:
        raise ValueError(f"invalid weight: {text!r}") from e
    
    # Validation happens in RangeEditor
    return weight


# Library functions

import json
import os
import re
from pathlib import Path


class RangeLibrary:
    """Named range library with strict JSON persistence.
    
    Format: poker-solver-range-library-v1
    Names are identifiers only, never paths.
    """

    def __init__(self, ranges: Dict[str, RangeEditor] = None):
        """Initialize library with optional ranges."""
        self._ranges = dict(ranges) if ranges else {}
        # Validate all names
        for name in self._ranges:
            _validate_range_name(name)

    def add_range(self, name: str, editor: RangeEditor) -> 'RangeLibrary':
        """Add or replace a named range.
        
        Args:
            name: Valid identifier (no path separators)
            editor: RangeEditor to store
            
        Returns:
            New RangeLibrary with added range
            
        Raises:
            ValueError: If name is invalid
        """
        _validate_range_name(name)
        if not isinstance(editor, RangeEditor):
            raise ValueError(f"editor must be RangeEditor, got {type(editor).__name__}")
        
        new_ranges = dict(self._ranges)
        new_ranges[name] = editor
        return RangeLibrary(new_ranges)

    def get_range(self, name: str) -> RangeEditor:
        """Get named range.
        
        Raises:
            KeyError: If name not found
        """
        return self._ranges[name]

    def range_names(self) -> list[str]:
        """Return sorted list of range names."""
        return sorted(self._ranges.keys())

    def save(self, path: Path | str) -> None:
        """Save library to JSON file atomically.
        
        Uses temporary file + os.replace for atomic write.
        
        Args:
            path: File path to save to
        """
        path = Path(path)
        
        # Build JSON structure
        data = {
            "format": "poker-solver-range-library-v1",
            "ranges": {}
        }
        
        # Convert each range to explicit combo list
        for name in sorted(self._ranges.keys()):
            editor = self._ranges[name]
            combos = editor.combos()
            
            # Sort combos for deterministic output
            sorted_combos = sorted(combos.items())
            
            entries = []
            for combo, weight in sorted_combos:
                entries.append({
                    "cards": [combo[0], combo[1]],
                    "weight": weight
                })
            
            data["ranges"][name] = entries
        
        # Write to temporary file then replace
        tmp_path = path.parent / f".{path.name}.tmp"
        try:
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2, allow_nan=False, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic replace
            os.replace(tmp_path, path)
        finally:
            # Clean up temp file if it still exists
            if tmp_path.exists():
                tmp_path.unlink()


def load_library(path: Path | str) -> RangeLibrary:
    """Load library from JSON file.
    
    Rejects duplicate range names and invalid data.
    
    Args:
        path: File path to load from
        
    Returns:
        RangeLibrary
        
    Raises:
        ValueError: If format is invalid or duplicate names exist
    """
    path = Path(path)
    
    with open(path) as f:
        # Use object_pairs_hook to detect duplicate keys
        def check_duplicates(pairs):
            seen = set()
            for key, value in pairs:
                if key in seen:
                    raise ValueError(f"duplicate key in JSON: {key!r}")
                seen.add(key)
            return dict(pairs)
        
        data = json.load(f, object_pairs_hook=check_duplicates)
    
    # Validate format
    if not isinstance(data, dict):
        raise ValueError("library must be JSON object")
    
    if data.get("format") != "poker-solver-range-library-v1":
        raise ValueError(f"unsupported format: {data.get('format')!r}")
    
    if "ranges" not in data:
        raise ValueError("missing 'ranges' field")
    
    ranges_data = data["ranges"]
    if not isinstance(ranges_data, dict):
        raise ValueError("'ranges' must be object")
    
    # Load each range
    ranges = {}
    for name, entries in ranges_data.items():
        _validate_range_name(name)
        
        if not isinstance(entries, list):
            raise ValueError(f"range {name!r} must be array")
        
        # Build combo dict
        combos = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"range {name!r} entry must be object")
            
            if "cards" not in entry or "weight" not in entry:
                raise ValueError(f"range {name!r} entry missing 'cards' or 'weight'")
            
            cards = entry["cards"]
            if not isinstance(cards, list) or len(cards) != 2:
                raise ValueError(f"range {name!r} cards must be 2-element array")
            
            c1, c2 = cards
            if not isinstance(c1, int) or not isinstance(c2, int):
                raise ValueError(f"range {name!r} cards must be integers")
            
            weight = entry["weight"]
            if isinstance(weight, bool):
                raise ValueError(f"range {name!r} weight cannot be boolean")
            if not isinstance(weight, (int, float)):
                raise ValueError(f"range {name!r} weight must be number")
            
            combo = (c1, c2) if c1 <= c2 else (c2, c1)
            
            if combo in combos:
                raise ValueError(f"range {name!r} has duplicate combo")
            
            combos[combo] = weight
        
        # Create editor (validates combos and weights)
        ranges[name] = RangeEditor(combos)
    
    return RangeLibrary(ranges)


def _validate_range_name(name: str) -> None:
    """Validate range name is a safe identifier.
    
    Names must match [A-Za-z0-9][A-Za-z0-9_.-]{0,63}
    No path separators or .. allowed.
    
    Raises:
        ValueError: If name is invalid
    """
    if not isinstance(name, str):
        raise ValueError(f"name must be string, got {type(name).__name__}")
    
    if not name:
        raise ValueError("name cannot be empty")
    
    if len(name) > 64:
        raise ValueError(f"name too long: {len(name)} > 64")
    
    # Check pattern
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$', name):
        raise ValueError(f"invalid name: {name!r} (must match [A-Za-z0-9][A-Za-z0-9_.-]{{0,63}})")
    
    # Reject path separators and ..
    if '/' in name or '\\' in name or '..' in name:
        raise ValueError(f"name cannot contain path separators or '..': {name!r}")
