"""
Complete verification script for Grafana setup
Checks all components and provides actionable feedback
"""
import asyncio
import httpx
from redis_client import redis_client

async def check_redis_connection():
    """Check if Redis is accessible"""
    print("1️⃣  Checking Redis connection...")
    try:
        await redis_client.connect()
        await redis_client.client.ping()
        print("   ✅ Redis connection successful")
        await redis_client.disconnect()
        return True
    except Exception as e:
        print(f"   ❌ Redis connection failed: {str(e)}")
        print("   💡 Check your .env file and Redis credentials")
        return False

async def check_backend_server():
    """Check if backend server is running"""
    print("\n2️⃣  Checking backend server...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs", timeout=5.0)
            if response.status_code == 200:
                print("   ✅ Backend server is running")
                return True
            else:
                print(f"   ❌ Backend returned status code: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Cannot connect to backend server")
        print("   💡 Start the server: uvicorn main:app --reload")
        return False

async def check_test_data():
    """Check if test data exists"""
    print("\n3️⃣  Checking for test data...")
    try:
        await redis_client.connect()
        keys = await redis_client.client.keys("order:*")
        count = len(keys)
        
        if count == 0:
            print("   ⚠️  No orders found in database")
            print("   💡 Generate test data: python generate_test_data.py")
            await redis_client.disconnect()
            return False
        else:
            print(f"   ✅ Found {count} orders in database")
            
            # Check for delivered orders
            delivered_count = 0
            for key in keys:
                order_data = await redis_client.client.get(key)
                if order_data and b'"status":"delivered"' in order_data:
                    delivered_count += 1
            
            print(f"   📦 Delivered orders: {delivered_count}")
            
            if delivered_count == 0:
                print("   ⚠️  No delivered orders found")
                print("   💡 Dashboard will show limited data")
            
            await redis_client.disconnect()
            return True
            
    except Exception as e:
        print(f"   ❌ Error checking data: {str(e)}")
        return False

async def check_prometheus_endpoint():
    """Check Prometheus metrics endpoint"""
    print("\n4️⃣  Checking Prometheus endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/metrics", timeout=5.0)
            if response.status_code == 200:
                print("   ✅ Prometheus endpoint working")
                
                # Parse some metrics
                lines = response.text.split('\n')
                metrics = {}
                for line in lines:
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            metrics[parts[0]] = parts[1]
                
                if 'orders_total' in metrics:
                    print(f"   📊 Total orders: {metrics['orders_total']}")
                if 'orders_delivered' in metrics:
                    print(f"   📊 Delivered: {metrics['orders_delivered']}")
                
                return True
            else:
                print(f"   ❌ Endpoint returned status: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

async def check_json_endpoint():
    """Check JSON API endpoint"""
    print("\n5️⃣  Checking JSON API endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/metrics", timeout=5.0)
            if response.status_code == 200:
                print("   ✅ JSON API endpoint working")
                data = response.json()
                
                if 'summary' in data:
                    summary = data['summary']
                    print(f"   📊 Delivery rate: {summary.get('delivery_rate', 0)}%")
                
                return True
            else:
                print(f"   ❌ Endpoint returned status: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

async def check_grafana_connection():
    """Check if Grafana is accessible"""
    print("\n6️⃣  Checking Grafana (optional)...")
    
    # Try common Grafana ports
    grafana_urls = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    
    for url in grafana_urls:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=3.0, follow_redirects=True)
                if response.status_code in [200, 302]:
                    print(f"   ✅ Grafana found at {url}")
                    return True
        except:
            continue
    
    print("   ⚠️  Grafana not detected on common ports")
    print("   💡 This is optional - install Grafana to visualize metrics")
    print("   💡 Docker: docker run -d -p 3000:3000 grafana/grafana")
    return None  # None means optional check

async def main():
    """Run all verification checks"""
    print("🔍 Grafana Setup Verification")
    print("=" * 60)
    
    results = []
    
    # Run all checks
    results.append(("Redis", await check_redis_connection()))
    results.append(("Backend", await check_backend_server()))
    results.append(("Test Data", await check_test_data()))
    results.append(("Prometheus", await check_prometheus_endpoint()))
    results.append(("JSON API", await check_json_endpoint()))
    results.append(("Grafana", await check_grafana_connection()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 60)
    
    required_checks = [r for r in results if r[1] is not None]
    passed = sum(1 for r in required_checks if r[1])
    total = len(required_checks)
    
    for name, status in results:
        if status is True:
            print(f"✅ {name}: PASS")
        elif status is False:
            print(f"❌ {name}: FAIL")
        else:
            print(f"⚠️  {name}: OPTIONAL")
    
    print("=" * 60)
    print(f"\n🎯 Score: {passed}/{total} required checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! You're ready to use Grafana!")
        print("\n📋 Next steps:")
        print("   1. Open Grafana (http://localhost:3000)")
        print("   2. Add Prometheus datasource:")
        print("      URL: http://localhost:8000/metrics")
        print("   3. Import dashboard:")
        print("      File: grafana/dashboard-orders-delivered.json")
        print("   4. View your metrics!")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\n📋 Quick fixes:")
        if not results[0][1]:  # Redis
            print("   • Check .env file and Redis credentials")
        if not results[1][1]:  # Backend
            print("   • Start backend: uvicorn main:app --reload")
        if not results[2][1]:  # Test data
            print("   • Generate data: python generate_test_data.py")

if __name__ == "__main__":
    asyncio.run(main())
