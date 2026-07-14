from models import Order, OrderStatus, OrderEvent, EventBatch, BatchResult
from datetime import datetime
import uuid
import json
import random
import string
import logging

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, redis_client, kafka_service=None):
        self.redis = redis_client
        self.kafka = kafka_service
    
    async def create_order(self, order: Order) -> OrderEvent:
        print(f"Creating order: {order.item_name} from {order.source_name}")
        order.id = str(uuid.uuid4())
        order.created_at = datetime.utcnow()
        order.updated_at = order.created_at
        order.status = OrderStatus.PENDING_SOURCE
        
        order.tracking_id = self._generate_tracking_id()
        order.source_tracking_id = self._generate_source_tracking_id(order.source_name)
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type="order.created",
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        print(f"Order created and published: {order.id}")
        print(f"  Tracking ID: {order.tracking_id}")
        print(f"  Source Tracking ID: {order.source_tracking_id}")
        return event
    
    async def source_respond(self, order_id: str, accept: bool, notes: str = None, estimated_time: int = None) -> OrderEvent:
        order = await self._get_order(order_id)
        
        if accept:
            order.status = OrderStatus.SOURCE_ACCEPTED
            order.source_notes = notes
            order.estimated_delivery_time = estimated_time or 30
            event_type = "order.source_accepted"
        else:
            order.status = OrderStatus.SOURCE_REJECTED
            order.source_notes = notes or "Source declined"
            event_type = "order.source_rejected"
        
        order.updated_at = datetime.utcnow()
        await self._save_order(order)
        
        event = OrderEvent(
            event_type=event_type,
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        return event
    
    async def buyer_accept(self, order_id: str, buyer_name: str, delivery_address: str) -> OrderEvent:
        order = await self._get_order(order_id)
        
        if order.status != OrderStatus.SOURCE_ACCEPTED:
            raise ValueError("Order must be accepted by source first")
        
        order.buyer_price = round(order.source_price * (1 + order.markup_percentage / 100), 2)
        order.buyer_name = buyer_name
        order.delivery_address = delivery_address
        order.status = OrderStatus.BUYER_ACCEPTED
        order.updated_at = datetime.utcnow()
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type="order.buyer_accepted",
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        return event
    
    async def dispatch_order(self, order_id: str, driver_name: str) -> OrderEvent:
        order = await self._get_order(order_id)
        
        order.driver_name = driver_name
        order.status = OrderStatus.DISPATCHED
        order.updated_at = datetime.utcnow()
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type="order.dispatched",
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        return event
    
    async def update_status(self, order_id: str, status: OrderStatus) -> OrderEvent:
        order = await self._get_order(order_id)
        order.status = status
        order.updated_at = datetime.utcnow()
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type=f"order.{status.value}",
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        return event
    
    async def get_all_orders(self):
        keys = await self.redis.client.keys("order:*")
        orders = []
        for key in keys:
            order_data = await self.redis.client.get(key)
            if order_data:
                orders.append(json.loads(order_data))
        return sorted(orders, key=lambda x: x['created_at'], reverse=True)
    
    async def get_order_by_tracking_id(self, tracking_id: str):
        """Find an order by its tracking ID"""
        all_orders = await self.get_all_orders()
        for order in all_orders:
            if order.get('tracking_id') == tracking_id or order.get('source_tracking_id') == tracking_id:
                return order
        return None
    
    async def _save_order(self, order: Order):
        order_dict = order.model_dump(mode='json')
        key = f"order:{order.id}"
        await self.redis.client.set(
            key,
            json.dumps(order_dict, default=str)
        )
        print(f"Order saved to Redis: {key}")
        
        saved = await self.redis.client.get(key)
        if saved:
            print(f"Verified order in Redis: {order.id}")
        else:
            print(f"Failed to verify order in Redis: {order.id}")
    
    async def _get_order(self, order_id: str) -> Order:
        order_data = await self.redis.client.get(f"order:{order_id}")
        if not order_data:
            raise ValueError(f"Order {order_id} not found")
        return Order(**json.loads(order_data))
    
    async def _publish_event(self, event: OrderEvent):
        event_data = event.model_dump(mode='json')
        
        await self.redis.publish(
            "orders",
            json.dumps(event_data, default=str)
        )
        
        stream_data = {
            "event_type": event.event_type,
            "order_id": event.order.id,
            "timestamp": event.timestamp.isoformat(),
            "data": json.dumps(event_data, default=str)
        }
        
        if event.correlation_id:
            stream_data["correlation_id"] = event.correlation_id
        
        await self.redis.add_to_stream("orders_stream", stream_data)
        print(f"Event published to stream: {event.event_type} for order {event.order.id}")

        if self.kafka:
            try:
                await self.kafka.publish_event(event_data)
                print(f"Event published to Kafka: {event.event_type} for order {event.order.id}")
            except Exception as e:
                logger.warning(
                    "Kafka publish failed for event %s on order %s (non-blocking): %s",
                    event.event_type,
                    event.order.id,
                    e,
                )
    
    def _generate_tracking_id(self) -> str:
        """
        Generate a human-readable tracking ID
        Format: ORD-YYYY-NNNNNN (e.g., ORD-2024-001234)
        """
        year = datetime.utcnow().year
        number = random.randint(100000, 999999)
        return f"ORD-{year}-{number}"
    
    def _generate_source_tracking_id(self, source_name: str) -> str:
        """
        Generate a source-specific tracking ID
        Format: SOURCE_PREFIX-NNNN (e.g., PP-1234 for Quick Mart)
        """
        words = source_name.upper().split()
        prefix = ''.join(word[0] for word in words[:3])
        
        number = random.randint(1000, 9999)
        
        return f"{prefix}-{number}"
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for event batching"""
        return f"batch-{uuid.uuid4()}"
    
    async def dispatch_events(self, events: list[dict], correlation_id: str = None) -> BatchResult:
        """
        Dispatch multiple events atomically with correlation ID tracking
        
        Args:
            events: List of event dictionaries to publish
            correlation_id: Optional correlation ID (generated if not provided)
        
        Returns:
            BatchResult with success status and processing details
        """
        if correlation_id is None:
            correlation_id = self._generate_correlation_id()
        
        batch = EventBatch(
            correlation_id=correlation_id,
            events=events,
            created_at=datetime.utcnow()
        )
        
        processed_count = 0
        failed_count = 0
        errors = []
        
        try:
            for event_data in events:
                try:
                    event_data['correlation_id'] = correlation_id
                    
                    await self.redis.publish(
                        "orders",
                        json.dumps(event_data, default=str)
                    )
                    
                    stream_data = {
                        "event_type": event_data.get("event_type", "batch_event"),
                        "correlation_id": correlation_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": json.dumps(event_data, default=str)
                    }
                    
                    await self.redis.add_to_stream("orders_stream", stream_data)

                    if self.kafka:
                        try:
                            await self.kafka.publish_event(event_data)
                        except Exception as e:
                            logger.warning(
                                "Kafka publish failed for batch event %s (correlation_id=%s, non-blocking): %s",
                                event_data.get("event_type", "batch_event"),
                                correlation_id,
                                e,
                            )

                    processed_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to publish event: {str(e)}")
                    
                    await self._publish_rollback_event(correlation_id, errors)
                    
                    return BatchResult(
                        correlation_id=correlation_id,
                        success=False,
                        processed_count=processed_count,
                        failed_count=failed_count,
                        errors=errors,
                        timestamp=datetime.utcnow()
                    )
            
            return BatchResult(
                correlation_id=correlation_id,
                success=True,
                processed_count=processed_count,
                failed_count=0,
                errors=[],
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            errors.append(f"Batch processing error: {str(e)}")
            await self._publish_rollback_event(correlation_id, errors)
            
            return BatchResult(
                correlation_id=correlation_id,
                success=False,
                processed_count=processed_count,
                failed_count=len(events) - processed_count,
                errors=errors,
                timestamp=datetime.utcnow()
            )
    
    async def _publish_rollback_event(self, correlation_id: str, errors: list[str]):
        """Publish a rollback event when batch processing fails"""
        rollback_event = {
            "event_type": "batch.rollback",
            "correlation_id": correlation_id,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.redis.publish(
                "orders",
                json.dumps(rollback_event, default=str)
            )
            print(f"Published rollback event for correlation_id: {correlation_id}")
        except Exception as e:
            print(f"Failed to publish rollback event: {str(e)}")
