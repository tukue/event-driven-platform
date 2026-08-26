#!/usr/bin/env python3
"""
Diagnostic script for order creation issues
"""
import requests
import json
from redis_client import redis_client
import asyncio

async def test_redis():
    """Test Redis connection"""
    print("1️⃣  Testing Redis connection...")
    try:
        await redis_client.connect()
        await redis_client.client.ping()
        print("   ✅ Redis connection: OK")
        await redis_client.disconnect()
        return True
    except Exception as e:
        print(f"   ❌ Redis connection: FAILED - {e}")
        return False

def test_backend_health():
    """Test if backend is running"""
    print("\n2️⃣  Testing backend health...")
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("   ✅ Backend is running")
            return True
        else:
            print(f"   ❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to backend - is it running?")
        print("   💡 Run: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_order_creation():
    """Test order creation endpoint"""
    print("\n3️⃣  Testing order creation endpoint...")
    
    url = "http://localhost:8000/api/orders"
    data = {
        "supplier_name": "Test Supplier",
        "pizza_name": "Margherita",
        "supplier_price": 10.00,
        "markup_percentage": 30
    }
    
    print(f"   📤 POST {url}")
    print(f"   📦 Data: {json.dumps(data, indent=6)}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"\n   📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Order created successfully!")
            result = response.json()
            print(f"   📋 Order ID: {result.get('order', {}).get('id', 'N/A')}")
            print(f"   📋 Status: {result.get('order', {}).get('status', 'N/A')}")
            return True
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
        print("   💡 Backend might be slow or unresponsive")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_get_orders():
    """Test getting all orders"""
    print("\n4️⃣  Testing get orders endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/orders", timeout=5)
        print(f"   📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            orders = response.json()
            print(f"   ✅ Retrieved {len(orders)} orders")
            return True
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    print("=" * 60)
    print("🔍 Order Creation Diagnostic Tool")
    print("=" * 60)
    
    results = []
    
    # Test Redis
    results.append(await test_redis())
    
    # Test backend health
    results.append(test_backend_health())
    
    # Test order creation
    results.append(test_order_creation())
    
    # Test get orders
    results.append(test_get_orders())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! Order creation should work.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        print("\n💡 Troubleshooting tips:")
        if not results[0]:
            print("   - Check Redis credentials in .env file")
            print("   - Run: python test_redis.py")
        if not results[1]:
            print("   - Start backend: uvicorn main:app --reload")
        if not results[2]:
            print("   - Check backend logs for errors")
            print("   - Try creating order via Swagger UI: http://localhost:8000/docs")

if __name__ == "__main__":
    asyncio.run(main())
