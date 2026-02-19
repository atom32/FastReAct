"""Python Decorators Explained

Decorators are functions that modify other functions/methods.
They use the @syntax and are applied above function definitions."""

# Basic decorator example
def simple_decorator(func):
    """A decorator that adds functionality before/after calling func"""
    def wrapper():
        print("Before function call")
        func()
        print("After function call")
    return wrapper

@simple_decorator
def say_hello():
    print("Hello!")

# Decorator with arguments
def repeat(n):
    """Decorator factory - returns a decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet(name):
    print(f"Hello, {name}!")

# Class-based decorator
class TimerDecorator:
    """Decorator as a class"""
    def __init__(self, func):
        self.func = func
    
    def __call__(self, *args, **kwargs):
        import time
        start = time.time()
        result = self.func(*args, **kwargs)
        end = time.time()
        print(f"{self.func.__name__} took {end-start:.2f} seconds")
        return result

@TimerDecorator
def calculate_sum(n):
    return sum(range(n))

# Built-in decorators
class ExampleClass:
    @staticmethod
    def static_method():
        print("Static method - no self/cls")
    
    @classmethod
    def class_method(cls):
        print(f"Class method - receives {cls}")
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val

# functools.wraps preserves metadata
from functools import wraps

def logging_decorator(func):
    @wraps(func)  # Preserves name, docstring, etc.
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with {args}")
        return func(*args, **kwargs)
    return wrapper

if __name__ == "__main__":
    print("=== Basic Decorator ===")
    say_hello()
    
    print("\n=== Decorator with Arguments ===")
    greet("Alice")
    
    print("\n=== Class-based Decorator ===")
    result = calculate_sum(1000000)
    print(f"Result: {result}")
    
    print("\n=== Built-in Decorators ===")
    ExampleClass.static_method()
    ExampleClass.class_method()