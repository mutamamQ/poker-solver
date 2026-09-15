# Probe Modules

This directory contains utility modules for the poker-solver project.

## fizzbuzz.py

### API

**`fizzbuzz(n)`**

Return FizzBuzz result for number n.

- **Args:**
  - `n`: Integer to evaluate

- **Returns:**
  - `'FizzBuzz'` if divisible by both 3 and 5
  - `'Fizz'` if divisible by 3
  - `'Buzz'` if divisible by 5
  - String representation of n otherwise

- **Raises:**
  - `TypeError`: If input is not an integer

### Validation Behavior

- Enforces strict type checking: only integers are accepted
- Non-integer inputs raise `TypeError`

### Test Commands

```bash
python -m pytest test_fizzbuzz.py
```

---

## roman.py

Roman numeral conversion utilities supporting the conventional canonical domain: integers 1..3999.

### API

**`int_to_roman(num: int) -> str`**

Convert an integer to a Roman numeral string.

- **Args:**
  - `num`: Integer in the range 1..3999

- **Returns:**
  - Roman numeral string representation

- **Raises:**
  - `ValueError`: If num is outside the valid range [1, 3999]

**`roman_to_int(s: str) -> int`**

Convert a Roman numeral string to an integer.

- **Args:**
  - `s`: Roman numeral string

- **Returns:**
  - Integer value in the range 1..3999

- **Raises:**
  - `ValueError`: If the string is not a valid Roman numeral or represents a number outside the valid range [1, 3999]

### Validation Behavior

- **int_to_roman:**
  - Validates input is an integer in range [1, 3999]
  - Raises `ValueError` for out-of-range or non-integer inputs

- **roman_to_int:**
  - Validates input is a non-empty string
  - Case-insensitive (converts to uppercase)
  - Validates all characters are valid Roman numeral symbols (I, V, X, L, C, D, M)
  - Validates result is in canonical range [1, 3999]
  - Enforces canonical form by round-trip validation (rejects non-canonical representations like "IIII")
  - Raises `ValueError` for invalid characters, empty strings, non-canonical forms, or out-of-range results

### Test Commands

```bash
python -m pytest test_roman.py
```
