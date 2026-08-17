import json

import pytest

from services.stream_consumer import StreamConsumer


@pytest.mark.asyncio
async def test_invalid_message_is_preserved_in_dead_letter_stream(mock_redis):
    consumer = StreamConsumer(stream_name="orders_stream", dead_letter_stream="orders_stream:dead_letter")
    consumer.redis = mock_redis
    message = {"event_type": "order.created", "data": "not-json"}

    with pytest.raises(ValueError, match="Invalid event payload"):
        await consumer._process_message("1-0", message)

    await consumer._send_to_dead_letter_queue("1-0", message, ValueError("Invalid event payload"))

    dead_letter = mock_redis._streams["orders_stream:dead_letter"][-1][1]
    assert dead_letter["original_stream"] == "orders_stream"
    assert dead_letter["original_message_id"] == "1-0"
    assert json.loads(dead_letter["data"]) == message
