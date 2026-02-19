"""
Generate test data for Grafana visualization testing
Creates sample orders with various statuses including delivered orders
"""
import asyncio
import random
from datetime import datetime, timedelta
from redis_client import redis_client
from services.order_service import OrderService
from models import PizzaOrder, OrderStatus

# Sample data
SUPPLIERS = ["Pizza Palace", "Mama Mia's", "Slice Heaven", "Dough Bros", "Crusty's"]
PIZZAS = ["Margherita", "Pepperoni", "Hawaiian", "Veggie Supreme", "Meat Lovers", "BBQ Chicken"]
DRIVERS = ["John Smith", "Maria Garcia", "Ahmed Khan", "Lisa Chen", "Carlos Rodriguez"]
CUSTOMERS = ["Alice Johnson", "Bob Williams", "Carol Davis", "David Martinez", "Emma Wilson"]
ADDRESSES = [
    "123 Main St, Apt 4B",
    "456 Oak Avenue",
    "789 Pine Road, Suite 200",
    "321 Elm Street",
    "654 Maple Drive"
]

async def create_sample_order(order_service: OrderService, status: OrderStatus, days_ago: int = 0):
    """Create a sample order with specified status"""
    
    # Create initial order
    order = PizzaOrder(
        supplier_name=random.choice(SUPPLIERS),
        pizza_name=random.choice(PIZZAS),
        supplier_price=round(random.uniform(8.0, 15.0), 2),
        markup_percentage=30.0
    )
    
    # Create order
    event = await order_service.create_order(order)
    order_id = event.order.id
    
    # Progress through states based on target status
    if status in [OrderStatus.SUPPLIER_ACCEPTED, OrderStatus.CUSTOMER_ACCEPTED, 
                  OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DISPATCHED,
                  OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.supplier_respond(
            order_id, 
            accept=True, 
            notes="Order confirmed",
            estimated_time=random.randint(20, 45)
        )
    
    if status in [OrderStatus.CUSTOMER_ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY,
                  OrderStatus.DISPATCHED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.customer_accept(
            order_id,
            customer_name=random.choice(CUSTOMERS),
            delivery_address=random.choice(ADDRESSES)
        )
    
    if status in [OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DISPATCHED,
                  OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.update_status(order_id, OrderStatus.PREPARING)
    
    if status in [OrderStatus.READY, OrderStatus.DISPATCHED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.update_status(order_id, OrderStatus.READY)
    
    if status in [OrderStatus.DISPATCHED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.dispatch_order(order_id, random.choice(DRIVERS))
    
    if status in [OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
        await order_service.update_status(order_id, OrderStatus.IN_TRANSIT)
    
    if status == OrderStatus.DELIVERED:
        await order_service.update_status(order_id, OrderStatus.DELIVERED)
    
    # Adjust timestamp if needed (for historical data)
    if days_ago > 0:
        order_obj = await order_service._get_order(order_id)
        past_date = datetime.utcnow() - timedelta(days=days_ago)
        order_obj.updated_at = past_date
        await order_service._save_order(order_obj)
    
    return order_id

async def generate_test_data():
    """Generate comprehensive test data for Grafana"""
    
    print("🚀 Starting test data generation...")
    print("=" * 60)
    
    await redis_client.connect()
    order_service = OrderService(redis_client)
    
    try:
        # Generate delivered orders over the past 30 days
        print("\n📦 Generating delivered orders (past 30 days)...")
        delivered_count = 0
        for i in range(50):  # 50 delivered orders
            days_ago = random.randint(0, 30)
            await create_sample_order(order_service, OrderStatus.DELIVERED, days_ago)
            delivered_count += 1
            if (i + 1) % 10 == 0:
                print(f"   ✅ Created {i + 1} delivered orders")
        
        print(f"\n✅ Total delivered orders: {delivered_count}")
        
        # Generate orders in various active states
        print("\n🔄 Generating active orders...")
        
        # In transit orders
        in_transit_count = 5
        for _ in range(in_transit_count):
            await create_sample_order(order_service, OrderStatus.IN_TRANSIT)
        print(f"   🚚 Created {in_transit_count} in-transit orders")
        
        # Dispatched orders
        dispatched_count = 3
        for _ in range(dispatched_count):
            await create_sample_order(order_service, OrderStatus.DISPATCHED)
        print(f"   📤 Created {dispatched_count} dispatched orders")
        
        # Ready orders
        ready_count = 4
        for _ in range(ready_count):
            await create_sample_order(order_service, OrderStatus.READY)
        print(f"   ✅ Created {ready_count} ready orders")
        
        # Preparing orders
        preparing_count = 6
        for _ in range(preparing_count):
            await create_sample_order(order_service, OrderStatus.PREPARING)
        print(f"   👨‍🍳 Created {preparing_count} preparing orders")
        
        # Pending orders
        pending_count = 8
        for _ in range(pending_count):
            await create_sample_order(order_service, OrderStatus.PENDING_SUPPLIER)
        print(f"   ⏳ Created {pending_count} pending orders")
        
        # Summary
        total_orders = delivered_count + in_transit_count + dispatched_count + ready_count + preparing_count + pending_count
        
        print("\n" + "=" * 60)
        print("📊 DATA GENERATION SUMMARY")
        print("=" * 60)
        print(f"Total Orders Created: {total_orders}")
        print(f"  - Delivered: {delivered_count}")
        print(f"  - In Transit: {in_transit_count}")
        print(f"  - Dispatched: {dispatched_count}")
        print(f"  - Ready: {ready_count}")
        print(f"  - Preparing: {preparing_count}")
        print(f"  - Pending: {pending_count}")
        print("=" * 60)
        
        print("\n✅ Test data generation complete!")
        print("\n📈 Next steps:")
        print("   1. Start your backend: uvicorn main:app --reload")
        print("   2. Check metrics at: http://localhost:8000/metrics")
        print("   3. View JSON metrics at: http://localhost:8000/api/metrics")
        print("   4. Configure Grafana to use these endpoints")
        
    except Exception as e:
        print(f"\n❌ Error generating test data: {str(e)}")
        raise
    finally:
        await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_test_data())
