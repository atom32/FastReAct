"""
Real-world async/await examples
"""

import asyncio
import aiohttp
import aiofiles
from datetime import datetime

# Example 1: Web scraping with async
async def fetch_urls_concurrently():
    print("\n=== Web Scraping Example ===")
    
    urls = [
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/2',
        'https://httpbin.org/delay/1'
    ]
    
    async def fetch_url(session, url):
        async with session.get(url) as response:
            return await response.text()
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        print(f"Fetched {len(results)} URLs concurrently")

# Example 2: File I/O with async
async def async_file_operations():
    print("\n=== Async File Operations ===")
    
    async def write_file(filename, content):
        async with aiofiles.open(filename, 'w') as f:
            await f.write(content)
        return f"Wrote {filename}"
    
    async def read_file(filename):
        async with aiofiles.open(filename, 'r') as f:
            content = await f.read()
        return content
    
    # Write multiple files concurrently
    tasks = [
        write_file("test1.txt", "Hello from async file 1"),
        write_file("test2.txt", "Hello from async file 2"),
        write_file("test3.txt", "Hello from async file 3")
    ]
    
    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)
    
    # Read them back
    content = await read_file("test1.txt")
    print(f"Read content: {content[:20]}...")

# Example 3: Database operations simulation
async def simulate_database_operations():
    print("\n=== Database Operations ===")
    
    async def query_database(query, delay):
        print(f"Starting query: {query}")
        await asyncio.sleep(delay)
        print(f"Completed query: {query}")
        return f"Result: {query}"
    
    queries = [
        ("SELECT * FROM users", 2),
        ("SELECT COUNT(*) FROM orders", 1),
        ("UPDATE products SET price = price * 1.1", 3),
        ("DELETE FROM logs WHERE date < '2023-01-01'", 1.5)
    ]
    
    tasks = [query_database(q, d) for q, d in queries]
    results = await asyncio.gather(*tasks)
    print(f"Executed {len(results)} queries concurrently")

# Example 4: Rate limiting with semaphores
async def rate_limited_requests():
    print("\n=== Rate Limited Requests ===")
    
    # Limit to 2 concurrent requests
    semaphore = asyncio.Semaphore(2)
    
    async def make_request(url):
        async with semaphore:
            print(f"Starting request to {url}")
            await asyncio.sleep(1)  # Simulate network request
            print(f"Completed request to {url}")
            return url
    
    urls = [f"https://api.example.com/resource/{i}" for i in range(5)]
    tasks = [make_request(url) for url in urls]
    await asyncio.gather(*tasks)

# Example 5: Producer-consumer pattern
async def producer_consumer():
    print("\n=== Producer-Consumer Pattern ===")
    
    queue = asyncio.Queue(maxsize=3)
    
    async def producer(name, items):
        for i in range(items):
            item = f"Item {i} from {name}"
            await queue.put(item)
            print(f"{name} produced: {item}")
            await asyncio.sleep(0.5)
        await queue.put(None)  # Signal completion
    
    async def consumer(name):
        while True:
            item = await queue.get()
            if item is None:
                queue.put(None)  # Pass signal to other consumers
                break
            print(f"{name} consumed: {item}")
            await asyncio.sleep(1)
    
    # Run producers and consumers concurrently
    producers = [
        producer("Producer1", 3),
        producer("Producer2", 2)
    ]
    
    consumers = [
        consumer("Consumer1"),
        consumer("Consumer2")
    ]
    
    await asyncio.gather(*producers)
    await asyncio.gather(*consumers)

async def main():
    # Run examples
    await fetch_urls_concurrently()
    await async_file_operations()
    await simulate_database_operations()
    await rate_limited_requests()
    await producer_consumer()
    
    print("\n=== Common Use Cases ===")
    print("1. Web scraping/crawling")
    print("2. API calls to multiple services")
    print("3. Database queries")
    print("4. File I/O operations")
    print("5. Network servers (websockets, HTTP)")
    print("6. Real-time applications")
    
    print("\n=== When NOT to use async ===")
    print("1. CPU-bound tasks (use multiprocessing)")
    print("2. Simple synchronous code")
    print("3. Blocking I/O without async alternatives")

if __name__ == "__main__":
    asyncio.run(main())