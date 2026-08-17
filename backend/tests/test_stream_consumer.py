import json

import pytest

from services.stream_consumer import StreamConsumer


@pytest.mark.asyncio
async def test_invalid_message_is_preserved_in_retry_stream(mock_redis):
    consumer = StreamConsumer(stream_name="orders_stream", retry_stream="orders_stream:retry")
    consumer.redis = mock_redis
    message = {"event_type": "order.created", "data": "not-json"}

    with pytest.raises(ValueError, match="Invalid event payload"):
        await consumer._process_message("1-0", message)

    await consumer._send_to_retry_stream("1-0", message, ValueError("Invalid event payload"))

    retry_message = mock_redis._streams["orders_stream:retry"][-1][1]
    assert retry_message["original_stream"] == "orders_stream"
    assert retry_message["original_message_id"] == "1-0"
    assert json.loads(retry_message["data"]) == message
