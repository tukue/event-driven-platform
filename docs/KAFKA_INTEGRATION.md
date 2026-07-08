# Kafka / Redpanda Integration

This document describes the Kafka integration implemented in the event-driven pizza delivery platform.

## Overview

Apache Kafka (via Redpanda — a Kafka-compatible event streaming platform) adds a durable, replayable, scalable event backbone alongside the existing Redis infrastructure. The integration follows a **dual-write migration strategy**: events are published to both Redis Streams and Kafka, allowing zero-risk adoption.

Key benefits over Redis-only eventing:

- **Durable retention** — Configurable time/size-based retention, compaction, replay
- **Consumer groups** — Independent offset tracking per consumer group
- **Partitioning** — Per-order ordering guarantees via key-based partitioning
- **Horizontal scalability** — Multi-broker, partition rebalancing across consumers
- **Ecosystem** — Kafka Connect, ksqlDB, Kafka Streams API

## Architecture

### Dual-Write Event Bus

```
  OrderService
       │
       ├──► Redis KV (order:{id})          — state storage (unchanged)
       │
       ├──► Redis Pub/Sub (pizza_orders)    — fallback WebSocket broadcast
       │
       ├──► Redis Stream (pizza_orders_stream)  — durable log (Phase 1)
       │
       └──► Kafka (pizza.orders)            — durable event backbone (NEW)
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
           ┌─────────────────┐        ┌──────────────────┐        ┌──────────────────┐
           │ WebSocketBridge │        │ MetricsProcessor │        │ AuditLogger      │
           │ (group: ws-bridge)       │ (future)         │        │ (future)         │
           │ broadcast to WS │        │                  │        │                  │
           └─────────────────┘        └──────────────────┘        └──────────────────┘
```

### Kafka Topic Design

| Topic          | Partitions | Key         | Retention     | Purpose                      |
|----------------|------------|-------------|---------------|------------------------------|
| `pizza.orders` | 3          | `order_id`  | 7 days        | All order lifecycle events   |

**Partitioning by `order_id`** ensures all events for a single order land on the same partition, preserving order.

### Message Format

Each Kafka message is a JSON object (the same structure used by Redis Pub/Sub and Streams):

```json
{
  "event_type": "order.created",
  "order": {
    "id": "uuid-string",
    "tracking_id": "PIZZA-2026-001234",
    "supplier_name": "Pizza Palace",
    "pizza_name": "Margherita",
    "supplier_price": 10.0,
    "customer_price": 13.0,
    "markup_percentage": 30.0,
    "status": "pending_supplier",
    "customer_name": null,
    "delivery_address": null,
    "driver_name": null,
    "estimated_delivery_time": null,
    "supplier_notes": null,
    "created_at": "2026-07-08T12:00:00",
    "updated_at": "2026-07-08T12:00:00"
  },
  "timestamp": "2026-07-08T12:00:00.000000",
  "correlation_id": null
}
```

## Components

### 1. Kafka Producer (`services/kafka_service.py` — `KafkaService`)

Manages the `AIOKafkaProducer` lifecycle:

```python
kafka = KafkaService(bootstrap_servers="localhost:9092", topic="pizza.orders")
await kafka.start()       # Connects and starts producer
await kafka.publish_event(event_data)  # Sends to topic, keyed by order_id
await kafka.publish_events(events)     # Batch publish
await kafka.stop()        # Graceful shutdown
```

- `publish_event()` extracts `order_id` from the event dict and uses it as the message key for partitioning.
- `publish_events()` iterates over a list and calls `publish_event()` for each.

### 2. WebSocket Bridge (`services/kafka_service.py` — `WebSocketBridge`)

Replaces Redis Pub/Sub as the real-time event source for the `/ws` WebSocket endpoint when Kafka is active:

```python
bridge = WebSocketBridge(bootstrap_servers="localhost:9092", topic="pizza.orders")
await bridge.start()           # Creates consumer in group "ws-bridge"
bridge.add_connection(ws)      # Register WebSocket for broadcasts
bridge.remove_connection(ws)   # Deregister on disconnect
await bridge.broadcast_loop()  # Background task: consume → broadcast
await bridge.stop()            # Graceful shutdown
```

- Consumer group `ws-bridge` enables horizontal scaling: multiple app instances share the group, each broadcasting to its local WebSocket connections.
- `auto_offset_reset="latest"` ensures the bridge only receives new events (no replay for WebSocket clients).
- Disconnected WebSockets are cleaned up automatically on send failure.

### 3. Updated Order Service (`services/order_service.py`)

`OrderService` now accepts an optional `kafka_service` parameter. When set, `_publish_event()` and `dispatch_events()` dual-write to Kafka alongside Redis Pub/Sub and Streams:

```python
class OrderService:
    def __init__(self, redis_client, kafka_service=None):
        self.redis = redis_client
        self.kafka = kafka_service

    async def _publish_event(self, event: OrderEvent):
        event_data = event.model_dump(mode='json')
        # Always publish to Redis Pub/Sub + Streams
        await self.redis.publish("pizza_orders", json.dumps(event_data))
        await self.redis.add_to_stream("pizza_orders_stream", stream_data)
        # Conditionally publish to Kafka
        if self.kafka:
            await self.kafka.publish_event(event_data)
```

### 4. Application Wiring (`main.py`)

On startup, the application conditionally initializes Kafka if `KAFKA_BOOTSTRAP_SERVERS` is configured:

```python
if settings.kafka_bootstrap_servers:
    kafka_service = KafkaService(settings.kafka_bootstrap_servers, settings.kafka_topic)
    await kafka_service.start()
    order_service.kafka = kafka_service  # inject into order service

    ws_bridge = WebSocketBridge(settings.kafka_bootstrap_servers, settings.kafka_topic)
    await ws_bridge.start()
    asyncio.create_task(ws_bridge.broadcast_loop())
```

The WebSocket endpoint uses Kafka when available, falling back to Redis Pub/Sub:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    if ws_bridge:
        ws_bridge.add_connection(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_bridge.remove_connection(websocket)
    else:
        # Fallback to Redis Pub/Sub
        pubsub = await redis_client.subscribe("pizza_orders")
        ...
```

## Configuration

### Environment Variables

| Variable                   | Default        | Description                              |
|----------------------------|----------------|------------------------------------------|
| `KAFKA_BOOTSTRAP_SERVERS`  | _(empty)_      | Kafka broker address (e.g., `localhost:9092`). Leave empty to disable Kafka. |
| `KAFKA_TOPIC`              | `pizza.orders` | Topic name for order events              |

Set in `backend/.env`:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=pizza.orders
```

### Settings Class (`config.py`)

```python
class Settings(BaseSettings):
    ...
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topic: str = "pizza.orders"
```

## Consumer Groups

Kafka consumer groups enable independent offset management. Each group receives every message, allowing different downstream processing:

| Consumer Group    | Purpose                       | auto.offset.reset | Created By        |
|-------------------|-------------------------------|-------------------|-------------------|
| `ws-bridge`       | WebSocket real-time broadcast | `latest`          | `WebSocketBridge` |
| *(future)* `metrics-processor` | Prometheus/Grafana metrics | `earliest`        | —                 |
| *(future)* `audit-log`        | Durable logging / archival    | `earliest`        | —                 |

Adding new groups requires no topic changes — just start a new consumer with the desired `group_id`.

### Scaling WebSocket Bridge

Multiple app instances can run the `ws-bridge` consumer group. Kafka balances partitions across instances:

- Instance A handles partitions 0, 1 → broadcasts to its local WebSocket connections
- Instance B handles partition 2 → broadcasts to its local WebSocket connections
- Each WebSocket client receives all events (each partition carries a subset, but collectively the group processes all messages)

## Usage

### Starting with Docker (Redpanda)

```bash
# Start Redpanda + app stack
docker compose up -d

# Check Redpanda is running
docker compose logs redpanda

# Create topic (auto-created on first publish)
docker compose exec redpanda rpk topic create pizza.orders --partitions 3
```

### Starting Standalone

```bash
# Terminal 1: Start Redpanda
docker run --rm -p 9092:9092 \
  docker.redpanda.com/redpandadata/redpanda:latest \
  redpanda start --mode dev-container --overprovisioned

# Terminal 2: Start the backend
cd backend
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python main.py

# Terminal 3: Start frontend
cd frontend
npm run dev
```

### Verifying Events in Kafka

```bash
# Using Redpanda's rpk CLI
docker compose exec redpanda rpk topic consume pizza.orders --num 10

# Using Kafka console consumer
docker compose exec redpanda kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic pizza.orders \
  --from-beginning \
  --max-messages 5
```

## Testing the Integration

### Unit Tests

```bash
cd backend
python -m pytest tests/test_kafka_integration.py -v
```

The test suite covers:

| Test                                      | What it verifies                                    |
|-------------------------------------------|-----------------------------------------------------|
| `test_kafka_service_start_stop`           | Producer lifecycle (start/stop)                     |
| `test_kafka_service_publish_event`        | Single event publish with correct topic/key/value   |
| `test_kafka_service_publish_multiple_events` | Batch event publish count                        |
| `test_kafka_service_publish_empty_events` | Handling empty event list                           |
| `test_kafka_service_publish_error_handling` | Graceful handling of producer failures            |
| `test_order_service_publishes_to_kafka`   | End-to-end: `OrderService` → Kafka publish          |
| `test_order_service_skips_kafka_when_not_configured` | Kafka is optional, works without it |
| `test_order_service_full_lifecycle_publishes_to_kafka` | All state transitions publish to Kafka |
| `test_websocket_bridge_connections`       | Add/remove connections, broadcast                   |
| `test_websocket_bridge_multiple_connections` | Broadcast to multiple connected clients          |
| `test_websocket_bridge_removes_disconnected_clients` | Cleanup dead connections          |
| `test_websocket_bridge_error_recovery`    | broadcast_loop restarts on consumer error           |
| `test_order_service_batch_publishes_to_kafka` | Batch dispatch publishes to Kafka               |

Tests use mocked `AIOKafkaProducer` and `AIOKafkaConsumer` — no real Kafka broker required.

### Manual End-to-End Test

```bash
# Terminal 1: Start Redpanda + app
docker compose up -d

# Terminal 2: Watch events
docker compose exec redpanda rpk topic consume pizza.orders

# Terminal 3: Create an order
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"supplier_name":"Pizza Palace","pizza_name":"Margherita","supplier_price":10.0,"markup_percentage":30.0}'
```

## Event Flow (State Transitions)

Each order state transition publishes a distinct event type to Kafka:

```
order.created          → PENDING_SUPPLIER
order.supplier_accepted → SUPPLIER_ACCEPTED
order.supplier_rejected → SUPPLIER_REJECTED (terminal)
order.customer_accepted → CUSTOMER_ACCEPTED
order.preparing        → PREPARING
order.ready            → READY
order.dispatched       → DISPATCHED
order.in_transit       → IN_TRANSIT
order.delivered        → DELIVERED (terminal)
order.cancelled        → CANCELLED (terminal)
```

All are published to the same `pizza.orders` topic, keyed by `order_id` for per-order ordering.

## Migration from Redis Streams

### Phase 1 — Dual Write (current)

Events are published to both Redis Streams and Kafka. Both systems operate in parallel:

- Redis Streams + `StreamConsumer` continue processing
- Kafka producers and `WebSocketBridge` run alongside
- Verify Kafka receives identical events

### Phase 2 — Kafka Primary

- Move `MetricsService` to read from Kafka instead of Redis Streams
- Add additional consumer groups for notifications, analytics
- Verify all downstream consumers work correctly

### Phase 3 — Retire Redis Streams

- Remove Redis Pub/Sub publishing from `_publish_event()`
- Remove `StreamConsumer` and related code
- Redis KV (`order:{id}`) and cache remain unchanged

## Monitoring and Operations

### Topic Health

```bash
# List topics
docker compose exec redpanda rpk topic list

# Describe topic
docker compose exec redpanda rpk topic describe pizza.orders

# Check consumer group status
docker compose exec redpanda rpk group describe ws-bridge
```

### Metrics to Watch

- **Producer request rate** — events/second published
- **Consumer lag** — unprocessed messages per consumer group
- **Partition count** — should match expected distribution
- **Message size** — ensure stays within limits

### Troubleshooting

| Symptom                          | Likely Cause                         | Fix                                      |
|----------------------------------|--------------------------------------|------------------------------------------|
| WebSocket clients not receiving events | Kafka not started / wrong bootstrap | Check `KAFKA_BOOTSTRAP_SERVERS` env var |
| Producer fails to connect        | Redpanda not running                 | `docker compose up -d redpanda`          |
| Duplicate events on WebSocket    | Both Kafka bridge + Redis Pub/Sub active | Phase 3: retire Redis Pub/Sub       |
| Consumer group rebalancing       | Instances starting/stopping          | Normal; verify partition count           |
| High consumer lag                | Consumer too slow                    | Increase partitions or app instances     |

## Performance Considerations

### Partition Count

- Start with 3 partitions for the demo platform
- Rule of thumb: at least as many partitions as expected concurrent consumers
- More partitions = more parallelism but more overhead

### Message Size

- Current events average 500-800 bytes
- Kafka default max message size is 1 MB (no changes needed)

### Retention

- 7-day time-based retention is configured by default
- For the demo, infinite retention is also acceptable (low volume)
- Use compaction if only the latest state per order matters

### Consumer Design

- `WebSocketBridge` uses `enable_auto_commit=True` for simplicity
- For at-least-once processing (metrics, audit), use manual commits
- The `broadcast_loop` auto-restarts on error with a 5-second delay

## Future Enhancements

- **Schema Registry** — Add Confluent Schema Registry + Avro/Protobuf for schema evolution
- **Kafka Connect** — Sink events to Elasticsearch, S3, or a time-series DB
- **Kafka Streams / ksqlDB** — Real-time aggregations (orders per supplier, delivery times)
- **Dead Letter Queue** — Route failed events to a `pizza.orders.dlq` topic
- **Idempotent Producer** — Enable `enable.idempotence=true` for exactly-once semantics
- **Tiered Storage** — Redpanda supports object store tiering for long retention
