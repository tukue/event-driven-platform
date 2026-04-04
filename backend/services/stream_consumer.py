import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any
from redis_client import redis_client

logger = logging.getLogger(__name__)

class StreamConsumer:
    """Redis Streams consumer for processing events asynchronously"""
    
    def __init__(self, stream_name: str = "pizza_orders_stream", group_name: str = "event_processors"):
        self.stream_name = stream_name
        self.group_name = group_name
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
        
        try:
            while self.running:
                # Read messages from the stream
                messages = await self.redis.read_stream_group(
                    self.stream_name, 
                    self.group_name, 
                    self.consumer_name,
                    count=10,
                    block=5000  # Block for 5 seconds
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
                                logger.error(f"Failed to process message {message_id}: {e}")
                    
                    # Acknowledge processed messages
                    if message_ids:
                        await self.redis.acknowledge_message(
                            self.stream_name, 
                            self.group_name, 
                            message_ids
                        )
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
        except Exception as e:
            logger.error(f"Error in stream consumer: {e}")
            if self.running:
                # Restart consumer after error
                await asyncio.sleep(5)
                await self.start_consuming()
    
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
            
            # Call registered handler if available
            if event_type in self.handlers:
                await self.handlers[event_type](event_data)
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event data: {e}")
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            raise  # Re-raise to prevent acknowledgment

class EventProcessor:
    """Example event processor that demonstrates stream consumption"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.consumer = StreamConsumer()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up event handlers"""
        self.consumer.register_handler("order.created", self._handle_order_created)
        self.consumer.register_handler("order.supplier_accepted", self._handle_supplier_accepted)
        self.consumer.register_handler("order.customer_accepted", self._handle_customer_accepted)
        self.consumer.register_handler("order.dispatched", self._handle_order_dispatched)
        self.consumer.register_handler("order.delivered", self._handle_order_delivered)
    
    async def _handle_order_created(self, event_data: dict):
        """Handle order creation events"""
        order = event_data.get("order", {})
        logger.info(f"Order created: {order.get('id')} - {order.get('pizza_name')} from {order.get('supplier_name')}")
        
        # Could trigger notifications, update metrics, etc.
        await self._update_order_metrics("created")
    
    async def _handle_supplier_accepted(self, event_data: dict):
        """Handle supplier acceptance events"""
        order = event_data.get("order", {})
        logger.info(f"Supplier accepted order: {order.get('id')}")
        
        await self._update_order_metrics("supplier_accepted")
    
    async def _handle_customer_accepted(self, event_data: dict):
        """Handle customer acceptance events"""
        order = event_data.get("order", {})
        logger.info(f"Customer accepted order: {order.get('id')}")
        
        await self._update_order_metrics("customer_accepted")
    
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
        # This could integrate with your metrics service
        # For now, just log the metric update
        logger.info(f"Updating metrics for event: {event_type}")
    
    async def start(self):
        """Start the event processor"""
        await self.consumer.start_consuming()
    
    async def stop(self):
        """Stop the event processor"""
        await self.consumer.stop_consuming()

# Global event processor instance
event_processor = EventProcessor(redis_client)