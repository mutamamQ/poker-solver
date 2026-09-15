"""Roman numeral conversion utilities.

Supports the conventional canonical Roman numeral domain: integers 1..3999.
"""


def int_to_roman(num: int) -> str:
    """Convert an integer to a Roman numeral string.
    
    Args:
        num: Integer in the range 1..3999
        
    Returns:
        Roman numeral string representation
        
    Raises:
        ValueError: If num is outside the valid range [1, 3999]
    """
    if not isinstance(num, int) or num < 1 or num > 3999:
        raise ValueError(f"Input must be an integer between 1 and 3999, got {num}")
    
    # Mapping of values to Roman numerals in descending order
    val_to_roman = [
        (1000, 'M'),
        (900, 'CM'),
        (500, 'D'),
        (400, 'CD'),
        (100, 'C'),
        (90, 'XC'),
        (50, 'L'),
        (40, 'XL'),
        (10, 'X'),
        (9, 'IX'),
        (5, 'V'),
        (4, 'IV'),
        (1, 'I')
    ]
    
    result = []
    for value, numeral in val_to_roman:
        count = num // value
        if count:
            result.append(numeral * count)
            num -= value * count
    
    return ''.join(result)


def roman_to_int(s: str) -> int:
    """Convert a Roman numeral string to an integer.
    
    Args:
        s: Roman numeral string
        
    Returns:
        Integer value in the range 1..3999
        
    Raises:
        ValueError: If the string is not a valid Roman numeral or represents
                    a number outside the valid range [1, 3999]
    """
    if not isinstance(s, str) or not s:
        raise ValueError("Input must be a non-empty string")
    
    # Mapping of Roman numerals to values
    roman_to_val = {
        'I': 1,
        'V': 5,
        'X': 10,
        'L': 50,
        'C': 100,
        'D': 500,
        'M': 1000
    }
    
    # Validate all characters are valid Roman numerals
    s = s.upper()
    for char in s:
        if char not in roman_to_val:
            raise ValueError(f"Invalid Roman numeral character: {char}")
    
    result = 0
    prev_value = 0
    
    # Process from right to left
    for char in reversed(s):
        value = roman_to_val[char]
        if value < prev_value:
            # Subtractive notation (e.g., IV, IX)
            result -= value
        else:
            result += value
        prev_value = value
    
    # Validate the result is in the canonical range
    if result < 1 or result > 3999:
        raise ValueError(f"Roman numeral represents a number outside valid range [1, 3999]: {result}")
    
    # Validate round-trip to ensure canonical form
    if int_to_roman(result) != s:
        raise ValueError(f"Non-canonical Roman numeral: {s}")
    
    return result
