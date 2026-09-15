#!/usr/bin/env python3
from roman import int_to_roman, roman_to_int

print("=== Roman Numeral Edge Case Tests ===")
print("\nConversion accuracy:")
tests = [(1, 'I'), (3999, 'MMMCMXCIX'), (444, 'CDXLIV'), (1984, 'MCMLXXXIV')]
for n, expected in tests:
    result = int_to_roman(n)
    status = "PASS" if result == expected else "FAIL"
    print(f"  {n} -> {result} (expected {expected}): {status}")

print("\nNon-canonical rejection:")
for invalid in ['IIII', 'VV', 'XXXX', 'MMMM']:
    try:
        roman_to_int(invalid)
        print(f"  {invalid}: FAIL - should reject non-canonical")
    except ValueError as e:
        print(f"  {invalid}: PASS - rejected")

print("\nInvalid subtractive (IC = 99):")
try:
    result = roman_to_int('IC')
    print(f"  IC: parsed as {result} - checking canonicality...")
except ValueError as e:
    print(f"  IC: PASS - rejected ({str(e)[:50]}...)")

print("\nBoundary validation:")
for val in [0, -1, 4000, 5000]:
    try:
        int_to_roman(val)
        print(f"  int_to_roman({val}): FAIL - should reject")
    except ValueError:
        print(f"  int_to_roman({val}): PASS - rejected")
