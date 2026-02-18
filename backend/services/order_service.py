from models import PizzaOrder, OrderStatus, OrderEvent
from datetime import datetime
import uuid
import json
import random
import string

class OrderService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def create_order(self, order: PizzaOrder) -> OrderEvent:
        print(f"📝 Creating order: {order.pizza_name} from {order.supplier_name}")
        order.id = str(uuid.uuid4())
        order.created_at = datetime.utcnow()
        order.updated_at = order.created_at
        order.status = OrderStatus.PENDING_SUPPLIER
        
        # Generate human-readable tracking IDs
        order.tracking_id = self._generate_tracking_id()
        order.supplier_tracking_id = self._generate_supplier_tracking_id(order.supplier_name)
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type="order.created",
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        print(f"✅ Order created and published: {order.id}")
        print(f"   📦 Tracking ID: {order.tracking_id}")
        print(f"   🏪 Supplier Tracking ID: {order.supplier_tracking_id}")
        return event
    
    async def supplier_respond(self, order_id: str, accept: bool, notes: str = None, estimated_time: int = None) -> OrderEvent:
        order = await self._get_order(order_id)
        
        if accept:
            order.status = OrderStatus.SUPPLIER_ACCEPTED
            order.supplier_notes = notes
            order.estimated_delivery_time = estimated_time or 30
            event_type = "order.supplier_accepted"
        else:
            order.status = OrderStatus.SUPPLIER_REJECTED
            order.supplier_notes = notes or "Supplier declined"
            event_type = "order.supplier_rejected"
        
        order.updated_at = datetime.utcnow()
        await self._save_order(order)
        
        event = OrderEvent(
            event_type=event_type,
            order=order,
            timestamp=datetime.utcnow()
        )
        await self._publish_event(event)
        return event
    
    async def customer_accept(self, order_id: str, customer_name: str, delivery_address: str) -> OrderEvent:
        order = await self._get_order(order_id)
        
        if order.status != OrderStatus.SUPPLIER_ACCEPTED:
            raise ValueError("Order must be accepted by supplier first")
        
        order.customer_price = round(order.supplier_price * (1 + order.markup_percentage / 100), 2)
        order.customer_name = customer_name
        order.delivery_address = delivery_address
        order.status = OrderStatus.CUSTOMER_ACCEPTED
        order.updated_at = datetime.utcnow()
        
        await self._save_order(order)
        
        event = OrderEvent(
            event_type="order.customer_accepted",
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
            if order.get('tracking_id') == tracking_id or order.get('supplier_tracking_id') == tracking_id:
                return order
        return None
    
    async def _save_order(self, order: PizzaOrder):
        order_dict = order.model_dump(mode='json')
        key = f"order:{order.id}"
        await self.redis.client.set(
            key,
            json.dumps(order_dict, default=str)
        )
        print(f"✅ Order saved to Redis: {key}")
        
        # Verify it was saved
        saved = await self.redis.client.get(key)
        if saved:
            print(f"✅ Verified order in Redis: {order.id}")
        else:
            print(f"❌ Failed to verify order in Redis: {order.id}")
    
    async def _get_order(self, order_id: str) -> PizzaOrder:
        order_data = await self.redis.client.get(f"order:{order_id}")
        if not order_data:
            raise ValueError(f"Order {order_id} not found")
        return PizzaOrder(**json.loads(order_data))
    
    async def _publish_event(self, event: OrderEvent):
        await self.redis.publish(
            "pizza_orders",
            json.dumps(event.model_dump(mode='json'), default=str)
        )
    
    def _generate_tracking_id(self) -> str:
        """
        Generate a human-readable tracking ID
        Format: PIZZA-YYYY-NNNNNN (e.g., PIZZA-2024-001234)
        """
        year = datetime.utcnow().year
        # Generate 6-digit random number
        number = random.randint(100000, 999999)
        return f"PIZZA-{year}-{number}"
    
    def _generate_supplier_tracking_id(self, supplier_name: str) -> str:
        """
        Generate a supplier-specific tracking ID
        Format: SUPPLIER_PREFIX-NNNN (e.g., PP-1234 for Pizza Palace)
        """
        # Create prefix from supplier name (first letters of each word)
        words = supplier_name.upper().split()
        prefix = ''.join(word[0] for word in words[:3])  # Max 3 letters
        
        # Generate 4-digit number
        number = random.randint(1000, 9999)
        
        return f"{prefix}-{number}"
