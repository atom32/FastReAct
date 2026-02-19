"""Python decorator examples and patterns"""

# 1. Basic decorator - modifies function behavior
def logger(func):
    """Log function calls with timing"""
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end-start:.3f} seconds")
        return result
    return wrapper

@logger
def slow_function():
    import time
    time.sleep(0.1)
    return "Done"

# 2. Decorator with arguments - configurable behavior
def retry(max_attempts=3):
    """Retry function on exception"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}")
            return None
        return wrapper
    return decorator

@retry(max_attempts=2)
def risky_function():
    import random
    if random.random() < 0.5:
        raise ValueError("Random failure")
    return "Success"

# 3. Class decorator - modifies class behavior
def singleton(cls):
    """Ensure only one instance exists"""
    instances = {}
    
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

@singleton
class Database:
    def __init__(self):
        print("Database connection created")

# 4. Property decorators - computed attributes
class Circle:
    def __init__(self, radius):
        self._radius = radius
    
    @property
    def radius(self):
        return self._radius
    
    @radius.setter
    def radius(self, value):
        if value <= 0:
            raise ValueError("Radius must be positive")
        self._radius = value
    
    @property
    def area(self):
        import math
        return math.pi * self._radius ** 2

# 5. Preserving function metadata
from functools import wraps

def preserve_metadata(func):
    """Decorator that preserves original function metadata"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@preserve_metadata
def documented_function():
    """This function has documentation"""
    return "Result"

# 6. Decorator factory pattern
def validate_input(*validators):
    """Validate function arguments"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Apply validators to args
            for i, (arg, validator) in enumerate(zip(args, validators)):
                if not validator(arg):
                    raise ValueError(f"Argument {i} failed validation")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@validate_input(lambda x: x > 0, lambda x: isinstance(x, str))
def process_data(num, text):
    return f"{text}: {num * 2}"

# Run examples
if __name__ == "__main__":
    print("1. Basic logger decorator:")
    print(slow_function())
    
    print("\n2. Retry decorator:")
    for _ in range(3):
        try:
            print(risky_function())
            break
        except ValueError as e:
            print(f"Failed: {e}")
    
    print("\n3. Singleton decorator:")
    db1 = Database()
    db2 = Database()
    print(f"Same instance: {db1 is db2}")
    
    print("\n4. Property decorators:")
    c = Circle(5)
    print(f"Radius: {c.radius}, Area: {c.area:.2f}")
    c.radius = 10
    print(f"New radius: {c.radius}, New area: {c.area:.2f}")
    
    print("\n5. Metadata preservation:")
    print(f"Name: {documented_function.__name__}")
    print(f"Doc: {documented_function.__doc__}")
    
    print("\n6. Validation decorator:")
    try:
        print(process_data(5, "Value"))
        print(process_data(-1, "Invalid"))  # Should fail
    except ValueError as e:
        print(f"Validation error: {e}")