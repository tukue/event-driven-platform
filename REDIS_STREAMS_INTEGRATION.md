# Redis Streams Integration

This document describes the Redis Streams integration implemented in the event-driven pizza delivery platform.

## Overview

Redis Streams provide a powerful data structure for handling event streams with persistence, consumer groups, and reliable message delivery. This integration enhances the existing pub/sub system with:

- **Persistence**: Events are stored and can be replayed
- **Consumer Groups**: Multiple consumers can process events reliably
- **Event Sourcing**: Complete audit trail of all events
- **Scalability**: Better performance for high-throughput scenarios

## Architecture

### Dual Publishing Strategy

The system now publishes events to both:
1. **Redis Pub/Sub** (`pizza_orders` channel) - for real-time WebSocket updates
2. **Redis Stream** (`pizza_orders_stream`) - for persistent event storage and processing

### Stream Structure

Each stream entry contains:
```json
{
  "event_type": "order.created",
  "order_id": "uuid-string",
  "timestamp": "2024-01-01T12:00:00.000000",
  "correlation_id": "batch-uuid",  // Optional, for batched events
  "data": "{\"event_type\": \"order.created\", \"order\": {...}, \"timestamp\": \"...\"}"
}
```

## Components

### 1. Enhanced Redis Client (`redis_client.py`)

Added stream operations:
- `add_to_stream()` - Add events to streams
- `read_stream()` - Read events from streams
- `read_stream_group()` - Consumer group reading
- `create_consumer_group()` - Create consumer groups
- `acknowledge_message()` - Acknowledge processed messages
- `get_stream_info()` - Get stream metadata

### 2. Updated Order Service (`services/order_service.py`)

Modified `_publish_event()` and `dispatch_events()` to publish to both pub/sub and streams.

### 3. Stream Consumer Service (`services/stream_consumer.py`)

Asynchronous event processor with:
- Consumer group management
- Event type-based routing
- Error handling and retry logic
- Extensible handler registration

### 4. Stream Inspector (`inspect_streams.py`)

Command-line utility for:
- Viewing stream information
- Reading recent events
- Managing consumer groups
- Stream maintenance operations

### 5. Test Suite (`test_streams.py`)

Comprehensive tests for:
- Stream publishing/consuming
- Consumer group operations
- Error handling scenarios

## Usage

### Starting the System

The stream consumer starts automatically with the FastAPI application:

```bash
cd backend
python main.py
```

## Testing the Integration

```bash
cd backend
python -m pytest tests/test_streams_integration.py -v
python test_streams.py
```

### Inspecting Streams

Use the stream inspector utility:

```bash
# Get stream information
python inspect_streams.py info pizza_orders_stream

# Read recent events
python inspect_streams.py read pizza_orders_stream 20

# List all streams
python inspect_streams.py list

# Get consumer group info
python inspect_streams.py group-info pizza_orders_stream event_processors

# Create a consumer group
python inspect_streams.py create-group pizza_orders_stream my_group 0

# Trim stream to max length
python inspect_streams.py trim pizza_orders_stream 1000

# Clear stream (delete all entries)
python inspect_streams.py clear pizza_orders_stream
```

### Testing Streams

Run the test suite:

```bash
python test_streams.py
```

## Event Processing

### Built-in Event Handlers

The `StreamConsumer` includes handlers for:
- `order.created` - Log order creation
- `order.supplier_accepted` - Track supplier responses
- `order.customer_accepted` - Track customer confirmations
- `order.dispatched` - Track dispatches
- `order.delivered` - Track deliveries

### Adding Custom Handlers

```python
from services.stream_consumer import event_processor

# Register a custom handler
async def my_custom_handler(event_data):
    print(f"Custom processing: {event_data}")

event_processor.consumer.register_handler("order.custom_event", my_custom_handler)
```

## Consumer Groups

### Default Consumer Group

- **Name**: `event_processors`
- **Stream**: `pizza_orders_stream`
- **Behavior**: Processes events asynchronously for metrics, notifications, etc.

### Creating Additional Groups

For different processing needs:

```python
# Analytics consumer group
await redis_client.create_consumer_group("pizza_orders_stream", "analytics_group")

# Notification consumer group
await redis_client.create_consumer_group("pizza_orders_stream", "notification_group")
```

## Monitoring and Maintenance

### Stream Health Checks

```python
# Get stream info
info = await redis_client.get_stream_info("pizza_orders_stream")
print(f"Stream length: {info['length']}")

# Check pending messages
pending = await redis_client.get_pending_messages("pizza_orders_stream", "event_processors")
```

### Stream Trimming

To prevent unbounded growth:

```python
# Keep only last 10,000 events
await redis_client.trim_stream("pizza_orders_stream", 10000)
```

### Consumer Group Monitoring

```python
# Check consumer lag
consumers = await redis_client.client.xinfo_consumers("pizza_orders_stream", "event_processors")
for consumer in consumers:
    print(f"Consumer {consumer['name']}: {consumer['pending']} pending messages")
```

## Performance Considerations

### Stream Configuration

- **Max Length**: Configure appropriate retention based on use case
- **Consumer Groups**: Use separate groups for different processing needs
- **Batch Processing**: Process multiple messages together for efficiency

### Memory Usage

- Streams consume memory proportional to retained events
- Monitor Redis memory usage
- Implement trimming policies based on business requirements

## Migration Notes

### Backward Compatibility

- Existing pub/sub functionality remains unchanged
- WebSocket clients continue to work without modification
- All existing APIs maintain their behavior

### Data Migration

- Historical events are not automatically migrated to streams
- New events are published to both systems
- Consider running a migration script if historical data is needed in streams

## Troubleshooting

### Common Issues

1. **Consumer not receiving messages**
   - Check consumer group exists: `xinfo_groups pizza_orders_stream`
   - Verify consumer is reading from correct position

2. **Stream growing too large**
   - Implement trimming: `xtrim pizza_orders_stream maxlen 10000`
   - Consider retention policies

3. **Duplicate processing**
   - Ensure messages are acknowledged after processing
   - Check consumer group configuration

### Debug Commands

```bash
# View stream contents
redis-cli xread streams pizza_orders_stream 0

# Check consumer groups
redis-cli xinfo groups pizza_orders_stream

# View pending messages
redis-cli xpending pizza_orders_stream event_processors

# Monitor stream additions
redis-cli xread block 0 streams pizza_orders_stream $
```

## Future Enhancements

- **Event Replay**: Implement event replay functionality for testing/debugging
- **Stream Analytics**: Add real-time analytics on event streams
- **Multi-Stream Processing**: Support for processing events across multiple streams
- **Dead Letter Queues**: Handle failed event processing
- **Event Schema Validation**: Validate event structure before processing
