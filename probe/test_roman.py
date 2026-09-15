"""Tests for Roman numeral conversion utilities."""

import pytest
from roman import int_to_roman, roman_to_int


class TestIntToRoman:
    """Tests for int_to_roman function."""
    
    def test_single_digits(self):
        """Test conversion of single digit numbers."""
        assert int_to_roman(1) == 'I'
        assert int_to_roman(2) == 'II'
        assert int_to_roman(3) == 'III'
        assert int_to_roman(4) == 'IV'
        assert int_to_roman(5) == 'V'
        assert int_to_roman(6) == 'VI'
        assert int_to_roman(7) == 'VII'
        assert int_to_roman(8) == 'VIII'
        assert int_to_roman(9) == 'IX'
    
    def test_tens(self):
        """Test conversion of multiples of ten."""
        assert int_to_roman(10) == 'X'
        assert int_to_roman(20) == 'XX'
        assert int_to_roman(30) == 'XXX'
        assert int_to_roman(40) == 'XL'
        assert int_to_roman(50) == 'L'
        assert int_to_roman(90) == 'XC'
    
    def test_hundreds(self):
        """Test conversion of multiples of hundred."""
        assert int_to_roman(100) == 'C'
        assert int_to_roman(400) == 'CD'
        assert int_to_roman(500) == 'D'
        assert int_to_roman(900) == 'CM'
    
    def test_thousands(self):
        """Test conversion of multiples of thousand."""
        assert int_to_roman(1000) == 'M'
        assert int_to_roman(2000) == 'MM'
        assert int_to_roman(3000) == 'MMM'
    
    def test_complex_numbers(self):
        """Test conversion of complex multi-digit numbers."""
        assert int_to_roman(58) == 'LVIII'
        assert int_to_roman(1994) == 'MCMXCIV'
        assert int_to_roman(2024) == 'MMXXIV'
        assert int_to_roman(3999) == 'MMMCMXCIX'
    
    def test_boundary_values(self):
        """Test boundary values of the valid range."""
        assert int_to_roman(1) == 'I'
        assert int_to_roman(3999) == 'MMMCMXCIX'
    
    def test_invalid_below_range(self):
        """Test that values below 1 raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 3999"):
            int_to_roman(0)
        with pytest.raises(ValueError, match="between 1 and 3999"):
            int_to_roman(-1)
    
    def test_invalid_above_range(self):
        """Test that values above 3999 raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 3999"):
            int_to_roman(4000)
        with pytest.raises(ValueError, match="between 1 and 3999"):
            int_to_roman(5000)
    
    def test_invalid_type(self):
        """Test that non-integer inputs raise ValueError."""
        with pytest.raises(ValueError):
            int_to_roman(3.14)
        with pytest.raises(ValueError):
            int_to_roman("42")


class TestRomanToInt:
    """Tests for roman_to_int function."""
    
    def test_single_characters(self):
        """Test conversion of single Roman numeral characters."""
        assert roman_to_int('I') == 1
        assert roman_to_int('V') == 5
        assert roman_to_int('X') == 10
        assert roman_to_int('L') == 50
        assert roman_to_int('C') == 100
        assert roman_to_int('D') == 500
        assert roman_to_int('M') == 1000
    
    def test_additive_notation(self):
        """Test conversion of additive Roman numerals."""
        assert roman_to_int('II') == 2
        assert roman_to_int('III') == 3
        assert roman_to_int('VI') == 6
        assert roman_to_int('VII') == 7
        assert roman_to_int('VIII') == 8
        assert roman_to_int('XX') == 20
        assert roman_to_int('XXX') == 30
    
    def test_subtractive_notation(self):
        """Test conversion of subtractive Roman numerals."""
        assert roman_to_int('IV') == 4
        assert roman_to_int('IX') == 9
        assert roman_to_int('XL') == 40
        assert roman_to_int('XC') == 90
        assert roman_to_int('CD') == 400
        assert roman_to_int('CM') == 900
    
    def test_complex_numerals(self):
        """Test conversion of complex Roman numerals."""
        assert roman_to_int('LVIII') == 58
        assert roman_to_int('MCMXCIV') == 1994
        assert roman_to_int('MMXXIV') == 2024
        assert roman_to_int('MMMCMXCIX') == 3999
    
    def test_case_insensitive(self):
        """Test that conversion is case-insensitive."""
        assert roman_to_int('iv') == 4
        assert roman_to_int('Ix') == 9
        assert roman_to_int('mcmxciv') == 1994
    
    def test_boundary_values(self):
        """Test boundary values of the valid range."""
        assert roman_to_int('I') == 1
        assert roman_to_int('MMMCMXCIX') == 3999
    
    def test_invalid_characters(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid Roman numeral character"):
            roman_to_int('ABC')
        with pytest.raises(ValueError, match="Invalid Roman numeral character"):
            roman_to_int('IXZ')
    
    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            roman_to_int('')
    
    def test_invalid_type(self):
        """Test that non-string inputs raise ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            roman_to_int(42)
        with pytest.raises(ValueError, match="non-empty string"):
            roman_to_int(None)
    
    def test_non_canonical_forms(self):
        """Test that non-canonical forms are rejected."""
        # IIII instead of IV
        with pytest.raises(ValueError, match="Non-canonical"):
            roman_to_int('IIII')
        # VV instead of X
        with pytest.raises(ValueError, match="Non-canonical"):
            roman_to_int('VV')
        # XXXX instead of XL
        with pytest.raises(ValueError, match="Non-canonical"):
            roman_to_int('XXXX')


class TestRoundTrip:
    """Test round-trip conversion consistency."""
    
    def test_round_trip_all_valid_range(self):
        """Test that all numbers in valid range round-trip correctly."""
        # Test a representative sample across the range
        test_values = list(range(1, 100)) + list(range(100, 1000, 10)) + list(range(1000, 4000, 100))
        for num in test_values:
            roman = int_to_roman(num)
            assert roman_to_int(roman) == num
    
    def test_round_trip_edge_cases(self):
        """Test round-trip for specific edge cases."""
        edge_cases = [1, 4, 5, 9, 10, 40, 50, 90, 100, 400, 500, 900, 1000, 3999]
        for num in edge_cases:
            roman = int_to_roman(num)
            assert roman_to_int(roman) == num
