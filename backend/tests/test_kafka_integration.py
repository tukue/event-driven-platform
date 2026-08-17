"""
Tests for Kafka/Redpanda event publishing integration.
Tests producer lifecycle, dual-write from OrderService, and WebSocket bridge broadcast.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from models import Order, OrderStatus, OrderEvent
from services.order_service import OrderService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kafka_producer():
    with patch("services.kafka_service.AIOKafkaProducer") as mock:
        instance = AsyncMock()
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        instance.send_and_wait = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def kafka_service(mock_kafka_producer):
    from services.kafka_service import KafkaService
    service = KafkaService("localhost:9092")
    return service


@pytest.fixture
def sample_event():
    order = Order(
        id="test-123",
        item_name="Test Item",
        source_name="Quick Mart",
        source_price=10.0,
        status=OrderStatus.PENDING_SOURCE,
        tracking_id="ORD-2026-000001",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return OrderEvent(
        event_type="order.created",
        order=order,
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def blank_order():
    return Order(
        source_name="Test Source Co",
        item_name="Test Item",
        source_price=15.99,
        markup_percentage=30.0,
    )


# ---------------------------------------------------------------------------
# KafkaService — producer lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kafka_service_start_stop(kafka_service):
    await kafka_service.start()
    kafka_service.producer.start.assert_awaited_once()

    await kafka_service.stop()
    kafka_service.producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_service_enables_idempotent_producer():
    with patch("services.kafka_service.AIOKafkaProducer") as producer_class:
        producer_class.return_value = AsyncMock()
        from services.kafka_service import KafkaService

        service = KafkaService("localhost:9092")
        await service.start()

        assert producer_class.call_args.kwargs["enable_idempotence"] is True
        await service.stop()


@pytest.mark.asyncio
async def test_kafka_service_start_stop_idempotent(kafka_service):
    await kafka_service.stop()


@pytest.mark.asyncio
async def test_kafka_service_publish_event(kafka_service, sample_event):
    await kafka_service.start()
    event_data = sample_event.model_dump(mode="json")

    await kafka_service.publish_event(event_data)

    kafka_service.producer.send_and_wait.assert_awaited_once()
    call_args = kafka_service.producer.send_and_wait.call_args
    assert call_args.kwargs["topic"] == "orders"
    assert call_args.kwargs["key"] == "test-123"
    assert call_args.kwargs["value"]["event_type"] == "order.created"
    assert ("event_id", event_data["event_id"].encode("utf-8")) in call_args.kwargs["headers"]
    assert ("schema_version", b"1") in call_args.kwargs["headers"]


@pytest.mark.asyncio
async def test_kafka_service_publish_event_no_order_id(kafka_service):
    await kafka_service.start()
    event_data = {"event_type": "system.heartbeat", "timestamp": "2026-01-01T00:00:00"}

    await kafka_service.publish_event(event_data)

    kafka_service.producer.send_and_wait.assert_awaited_once()
    call_args = kafka_service.producer.send_and_wait.call_args
    assert call_args.kwargs["key"] is None


@pytest.mark.asyncio
async def test_kafka_service_uses_top_level_order_id_as_key(kafka_service):
    await kafka_service.start()

    await kafka_service.publish_event(
        {"event_type": "order.validation_passed", "order_id": "test-123"}
    )

    call_args = kafka_service.producer.send_and_wait.call_args
    assert call_args.kwargs["key"] == "test-123"


@pytest.mark.asyncio
async def test_order_event_exposes_top_level_order_id(kafka_service, sample_event):
    await kafka_service.start()
    event_data = sample_event.model_dump(mode="json")

    await kafka_service.publish_event(event_data)

    call_args = kafka_service.producer.send_and_wait.call_args
    assert event_data["order_id"] == "test-123"
    assert call_args.kwargs["key"] == event_data["order_id"]


@pytest.mark.asyncio
async def test_kafka_service_publish_event_requires_started_producer(kafka_service):
    with pytest.raises(RuntimeError, match="Kafka producer not started"):
        await kafka_service.publish_event({"event_type": "order.created", "order": {"id": "1"}})


@pytest.mark.asyncio
async def test_kafka_service_publish_multiple_events(kafka_service):
    await kafka_service.start()
    events = [
        {"event_type": "order.created", "order": {"id": "1"}},
        {"event_type": "order.dispatched", "order": {"id": "2"}},
    ]

    await kafka_service.publish_events(events)

    assert kafka_service.producer.send_and_wait.await_count == 2


@pytest.mark.asyncio
async def test_kafka_service_publish_empty_events(kafka_service):
    await kafka_service.start()
    await kafka_service.publish_events([])
    kafka_service.producer.send_and_wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_kafka_service_publish_error_handling(kafka_service, sample_event):
    await kafka_service.start()
    kafka_service.producer.send_and_wait.side_effect = Exception("Kafka broker unreachable")

    with pytest.raises(Exception, match="Kafka broker unreachable"):
        await kafka_service.publish_event(sample_event.model_dump(mode="json"))
    kafka_service.producer.send_and_wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_service_serialization(kafka_service, sample_event):
    await kafka_service.start()
    event_data = sample_event.model_dump(mode="json")

    await kafka_service.publish_event(event_data)

    call_args = kafka_service.producer.send_and_wait.call_args
    sent_value = call_args.kwargs["value"]
    assert sent_value["event_type"] == "order.created"
    assert sent_value["order"]["id"] == "test-123"
    assert "timestamp" in sent_value


# ---------------------------------------------------------------------------
# OrderService → Kafka dual-write
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_service_publishes_to_kafka(mock_redis, sample_event, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()

    service = OrderService(mock_redis, kafka_service=kafka)
    await service.create_order(sample_event.order)

    kafka.producer.send_and_wait.assert_awaited_once()
    call_args = kafka.producer.send_and_wait.call_args
    assert call_args.kwargs["topic"] == "orders"
    assert call_args.kwargs["value"]["event_type"] == "order.created"


@pytest.mark.asyncio
async def test_order_service_skips_kafka_when_not_configured(mock_redis, sample_event):
    service = OrderService(mock_redis, kafka_service=None)
    event = await service.create_order(sample_event.order)
    assert event.event_type == "order.created"


@pytest.mark.asyncio
async def test_order_service_full_lifecycle_publishes_to_kafka(mock_redis, blank_order, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()

    service = OrderService(mock_redis, kafka_service=kafka)

    # Full lifecycle
    event1 = await service.create_order(blank_order)
    order_id = event1.order.id

    event2 = await service.source_respond(order_id, accept=True, estimated_time=30)
    event3 = await service.buyer_accept(order_id, "Jane", "456 Oak St")
    event4 = await service.dispatch_order(order_id, "Driver Dave")
    event5 = await service.update_status(order_id, OrderStatus.IN_TRANSIT)
    event6 = await service.update_status(order_id, OrderStatus.DELIVERED)

    assert kafka.producer.send_and_wait.await_count == 6

    sent_types = [call.kwargs["value"]["event_type"] for call in kafka.producer.send_and_wait.call_args_list]
    assert sent_types == [
        "order.created",
        "order.source_accepted",
        "order.buyer_accepted",
        "order.dispatched",
        "order.in_transit",
        "order.delivered",
    ]

    for call in kafka.producer.send_and_wait.call_args_list:
        assert call.kwargs["topic"] == "orders"
        assert call.kwargs["key"] == order_id


@pytest.mark.asyncio
async def test_order_service_kafka_failure_does_not_block_redis(mock_redis, sample_event, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()
    kafka.producer.send_and_wait.side_effect = Exception("Kafka down")

    service = OrderService(mock_redis, kafka_service=kafka)

    event = await service.create_order(sample_event.order)

    assert event.event_type == "order.created"
    kafka.producer.send_and_wait.assert_awaited_once()
    assert mock_redis.publish.await_count == 1
    assert "order:" in next(iter(mock_redis._storage.keys()))


@pytest.mark.asyncio
async def test_order_service_batch_publishes_to_kafka(mock_redis, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()

    service = OrderService(mock_redis, kafka_service=kafka)

    batch_events = [
        {"event_type": "order.created", "order": {"id": "batch-1"}, "timestamp": datetime.utcnow().isoformat()},
        {"event_type": "order.dispatched", "order": {"id": "batch-2"}, "timestamp": datetime.utcnow().isoformat()},
    ]

    result = await service.dispatch_events(batch_events, correlation_id="test-correlation")

    assert result.success is True
    assert result.processed_count == 2
    assert kafka.producer.send_and_wait.await_count == 2

    for call in kafka.producer.send_and_wait.call_args_list:
        assert call.kwargs["topic"] == "orders"


@pytest.mark.asyncio
async def test_order_service_batch_does_not_duplicate_events(mock_redis, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()

    service = OrderService(mock_redis, kafka_service=kafka)

    batch_events = [
        {"event_type": "order.created", "order": {"id": "ok-1"}, "timestamp": datetime.utcnow().isoformat()},
        {"event_type": "order.dispatched", "order": {"id": "ok-1"}, "timestamp": datetime.utcnow().isoformat()},
    ]

    result = await service.dispatch_events(batch_events, correlation_id="corr-123")

    assert result.success is True
    assert result.processed_count == 2
    assert kafka.producer.send_and_wait.await_count == 2
    for call in kafka.producer.send_and_wait.call_args_list:
        assert call.kwargs["value"].get("correlation_id") == "corr-123"


@pytest.mark.asyncio
async def test_order_service_batch_kafka_failure_does_not_fail_batch(mock_redis, mock_kafka_producer):
    from services.kafka_service import KafkaService

    kafka = KafkaService("localhost:9092")
    kafka.producer = mock_kafka_producer
    kafka.producer.start = AsyncMock()
    kafka.producer.stop = AsyncMock()
    kafka.producer.send_and_wait.side_effect = Exception("Kafka down")

    service = OrderService(mock_redis, kafka_service=kafka)

    batch_events = [
        {"event_type": "order.created", "order": {"id": "batch-1"}, "timestamp": datetime.utcnow().isoformat()},
        {"event_type": "order.dispatched", "order": {"id": "batch-2"}, "timestamp": datetime.utcnow().isoformat()},
    ]

    result = await service.dispatch_events(batch_events, correlation_id="test-correlation")

    assert result.success is True
    assert result.processed_count == 2
    assert result.failed_count == 0
    assert result.errors == []
    assert kafka.producer.send_and_wait.await_count == 2
    assert mock_redis.publish.await_count == 2


# ---------------------------------------------------------------------------
# WebSocket Bridge
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_websocket_bridge_broadcast_loop_requires_started_consumer(caplog):
    from services.kafka_service import WebSocketBridge

    bridge = WebSocketBridge("localhost:9092")

    with caplog.at_level("ERROR", logger="services.kafka_service"):
        await bridge.broadcast_loop()

    assert "Kafka consumer not initialized" in caplog.text


@pytest.mark.asyncio
async def test_websocket_bridge_connections():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092")
        await bridge.start()

        ws1 = MagicMock()
        ws2 = MagicMock()

        bridge.add_connection(ws1)
        bridge.add_connection(ws2)
        assert len(bridge.connections) == 2

        ws1_send = AsyncMock()
        ws2_send = AsyncMock()
        ws1.send_text = ws1_send
        ws2.send_text = ws2_send

        mock_msg = MagicMock()
        mock_msg.value = {"event_type": "order.created", "order": {"id": "1"}}
        mock_consumer.__aiter__.return_value = [mock_msg]

        bridge.running = True
        await bridge.broadcast_loop()

        ws1_send.assert_awaited_once()
        ws2_send.assert_awaited_once()

        bridge.remove_connection(ws1)
        assert len(bridge.connections) == 1

        await bridge.stop()
        mock_consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_websocket_bridge_multiple_connections():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092")
        await bridge.start()

        num_clients = 5
        wss = []
        sends = []
        for i in range(num_clients):
            ws = MagicMock()
            send = AsyncMock()
            ws.send_text = send
            wss.append(ws)
            sends.append(send)
            bridge.add_connection(ws)

        assert len(bridge.connections) == num_clients

        mock_msg = MagicMock()
        mock_msg.value = {"event_type": "order.test", "order": {"id": "test"}}
        mock_consumer.__aiter__.return_value = [mock_msg]

        bridge.running = True
        await bridge.broadcast_loop()

        for send in sends:
            send.assert_awaited_once_with(json.dumps(mock_msg.value))

        await bridge.stop()


@pytest.mark.asyncio
async def test_websocket_bridge_removes_disconnected_clients():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092")
        await bridge.start()

        healthy_ws = MagicMock()
        healthy_send = AsyncMock()
        healthy_ws.send_text = healthy_send

        dead_ws = MagicMock()
        dead_send = AsyncMock()
        dead_send.side_effect = Exception("Connection closed")
        dead_ws.send_text = dead_send

        bridge.add_connection(healthy_ws)
        bridge.add_connection(dead_ws)
        assert len(bridge.connections) == 2

        mock_msg = MagicMock()
        mock_msg.value = {"event_type": "order.test"}
        mock_consumer.__aiter__.return_value = [mock_msg]

        bridge.running = True
        await bridge.broadcast_loop()

        healthy_send.assert_awaited_once()
        dead_send.assert_awaited_once()
        assert dead_ws not in bridge.connections
        assert healthy_ws in bridge.connections

        await bridge.stop()


@pytest.mark.asyncio
async def test_websocket_bridge_error_recovery():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()

        class RaiseOnFirstCall:
            def __init__(self):
                self.called = False
            def __aiter__(self):
                return self
            async def __anext__(self):
                if not self.called:
                    self.called = True
                    raise Exception("Kafka connection lost")
                raise StopAsyncIteration

        mock_consumer.__aiter__.return_value = RaiseOnFirstCall()

        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092")
        await bridge.start()
        bridge.running = True

        with patch("asyncio.sleep", AsyncMock()):
            await bridge.broadcast_loop()

        await bridge.stop()


@pytest.mark.asyncio
async def test_websocket_bridge_consumer_configuration():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092", topic="orders")
        await bridge.start()

        mock_consumer_cls.assert_called_once()
        call_kwargs = mock_consumer_cls.call_args.kwargs
        assert call_kwargs["group_id"] == "ws-bridge"
        assert call_kwargs["auto_offset_reset"] == "latest"
        assert call_kwargs["enable_auto_commit"] is True
        assert "localhost:9092" in call_kwargs["bootstrap_servers"]
        assert "orders" in call_kwargs["bootstrap_servers"] or "orders" in mock_consumer_cls.call_args.args

        await bridge.stop()


@pytest.mark.asyncio
async def test_websocket_bridge_add_remove_connection():
    with patch("services.kafka_service.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        mock_consumer_cls.return_value = mock_consumer

        from services.kafka_service import WebSocketBridge

        bridge = WebSocketBridge("localhost:9092")
        await bridge.start()

        ws = MagicMock()
        bridge.add_connection(ws)
        assert ws in bridge.connections

        bridge.remove_connection(ws)
        assert ws not in bridge.connections

        bridge.remove_connection(ws)

        await bridge.stop()
