"""
Async/Await Cheatsheet

Core Syntax:
async def my_function():     # Define async function
    result = await some_async_operation()  # Await async call
    return result

Event Loop:
asyncio.run(main())          # Run main async function

Concurrency:
await asyncio.gather(task1(), task2())     # Run concurrently
await asyncio.wait([task1(), task2()])     # Wait for tasks
asyncio.create_task(coro())                # Schedule task

Common Patterns:
1. Sequential: await func1(); await func2()
2. Concurrent: await asyncio.gather(func1(), func2())
3. With timeout: await asyncio.wait_for(task, timeout=5)
4. With semaphore: async with semaphore: ...
5. Background tasks: task = asyncio.create_task(coro())

Key Functions:
- asyncio.sleep(): Non-blocking sleep
- asyncio.gather(): Run multiple coroutines
- asyncio.wait(): Wait for tasks with conditions
- asyncio.create_task(): Schedule coroutine
- asyncio.run(): Run async program

Error Handling:
try:
    await async_function()
except Exception as e:
    print(f"Error: {e}")

Common Pitfalls:
1. Forgetting 'await' on async calls
2. Mixing sync I/O with async code
3. Not using asyncio.run() to start
4. Blocking the event loop with CPU work
"""

import asyncio

# Basic async function
async def basic_example():
    print("Start")
    await asyncio.sleep(1)
    print("End")

# Multiple async tasks
async def multiple_tasks():
    async def task(name, delay):
        await asyncio.sleep(delay)
        return f"{name} done"
    
    # Method 1: Gather (all at once)
    results = await asyncio.gather(
        task("Task1", 1),
        task("Task2", 2),
        task("Task3", 1)
    )
    print(f"Gather results: {results}")
    
    # Method 2: Wait (more control) - create tasks explicitly
    tasks = [asyncio.create_task(task("TaskA", 1)), asyncio.create_task(task("TaskB", 2))]
    done, pending = await asyncio.wait(tasks, timeout=1.5)
    print(f"Done: {len(done)}, Pending: {len(pending)}")

# Timeout example
async def with_timeout():
    async def slow_task():
        await asyncio.sleep(3)
        return "Done"
    
    try:
        result = await asyncio.wait_for(slow_task(), timeout=2)
        print(f"Result: {result}")
    except asyncio.TimeoutError:
        print("Task timed out!")

# Semaphore example (rate limiting)
async def with_semaphore():
    sem = asyncio.Semaphore(2)  # Allow 2 concurrent
    
    async def limited_task(id):
        async with sem:
            print(f"Task {id} starting")
            await asyncio.sleep(1)
            print(f"Task {id} finished")
            return id
    
    tasks = [limited_task(i) for i in range(5)]
    await asyncio.gather(*tasks)

async def main():
    print("=== Async/Await Cheatsheet ===\n")
    
    print("1. Basic async function:")
    await basic_example()
    
    print("\n2. Multiple tasks:")
    await multiple_tasks()
    
    print("\n3. With timeout:")
    await with_timeout()
    
    print("\n4. With semaphore (rate limiting):")
    await with_semaphore()

if __name__ == "__main__":
    asyncio.run(main())