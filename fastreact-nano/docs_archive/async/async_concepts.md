# Async/Await Concepts Explained

## Basic Concepts

**Asynchronous Programming**: Allows tasks to run concurrently without blocking the main thread.
**Sync**: Tasks run sequentially, each blocks until completion.
**Async**: Tasks can start, pause, resume while waiting for I/O.

## Key Syntax

### 1. Defining Async Functions
```python
async def fetch_data():
    await asyncio.sleep(1)
    return "data"
```

### 2. Calling Async Functions
```python
# Must use await inside async functions
result = await fetch_data()

# Or schedule with create_task()
task = asyncio.create_task(fetch_data())
```

### 3. Running Async Code
```python
# Entry point
asyncio.run(main())
```

## Real Examples from Codebase

### From test_agent.py:
```python
@pytest.mark.asyncio  # Mark test as async
async def test_run_method_exists(self):
    """Test run method is callable"""
    agent = Agent()
    assert inspect.iscoroutinefunction(agent.run)
```

### Async Generator:
```python
async def stream_to_iterator(callback, generator):
    async for chunk in generator:  # Process each chunk as it arrives
        await callback(chunk)  # Non-blocking callback
```

## Key Differences

| Sync | Async |
|------|-------|
| `time.sleep(1)` | `await asyncio.sleep(1)` |
| Blocks execution | Yields control |
| Sequential | Concurrent |
| Simple | More complex |

## When to Use Async

✅ **I/O-bound operations**: Network requests, file reading, database queries
✅ **Multiple concurrent tasks**: Fetching multiple APIs, processing streams
❌ **CPU-bound operations**: Math calculations, data processing (use threads)

## Common Patterns

1. **Concurrent Tasks**:
```python
tasks = [asyncio.create_task(fetch(url)) for url in urls]
results = await asyncio.gather(*tasks)
```

2. **Timeout Handling**:
```python
try:
    result = await asyncio.wait_for(fetch(), timeout=5.0)
except asyncio.TimeoutError:
    print("Timeout!")
```

3. **Async Context Managers**:
```python
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

## Best Practices

1. Always use `await` with async functions
2. Use `asyncio.create_task()` for fire-and-forget
3. Handle exceptions with try/except in async code
4. Use `asyncio.gather()` for waiting on multiple tasks
5. Avoid mixing sync and async code unnecessarily

## Common Pitfalls

1. **Forgetting `await`**: Code won't execute
2. **Blocking calls**: Using `time.sleep()` instead of `asyncio.sleep()`
3. **Async in sync context**: Can't call `await` in regular functions
4. **Unawaited tasks**: Tasks that never get awaited may not complete

## Performance Impact

**Sync** (2 tasks, 1s each): ~2 seconds total
**Async** (2 tasks, 1s each): ~1 second total (concurrent!)

The example shows async tasks complete in half the time by running concurrently instead of sequentially.