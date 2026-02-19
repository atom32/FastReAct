def factorial(n):
    # Base case: factorial of 0 or 1 is 1
    if n <= 1:
        return 1
    # Recursive case: n! = n * (n-1)!
    else:
        return n * factorial(n - 1)

# Example usage
print(f"5! = {factorial(5)}")
print(f"0! = {factorial(0)}")
print(f"1! = {factorial(1)}")
