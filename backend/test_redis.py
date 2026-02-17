import asyncio
import redis.asyncio as redis
from config import settings

async def test_redis_connection():
    print("Testing Redis connection...")
    print(f"Host: {settings.redis_host}")
    print(f"Port: {settings.redis_port}")
    print(f"Username: {settings.redis_username or '(not set)'}")
    print(f"Password: {'*' * len(settings.redis_password) if settings.redis_password else '(not set)'}")
    print(f"DB: {settings.redis_db}")
    print()
    
    try:
        connection_params = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True
        }
        
        # Add username if provided
        if settings.redis_username:
            connection_params["username"] = settings.redis_username
        
        # Add password if provided
        if settings.redis_password:
            connection_params["password"] = settings.redis_password
        
        client = redis.Redis(**connection_params)
        
        # Test connection
        await client.ping()
        print("✅ Redis connection successful!")
        
        # Test write
        await client.set("test_key", "test_value")
        print("✅ Write operation successful!")
        
        # Test read
        value = await client.get("test_key")
        print(f"✅ Read operation successful! Value: {value}")
        
        # Test pub/sub
        pubsub = client.pubsub()
        await pubsub.subscribe("test_channel")
        print("✅ Pub/Sub subscription successful!")
        
        # Cleanup
        await client.delete("test_key")
        await pubsub.unsubscribe("test_channel")
        await pubsub.aclose()
        await client.aclose()
        
        print("\n🎉 All Redis operations working correctly!")
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Redis password in .env file")
        print("2. For Redis Cloud, you may need a username (usually 'default')")
        print("3. Get credentials from Redis Cloud dashboard:")
        print("   - Go to your database")
        print("   - Click 'Connect'")
        print("   - Copy the password shown")
        print("4. Verify your IP is whitelisted in Redis Cloud")

if __name__ == "__main__":
    asyncio.run(test_redis_connection())
