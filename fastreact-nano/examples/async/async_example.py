"""
Async/Await Explained with Examples

Key concepts:
1. Asynchronous programming: Non-blocking operations
2. async: Declares that a function is asynchronous
3. await: Pauses execution until async operation completes
4. Event loop: Manages async tasks
"""

import asyncio
import time

# Synchronous (blocking) function
def sync_task(name, delay):
    print(f"Sync task {name} starting (will block for {delay}s)")
    time.sleep(delay)
    print(f"Sync task {name} completed")
    return f"Sync result {name}"

# Asynchronous (non-blocking) function
async def async_task(name, delay):
    print(f"Async task {name} starting (non-blocking)")
    await asyncio.sleep(delay)  # Non-blocking sleep
    print(f"Async task {name} completed")
    return f"Async result {name}"

# Running sync tasks (sequential)
def run_sync_example():
    print("\n=== Synchronous Execution ===")
    start = time.time()
    
    result1 = sync_task("A", 2)
    result2 = sync_task("B", 1)
    
    print(f"Total time: {time.time() - start:.2f}s")
    print(f"Results: {result1}, {result2}")

# Running async tasks (concurrent)
async def run_async_example():
    print("\n=== Asynchronous Execution ===")
    start = time.time()
    
    # Create tasks (they don't start executing yet)
    task1 = async_task("A", 2)
    task2 = async_task("B", 1)
    
    # Run tasks concurrently using asyncio.gather
    results = await asyncio.gather(task1, task2)
    
    print(f"Total time: {time.time() - start:.2f}s")
    print(f"Results: {results}")

# Async function with error handling
async def async_with_error():
    print("\n=== Async with Error Handling ===")
    try:
        await asyncio.sleep(1)
        raise ValueError("Something went wrong!")
    except ValueError as e:
        print(f"Caught error: {e}")

# Chaining async functions
async def chain_async_functions():
    print("\n=== Chaining Async Functions ===")
    
    # Function 1
    async def fetch_data():
        await asyncio.sleep(1)
        return {"data": "Some data"}
    
    # Function 2 depends on Function 1
    async def process_data(data):
        await asyncio.sleep(0.5)
        return f"Processed: {data['data']}"
    
    data = await fetch_data()
    result = await process_data(data)
    print(f"Chained result: {result}")

# Running async functions concurrently vs sequentially
async def compare_concurrent_vs_sequential():
    print("\n=== Concurrent vs Sequential ===")
    
    async def task(name, delay):
        await asyncio.sleep(delay)
        return f"{name} took {delay}s"
    
    # Sequential (one after another)
    start = time.time()
    result1 = await task("Task1", 1)
    result2 = await task("Task2", 1)
    print(f"Sequential time: {time.time() - start:.2f}s")
    
    # Concurrent (at the same time)
    start = time.time()
    tasks = [task("Task1", 1), task("Task2", 1)]
    results = await asyncio.gather(*tasks)
    print(f"Concurrent time: {time.time() - start:.2f}s")

async def main():
    # Run all examples
    run_sync_example()
    await run_async_example()
    await async_with_error()
    await chain_async_functions()
    await compare_concurrent_vs_sequential()
    
    print("\n=== Key Takeaways ===")
    print("1. async def: Declares an asynchronous function")
    print("2. await: Pauses function until async operation completes")
    print("3. asyncio.gather(): Runs multiple async tasks concurrently")
    print("4. asyncio.sleep(): Non-blocking alternative to time.sleep()")
    print("5. Event loop: Required to run async functions (asyncio.run())")

if __name__ == "__main__":
    # Start the event loop
    asyncio.run(main())