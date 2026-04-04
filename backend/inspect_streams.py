#!/usr/bin/env python3
"""
Redis Streams Inspection and Management Utility
Provides tools to inspect, monitor, and manage Redis Streams in the event-driven platform.
"""

import asyncio
import json
import sys
from datetime import datetime
from redis_client import redis_client

class StreamInspector:
    """Utility class for inspecting and managing Redis Streams"""

    def __init__(self):
        self.redis = redis_client

    async def connect(self):
        """Connect to Redis"""
        await self.redis.connect()

    async def disconnect(self):
        """Disconnect from Redis"""
        await self.redis.disconnect()

    async def get_stream_info(self, stream_name: str):
        """Get detailed information about a stream"""
        info = await self.redis.get_stream_info(stream_name)
        if info:
            print(f"\n=== Stream Info: {stream_name} ===")
            print(f"Length: {info.get('length', 'N/A')}")
            print(f"First entry ID: {info.get('first-entry', ['N/A'])[0] if info.get('first-entry') else 'N/A'}")
            print(f"Last entry ID: {info.get('last-entry', ['N/A'])[0] if info.get('last-entry') else 'N/A'}")

            # Get consumer groups
            try:
                groups = await self.redis.client.xinfo_groups(stream_name)
                if groups:
                    print(f"Consumer Groups: {len(groups)}")
                    for group in groups:
                        print(f"  - {group['name']}: {group['consumers']} consumers, {group['pending']} pending")
                else:
                    print("Consumer Groups: None")
            except Exception as e:
                print(f"Consumer Groups: Error - {e}")
        else:
            print(f"Stream '{stream_name}' does not exist or is empty")

    async def read_recent_events(self, stream_name: str, count: int = 10):
        """Read the most recent events from a stream"""
        try:
            entries = await self.redis.read_stream(stream_name, "-", "+", count=count)
            print(f"\n=== Recent Events from {stream_name} (last {count}) ===")

            for entry_id, data in reversed(entries):  # Show newest first
                timestamp = data.get('timestamp', 'N/A')
                event_type = data.get('event_type', 'N/A')
                correlation_id = data.get('correlation_id', 'N/A')

                print(f"\nID: {entry_id}")
                print(f"Event Type: {event_type}")
                print(f"Timestamp: {timestamp}")
                print(f"Correlation ID: {correlation_id}")

                # Try to parse the data field
                try:
                    event_data = json.loads(data.get('data', '{}'))
                    if 'order' in event_data:
                        order = event_data['order']
                        print(f"Order ID: {order.get('id', 'N/A')}")
                        print(f"Status: {order.get('status', 'N/A')}")
                        print(f"Pizza: {order.get('pizza_name', 'N/A')}")
                except:
                    print(f"Raw Data: {data.get('data', 'N/A')[:200]}...")

        except Exception as e:
            print(f"Error reading stream: {e}")

    async def list_all_streams(self):
        """List all Redis streams in the database"""
        try:
            # Get all keys that look like streams (this is a heuristic)
            keys = await self.redis.client.keys("*")
            streams = []

            for key in keys:
                try:
                    # Check if it's a stream by trying to get stream info
                    info = await self.redis.get_stream_info(key)
                    if info:
                        streams.append((key, info.get('length', 0)))
                except:
                    pass

            print("\n=== Redis Streams ===")
            if streams:
                for stream_name, length in sorted(streams):
                    print(f"{stream_name}: {length} entries")
            else:
                print("No streams found")

        except Exception as e:
            print(f"Error listing streams: {e}")

    async def get_consumer_group_info(self, stream_name: str, group_name: str):
        """Get detailed information about a consumer group"""
        try:
            print(f"\n=== Consumer Group Info: {group_name} on {stream_name} ===")

            # Get pending messages
            pending = await self.redis.get_pending_messages(stream_name, group_name)
            if pending:
                print(f"Pending messages: {len(pending)}")
                for item in pending[:5]:  # Show first 5
                    print(f"  Consumer: {item.get('consumer', 'N/A')}, Messages: {item.get('count', 0)}")
            else:
                print("No pending messages")

            # Get consumer info
            consumers = await self.redis.client.xinfo_consumers(stream_name, group_name)
            if consumers:
                print(f"Consumers: {len(consumers)}")
                for consumer in consumers:
                    print(f"  - {consumer['name']}: {consumer['pending']} pending")
            else:
                print("No consumers")

        except Exception as e:
            print(f"Error getting consumer group info: {e}")

    async def create_consumer_group(self, stream_name: str, group_name: str, start_id: str = "0"):
        """Create a consumer group"""
        try:
            await self.redis.create_consumer_group(stream_name, group_name, start_id)
            print(f"Created consumer group '{group_name}' on stream '{stream_name}' starting at ID '{start_id}'")
        except Exception as e:
            print(f"Error creating consumer group: {e}")

    async def trim_stream(self, stream_name: str, max_len: int):
        """Trim a stream to maximum length"""
        try:
            await self.redis.trim_stream(stream_name, max_len)
            print(f"Trimmed stream '{stream_name}' to maximum {max_len} entries")
        except Exception as e:
            print(f"Error trimming stream: {e}")

    async def clear_stream(self, stream_name: str):
        """Delete all entries from a stream"""
        try:
            await self.redis.client.delete(stream_name)
            print(f"Cleared stream '{stream_name}'")
        except Exception as e:
            print(f"Error clearing stream: {e}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_streams.py <command> [args...]")
        print("\nCommands:")
        print("  info <stream_name>              - Get stream information")
        print("  read <stream_name> [count]      - Read recent events (default 10)")
        print("  list                            - List all streams")
        print("  group-info <stream> <group>     - Get consumer group info")
        print("  create-group <stream> <group> [start_id] - Create consumer group")
        print("  trim <stream> <max_len>         - Trim stream to max length")
        print("  clear <stream>                  - Clear all entries from stream")
        return

    inspector = StreamInspector()
    await inspector.connect()

    try:
        command = sys.argv[1]

        if command == "info" and len(sys.argv) >= 3:
            await inspector.get_stream_info(sys.argv[2])

        elif command == "read" and len(sys.argv) >= 3:
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            await inspector.read_recent_events(sys.argv[2], count)

        elif command == "list":
            await inspector.list_all_streams()

        elif command == "group-info" and len(sys.argv) >= 4:
            await inspector.get_consumer_group_info(sys.argv[2], sys.argv[3])

        elif command == "create-group" and len(sys.argv) >= 4:
            start_id = sys.argv[4] if len(sys.argv) > 4 else "0"
            await inspector.create_consumer_group(sys.argv[2], sys.argv[3], start_id)

        elif command == "trim" and len(sys.argv) >= 4:
            await inspector.trim_stream(sys.argv[2], int(sys.argv[3]))

        elif command == "clear" and len(sys.argv) >= 3:
            await inspector.clear_stream(sys.argv[2])

        else:
            print("Invalid command or arguments")

    finally:
        await inspector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())