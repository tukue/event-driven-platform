import asyncio
import redis.asyncio as redis
from config import settings
import json

async def inspect_redis_data():
    """Inspect all orders stored in Redis"""
    print("Connecting to Redis...")
    
    try:
        connection_params = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True
        }
        
        if settings.redis_username:
            connection_params["username"] = settings.redis_username
        
        if settings.redis_password:
            connection_params["password"] = settings.redis_password
        
        client = redis.Redis(**connection_params)
        
        await client.ping()
        print("✅ Connected to Redis\n")
        
        # Get all order keys
        keys = await client.keys("order:*")
        print(f"Found {len(keys)} orders in database\n")
        
        if not keys:
            print("No orders found. Create some orders to see them here!")
        else:
            for key in keys:
                order_data = await client.get(key)
                order = json.loads(order_data)
                
                print(f"{'='*60}")
                print(f"Order ID: {order['id']}")
                print(f"Pizza: {order['pizza_name']}")
                print(f"Supplier: {order['supplier_name']}")
                print(f"Status: {order['status']}")
                print(f"Supplier Price: ${order['supplier_price']}")
                if order.get('customer_price'):
                    print(f"Customer Price: ${order['customer_price']}")
                if order.get('customer_name'):
                    print(f"Customer: {order['customer_name']}")
                    print(f"Address: {order['delivery_address']}")
                if order.get('driver_name'):
                    print(f"Driver: {order['driver_name']}")
                print(f"Created: {order['created_at']}")
                print(f"{'='*60}\n")
        
        # Check pub/sub channels
        print("\nActive Pub/Sub Channels:")
        channels = await client.pubsub_channels()
        if channels:
            for channel in channels:
                print(f"  - {channel}")
        else:
            print("  No active channels (normal when no clients connected)")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_redis_data())
