import asyncio
from redis_client import redis_client
from services.order_service import OrderService
from models import Order

async def test_order_creation():
    """Test creating an order and verifying it's saved to Redis"""
    
    print("=" * 60)
    print("Testing Order Creation and Redis Storage")
    print("=" * 60)
    
    # Connect to Redis
    await redis_client.connect()
    print("✅ Connected to Redis\n")
    
    # Create order service
    order_service = OrderService(redis_client)
    
    # Create test order
    test_order = Order(
        source_name="Test Quick Mart",
        item_name="Electronics Bundle",
        source_price=12.50,
        markup_percentage=30.0
    )
    
    print(f"Creating order: {test_order.item_name}")
    print(f"Source: {test_order.source_name}")
    print(f"Price: ${test_order.source_price}")
    print(f"Markup: {test_order.markup_percentage}%\n")
    
    # Create the order
    event = await order_service.create_order(test_order)
    
    print(f"\n✅ Order created with ID: {event.order.id}")
    print(f"Status: {event.order.status}")
    print(f"Event type: {event.event_type}\n")
    
    # Verify it's in Redis
    print("Verifying order in Redis...")
    order_key = f"order:{event.order.id}"
    stored_data = await redis_client.client.get(order_key)
    
    if stored_data:
        print(f"✅ Order found in Redis!")
        print(f"Key: {order_key}")
        print(f"Data length: {len(stored_data)} bytes\n")
    else:
        print(f"❌ Order NOT found in Redis!")
        return
    
    # Get all orders
    print("Fetching all orders from Redis...")
    all_orders = await order_service.get_all_orders()
    print(f"✅ Total orders in database: {len(all_orders)}\n")
    
    # Display all orders
    for i, order in enumerate(all_orders, 1):
        print(f"{i}. {order['item_name']} - ${order['source_price']} ({order['status']})")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    
    await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_order_creation())
