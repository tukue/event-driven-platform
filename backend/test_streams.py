#!/usr/bin/env python3
"""
Test script for Redis Streams integration
Demonstrates publishing events to streams and consuming them.
"""

import asyncio
import json
from datetime import datetime
from redis_client import redis_client
from services.stream_consumer import StreamConsumer
from models import PizzaOrder, OrderEvent, OrderStatus

async def test_stream_operations():
    """Test basic stream operations"""
    print("🔄 Testing Redis Streams integration...")

    await redis_client.connect()

    try:
        # Test 1: Add events to stream
        print("\n📝 Test 1: Publishing events to stream")

        # Create a sample order
        order = PizzaOrder(
            supplier_name="Test Pizza Co",
            pizza_name="Margherita Pizza",
            supplier_price=15.99,
            markup_percentage=30.0
        )

        # Create events
        events = [
            {
                "event_type": "order.created",
                "order_id": order.id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": json.dumps({
                    "event_type": "order.created",
                    "order": order.model_dump(mode='json'),
                    "timestamp": datetime.utcnow().isoformat()
                }, default=str)
            },
            {
                "event_type": "order.supplier_accepted",
                "order_id": order.id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": json.dumps({
                    "event_type": "order.supplier_accepted",
                    "order": {**order.model_dump(mode='json'), "status": "supplier_accepted"},
                    "timestamp": datetime.utcnow().isoformat()
                }, default=str)
            }
        ]

        # Add events to stream
        stream_ids = []
        for event in events:
            stream_id = await redis_client.add_to_stream("test_stream", event)
            stream_ids.append(stream_id)
            print(f"✅ Added event to stream: {stream_id}")

        # Test 2: Read events from stream
        print("\n📖 Test 2: Reading events from stream")
        entries = await redis_client.read_stream("test_stream", "0", count=10)

        for entry_id, data in entries:
            print(f"📄 Event ID: {entry_id}")
            print(f"   Type: {data.get('event_type')}")
            print(f"   Order ID: {data.get('order_id')}")

        # Test 3: Consumer group operations
        print("\n👥 Test 3: Consumer group operations")

        # Create consumer group
        await redis_client.create_consumer_group("test_stream", "test_group")
        print("✅ Created consumer group 'test_group'")

        # Read from consumer group
        messages = await redis_client.read_stream_group(
            "test_stream", "test_group", "test_consumer", count=2
        )

        if messages:
            message_ids = []
            for stream_messages in messages:
                stream_name, entries = stream_messages
                for message_id, message_data in entries:
                    print(f"📨 Consumed message: {message_id}")
                    print(f"   Event: {message_data.get('event_type')}")
                    message_ids.append(message_id)

            # Acknowledge messages
            if message_ids:
                await redis_client.acknowledge_message("test_stream", "test_group", message_ids)
                print("✅ Acknowledged messages")

        # Test 4: Stream consumer
        print("\n🔄 Test 4: Stream consumer")

        consumer = StreamConsumer(stream_name="test_stream", group_name="test_group")

        # Register a test handler
        async def test_handler(event_data):
            print(f"🎯 Handler called for event: {event_data.get('event_type')}")

        consumer.register_handler("order.created", test_handler)
        consumer.register_handler("order.supplier_accepted", test_handler)

        # Add one more event to test consumer
        test_event = {
            "event_type": "order.created",
            "order_id": "test-order-123",
            "timestamp": datetime.utcnow().isoformat(),
            "data": json.dumps({
                "event_type": "order.created",
                "order": {"id": "test-order-123", "pizza_name": "Test Pizza"},
                "timestamp": datetime.utcnow().isoformat()
            }, default=str)
        }

        await redis_client.add_to_stream("test_stream", test_event)
        print("✅ Added test event for consumer")

        # Start consumer briefly
        consumer_task = asyncio.create_task(consumer.start_consuming())

        # Let it run for a few seconds
        await asyncio.sleep(3)

        # Stop consumer
        await consumer.stop_consuming()
        consumer_task.cancel()

        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        print("✅ Consumer test completed")

        # Test 5: Stream info
        print("\n📊 Test 5: Stream information")
        info = await redis_client.get_stream_info("test_stream")
        if info:
            print(f"Stream length: {info.get('length', 'N/A')}")
            print(f"First entry: {info.get('first-entry', ['N/A'])[0] if info.get('first-entry') else 'N/A'}")
            print(f"Last entry: {info.get('last-entry', ['N/A'])[0] if info.get('last-entry') else 'N/A'}")

        print("\n🎉 All Redis Streams tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_stream_operations())