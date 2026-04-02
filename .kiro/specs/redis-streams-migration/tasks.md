# Implementation Plan: Redis Streams Migration

## Overview

Add Redis Streams as a parallel, persistent event log alongside the existing Pub/Sub infrastructure. All changes are purely additive — no existing code paths are removed or altered. Implementation proceeds in layers: config and client primitives first, then service dual-write, then WebSocket replay, then tests.

## Tasks

- [ ] 1. Add configuration and constants
  - Add `STREAM_NAME = "pizza_orders_stream"` and `GROUP_NAME = "pizza_consumers"` as module-level constants in `backend/redis_client.py`
  - Add `stream_max_len: int = Field(default=10000, env="STREAM_MAX_LEN")` to the `Settings` class in `backend/config.py`
  - _Requirements: 2.5, 4.1_

- [ ] 2. Add Stream methods to RedisClient
  - [ ] 2.1 Implement `_ensure_consumer_group` and call it from `connect()`
    - Add `async def _ensure_consumer_group(self)` that calls `xgroup_create` with `id="$"` and `mkstream=True`
    - Catch `ResponseError` and silently ignore `BUSYGROUP`; re-raise all other errors
    - Call `await self._ensure_consumer_group()` at the end of `connect()` in `redis_client.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 2.2 Implement `xadd`
    - Add `async def xadd(self, stream: str, message: str) -> str` to `RedisClient`
    - Store the message under field key `data` using `XADD stream MAXLEN ~ settings.stream_max_len * data message`
    - Return the auto-generated Entry_ID string
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 2.3 Implement `xrange`
    - Add `async def xrange(self, stream: str, start: str = "-", end: str = "+", count: int = None) -> list[dict]` to `RedisClient`
    - For each entry returned by Redis, deserialize the `data` field from JSON; raise `ValueError` with the entry ID if `data` is not valid JSON
    - Return list of dicts with keys `id` and `data`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.2, 7.4_

  - [ ] 2.4 Implement `xreadgroup` and `xack`
    - Add `async def xreadgroup(self, stream: str, group: str, consumer: str, count: int = 10, block: int = 1000) -> list[dict]` to `RedisClient`
    - Deserialize `data` field for each entry; raise `ValueError` on malformed JSON (same as `xrange`)
    - Add `async def xack(self, stream: str, group: str, entry_id: str) -> None` to `RedisClient`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.2, 7.4_

  - [ ]* 2.5 Write unit tests for new RedisClient methods
    - `test_xadd_stores_data_field`: assert `data` field present and valid JSON after `xadd`
    - `test_xrange_returns_ordered_entries`: append 3 events, assert `xrange` returns them in insertion order
    - `test_xrange_with_start_id_excludes_prior`: append events, replay from middle ID, assert earlier entries absent
    - `test_ensure_consumer_group_idempotent`: call `_ensure_consumer_group` twice, assert no error and one group exists
    - `test_malformed_data_raises_value_error`: insert raw entry with non-JSON `data`, call `xrange`, assert `ValueError`
    - _Requirements: 2.1, 3.1, 4.3, 6.1, 7.4_

- [ ] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Extend OrderService to dual-write to Stream
  - [ ] 4.1 Extend `_publish_event` to dual-write
    - Import `STREAM_NAME` from `redis_client` in `order_service.py`
    - After the existing `await self.redis.publish(...)` call, add a try/except block that calls `await self.redis.xadd(STREAM_NAME, payload)` and logs a warning on failure without re-raising
    - The Pub/Sub call must remain unchanged and must not be affected by stream write failures
    - _Requirements: 5.1, 5.4_

  - [ ] 4.2 Extend `dispatch_events` to dual-write each event
    - In the per-event loop inside `dispatch_events`, after the existing `await self.redis.publish(...)` call, add the same try/except `xadd` pattern
    - Apply the same pattern to `_publish_rollback_event` so `batch.rollback` events are also streamed
    - _Requirements: 5.2, 5.3, 5.4_

  - [ ]* 4.3 Write unit tests for dual-write behaviour
    - `test_publish_event_dual_writes`: mock both `publish` and `xadd`, call `_publish_event`, assert both called with correct args
    - `test_stream_failure_non_blocking`: mock `xadd` to raise, call `_publish_event`, assert `publish` still called and no exception propagates
    - `test_dispatch_events_dual_writes`: mock both, call `dispatch_events` with N events, assert `xadd` called N times
    - _Requirements: 5.1, 5.2, 5.4_

- [ ] 5. Update WebSocket endpoint to support event replay
  - [ ] 5.1 Add `last_event_id` query parameter to `/ws`
    - Change the signature of `websocket_endpoint` in `main.py` to accept `last_event_id: str | None = None`
    - Import `STREAM_NAME` from `redis_client` in `main.py`
    - _Requirements: 8.1, 8.2_

  - [ ] 5.2 Implement replay-then-live logic
    - If `last_event_id` is provided, call `await redis_client.xrange(STREAM_NAME, start=last_event_id, end="+")` and send each entry's `data` field as a JSON text frame before entering the Pub/Sub loop
    - The existing Pub/Sub loop must remain unchanged and must execute after replay completes
    - Handle `WebSocketDisconnect` during replay the same way it is handled in the live loop
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 5.3 Write unit tests for WebSocket replay
    - `test_websocket_no_last_event_id_unchanged`: connect without param, assert `xrange` never called
    - `test_websocket_with_last_event_id_replays`: seed stream with events, connect with `last_event_id`, assert replay messages received before live events
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Write property-based tests (Hypothesis)
  - [ ]* 7.1 Property 1 — Pub/Sub unaffected by stream write outcome
    - `test_prop_pubsub_unaffected`: use `st.text()` payloads; mock `xadd` to randomly raise or succeed; assert `publish` always called and no exception propagates
    - **Property 1: Pub/Sub delivery is unaffected by stream write outcome**
    - **Validates: Requirements 1.3, 5.4**

  - [ ]* 7.2 Property 2 — Serialization round-trip
    - `test_prop_serialization_round_trip`: use `st.builds(OrderEvent, ...)` or `st.fixed_dictionaries`; assert `json.loads(json.dumps(obj, default=str)) == obj`
    - **Property 2: Serialization round-trip**
    - **Validates: Requirements 7.3**

  - [ ]* 7.3 Property 3 — xrange returns entries in insertion order
    - `test_prop_xrange_ordered`: use `st.lists(st.text(), min_size=1)` for payloads; append all, call `xrange("-", "+")`, assert returned IDs are monotonically increasing
    - **Property 3: xrange returns entries in insertion order**
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 7.4 Property 4 — xrange with start ID excludes prior entries
    - `test_prop_xrange_start_excludes_prior`: use `st.lists(st.text(), min_size=2)`; append all, pick a middle ID, call `xrange(start=mid_id)`, assert no returned entry has ID less than `mid_id`
    - **Property 4: xrange with start ID excludes prior entries**
    - **Validates: Requirements 6.1, 8.1**

  - [ ]* 7.5 Property 5 — Consumer group creation is idempotent
    - `test_prop_consumer_group_idempotent`: use `st.integers(min_value=1, max_value=10)` for call count; call `_ensure_consumer_group` N times, assert no error and exactly one group named `pizza_consumers` exists
    - **Property 5: Consumer group creation is idempotent**
    - **Validates: Requirements 4.1, 4.3**

  - [ ]* 7.6 Property 6 — Dual-write completeness
    - `test_prop_dual_write_completeness`: use `st.builds(OrderEvent, ...)`; call `_publish_event`, assert both `publish` and `xadd` called and stream entry `data` deserializes to equal dict
    - **Property 6: Dual-write completeness**
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [ ]* 7.7 Property 7 — WebSocket replay then live
    - `test_prop_websocket_replay_then_live`: use `st.lists(st.builds(OrderEvent, ...), min_size=1)`; seed stream, connect with `last_event_id`, assert replay messages arrive before any live Pub/Sub message
    - **Property 7: WebSocket replay then live**
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]* 7.8 Property 8 — Malformed stream entry raises ValueError
    - `test_prop_malformed_entry_raises`: use `st.text().filter(lambda s: not is_valid_json(s))`; insert raw entry with non-JSON `data`, call `xrange`, assert `ValueError` raised
    - **Property 8: Malformed stream entry raises ValueError**
    - **Validates: Requirements 7.4**

  - [ ]* 7.9 Property 9 — xack prevents redelivery
    - `test_prop_xack_prevents_redelivery`: use `st.lists(st.text(), min_size=1)`; append entries, read via `xreadgroup`, ack each, call `xreadgroup` again, assert empty result
    - **Property 9: xack prevents redelivery**
    - **Validates: Requirements 3.4, 3.5**

  - [ ]* 7.10 Property 10 — xrange respects count limit
    - `test_prop_xrange_count_limit`: use `st.integers(min_value=1)` for count C and `st.lists(st.text(), min_size=2)` for entries; append N > C entries, call `xrange(count=C)`, assert exactly C entries returned
    - **Property 10: xrange respects count limit**
    - **Validates: Requirements 6.3**

  - [ ]* 7.11 Property 11 — MAXLEN trimming bounds stream length
    - `test_prop_maxlen_bounds_stream`: use `st.integers(min_value=10, max_value=100)` for MAXLEN M; insert 2×M entries with that MAXLEN, assert stream length ≤ 1.5×M (Redis approximate trimming tolerance)
    - **Property 11: MAXLEN trimming bounds stream length**
    - **Validates: Requirements 2.4, 2.5**

- [ ] 8. Final checkpoint — Ensure all tests pass
  - Run the full test suite (`pytest backend/tests/`) and confirm all existing tests still pass alongside the new ones.
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests (tasks 7.x) require `hypothesis` — add to `backend/requirements.txt` if not already present
- All property-based tests must include the comment `# Feature: redis-streams-migration, Property N: <text>` per the design spec
- The `conftest.py` mock_redis fixture will need `xadd`, `xrange`, `xreadgroup`, and `xack` added as `AsyncMock` attributes for unit tests that use the fixture
- Stream methods that interact with a real Redis instance should be tested against a live Redis in integration tests; unit tests should use mocks
