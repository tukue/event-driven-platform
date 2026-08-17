import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any
from redis_client import redis_client

logger = logging.getLogger(__name__)

class StreamConsumer:
    """Redis Streams consumer for processing events asynchronously"""
    
    def __init__(
        self,
        stream_name: str = "orders_stream",
        group_name: str = "event_processors",
        dead_letter_stream: str = "orders_stream:dead_letter",
    ):
        self.stream_name = stream_name
        self.group_name = group_name
        self.dead_letter_stream = dead_letter_stream
        self.consumer_name = f"consumer_{id(self)}"
        self.redis = redis_client
        self.handlers: Dict[str, Callable] = {}
        self.running = False
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register an event handler for a specific event type
        
        Args:
            event_type: The event type to handle (e.g., "order.created")
            handler: Async function that takes event_data as parameter
        """
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def start_consuming(self):
        """Start consuming events from the stream"""
        self.running = True
        logger.info(f"Starting stream consumer for {self.stream_name} in group {self.group_name}")

        while self.running:
            try:
                messages = await self.redis.read_stream_group(
                    self.stream_name, 
                    self.group_name, 
                    self.consumer_name,
                    count=10,
                    block=5000
                )
                
                if messages:
                    message_ids = []
                    
                    for stream_messages in messages:
                        stream_name, entries = stream_messages
                        
                        for message_id, message_data in entries:
                            try:
                                await self._process_message(message_id, message_data)
                                message_ids.append(message_id)
                            except Exception as e:
                                logger.exception("Failed to process message %s", message_id)
                                try:
                                    await self._send_to_dead_letter_queue(message_id, message_data, e)
                                    message_ids.append(message_id)
                                except Exception:
                                    logger.exception(
                                        "Unable to dead-letter message %s; leaving it pending",
                                        message_id,
                                    )
                    
                    if message_ids:
                        await self.redis.acknowledge_message(
                            self.stream_name, 
                            self.group_name, 
                            message_ids
                        )
                
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in stream consumer")
                if self.running:
                    await asyncio.sleep(5)
    
    async def stop_consuming(self):
        """Stop consuming events"""
        self.running = False
        logger.info("Stopped stream consumer")
    
    async def _process_message(self, message_id: str, message_data: dict):
        """Process a single message from the stream"""
        try:
            event_type = message_data.get("event_type")
            event_data = json.loads(message_data.get("data", "{}"))
            
            logger.info(f"Processing event: {event_type} (ID: {message_id})")
            
            if event_type in self.handlers:
                await self.handlers[event_type](event_data)
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event data: {e}")
            raise ValueError(f"Invalid event payload: {e}") from e
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            raise

    async def _send_to_dead_letter_queue(
        self, message_id: str, message_data: dict, error: Exception
    ) -> None:
        """Preserve unprocessable events before acknowledging them from the source stream."""
        await self.redis.add_to_stream(
            self.dead_letter_stream,
            {
                "original_stream": self.stream_name,
                "original_message_id": message_id,
                "failed_at": datetime.utcnow().isoformat(),
                "error": str(error),
                "data": json.dumps(message_data, default=str),
            },
        )

class EventProcessor:
    """Example event processor that demonstrates stream consumption"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.consumer = StreamConsumer()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up event handlers"""
        self.consumer.register_handler("order.created", self._handle_order_created)
        self.consumer.register_handler("order.source_accepted", self._handle_source_accepted)
        self.consumer.register_handler("order.buyer_accepted", self._handle_buyer_accepted)
        self.consumer.register_handler("order.dispatched", self._handle_order_dispatched)
        self.consumer.register_handler("order.delivered", self._handle_order_delivered)
    
    async def _handle_order_created(self, event_data: dict):
        """Handle order creation events"""
        order = event_data.get("order", {})
        logger.info(f"Order created: {order.get('id')} - {order.get('item_name')} from {order.get('source_name')}")
        
        await self._update_order_metrics("created")
    
    async def _handle_source_accepted(self, event_data: dict):
        """Handle source acceptance events"""
        order = event_data.get("order", {})
        logger.info(f"Source accepted order: {order.get('id')}")
        
        await self._update_order_metrics("source_accepted")
    
    async def _handle_buyer_accepted(self, event_data: dict):
        """Handle buyer acceptance events"""
        order = event_data.get("order", {})
        logger.info(f"Buyer accepted order: {order.get('id')}")
        
        await self._update_order_metrics("buyer_accepted")
    
    async def _handle_order_dispatched(self, event_data: dict):
        """Handle order dispatch events"""
        order = event_data.get("order", {})
        logger.info(f"Order dispatched: {order.get('id')} - Driver: {order.get('driver_name')}")
        
        await self._update_order_metrics("dispatched")
    
    async def _handle_order_delivered(self, event_data: dict):
        """Handle order delivery events"""
        order = event_data.get("order", {})
        logger.info(f"Order delivered: {order.get('id')}")
        
        await self._update_order_metrics("delivered")
    
    async def _update_order_metrics(self, event_type: str):
        """Update metrics based on event type"""
        logger.info(f"Updating metrics for event: {event_type}")
    
    async def start(self):
        """Start the event processor"""
        await self.consumer.start_consuming()
    
    async def stop(self):
        """Stop the event processor"""
        await self.consumer.stop_consuming()

# Global event processor instance
event_processor = EventProcessor(redis_client)
