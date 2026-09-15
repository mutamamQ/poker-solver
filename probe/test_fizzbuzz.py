import pytest
from fizzbuzz import fizzbuzz


def test_fizzbuzz_multiples_of_fifteen():
    """Test that multiples of 15 return 'FizzBuzz'."""
    assert fizzbuzz(15) == "FizzBuzz"
    assert fizzbuzz(30) == "FizzBuzz"
    assert fizzbuzz(45) == "FizzBuzz"
    assert fizzbuzz(0) == "FizzBuzz"


def test_fizzbuzz_multiples_of_three_and_five():
    """Test Fizz for multiples of 3 and Buzz for multiples of 5."""
    # Multiples of 3 (not 15)
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(6) == "Fizz"
    assert fizzbuzz(9) == "Fizz"
    
    # Multiples of 5 (not 15)
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(10) == "Buzz"
    assert fizzbuzz(20) == "Buzz"


def test_fizzbuzz_regular_numbers():
    """Test that non-multiples return their string representation."""
    assert fizzbuzz(1) == "1"
    assert fizzbuzz(2) == "2"
    assert fizzbuzz(7) == "7"
    assert fizzbuzz(13) == "13"
