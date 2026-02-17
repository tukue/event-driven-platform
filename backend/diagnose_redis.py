import asyncio
import redis.asyncio as redis
from config import settings

async def test_connection_methods():
    """Test different Redis authentication methods"""
    
    print("=" * 60)
    print("Redis Connection Diagnostics")
    print("=" * 60)
    print(f"Host: {settings.redis_host}")
    print(f"Port: {settings.redis_port}")
    print(f"DB: {settings.redis_db}")
    print()
    
    # Method 1: Username + Password
    print("Method 1: Testing with username + password...")
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            username=settings.redis_username,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        await client.ping()
        print("✅ SUCCESS with username + password!")
        await client.close()
        return
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Method 2: Password only (no username)
    print("\nMethod 2: Testing with password only (no username)...")
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        await client.ping()
        print("✅ SUCCESS with password only!")
        print("\n⚠️  Update your .env file: Remove or comment out REDIS_USERNAME")
        await client.close()
        return
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Method 3: No authentication
    print("\nMethod 3: Testing without authentication...")
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        await client.ping()
        print("✅ SUCCESS without authentication!")
        print("\n⚠️  Update your .env file: Remove REDIS_USERNAME and REDIS_PASSWORD")
        await client.close()
        return
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("All methods failed. Please check:")
    print("=" * 60)
    print("1. Password is correct (copy from Redis Cloud dashboard)")
    print("2. Your IP address is whitelisted in Redis Cloud:")
    print("   - Go to Redis Cloud dashboard")
    print("   - Select your database")
    print("   - Go to 'Security' tab")
    print("   - Add your public IP address")
    print("3. Database is active and running")
    print("4. Port 13869 is not blocked by firewall")
    print()
    print("To find your public IP: https://whatismyipaddress.com/")

if __name__ == "__main__":
    asyncio.run(test_connection_methods())
