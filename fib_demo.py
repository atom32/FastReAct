def fibonacci(n):
    a, b = 0, 1
    sequence = []
    for _ in range(n):
        sequence.append(a)
        a, b = b, a + b
    return sequence

if __name__ == '__main__':
    fib_sequence = fibonacci(15)
    print(f"First 15 Fibonacci numbers: {fib_sequence}")