#!/usr/bin/env python3
"""
Async/Await Explanation Example

Key Concepts:
1. Asynchronous functions are defined with `async def`
2. `await` pauses execution until an async operation completes
3. Coroutines are async functions that can be paused/resumed
4. Event loop manages execution of async tasks
"""

import asyncio
import time

# Traditional synchronous function
def sync_task(name: str, delay: int):
    """Synchronous function - blocks execution"""
    print(f"{name}: Starting sync task")
    time.sleep(delay)  # Blocks entire thread
    print(f"{name}: Finished after {delay}s")
    return f"Result from {name}"

# Asynchronous function (coroutine)
async def async_task(name: str, delay: int):
    """Asynchronous function - non-blocking"""
    print(f"{name}: Starting async task")
    await asyncio.sleep(delay)  # Non-blocking sleep
    print(f"{name}: Finished after {delay}s")
    return f"Async result from {name}"

# Synchronous execution (one after another)
def run_sync():
    print("\n=== Synchronous Execution ===")
    start = time.time()
    
    result1 = sync_task("Task 1", 2)
    result2 = sync_task("Task 2", 1)
    result3 = sync_task("Task 3", 1)
    
    total = time.time() - start
    print(f"Total time: {total:.2f}s")
    print(f"Results: {result1}, {result2}, {result3}")

# Asynchronous execution (concurrent)
async def run_async():
    print("\n=== Asynchronous Execution ===")
    start = time.time()
    
    # Create tasks - they start running immediately
    task1 = asyncio.create_task(async_task("Task 1", 2))
    task2 = asyncio.create_task(async_task("Task 2", 1))
    task3 = asyncio.create_task(async_task("Task 3", 1))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(task1, task2, task3)
    
    total = time.time() - start
    print(f"Total time: {total:.2f}s")
    print(f"Results: {results}")

# Example with real async operations
async def fetch_data(url: str, delay: int):
    """Simulate network request"""
    print(f"Fetching {url}")
    await asyncio.sleep(delay)
    return f"Data from {url}"

async def concurrent_requests():
    print("\n=== Concurrent Web Requests ===")
    
    urls = [
        ("https://api.example.com/users", 2),
        ("https://api.example.com/posts", 1),
        ("https://api.example.com/comments", 1),
    ]
    
    # Create tasks for all URLs
    tasks = [fetch_data(url, delay) for url, delay in urls]
    
    # Run concurrently and get results as they complete
    for future in asyncio.as_completed(tasks):
        result = await future
        print(f"Received: {result}")

# Common patterns
async def common_patterns():
    """Demonstrate common async/await patterns"""
    
    # Pattern 1: Sequential async operations
    print("\n--- Pattern 1: Sequential ---")
    result1 = await async_task("Sequential 1", 1)
    result2 = await async_task("Sequential 2", 1)
    
    # Pattern 2: Concurrent with gather
    print("\n--- Pattern 2: Concurrent (gather) ---")
    results = await asyncio.gather(
        async_task("Concurrent 1", 2),
        async_task("Concurrent 2", 1),
        async_task("Concurrent 3", 1)
    )
    
    # Pattern 3: Timeout handling
    print("\n--- Pattern 3: Timeout ---")
    try:
        result = await asyncio.wait_for(async_task("Long Task", 3), timeout=2.0)
    except asyncio.TimeoutError:
        print("Task timed out!")
    
    # Pattern 4: Multiple tasks with as_completed
    print("\n--- Pattern 4: As Completed ---")
    tasks = [
        async_task("Task A", 3),
        async_task("Task B", 1),
        async_task("Task C", 2)
    ]
    
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        print(f"Completed: {result}")

# Main execution
async def main():
    # Run sync version first
    run_sync()
    
    # Run async version
    await run_async()
    
    # Concurrent requests example
    await concurrent_requests()
    
    # Common patterns
    await common_patterns()
    
    print("\n=== Summary ===")
    print("""
Key Takeaways:
- Use `async def` to define coroutines
- Use `await` to pause execution of a coroutine
- Use `asyncio.create_task()` to start background tasks
- Use `asyncio.gather()` to run multiple tasks concurrently
- Use `asyncio.as_completed()` to process results as they arrive
- Use `asyncio.wait_for()` for timeout handling
- Sync code blocks thread; async code yields control during I/O
    """)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())