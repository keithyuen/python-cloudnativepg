#!/usr/bin/env python3

import asyncio
import aiohttp
import random
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import backoff

class APILoadTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.items = []
        self.stats = {
            "create": {"success": 0, "fail": 0, "time": 0},
            "read": {"success": 0, "fail": 0, "time": 0},
            "update": {"success": 0, "fail": 0, "time": 0},
            "delete": {"success": 0, "fail": 0, "time": 0},
            "read_all": {"success": 0, "fail": 0, "time": 0}
        }
        self.semaphore = asyncio.Semaphore(20)  # Limit concurrent requests
        self.rate_limit = asyncio.Semaphore(100)  # Limit requests per second

    @backoff.on_exception(backoff.expo, 
                         (aiohttp.ClientError, asyncio.TimeoutError),
                         max_tries=3)
    async def _make_request(self, session, method, url, **kwargs):
        async with self.semaphore:  # Limit concurrent requests
            async with self.rate_limit:  # Rate limiting
                try:
                    async with getattr(session, method.lower())(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Too Many Requests
                            await asyncio.sleep(1)  # Wait before retry
                            raise aiohttp.ClientError("Rate limit exceeded")
                        else:
                            raise aiohttp.ClientError(f"HTTP {response.status}")
                except Exception as e:
                    print(f"Request error: {e}")
                    raise

    async def create_item(self, session, name):
        start_time = time.time()
        try:
            item = await self._make_request(
                session, "post", f"{self.base_url}/items",
                json={"title": name, "description": f"Test item {name}"}
            )
            self.items.append(item["id"])
            self.stats["create"]["success"] += 1
        except Exception as e:
            print(f"Create error: {e}")
            self.stats["create"]["fail"] += 1
        finally:
            self.stats["create"]["time"] += time.time() - start_time

    async def read_item(self, session, item_id):
        start_time = time.time()
        try:
            await self._make_request(session, "get", f"{self.base_url}/items/{item_id}")
            self.stats["read"]["success"] += 1
        except Exception as e:
            print(f"Read error: {e}")
            self.stats["read"]["fail"] += 1
        finally:
            self.stats["read"]["time"] += time.time() - start_time

    async def update_item(self, session, item_id):
        start_time = time.time()
        try:
            await self._make_request(
                session, "put", f"{self.base_url}/items/{item_id}",
                json={"title": f"Updated {item_id}", "description": f"Updated test item {item_id}"}
            )
            self.stats["update"]["success"] += 1
        except Exception as e:
            print(f"Update error: {e}")
            self.stats["update"]["fail"] += 1
        finally:
            self.stats["update"]["time"] += time.time() - start_time

    async def delete_item(self, session, item_id):
        start_time = time.time()
        try:
            await self._make_request(session, "delete", f"{self.base_url}/items/{item_id}")
            self.stats["delete"]["success"] += 1
        except Exception as e:
            print(f"Delete error: {e}")
            self.stats["delete"]["fail"] += 1
        finally:
            self.stats["delete"]["time"] += time.time() - start_time

    async def read_all_items(self, session):
        start_time = time.time()
        try:
            await self._make_request(session, "get", f"{self.base_url}/items")
            self.stats["read_all"]["success"] += 1
        except Exception as e:
            print(f"Read all error: {e}")
            self.stats["read_all"]["fail"] += 1
        finally:
            self.stats["read_all"]["time"] += time.time() - start_time

    def print_stats(self):
        print("\nTest Results:")
        print("=" * 50)
        for operation, stats in self.stats.items():
            total = stats["success"] + stats["fail"]
            if total > 0:
                avg_time = stats["time"] / total
                success_rate = (stats["success"] / total) * 100
                print(f"\n{operation.upper()}:")
                print(f"Total requests: {total}")
                print(f"Success rate: {success_rate:.2f}%")
                print(f"Average response time: {avg_time:.4f}s")

    async def run_test(self, num_requests=10000):
        print(f"Starting load test with {num_requests} requests...")
        start_time = datetime.now()

        # Create TCP connection pool with limits
        connector = aiohttp.TCPConnector(
            limit=20,  # Limit concurrent connections
            limit_per_host=10,  # Limit connections per host
            ttl_dns_cache=300,  # Cache DNS results
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout for the whole request
            connect=10,  # Timeout for connecting to the server
            sock_read=10  # Timeout for reading from the socket
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"Connection": "keep-alive"}
        ) as session:
            # Create items
            create_tasks = []
            for i in range(num_requests // 4):
                task = self.create_item(session, f"Item {i}")
                create_tasks.append(task)
                await asyncio.sleep(0.01)  # Small delay between requests
            await asyncio.gather(*create_tasks)

            # Mix of read, update, and list operations
            mixed_tasks = []
            for _ in range(num_requests // 2):
                if self.items:
                    item_id = random.choice(self.items)
                    operation = random.choice([
                        lambda: self.read_item(session, item_id),
                        lambda: self.update_item(session, item_id),
                        lambda: self.read_all_items(session)
                    ])
                    mixed_tasks.append(operation())
                    await asyncio.sleep(0.01)  # Small delay between requests
            await asyncio.gather(*mixed_tasks)

            # Delete items
            delete_tasks = []
            for item_id in self.items[:]:
                task = self.delete_item(session, item_id)
                delete_tasks.append(task)
                await asyncio.sleep(0.01)  # Small delay between requests
            await asyncio.gather(*delete_tasks)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\nLoad Test Complete!")
        print(f"Total duration: {duration:.2f} seconds")
        print(f"Average requests per second: {num_requests/duration:.2f}")
        self.print_stats()

async def health_check(url="http://localhost:8000"):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "healthy":
                        return True
    except:
        pass
    return False

async def main():
    parser = argparse.ArgumentParser(description='API Load Tester')
    parser.add_argument('--requests', type=int, default=10000,
                      help='Number of requests to perform (default: 10000)')
    parser.add_argument('--url', type=str, default="http://localhost:8000",
                      help='Base URL of the API (default: http://localhost:8000)')
    args = parser.parse_args()

    # Check if the API is available
    print("Checking API health...")
    if not await health_check(args.url):
        print("Error: API is not available. Please make sure the application is running.")
        return

    # Run the load test
    tester = APILoadTester(args.url)
    await tester.run_test(args.requests)

if __name__ == "__main__":
    asyncio.run(main()) 