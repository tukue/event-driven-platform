# Requirements Document

## Introduction

The pizza delivery marketplace currently uses Redis Pub/Sub (`PUBLISH`/`SUBSCRIBE`) for real-time event delivery. This works well for live clients but has a fundamental limitation: Pub/Sub is fire-and-forget. If no subscriber is listening when an event is published, the event is permanently lost. There is no message persistence, no way to replay events after a crash or reconnect, no consumer group semantics to track which events have been processed, and no audit trail of what occurred.

This creates concrete problems in the current system:

- Frontend clients that disconnect and reconnect miss all events that occurred during the gap
- Batch rollback events are published but nothing can consume them reliably if the consumer is not connected at that exact moment
- There is no history of order lifecycle events for debugging or auditing
- A backend restart loses all in-flight event context

This feature adds Redis Streams alongside the existing Pub/Sub infrastructure. **Pub/Sub is not removed or replaced.** The existing `publish(channel, message)` and `subscribe(channel)` methods on `RedisClient` remain fully intact and continue to work exactly as before. Redis Streams is added as a parallel, persistent event log that provides:

- Durable storage of all order lifecycle events
- Consumer group semantics for reliable at-least-once delivery
- Event replay from any point in history for reconnecting clients
- An audit trail of all events that occurred

The `RedisClient` will support both mechanisms simultaneously:

| Method | Redis Command | Purpose |
|---|---|---|
| `publish(channel, message)` | `PUBLISH` | Existing real-time Pub/Sub (unchanged) |
| `subscribe(channel)` | `SUBSCRIBE` | Existing Pub/Sub listener (unchanged) |
| `xadd(stream, message)` | `XADD` | New: append event to persistent stream |
| `xreadgroup(...)` | `XREADGROUP` | New: consumer group read from stream |

All existing tests and behavior remain unchanged. Redis Streams is purely additive.

## Glossary

- **RedisClient**: The `RedisClient` class in `redis_client.py` that manages the connection to Redis and exposes both Pub/Sub and Streams methods.
- **PubSub_Channel**: The existing Redis Pub/Sub channel `pizza_orders` used for real-time fire-and-forget event delivery.
- **Stream**: The Redis Stream key `pizza_orders_stream` that stores a persistent, ordered log of all order events.
- **Stream_Writer**: The new `xadd` method on `RedisClient` that appends events to the Stream.
- **Stream_Reader**: The new `xreadgroup` method on `RedisClient` that reads events from the Stream using a Consumer_Group.
- **Consumer_Group**: A Redis Streams consumer group that tracks which messages have been delivered and acknowledged, enabling reliable at-least-once delivery.
- **Entry_ID**: The Redis Streams auto-generated message identifier in the format `<milliseconds>-<sequence>`.
- **Event_Replayer**: The component that reads historical events from the Stream starting from a given Entry_ID, used to recover missed events.
- **Order_Service**: The `OrderService` class in `order_service.py` that publishes order lifecycle events via Pub/Sub.
- **WebSocket_Bridge**: The `/ws` endpoint in `main.py` that currently reads from Pub/Sub and forwards events to connected frontend clients.
- **Batch_Dispatcher**: The logic in `OrderService.dispatch_events` that publishes multiple events in a single operation via Pub/Sub.
- **Dead_Letter**: An event that has been delivered to a consumer but not acknowledged after a configurable number of retries.

---

## Requirements

### Requirement 1: Existing Pub/Sub interface remains fully intact

**User Story:** As a backend developer, I want the existing `publish` and `subscribe` methods on `RedisClient` to continue working exactly as before, so that no existing code, tests, or behavior is broken by adding Redis Streams support.

#### Acceptance Criteria

1. THE `RedisClient` SHALL retain the `publish(channel: str, message: str)` coroutine that issues a Redis `PUBLISH` command to the given channel.
2. THE `RedisClient` SHALL retain the `subscribe(channel: str)` coroutine that returns a `pubsub` object compatible with the existing WebSocket bridge loop in `main.py`.
3. WHEN `Order_Service` calls `redis_client.publish("pizza_orders", json_string)`, THE `RedisClient` SHALL deliver the message to all active Pub/Sub subscribers on that channel without modification.
4. WHEN the test suite in `backend/tests/` is executed, THE system SHALL pass all existing tests without any modification to the test files.
5. THE `RedisClient` SHALL retain the `connect()` and `disconnect()` lifecycle methods with the same signatures and behavior.

---

### Requirement 2: New Stream write method added to RedisClient

**User Story:** As a backend developer, I want a new `xadd` method on `RedisClient` that appends events to a Redis Stream, so that I can persist events durably alongside the existing Pub/Sub delivery.

#### Acceptance Criteria

1. THE `RedisClient` SHALL expose a new `xadd(stream: str, message: str)` coroutine that appends the message to the named Redis Stream using the `XADD` command.
2. WHEN `xadd` is called, THE `Stream_Writer` SHALL store the event as a Redis Stream entry with at minimum the fields `event_type` and `data`.
3. THE `Stream_Writer` SHALL use the auto-generated `*` Entry_ID so Redis assigns monotonically increasing IDs.
4. WHEN `xadd` is called with a `MAXLEN ~` cap configured, THE `Stream_Writer` SHALL apply approximate trimming to prevent unbounded stream growth.
5. THE `Stream_Writer` SHALL read the maximum stream length from application configuration with a default value of 10,000 entries.

---

### Requirement 3: New Stream consumer group read method added to RedisClient

**User Story:** As a backend developer, I want a new `xreadgroup` method on `RedisClient` that reads events from a Redis Stream using a consumer group, so that events can be consumed reliably with at-least-once delivery guarantees.

#### Acceptance Criteria

1. THE `RedisClient` SHALL expose a new `xreadgroup(stream: str, group: str, consumer: str, count: int, block: int)` coroutine that reads messages from the named stream using `XREADGROUP`.
2. WHEN `xreadgroup` is called and new messages are available, THE `Stream_Reader` SHALL return the list of stream entries as Python dicts.
3. WHEN `xreadgroup` is called and no new messages are available, THE `Stream_Reader` SHALL block for the configured timeout and return an empty list.
4. THE `RedisClient` SHALL expose a new `xack(stream: str, group: str, entry_id: str)` coroutine that acknowledges a processed stream entry using `XACK`.
5. WHEN a stream entry is acknowledged via `xack`, THE Consumer_Group SHALL not redeliver that entry to any consumer.

---

### Requirement 4: Consumer group lifecycle management

**User Story:** As a backend developer, I want the consumer group to be created automatically at startup, so that the Stream is ready to use without manual Redis configuration.

#### Acceptance Criteria

1. WHEN the application starts up, THE `RedisClient` SHALL create a Consumer_Group named `pizza_consumers` on the `pizza_orders_stream` stream if it does not already exist.
2. WHEN the `pizza_orders_stream` stream does not exist at startup, THE `RedisClient` SHALL create the stream and the Consumer_Group atomically using `XGROUP CREATE ... MKSTREAM`.
3. WHEN the Consumer_Group already exists at startup, THE `RedisClient` SHALL continue without raising an error.
4. THE `RedisClient` SHALL use the starting offset `$` for the Consumer_Group so that only new messages are delivered to consumers by default.

---

### Requirement 5: Order Service writes to Stream in addition to Pub/Sub

**User Story:** As a backend developer, I want order lifecycle events written to the Redis Stream in addition to being published on the Pub/Sub channel, so that events are both delivered in real time and persisted for replay.

#### Acceptance Criteria

1. WHEN `Order_Service` publishes any order lifecycle event (`order.created`, `order.supplier_accepted`, `order.supplier_rejected`, `order.customer_accepted`, `order.dispatched`, `order.{status}`), THE `Order_Service` SHALL call both `redis_client.publish` (Pub/Sub) and `redis_client.xadd` (Stream) for each event.
2. WHEN `Batch_Dispatcher` publishes a batch of events, THE `Order_Service` SHALL append each event to the Stream in addition to publishing it on the Pub/Sub channel, in the same order.
3. WHEN a `batch.rollback` event is triggered, THE `Order_Service` SHALL append the rollback event to the Stream in addition to publishing it on the Pub/Sub channel.
4. IF the `xadd` call fails for any event, THEN THE `Order_Service` SHALL log the failure and continue without interrupting the Pub/Sub delivery path.

---

### Requirement 6: Event replay capability

**User Story:** As a backend developer, I want to replay events from a specific point in the Stream, so that consumers can recover missed events after a restart, crash, or reconnect.

#### Acceptance Criteria

1. WHEN `Event_Replayer` is called with a starting Entry_ID, THE `RedisClient` SHALL return all stream entries from that Entry_ID onward using `XRANGE`.
2. WHEN `Event_Replayer` is called with the starting Entry_ID `0`, THE `RedisClient` SHALL return all entries in the stream from the beginning.
3. WHEN `Event_Replayer` is called with a count limit, THE `RedisClient` SHALL return at most that many entries.
4. IF the provided starting Entry_ID does not exist in the stream, THEN THE `RedisClient` SHALL return all entries with an ID greater than the provided value (standard `XRANGE` behavior).
5. THE `RedisClient` SHALL expose a `xrange(stream: str, start: str, end: str, count: int)` coroutine for replay use.

---

### Requirement 7: Stream entry serialization and deserialization

**User Story:** As a backend developer, I want stream entries to be serialized and deserialized consistently, so that the event format is stable across the write and read paths.

#### Acceptance Criteria

1. WHEN an event is appended to the stream via `xadd`, THE `Stream_Writer` SHALL serialize the event payload as a JSON string stored under the field key `data`.
2. WHEN a stream entry is read via `xreadgroup` or `xrange`, THE `Stream_Reader` SHALL deserialize the `data` field from JSON back to a Python dict before returning it to the caller.
3. THE `RedisClient` SHALL serialize and deserialize event payloads such that `deserialize(serialize(event)) == event` for all valid event dicts (round-trip property).
4. IF a stream entry contains a `data` field that is not valid JSON, THEN THE `Stream_Reader` SHALL raise a descriptive `ValueError` identifying the malformed entry.

---

### Requirement 8: WebSocket bridge can optionally use Stream for missed event recovery

**User Story:** As a frontend developer, I want reconnecting WebSocket clients to be able to request missed events from the Stream, so that clients do not lose events that occurred while they were disconnected.

#### Acceptance Criteria

1. WHEN a WebSocket client connects to `/ws` with a `last_event_id` query parameter, THE `WebSocket_Bridge` SHALL replay all stream entries after that Entry_ID to the client before switching to live delivery.
2. WHEN a WebSocket client connects to `/ws` without a `last_event_id` parameter, THE `WebSocket_Bridge` SHALL behave exactly as it does today, reading from the Pub/Sub channel only.
3. WHEN replaying missed events, THE `WebSocket_Bridge` SHALL send each event as a JSON string preserving the same message format that the existing `useWebSocket.js` frontend hook expects.
4. WHEN replay is complete, THE `WebSocket_Bridge` SHALL continue delivering live events from the Pub/Sub channel as normal.
5. IF the provided `last_event_id` is not found in the stream, THEN THE `WebSocket_Bridge` SHALL send all available stream entries and then continue with live delivery.
