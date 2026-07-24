import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Kafka consumer for processing order events asynchronously via consumer groups"""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str = "orders",
        group_id: str = "order-processors",
        auto_offset_reset: str = "earliest",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        self._consume_task: Optional[asyncio.Task] = None
        self._processed_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None

    def register_handler(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
        )
        await self.consumer.start()
        self.running = True
        self._consume_task = asyncio.create_task(self.consume())
        logger.info(
            f"Kafka consumer started (group={self.group_id}, topic={self.topic})"
        )

    async def stop(self):
        self.running = False
        if self._consume_task and not self._consume_task.done():
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
            self._consume_task = None
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(self):
        if not self.consumer:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        logger.info("Starting event consumption loop")
        try:
            async for msg in self.consumer:
                if not self.running:
                    break
                await self._process_message(msg)
        except Exception as e:
            logger.error(f"Error in consume loop: {e}")
            self._last_error = str(e)
            self._error_count += 1
            if self.running:
                logger.info("Attempting to restart consumption in 5 seconds...")
                await asyncio.sleep(5)
                self._consume_task = asyncio.create_task(self.consume())

    async def _process_message(self, msg):
        try:
            event_data = msg.value
            event_type = event_data.get("event_type", "unknown")

            logger.info(
                f"Received event: {event_type} (partition={msg.partition}, offset={msg.offset})"
            )

            if event_type in self.handlers:
                await self.handlers[event_type](event_data)
                self._processed_count += 1
            else:
                logger.warning(f"No handler registered for event type: {event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize message: {e}")
            self._error_count += 1
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._error_count += 1
            self._last_error = str(e)
            raise

    def get_stats(self) -> dict:
        return {
            "running": self.running,
            "group_id": self.group_id,
            "topic": self.topic,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "registered_handlers": list(self.handlers.keys()),
        }


class OrderEventProcessor:
    """Processes order lifecycle events consumed from Kafka"""

    def __init__(self, kafka_bootstrap_servers: str, topic: str = "orders"):
        self.consumer = KafkaConsumerService(
            bootstrap_servers=kafka_bootstrap_servers,
            topic=topic,
            group_id="order-event-processors",
        )
        self._order_log: list = []
        self._consume_task: Optional[asyncio.Task] = None
        self._setup_handlers()

    def _setup_handlers(self):
        self.consumer.register_handler("order.created", self._handle_order_created)
        self.consumer.register_handler(
            "order.source_accepted", self._handle_source_accepted
        )
        self.consumer.register_handler(
            "order.source_rejected", self._handle_source_rejected
        )
        self.consumer.register_handler(
            "order.buyer_accepted", self._handle_buyer_accepted
        )
        self.consumer.register_handler(
            "order.dispatched", self._handle_order_dispatched
        )
        self.consumer.register_handler(
            "order.preparing", self._handle_status_change
        )
        self.consumer.register_handler("order.ready", self._handle_status_change)
        self.consumer.register_handler(
            "order.in_transit", self._handle_status_change
        )
        self.consumer.register_handler(
            "order.delivered", self._handle_order_delivered
        )
        self.consumer.register_handler(
            "batch.rollback", self._handle_batch_rollback
        )

    async def _handle_order_created(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(
            f"Order created: {order.get('id')} - {order.get('item_name')} from {order.get('source_name')}"
        )
        self._log_event("order.created", order.get("id"))

    async def _handle_source_accepted(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(f"Source accepted order: {order.get('id')}")
        self._log_event("order.source_accepted", order.get("id"))

    async def _handle_source_rejected(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(
            f"Source rejected order: {order.get('id')} - {order.get('source_notes')}"
        )
        self._log_event("order.source_rejected", order.get("id"))

    async def _handle_buyer_accepted(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(
            f"Buyer accepted order: {order.get('id')} - buyer: {order.get('buyer_name')}"
        )
        self._log_event("order.buyer_accepted", order.get("id"))

    async def _handle_order_dispatched(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(
            f"Order dispatched: {order.get('id')} - Driver: {order.get('driver_name')}"
        )
        self._log_event("order.dispatched", order.get("id"))

    async def _handle_status_change(self, event_data: dict):
        order = event_data.get("order", {})
        event_type = event_data.get("event_type", "unknown")
        logger.info(f"Order {event_type}: {order.get('id')}")
        self._log_event(event_type, order.get("id"))

    async def _handle_order_delivered(self, event_data: dict):
        order = event_data.get("order", {})
        logger.info(f"Order delivered: {order.get('id')}")
        self._log_event("order.delivered", order.get("id"))

    async def _handle_batch_rollback(self, event_data: dict):
        correlation_id = event_data.get("correlation_id")
        errors = event_data.get("errors", [])
        logger.warning(
            f"Batch rollback: correlation_id={correlation_id}, errors={errors}"
        )
        self._log_event("batch.rollback", correlation_id)

    def _log_event(self, event_type: str, entity_id: str):
        self._order_log.append(
            {
                "event_type": event_type,
                "entity_id": entity_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def start(self):
        await self.consumer.start()
        self._consume_task = self.consumer._consume_task

    async def consume(self):
        await self.consumer.consume()

    async def stop(self):
        if self._consume_task and not self._consume_task.done():
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
            self._consume_task = None
        await self.consumer.stop()

    def get_stats(self) -> dict:
        stats = self.consumer.get_stats()
        stats["order_log_count"] = len(self._order_log)
        return stats

    def get_order_log(self) -> list:
        return list(self._order_log)
