"""
Async/Await Examples - Understanding Python's async programming

Key concepts:
1. async def: Declares an async function (coroutine)
2. await: Pauses execution until async operation completes
3. asyncio.run(): Runs the main async function
4. asyncio.gather(): Runs multiple async functions concurrently
"""

import asyncio
import time

# Basic async function example
async def simple_task(name: str, delay: int):
    """A simple async task that simulates I/O work"""
    print(f"[{name}] Starting task, waiting {delay} seconds...")
    await asyncio.sleep(delay)  # Non-blocking sleep
    print(f"[{name}] Task completed after {delay} seconds")
    return f"{name}_result"

# Sequential execution (slow)
async def sequential_execution():
    """Runs tasks one after another"""
    print("\n=== SEQUENTIAL EXECUTION ===")
    start = time.time()
    
    result1 = await simple_task("Task1", 2)
    result2 = await simple_task("Task2", 1)
    result3 = await simple_task("Task3", 3)
    
    elapsed = time.time() - start
    print(f"Sequential total time: {elapsed:.2f}s")
    print(f"Results: {result1}, {result2}, {result3}")

# Concurrent execution (fast)
async def concurrent_execution():
    """Runs tasks concurrently"""
    print("\n=== CONCURRENT EXECUTION ===")
    start = time.time()
    
    # Create tasks (they don't start until awaited)
    task1 = asyncio.create_task(simple_task("Task1", 2))
    task2 = asyncio.create_task(simple_task("Task2", 1))
    task3 = asyncio.create_task(simple_task("Task3", 3))
    
    # Run concurrently
    results = await asyncio.gather(task1, task2, task3)
    
    elapsed = time.time() - start
    print(f"Concurrent total time: {elapsed:.2f}s")
    print(f"Results: {results}")

# Real-world example: Web API calls
async def fetch_data(url: str, delay: float):
    """Simulate fetching data from API"""
    print(f"Fetching from {url}...")
    await asyncio.sleep(delay)  # Simulate network delay
    return f"Data from {url}"

async def web_api_example():
    """Example of concurrent API requests"""
    print("\n=== WEB API EXAMPLE ===")
    
    urls = [
        ("https://api.example.com/users", 1.5),
        ("https://api.example.com/posts", 2.0),
        ("https://api.example.com/comments", 1.0),
    ]
    
    # Create fetch tasks for all URLs
    tasks = [fetch_data(url, delay) for url, delay in urls]
    
    # Execute all concurrently
    results = await asyncio.gather(*tasks)
    
    print(f"Fetched {len(results)} endpoints")
    for result in results:
        print(f"  - {result}")

# Error handling in async functions
async def risky_task(name: str):
    """Task that might fail"""
    await asyncio.sleep(0.5)
    if name == "Task2":
        raise ValueError(f"Error in {name}")
    return f"{name}_success"

async def error_handling_example():
    """Demonstrate async error handling"""
    print("\n=== ERROR HANDLING ===")
    
    try:
        results = await asyncio.gather(
            risky_task("Task1"),
            risky_task("Task2"),
            risky_task("Task3"),
            return_exceptions=True  # Returns exceptions instead of raising
        )
        
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"Task{i} failed: {result}")
            else:
                print(f"Task{i} succeeded: {result}")
                
    except Exception as e:
        print(f"Caught exception: {e}")

# Main async function
async def main():
    """Run all examples"""
    print("Async/Await Tutorial Examples")
    print("=" * 50)
    
    # Run examples
    await sequential_execution()
    await concurrent_execution()
    await web_api_example()
    await error_handling_example()
    
    print("\n" + "=" * 50)
    print("All examples completed!")

# Run the program
if __name__ == "__main__":
    asyncio.run(main())
