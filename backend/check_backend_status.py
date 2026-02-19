#!/usr/bin/env python3
"""
Quick check of backend status
"""
import asyncio
from redis_client import redis_client

async def main():
    print("Checking backend components...")
    print()
    
    # Test Redis
    print("1. Testing Redis connection...")
    try:
        await redis_client.connect()
        await redis_client.client.ping()
        print("   ✅ Redis: Connected")
        
        # Test publish
        print("\n2. Testing Redis publish...")
        await redis_client.publish("test_channel", "test_message")
        print("   ✅ Redis publish: Working")
        
        await redis_client.disconnect()
    except Exception as e:
        print(f"   ❌ Redis error: {e}")
        return
    
    print("\n✅ All checks passed!")
    print("\nIf backend is still hanging, the issue might be:")
    print("1. Backend not fully started - wait a few more seconds")
    print("2. Another process using port 8000")
    print("3. Firewall blocking connections")
    
    print("\nTo restart backend:")
    print("1. Press CTRL+C in the terminal running uvicorn")
    print("2. Run: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(main())
