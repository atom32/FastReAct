# Async/Await Cheatsheet

## Core Concepts

### 1. Defining Async Functions
```python
async def fetch_data():      # Coroutine function
    return await get_data()  # Returns coroutine object
```

### 2. Running Async Code
```python
# Python 3.7+
result = asyncio.run(main())

# Python <3.7
loop = asyncio.get_event_loop()
result = loop.run_until_complete(main())
```

### 3. Creating Tasks
```python
# Start executing immediately
task = asyncio.create_task(my_coroutine())
await task  # Wait for completion
```

### 4. Concurrent Execution

**Option A: gather()** (all results)
```python
results = await asyncio.gather(
    task1(),
    task2(),
    task3()
)
```

**Option B: as_completed()** (as they finish)
```python
tasks = [task1(), task2(), task3()]
for completed in asyncio.as_completed(tasks):
    result = await completed
    process(result)
```

**Option C: wait()** (control groups)
```python
done, pending = await asyncio.wait(tasks, timeout=5.0)
```

### 5. Common Patterns

**Timeout handling:**
```python
try:
    result = await asyncio.wait_for(task(), timeout=2.0)
except asyncio.TimeoutError:
    print("Timeout!")
```

**Shield from cancellation:**
```python
# Task won't be cancelled
result = await asyncio.shield(task())
```

**Sleep (non-blocking):**
```python
await asyncio.sleep(1.0)  # Yield control for 1 second
```

### 6. Event Loop Control
```python
# Run until complete
loop.run_until_complete(main())

# Run forever
loop.run_forever()

# Stop gracefully
loop.stop()
```

### 7. Synchronization Primitives

**Lock:**
```python
lock = asyncio.Lock()
async with lock:
    # Critical section
```

**Semaphore:**
```python
sem = asyncio.Semaphore(5)  # Max 5 concurrent
async with sem:
    # Limited concurrency
```

**Queue:**
```python
queue = asyncio.Queue()
await queue.put(item)
item = await queue.get()
```

### 8. Mixing Sync/Async

**Run sync in thread pool:**
```python
result = await loop.run_in_executor(None, blocking_function)
```

**Call async from sync:**
```python
# Not recommended, but possible
asyncio.run(async_function())
```

### 9. Error Handling
```python
try:
    await risky_task()
except Exception as e:
    print(f"Error: {e}")

# Gather with return_exceptions
results = await asyncio.gather(
    task1(),
    task2(),
    return_exceptions=True
)
```

### 10. Best Practices

1. **Don't mix sync/async I/O** - Use `run_in_executor` for blocking calls
2. **Use async context managers** - `async with` for async resources
3. **Cancel tasks properly** - Handle `asyncio.CancelledError`
4. **Limit concurrency** - Use semaphores for rate limiting
5. **Monitor tasks** - Keep references to track completion
6. **Use structured concurrency** - Group related tasks

## Common Pitfalls

1. **Forgetting `await`** - Coroutine won't execute
2. **Blocking calls in async** - Blocks entire event loop
3. **Creating too many tasks** - Memory/CPU overhead
4. **Not handling cancellation** - Resources may leak
5. **Race conditions** - Use locks/semaphores

## Performance Tips

1. **Batch operations** - Group I/O calls when possible
2. **Connection pooling** - Reuse connections
3. **Timeouts everywhere** - Prevent hanging tasks
4. **Monitor event loop** - Watch for bottlenecks
5. **Profile with `asyncio.run()`** - Use debug mode for issues

## When to Use Async

✅ **Good for:**
- Network I/O (HTTP, WebSockets, databases)
- File I/O (with proper async libraries)
- Web servers/frameworks
- Chat bots/real-time systems
- Concurrent API calls

❌ **Not for:**
- CPU-bound computations (use multiprocessing)
- Simple scripts with no I/O
- Legacy synchronous codebases
- When simplicity > performance

## Example: Web Scraper
```python
async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    async with aiohttp.ClientSession() as session:
        urls = ["url1", "url2", "url3"]
        tasks = [fetch_url(session, url) for url in urls]
        pages = await asyncio.gather(*tasks)
        return pages
```