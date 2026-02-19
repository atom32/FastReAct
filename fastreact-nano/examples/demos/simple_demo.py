"""
Quick async/await demo showing the core concept
"""

import asyncio
import time

# Traditional blocking function
def blocking_function(name, seconds):
    print(f"Blocking function '{name}' started - will block for {seconds} seconds")
    time.sleep(seconds)  # Blocks everything!
    print(f"Blocking function '{name}' finished")
    return f"Result from {name}"

# Async non-blocking function  
async def non_blocking_function(name, seconds):
    print(f"Async function '{name}' started - won't block")
    await asyncio.sleep(seconds)  # Only pauses THIS function
    print(f"Async function '{name}' finished")
    return f"Async result from {name}"

# Run blocking functions (sequential)
def run_blocking():
    print("=== BLOCKING (Traditional) ===")
    start = time.time()
    
    result1 = blocking_function("Task1", 2)
    result2 = blocking_function("Task2", 1)
    
    total = time.time() - start
    print(f"Total time: {total:.1f} seconds")
    print(f"Task2 had to wait for Task1 to finish!\n")

# Run async functions (concurrent)
async def run_async():
    print("=== NON-BLOCKING (Async/Await) ===")
    start = time.time()
    
    # Run both async functions at the same time
    task1 = non_blocking_function("Task1", 2)
    task2 = non_blocking_function("Task2", 1)
    
    # Wait for both to complete
    results = await asyncio.gather(task1, task2)
    
    total = time.time() - start
    print(f"Total time: {total:.1f} seconds")
    print(f"Both tasks ran concurrently!\n")
    return results

# Main function to demonstrate both
async def main():
    run_blocking()
    results = await run_async()
    
    print("\n=== SUMMARY ===")
    print("Blocking (traditional):")
    print("  - time.sleep() blocks entire program")
    print("  - Functions run one after another")
    print("  - Total time = sum of all delays")
    print()
    print("Non-blocking (async/await):")
    print("  - asyncio.sleep() only pauses that function")
    print("  - Multiple async functions can run concurrently")
    print("  - Total time = longest delay, not sum")

# Run the demo
if __name__ == "__main__":
    asyncio.run(main())