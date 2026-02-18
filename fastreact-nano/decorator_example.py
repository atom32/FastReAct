def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time()-start:.2f}s")
        return result
    return wrapper

@timer
def compute():
    total = sum(range(1000000))
    return total

if __name__ == "__main__":
    compute()