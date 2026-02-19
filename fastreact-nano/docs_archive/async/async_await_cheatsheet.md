# Async/Await Cheatsheet

## Core Concepts

### 1. **async def**
- Declares an async function (coroutine)
- Returns a coroutine object when called (needs to be awaited)
```python
async def fetch_data():
    return "data"
```

### 2. **await**
- Pauses execution until async operation completes
- Can only be used inside async functions
```python
result = await fetch_data()
```

### 3. **asyncio.run()**
- Runs the top-level async function
- Creates event loop, runs coroutine, closes loop
```python
asyncio.run(main())
```

## Key Functions

### **asyncio.create_task()**
- Schedules coroutine to run "soon"
- Returns a Task object
```python
task = asyncio.create_task(fetch_data())
result = await task
```

### **asyncio.gather()**
- Runs multiple coroutines concurrently
- Returns results in order
```python
results = await asyncio.gather(task1, task2, task3)
```

### **asyncio.sleep()**
- Non-blocking sleep
- Used to simulate I/O delays
```python
await asyncio.sleep(1)  # Wait 1 second
```

## Common Patterns

### Sequential vs Concurrent
```python
# Sequential (slow)
result1 = await task1()
result2 = await task2()  # Waits for task1

# Concurrent (fast)
task1_obj = asyncio.create_task(task1())
task2_obj = asyncio.create_task(task2())
results = await asyncio.gather(task1_obj, task2_obj)
```

### Error Handling
```python
# Gather with exceptions
results = await asyncio.gather(
    task1(), task2(), task3(),
    return_exceptions=True
)

for result in results:
    if isinstance(result, Exception):
        print(f"Task failed: {result}")
    else:
        print(f"Task succeeded: {result}")
```

### Timeouts
```python
try:
    result = await asyncio.wait_for(task(), timeout=5.0)
except asyncio.TimeoutError:
    print("Task timed out")
```

## Real-World Examples

### Web API Requests
```python
async def fetch_multiple_apis(urls):
    tasks = [fetch_single_api(url) for url in urls]
    return await asyncio.gather(*tasks)
```

### Database Operations
```python
async def process_users(users):
    tasks = [save_user_to_db(user) for user in users]
    return await asyncio.gather(*tasks)
```

### File I/O
```python
async def read_multiple_files(files):
    tasks = [read_file_async(file) for file in files]
    return await asyncio.gather(*tasks)
```

## Common Pitfalls

1. **Forgetting `await`**
   ```python
   # WRONG
   result = fetch_data()  # Returns coroutine, not result
   
   # CORRECT
   result = await fetch_data()
   ```

2. **Blocking operations in async functions**
   ```python
   # BAD - blocks event loop
   async def bad_example():
       time.sleep(1)  # Blocking!
   
   # GOOD - non-blocking
   async def good_example():
       await asyncio.sleep(1)
   ```

3. **Mixing sync and async code**
   ```python
   # Can't call async from sync without event loop
   def sync_function():
       # This won't work
       result = await async_function()
   ```

## Best Practices

1. Use `asyncio.create_task()` for fire-and-forget operations
2. Use `asyncio.gather()` for concurrent execution
3. Always handle timeouts and errors
4. Use `async with` for context managers
5. Profile async code with `asyncio.run()` wrapper

## Performance Notes

- Async is for I/O-bound operations (network, file, database)
- Not for CPU-bound operations (use threads/processes instead)
- Event loop runs on single thread
- Context switching is lightweight