"""Phase 3 weighted range editor tests.

Vertical TDD: observe RED before implementing each behavior.
Owned exclusively by ranges.py implementer.
"""

import pytest
from poker_solver.ranges import RangeEditor


class TestCanonicalComboRepresentation:
    """Combos are sorted explicit two-card tuples."""

    def test_pair_has_six_combos(self):
        """AA expands to exactly 6 suit combinations."""
        editor = RangeEditor()
        result = editor.add("AA")
        assert len(result.combos()) == 6

    def test_suited_class_has_four_combos(self):
        """AKs expands to exactly 4 suited combinations."""
        editor = RangeEditor()
        result = editor.add("AKs")
        assert len(result.combos()) == 4

    def test_offsuit_class_has_twelve_combos(self):
        """AKo expands to exactly 12 offsuit combinations."""
        editor = RangeEditor()
        result = editor.add("AKo")
        assert len(result.combos()) == 12

    def test_all_169_classes_expand_to_1326_combos(self):
        """All 169 canonical classes expand to exactly 1,326 unique combos."""
        editor = RangeEditor()
        # Build all 169 classes
        ranks = "AKQJT98765432"
        for i, r1 in enumerate(ranks):
            # Pairs
            editor = editor.add(f"{r1}{r1}")
            # Suited and offsuit
            for r2 in ranks[i+1:]:
                editor = editor.add(f"{r1}{r2}s")
                editor = editor.add(f"{r1}{r2}o")
        
        assert len(editor.combos()) == 1326


class TestWeightValidation:
    """Weights must be finite numbers in [0,1], booleans rejected."""

    def test_weight_must_be_in_range(self):
        """Weight outside [0,1] is rejected."""
        editor = RangeEditor()
        with pytest.raises(ValueError, match="weight must be in"):
            editor.add("AA", weight=1.5)
        with pytest.raises(ValueError, match="weight must be in"):
            editor.add("AA", weight=-0.1)

    def test_boolean_weight_rejected(self):
        """Boolean values are rejected even though True==1, False==0."""
        editor = RangeEditor()
        with pytest.raises(ValueError, match="cannot be boolean"):
            editor.add("AA", weight=True)
        with pytest.raises(ValueError, match="cannot be boolean"):
            editor.add("AA", weight=False)

    def test_nan_weight_rejected(self):
        """NaN is rejected."""
        editor = RangeEditor()
        with pytest.raises(ValueError, match="NaN"):
            editor.add("AA", weight=float('nan'))

    def test_infinite_weight_rejected(self):
        """Infinite weights are rejected."""
        editor = RangeEditor()
        with pytest.raises(ValueError, match="infinite"):
            editor.add("AA", weight=float('inf'))
        with pytest.raises(ValueError, match="infinite"):
            editor.add("AA", weight=float('-inf'))

    def test_zero_and_one_weights_accepted(self):
        """Boundary values 0 and 1 are valid."""
        editor = RangeEditor()
        result = editor.add("AA", weight=0)
        assert len(result.combos()) == 6
        result = editor.add("KK", weight=1.0)
        assert len(result.combos()) == 6


class TestAtomicOperations:
    """Add/remove/set operations are atomic: all-or-nothing."""

    def test_add_rejects_duplicate_combo(self):
        """Adding an existing combo fails atomically."""
        editor = RangeEditor().add("AsKd")
        with pytest.raises(ValueError, match="already exists"):
            editor.add("AsKd")

    def test_add_class_rejects_partial_overlap(self):
        """Adding a class that partially overlaps existing combos fails atomically."""
        editor = RangeEditor().add("AsKs")  # One combo of AKs
        # Try to add full AKs class - should fail because AsKs exists
        with pytest.raises(ValueError, match="already exists"):
            editor.add("AKs")
        # Original range unchanged
        assert len(editor.combos()) == 1

    def test_remove_requires_all_combos_exist(self):
        """Removing a class fails if any combo is missing."""
        editor = RangeEditor().add("AA")
        # Try to remove AKs when it doesn't exist
        with pytest.raises(ValueError, match="not in range"):
            editor.remove("AKs")

    def test_set_weight_requires_all_combos_exist(self):
        """Setting weight fails if any combo is missing."""
        editor = RangeEditor().add("AA")
        with pytest.raises(ValueError, match="not in range"):
            editor.set_weight("KK", 0.5)

    def test_remove_class_atomic(self):
        """Removing a class removes all combos atomically."""
        editor = RangeEditor().add("AKs")
        assert len(editor.combos()) == 4
        result = editor.remove("AKs")
        assert len(result.combos()) == 0

    def test_set_weight_class_atomic(self):
        """Setting weight on a class updates all combos atomically."""
        editor = RangeEditor().add("AKo", weight=1.0)
        result = editor.set_weight("AKo", 0.25)
        combos = result.combos()
        assert len(combos) == 12
        assert all(w == 0.25 for w in combos.values())


class TestTextFormat:
    """poker-solver-range-v1 text format: explicit combos with weights."""

    def test_export_explicit_combos_with_weights(self):
        """Export produces explicit combo text, not class shorthand."""
        from poker_solver.ranges import export_range_text
        editor = RangeEditor().add("AA", weight=0.5)
        text = export_range_text(editor)
        # Should have 6 explicit combos, not "AA:0.5"
        assert "AA" not in text or ":" not in text.split("AA")[0]  # Not class notation
        combos = [c.strip() for c in text.split(",")]
        assert len(combos) == 6
        # Each should be 4-char combo with weight
        for combo in combos:
            assert ":" in combo
            cards, weight = combo.split(":")
            assert len(cards) == 4
            assert weight == "0.5"

    def test_import_class_expands_to_combos(self):
        """Import accepts class tokens and expands them."""
        from poker_solver.ranges import import_range_text
        editor = import_range_text("AKs:0.25")
        assert len(editor.combos()) == 4
        assert all(w == 0.25 for w in editor.combos().values())

    def test_import_rejects_overlap(self):
        """Import rejects overlapping entries."""
        from poker_solver.ranges import import_range_text
        # AsKs appears in AKs class
        with pytest.raises(ValueError, match="already exists|overlap"):
            import_range_text("AKs,AsKs")

    def test_round_trip_preserves_weights(self):
        """Export then import preserves exact combo weights."""
        from poker_solver.ranges import export_range_text, import_range_text
        editor = RangeEditor().add("AsKd", 0.75).add("QcQd", 0.25)
        text = export_range_text(editor)
        restored = import_range_text(text)
        assert restored.combos() == editor.combos()


class TestLibraryFormat:
    """poker-solver-range-library-v1 JSON format."""

    def test_save_library_creates_json(self, tmp_path):
        """Save library creates strict JSON file."""
        from poker_solver.ranges import RangeLibrary
        lib = RangeLibrary()
        lib = lib.add_range("test_range", RangeEditor().add("AA"))
        
        path = tmp_path / "test.json"
        lib.save(path)
        
        assert path.exists()
        import json
        with open(path) as f:
            data = json.load(f)
        assert data["format"] == "poker-solver-range-library-v1"
        assert "test_range" in data["ranges"]

    def test_load_library_rejects_duplicate_keys(self, tmp_path):
        """Load rejects JSON with duplicate range names."""
        from poker_solver.ranges import load_library
        path = tmp_path / "dup.json"
        # Write JSON with duplicate keys manually
        with open(path, 'w') as f:
            f.write('{"format":"poker-solver-range-library-v1","ranges":{"dup":[],"dup":[]}}')
        
        with pytest.raises(ValueError, match="duplicate"):
            load_library(path)

    def test_library_name_validation(self):
        """Range names must be valid identifiers, not paths."""
        from poker_solver.ranges import RangeLibrary
        lib = RangeLibrary()
        
        # Valid names
        lib.add_range("valid_name", RangeEditor())
        lib.add_range("Name123", RangeEditor())
        lib.add_range("name-with-dash", RangeEditor())
        
        # Invalid: path separators
        with pytest.raises(ValueError, match="name|identifier"):
            lib.add_range("../etc/passwd", RangeEditor())
        with pytest.raises(ValueError, match="name|identifier"):
            lib.add_range("path/to/file", RangeEditor())



class TestIncludeOrReplace:
    """Explicit upsert operation."""

    def test_include_or_replace_adds_new_combo(self):
        """include_or_replace adds combo if absent."""
        from poker_solver.cards import parse_card

        editor = RangeEditor()
        result = editor.include_or_replace("AsKd", 0.5)
        assert len(result.combos()) == 1
        key = tuple(sorted((parse_card("As"), parse_card("Kd"))))
        assert result.combos()[key] == 0.5

    def test_include_or_replace_updates_existing(self):
        """include_or_replace updates weight if present."""
        from poker_solver.cards import parse_card

        editor = RangeEditor().add("AsKd", 0.5)
        result = editor.include_or_replace("AsKd", 0.75)
        assert len(result.combos()) == 1
        key = tuple(sorted((parse_card("As"), parse_card("Kd"))))
        assert result.combos()[key] == 0.75

    def test_include_or_replace_class(self):
        """include_or_replace works with class tokens."""
        editor = RangeEditor().add("AA", 0.5)
        result = editor.include_or_replace("AA", 1.0)
        assert len(result.combos()) == 6
        assert all(w == 1.0 for w in result.combos().values())


class TestBlockedCombos:
    """Blocker filtering for conditional ranges."""

    def test_blocked_removes_dead_card_combos(self):
        """blocked() returns range without dead-card combos."""
        from poker_solver.cards import parse_card
        
        editor = RangeEditor().add("AA")
        # Block one ace
        dead = [parse_card("As")]
        result = editor.blocked(dead)
        
        # Should have 3 combos left (not 6)
        assert len(result.combos()) == 3

    def test_blocked_does_not_mutate_original(self):
        """blocked() returns new editor, doesn't mutate."""
        from poker_solver.cards import parse_card
        
        editor = RangeEditor().add("AA")
        dead = [parse_card("As")]
        result = editor.blocked(dead)
        
        # Original unchanged
        assert len(editor.combos()) == 6
        assert len(result.combos()) == 3


class TestDeterministicOrdering:
    """Export and library operations are deterministic."""

    def test_export_order_deterministic(self):
        """Multiple exports produce identical text."""
        from poker_solver.ranges import export_range_text
        
        editor = RangeEditor().add("AKs", 0.5).add("QQ", 0.75)
        text1 = export_range_text(editor)
        text2 = export_range_text(editor)
        assert text1 == text2

    def test_library_save_deterministic(self, tmp_path):
        """Multiple saves produce identical bytes."""
        from poker_solver.ranges import RangeLibrary
        
        lib = RangeLibrary()
        lib = lib.add_range("range1", RangeEditor().add("AA"))
        lib = lib.add_range("range2", RangeEditor().add("KK"))
        
        path1 = tmp_path / "lib1.json"
        path2 = tmp_path / "lib2.json"
        
        lib.save(path1)
        lib.save(path2)
        
        assert path1.read_bytes() == path2.read_bytes()
