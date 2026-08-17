import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

logger = logging.getLogger(__name__)

class KafkaService:
    def __init__(self, bootstrap_servers: str, topic: str = "orders"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            enable_idempotence=True,
        )
        await self.producer.start()
        logger.info(f"Kafka producer started (bootstrap_servers={self.bootstrap_servers}, topic={self.topic})")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def publish_event(self, event_data: dict):
        """Publish an event only after Kafka acknowledges durable receipt."""
        if not self.producer:
            raise RuntimeError("Kafka producer not started. Call start() first.")

        order_id = event_data.get("order", {}).get("id") or event_data.get("order_id")
        headers = self._event_headers(event_data)
        return await self.producer.send_and_wait(
            topic=self.topic,
            key=order_id,
            value=event_data,
            headers=headers,
        )

    async def publish_events(self, events: list[dict]):
        for event_data in events:
            await self.publish_event(event_data)

    @staticmethod
    def _event_headers(event_data: dict) -> list[tuple[str, bytes]]:
        """Expose routing and tracing metadata without consumers parsing the payload."""
        header_fields = ("event_id", "event_type", "schema_version", "correlation_id")
        return [
            (field, str(event_data[field]).encode("utf-8"))
            for field in header_fields
            if event_data.get(field) is not None
        ]


class WebSocketBridge:
    def __init__(self, bootstrap_servers: str, topic: str = "orders"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer = None
        self.connections: set = set()
        self.running = False

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id="ws-bridge",
            value_deserializer=lambda m: json.loads(m.decode()),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self.consumer.start()
        self.running = True
        logger.info(f"WebSocket bridge consumer started (group=ws-bridge, topic={self.topic})")

    async def stop(self):
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("WebSocket bridge consumer stopped")

    def add_connection(self, websocket):
        self.connections.add(websocket)

    def remove_connection(self, websocket):
        self.connections.discard(websocket)

    async def broadcast_loop(self):
        if not self.consumer:
            logger.error("Kafka consumer not initialized. Call start() first.")
            return

        try:
            async for msg in self.consumer:
                if not self.running:
                    break
                for ws in list(self.connections):
                    try:
                        await ws.send_text(json.dumps(msg.value))
                    except Exception:
                        self.connections.discard(ws)
        except Exception as e:
            logger.error(f"WebSocket bridge error: {e}")
            if self.running:
                await asyncio.sleep(5)
                asyncio.create_task(self.broadcast_loop())
