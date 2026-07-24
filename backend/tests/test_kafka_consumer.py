"""
Tests for Kafka consumer service.

Covers KafkaConsumerService lifecycle, handler registration, message processing,
error handling, and the OrderEventProcessor integration layer.
All tests use mocked aiokafka — no live broker required.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import AsyncIterator

from tests.kafka_testdata import (
    make_order_created_event,
    make_source_accepted_event,
    make_source_rejected_event,
    make_buyer_accepted_event,
    make_dispatched_event,
    make_delivered_event,
    make_batch_rollback_event,
    make_full_lifecycle_events,
    make_bulk_events,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_consumer_msg(value: dict, partition: int = 0, offset: int = 0, key: str | None = None):
    """Build a mock Kafka message resembling aiokafka ConsumerRecord"""
    msg = MagicMock()
    msg.value = value
    msg.key = key
    msg.partition = partition
    msg.offset = offset
    msg.topic = "orders"
    msg.timestamp = int(datetime.utcnow().timestamp() * 1000)
    return msg


class FakeConsumer:
    """Async iterator that yields a finite list of mock Kafka messages then stops"""

    def __init__(self, messages: list[dict]):
        self._messages = [_build_consumer_msg(m) for m in messages]
        self._index = 0

    def __aiter__(self) -> AsyncIterator:
        return self

    async def __anext__(self):
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        msg = self._messages[self._index]
        self._index += 1
        return msg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_aiokafka_consumer():
    with patch("services.kafka_consumer.AIOKafkaConsumer") as cls:
        instance = AsyncMock()
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        cls.return_value = instance
        yield instance


@pytest.fixture
def kafka_consumer_service(mock_aiokafka_consumer):
    from services.kafka_consumer import KafkaConsumerService
    return KafkaConsumerService("localhost:9092", topic="orders", group_id="test-group")


@pytest.fixture
def order_event_processor(mock_aiokafka_consumer):
    from services.kafka_consumer import OrderEventProcessor
    return OrderEventProcessor("localhost:9092", topic="orders")


# ---------------------------------------------------------------------------
# KafkaConsumerService — lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consumer_start_stop(kafka_consumer_service, mock_aiokafka_consumer):
    await kafka_consumer_service.start()
    mock_aiokafka_consumer.start.assert_awaited_once()
    assert kafka_consumer_service.running is True

    await kafka_consumer_service.stop()
    assert kafka_consumer_service.running is False
    mock_aiokafka_consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_start_configures_aiokafka(kafka_consumer_service, mock_aiokafka_consumer):
    await kafka_consumer_service.start()

    consumer_instance = kafka_consumer_service.consumer
    consumer_instance.start.assert_awaited_once()
    assert kafka_consumer_service.group_id == "test-group"
    assert kafka_consumer_service.auto_offset_reset == "earliest"
    assert kafka_consumer_service.topic == "orders"
    assert kafka_consumer_service.bootstrap_servers == "localhost:9092"


@pytest.mark.asyncio
async def test_consumer_stop_without_start():
    from services.kafka_consumer import KafkaConsumerService
    svc = KafkaConsumerService("localhost:9092")
    await svc.stop()
    assert svc.running is False


# ---------------------------------------------------------------------------
# KafkaConsumerService — handler registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_handler(kafka_consumer_service):
    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)
    assert "order.created" in kafka_consumer_service.handlers
    assert kafka_consumer_service.handlers["order.created"] is handler


@pytest.mark.asyncio
async def test_register_multiple_handlers(kafka_consumer_service):
    h1 = AsyncMock()
    h2 = AsyncMock()
    kafka_consumer_service.register_handler("order.created", h1)
    kafka_consumer_service.register_handler("order.delivered", h2)
    assert len(kafka_consumer_service.handlers) == 2


# ---------------------------------------------------------------------------
# KafkaConsumerService — message processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_message_dispatches_to_handler(kafka_consumer_service):
    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)

    event = make_order_created_event(order_id="proc-1")
    msg = _build_consumer_msg(event)

    await kafka_consumer_service._process_message(msg)

    handler.assert_awaited_once_with(event)
    assert kafka_consumer_service._processed_count == 1


@pytest.mark.asyncio
async def test_process_message_unknown_event_type(kafka_consumer_service, caplog):
    msg = _build_consumer_msg({"event_type": "order.unknown", "order": {}})

    with caplog.at_level("WARNING", logger="services.kafka_consumer"):
        await kafka_consumer_service._process_message(msg)

    assert "No handler registered" in caplog.text
    assert kafka_consumer_service._processed_count == 0


@pytest.mark.asyncio
async def test_process_message_non_dict_value(kafka_consumer_service, caplog):
    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)

    msg = MagicMock()
    msg.value = "not-a-dict"
    msg.partition = 0
    msg.offset = 0

    with pytest.raises(AttributeError):
        with caplog.at_level("ERROR", logger="services.kafka_consumer"):
            await kafka_consumer_service._process_message(msg)

    assert kafka_consumer_service._error_count == 1
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_message_handler_exception(kafka_consumer_service):
    failing_handler = AsyncMock(side_effect=RuntimeError("handler boom"))
    kafka_consumer_service.register_handler("order.created", failing_handler)

    msg = _build_consumer_msg(make_order_created_event())

    with pytest.raises(RuntimeError, match="handler boom"):
        await kafka_consumer_service._process_message(msg)

    assert kafka_consumer_service._error_count == 1
    assert kafka_consumer_service._last_error == "handler boom"


# ---------------------------------------------------------------------------
# KafkaConsumerService — consume loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_processes_multiple_messages(kafka_consumer_service, mock_aiokafka_consumer):
    events = make_full_lifecycle_events(order_id="loop-1")
    fake = FakeConsumer(events)
    mock_aiokafka_consumer.__aiter__ = lambda self: fake

    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)
    kafka_consumer_service.register_handler("order.source_accepted", handler)
    kafka_consumer_service.register_handler("order.buyer_accepted", handler)
    kafka_consumer_service.register_handler("order.dispatched", handler)
    kafka_consumer_service.register_handler("order.delivered", handler)

    await kafka_consumer_service.start()
    await kafka_consumer_service.consume()

    assert handler.await_count == 5
    assert kafka_consumer_service._processed_count == 5


@pytest.mark.asyncio
async def test_consume_stops_when_running_false(kafka_consumer_service, mock_aiokafka_consumer):
    events = make_full_lifecycle_events()
    fake = FakeConsumer(events)
    mock_aiokafka_consumer.__aiter__ = lambda self: fake

    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)

    await kafka_consumer_service.start()
    kafka_consumer_service.running = False
    await kafka_consumer_service.consume()

    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_requires_started_consumer():
    from services.kafka_consumer import KafkaConsumerService
    svc = KafkaConsumerService("localhost:9092")
    with pytest.raises(RuntimeError, match="not started"):
        await svc.consume()


# ---------------------------------------------------------------------------
# KafkaConsumerService — stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_stats_initial(kafka_consumer_service):
    stats = kafka_consumer_service.get_stats()
    assert stats["running"] is False
    assert stats["processed_count"] == 0
    assert stats["error_count"] == 0
    assert stats["group_id"] == "test-group"
    assert stats["topic"] == "orders"


@pytest.mark.asyncio
async def test_get_stats_after_processing(kafka_consumer_service):
    kafka_consumer_service.register_handler("order.created", AsyncMock())
    msg = _build_consumer_msg(make_order_created_event())
    await kafka_consumer_service._process_message(msg)

    stats = kafka_consumer_service.get_stats()
    assert stats["processed_count"] == 1
    assert "order.created" in stats["registered_handlers"]


# ---------------------------------------------------------------------------
# OrderEventProcessor — handler wiring
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_event_processor_registers_all_handlers(order_event_processor):
    expected = {
        "order.created",
        "order.source_accepted",
        "order.source_rejected",
        "order.buyer_accepted",
        "order.dispatched",
        "order.preparing",
        "order.ready",
        "order.in_transit",
        "order.delivered",
        "batch.rollback",
    }
    assert set(order_event_processor.consumer.handlers.keys()) == expected


# ---------------------------------------------------------------------------
# OrderEventProcessor — each event type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_event_processor_handle_created(order_event_processor):
    event = make_order_created_event(order_id="ep-1")
    handler = order_event_processor.consumer.handlers["order.created"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert len(log) == 1
    assert log[0]["event_type"] == "order.created"
    assert log[0]["entity_id"] == "ep-1"


@pytest.mark.asyncio
async def test_order_event_processor_handle_source_accepted(order_event_processor):
    event = make_source_accepted_event(order_id="ep-2")
    handler = order_event_processor.consumer.handlers["order.source_accepted"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "order.source_accepted"
    assert log[0]["entity_id"] == "ep-2"


@pytest.mark.asyncio
async def test_order_event_processor_handle_source_rejected(order_event_processor):
    event = make_source_rejected_event(order_id="ep-3")
    handler = order_event_processor.consumer.handlers["order.source_rejected"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "order.source_rejected"
    assert log[0]["entity_id"] == "ep-3"


@pytest.mark.asyncio
async def test_order_event_processor_handle_buyer_accepted(order_event_processor):
    event = make_buyer_accepted_event(order_id="ep-4")
    handler = order_event_processor.consumer.handlers["order.buyer_accepted"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "order.buyer_accepted"
    assert log[0]["entity_id"] == "ep-4"


@pytest.mark.asyncio
async def test_order_event_processor_handle_dispatched(order_event_processor):
    event = make_dispatched_event(order_id="ep-5")
    handler = order_event_processor.consumer.handlers["order.dispatched"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "order.dispatched"
    assert log[0]["entity_id"] == "ep-5"


@pytest.mark.asyncio
async def test_order_event_processor_handle_delivered(order_event_processor):
    event = make_delivered_event(order_id="ep-6")
    handler = order_event_processor.consumer.handlers["order.delivered"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "order.delivered"
    assert log[0]["entity_id"] == "ep-6"


@pytest.mark.asyncio
async def test_order_event_processor_handle_status_change(order_event_processor):
    for status in ["preparing", "ready", "in_transit"]:
        event = {
            "event_type": f"order.{status}",
            "order": {"id": f"ep-status-{status}"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        handler = order_event_processor.consumer.handlers[f"order.{status}"]
        await handler(event)

    log = order_event_processor.get_order_log()
    assert len(log) == 3
    types = [e["event_type"] for e in log]
    assert "order.preparing" in types
    assert "order.ready" in types
    assert "order.in_transit" in types


@pytest.mark.asyncio
async def test_order_event_processor_handle_batch_rollback(order_event_processor):
    event = make_batch_rollback_event(correlation_id="batch-test-abc")
    handler = order_event_processor.consumer.handlers["batch.rollback"]
    await handler(event)

    log = order_event_processor.get_order_log()
    assert log[0]["event_type"] == "batch.rollback"
    assert log[0]["entity_id"] == "batch-test-abc"


# ---------------------------------------------------------------------------
# OrderEventProcessor — full lifecycle via consume loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_event_processor_full_lifecycle(order_event_processor, mock_aiokafka_consumer):
    events = make_full_lifecycle_events(order_id="lifecycle-1")
    fake = FakeConsumer(events)
    mock_aiokafka_consumer.__aiter__ = lambda self: fake

    await order_event_processor.consumer.start()
    await order_event_processor.consume()

    log = order_event_processor.get_order_log()
    assert len(log) == 5
    types = [e["event_type"] for e in log]
    assert types == [
        "order.created",
        "order.source_accepted",
        "order.buyer_accepted",
        "order.dispatched",
        "order.delivered",
    ]


@pytest.mark.asyncio
async def test_order_event_processor_bulk_events(order_event_processor, mock_aiokafka_consumer):
    events = make_bulk_events(count=15)
    fake = FakeConsumer(events)
    mock_aiokafka_consumer.__aiter__ = lambda self: fake

    await order_event_processor.consumer.start()
    await order_event_processor.consume()

    log = order_event_processor.get_order_log()
    assert len(log) == 15
    assert all(e["event_type"] == "order.created" for e in log)


# ---------------------------------------------------------------------------
# OrderEventProcessor — stats & lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_event_processor_start_stop(order_event_processor, mock_aiokafka_consumer):
    await order_event_processor.start()
    assert order_event_processor.consumer.running is True

    await order_event_processor.stop()
    assert order_event_processor.consumer.running is False


@pytest.mark.asyncio
async def test_order_event_processor_get_stats(order_event_processor):
    stats = order_event_processor.get_stats()
    assert stats["group_id"] == "order-event-processors"
    assert stats["order_log_count"] == 0


# ---------------------------------------------------------------------------
# Kafka producer + consumer integration (end-to-end with mocks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_producer_consumer_roundtrip(mock_aiokafka_consumer):
    from services.kafka_service import KafkaService
    from services.kafka_consumer import KafkaConsumerService

    producer = KafkaService("localhost:9092")
    with patch("services.kafka_service.AIOKafkaProducer") as mock_producer_cls:
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.send = AsyncMock()
        mock_producer_cls.return_value = mock_producer

        await producer.start()

        consumer = KafkaConsumerService("localhost:9092")
        received_events = []

        async def capture_handler(event_data):
            received_events.append(event_data)

        consumer.register_handler("order.created", capture_handler)

        events = make_bulk_events(count=5)
        for e in events:
            await producer.publish_event(e)

        assert mock_producer.send.await_count == 5

        fake = FakeConsumer(events)
        mock_aiokafka_consumer.__aiter__ = lambda self: fake

        await consumer.start()
        await consumer.consume()

        assert len(received_events) == 5
        assert received_events[0]["event_type"] == "order.created"

        await producer.stop()
        await consumer.stop()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_message_with_null_key(kafka_consumer_service):
    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)

    msg = _build_consumer_msg(make_order_created_event(), key=None)
    await kafka_consumer_service._process_message(msg)
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_message_with_binary_key(kafka_consumer_service):
    handler = AsyncMock()
    kafka_consumer_service.register_handler("order.created", handler)

    msg = _build_consumer_msg(make_order_created_event(), key=b"order-id-123")
    await kafka_consumer_service._process_message(msg)
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_event_processor_logs_timestamp(order_event_processor):
    before = datetime.utcnow().isoformat()
    event = make_order_created_event(order_id="ts-check")
    handler = order_event_processor.consumer.handlers["order.created"]
    await handler(event)
    after = datetime.utcnow().isoformat()

    log = order_event_processor.get_order_log()
    assert before <= log[0]["timestamp"] <= after
