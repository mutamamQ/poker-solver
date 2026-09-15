#!/usr/bin/env python3
from fizzbuzz import fizzbuzz

print("=== FizzBuzz Edge Case Tests ===")
print("\nNegative numbers:")
print(f"  fizzbuzz(-1) = {fizzbuzz(-1)}")
print(f"  fizzbuzz(-15) = {fizzbuzz(-15)}")
print(f"  fizzbuzz(-100) = {fizzbuzz(-100)}")

print("\nLarge numbers:")
print(f"  fizzbuzz(1000000) = {fizzbuzz(1000000)}")
print(f"  fizzbuzz(999999) = {fizzbuzz(999999)}")

print("\nType validation:")
try:
    fizzbuzz(3.5)
    print("  fizzbuzz(3.5): FAIL - should raise TypeError")
except TypeError as e:
    print(f"  fizzbuzz(3.5): PASS - raised TypeError")

try:
    fizzbuzz("15")
    print("  fizzbuzz('15'): FAIL - should raise TypeError")
except TypeError as e:
    print(f"  fizzbuzz('15'): PASS - raised TypeError")
