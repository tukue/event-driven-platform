"""
Unit tests for Redis Streams integration
Tests stream publishing, consuming, and consumer group operations
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from models import PizzaOrder, OrderEvent, OrderStatus
from services.order_service import OrderService
from redis_client import RedisClient


@pytest.fixture
def mock_redis_streams():
    """Create a mock Redis client with streams support"""
    mock = MagicMock()
    mock.client = AsyncMock()
    
    # Storage for orders and streams
    mock._storage = {}
    mock._streams = {}
    
    # Mock set/get for orders
    async def mock_set(key, value):
        mock._storage[key] = value
        return True
    
    async def mock_get(key):
        return mock._storage.get(key)
    
    async def mock_keys(pattern):
        return [k for k in mock._storage.keys() if pattern.replace("*", "") in k]
    
    # Mock pub/sub
    mock.publish = AsyncMock(return_value=1)
    
    # Mock stream operations
    async def mock_add_to_stream(stream_name, event_data, stream_id="*"):
        if stream_name not in mock._streams:
            mock._streams[stream_name] = []
        if stream_id == "*":
            stream_id = f"{len(mock._streams[stream_name])+1}-0"
        mock._streams[stream_name].append((stream_id, event_data))
        return stream_id
    
    async def mock_read_stream(stream_name, start_id="0", stop_id="+", count=None):
        if stream_name not in mock._streams:
            return []
        entries = mock._streams[stream_name]
        if count:
            return entries[-count:]
        return entries
    
    async def mock_get_stream_info(stream_name):
        if stream_name in mock._streams:
            return {
                "length": len(mock._streams[stream_name]),
                "first-entry": mock._streams[stream_name][0] if mock._streams[stream_name] else None,
                "last-entry": mock._streams[stream_name][-1] if mock._streams[stream_name] else None,
            }
        return None
    
    async def mock_create_consumer_group(stream_name, group_name, start_id="0", mkstream=True):
        return True
    
    async def mock_acknowledge_message(stream_name, group_name, message_ids):
        return len(message_ids)
    
    async def mock_read_stream_group(stream_name, group_name, consumer_name, count=1, block=None):
        if stream_name not in mock._streams:
            return []
        entries = mock._streams[stream_name]
        if count and len(entries) > 0:
            return [(stream_name, entries[-count:])]
        return []
    
    async def mock_trim_stream(stream_name, max_len, approximate=True):
        if stream_name in mock._streams:
            mock._streams[stream_name] = mock._streams[stream_name][-max_len:]
        return len(mock._streams.get(stream_name, []))
    
    async def mock_get_pending_messages(stream_name, group_name, consumer_name=None):
        return []
    
    # Assign all methods
    mock.client.set = mock_set
    mock.client.get = mock_get
    mock.client.keys = mock_keys
    mock.add_to_stream = mock_add_to_stream
    mock.read_stream = mock_read_stream
    mock.get_stream_info = mock_get_stream_info
    mock.create_consumer_group = mock_create_consumer_group
    mock.acknowledge_message = mock_acknowledge_message
    mock.read_stream_group = mock_read_stream_group
    mock.trim_stream = mock_trim_stream
    mock.get_pending_messages = mock_get_pending_messages
    
    return mock


@pytest.mark.asyncio
async def test_stream_event_publication(mock_redis_streams):
    """Test that events are published to streams"""
    order_service = OrderService(mock_redis_streams)
    
    # Create an order
    order = PizzaOrder(
        supplier_name="Test Pizza Co",
        pizza_name="Margherita",
        supplier_price=15.99,
        markup_percentage=30.0
    )
    
    event = await order_service.create_order(order)
    
    # Verify event was published to stream
    assert "pizza_orders_stream" in mock_redis_streams._streams
    assert len(mock_redis_streams._streams["pizza_orders_stream"]) > 0
    
    # Verify stream entry contains event data
    stream_id, stream_data = mock_redis_streams._streams["pizza_orders_stream"][-1]
    assert stream_data["event_type"] == "order.created"
    assert stream_data["order_id"] == order.id


@pytest.mark.asyncio
async def test_stream_read_operations(mock_redis_streams):
    """Test reading from streams"""
    order_service = OrderService(mock_redis_streams)
    
    # Create multiple orders
    orders = []
    for i in range(3):
        order = PizzaOrder(
            supplier_name=f"Pizza Co {i}",
            pizza_name=f"Pizza {i}",
            supplier_price=15.99 + i,
            markup_percentage=30.0
        )
        event = await order_service.create_order(order)
        orders.append(order)
    
    # Read from stream
    entries = await mock_redis_streams.read_stream("pizza_orders_stream", count=2)
    
    assert len(entries) == 2
    assert entries[-1][1]["event_type"] == "order.created"


@pytest.mark.asyncio
async def test_stream_with_correlation_id(mock_redis_streams):
    """Test stream events with correlation IDs"""
    order_service = OrderService(mock_redis_streams)
    
    # Create an order
    order = PizzaOrder(
        supplier_name="Test Pizza Co",
        pizza_name="Margherita",
        supplier_price=15.99,
        markup_percentage=30.0
    )
    
    event = await order_service.create_order(order)
    
    # Accept order as supplier
    event = await order_service.supplier_respond(order.id, accept=True, estimated_time=30)
    
    # Check that events are in stream
    entries = await mock_redis_streams.read_stream("pizza_orders_stream")
    
    assert len(entries) >= 2
    
    # Both events should be in stream
    event_types = [entry[1]["event_type"] for entry in entries]
    assert "order.created" in event_types
    assert "order.supplier_accepted" in event_types


@pytest.mark.asyncio
async def test_stream_info_retrieval(mock_redis_streams):
    """Test getting stream information"""
    order_service = OrderService(mock_redis_streams)
    
    # Create an order to populate stream
    order = PizzaOrder(
        supplier_name="Test Pizza Co",
        pizza_name="Margherita",
        supplier_price=15.99,
        markup_percentage=30.0
    )
    await order_service.create_order(order)
    
    # Get stream info
    info = await mock_redis_streams.get_stream_info("pizza_orders_stream")
    
    assert info is not None
    assert "length" in info
    assert info["length"] >= 1


@pytest.mark.asyncio
async def test_stream_consumer_group_creation(mock_redis_streams):
    """Test creating consumer groups"""
    # Create consumer group
    result = await mock_redis_streams.create_consumer_group(
        "pizza_orders_stream",
        "test_group"
    )
    
    assert result == True


@pytest.mark.asyncio
async def test_stream_message_acknowledgment(mock_redis_streams):
    """Test acknowledging stream messages"""
    order_service = OrderService(mock_redis_streams)
    
    # Create an order
    order = PizzaOrder(
        supplier_name="Test Pizza Co",
        pizza_name="Margherita",
        supplier_price=15.99,
        markup_percentage=30.0
    )
    await order_service.create_order(order)
    
    # Get message IDs
    entries = await mock_redis_streams.read_stream("pizza_orders_stream")
    message_ids = [entry[0] for entry in entries]
    
    # Acknowledge messages
    ack_count = await mock_redis_streams.acknowledge_message(
        "pizza_orders_stream",
        "test_group",
        message_ids
    )
    
    assert ack_count == len(message_ids)


@pytest.mark.asyncio
async def test_stream_trim_operation(mock_redis_streams):
    """Test trimming streams to maintain size"""
    order_service = OrderService(mock_redis_streams)
    
    # Create 5 orders
    for i in range(5):
        order = PizzaOrder(
            supplier_name=f"Pizza Co {i}",
            pizza_name=f"Pizza {i}",
            supplier_price=15.99,
            markup_percentage=30.0
        )
        await order_service.create_order(order)
    
    # Get initial stream size
    info = await mock_redis_streams.get_stream_info("pizza_orders_stream")
    initial_length = info["length"]
    
    # Trim stream to keep only 2 entries
    await mock_redis_streams.trim_stream("pizza_orders_stream", 2)
    
    # Check trimmed size
    info = await mock_redis_streams.get_stream_info("pizza_orders_stream")
    assert info["length"] <= 2


@pytest.mark.asyncio
async def test_stream_persistence_across_orders(mock_redis_streams):
    """Test that stream persists events across multiple order operations"""
    order_service = OrderService(mock_redis_streams)
    
    # Create order
    order = PizzaOrder(
        supplier_name="Test Pizza Co",
        pizza_name="Margherita",
        supplier_price=15.99,
        markup_percentage=30.0
    )
    await order_service.create_order(order)
    
    # Accept as supplier
    await order_service.supplier_respond(order.id, accept=True, estimated_time=30)
    
    # Accept as customer
    await order_service.customer_accept(order.id, "John Doe", "123 Main St")
    
    # Dispatch
    await order_service.dispatch_order(order.id, "Bob Driver")
    
    # Check stream has all events
    entries = await mock_redis_streams.read_stream("pizza_orders_stream")
    
    # Should have at least 4 events (create, supplier_accept, customer_accept, dispatch)
    assert len(entries) >= 4
    
    event_types = [entry[1]["event_type"] for entry in entries]
    assert "order.created" in event_types
    assert "order.supplier_accepted" in event_types
    assert "order.customer_accepted" in event_types
    assert "order.dispatched" in event_types


@pytest.mark.asyncio
async def test_stream_batch_operations(mock_redis_streams):
    """Test batch event publishing to streams"""
    order_service = OrderService(mock_redis_streams)
    
    # Create multiple events for batch dispatch
    events = [
        {
            "event_type": "order.preparing",
            "order_id": "order-1",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "event_type": "order.ready",
            "order_id": "order-2",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    # Dispatch batch
    result = await order_service.dispatch_events(events, correlation_id="batch-test-123")
    
    assert result.success == True
    assert result.processed_count == 2
    
    # Verify events in stream
    info = await mock_redis_streams.get_stream_info("pizza_orders_stream")
    assert info is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
