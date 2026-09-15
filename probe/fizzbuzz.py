def fizzbuzz(n):
    """Return FizzBuzz result for number n.
    
    Args:
        n: Integer to evaluate
        
    Returns:
        - 'FizzBuzz' if divisible by both 3 and 5
        - 'Fizz' if divisible by 3
        - 'Buzz' if divisible by 5
        - String representation of n otherwise
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    
    if n % 15 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    else:
        return str(n)
