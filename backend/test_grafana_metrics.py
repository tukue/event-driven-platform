"""
Test script to verify Grafana metrics endpoints
"""
import asyncio
import httpx

async def test_metrics_endpoints():
    """Test both Prometheus and JSON metrics endpoints"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Grafana Metrics Endpoints")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test Prometheus endpoint
        print("\n1️⃣  Testing Prometheus endpoint (/metrics)...")
        try:
            response = await client.get(f"{base_url}/metrics")
            if response.status_code == 200:
                print("   ✅ Prometheus endpoint is working")
                lines = response.text.split('\n')
                print(f"   📊 Response contains {len(lines)} lines")
                
                # Show sample metrics
                print("\n   Sample metrics:")
                for line in lines[:15]:
                    if line and not line.startswith('#'):
                        print(f"      {line}")
            else:
                print(f"   ❌ Failed with status code: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            print("   💡 Make sure the backend server is running:")
            print("      cd backend && uvicorn main:app --reload")
            return
        
        # Test JSON endpoint
        print("\n2️⃣  Testing JSON API endpoint (/api/metrics)...")
        try:
            response = await client.get(f"{base_url}/api/metrics")
            if response.status_code == 200:
                print("   ✅ JSON API endpoint is working")
                data = response.json()
                
                print("\n   📊 Metrics Summary:")
                if 'summary' in data:
                    summary = data['summary']
                    print(f"      Total Orders: {summary.get('total_orders', 0)}")
                    print(f"      Delivered: {summary.get('total_delivered', 0)}")
                    print(f"      In Transit: {summary.get('in_transit', 0)}")
                    print(f"      Delivery Rate: {summary.get('delivery_rate', 0)}%")
                
                if 'time_series' in data:
                    ts = data['time_series']
                    print(f"\n   📈 Time Series:")
                    print(f"      Today: {ts.get('today', 0)}")
                    print(f"      Last 7 Days: {ts.get('last_7_days', 0)}")
                    print(f"      Last 30 Days: {ts.get('last_30_days', 0)}")
                
                if 'by_supplier' in data:
                    print(f"\n   🏪 Top Suppliers:")
                    suppliers = sorted(data['by_supplier'].items(), 
                                     key=lambda x: x[1], reverse=True)[:3]
                    for supplier, count in suppliers:
                        print(f"      {supplier}: {count} deliveries")
                
                if 'by_driver' in data:
                    print(f"\n   🚗 Top Drivers:")
                    drivers = sorted(data['by_driver'].items(), 
                                   key=lambda x: x[1], reverse=True)[:3]
                    for driver, count in drivers:
                        print(f"      {driver}: {count} deliveries")
            else:
                print(f"   ❌ Failed with status code: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ Metrics endpoints test complete!")
    print("\n📋 Next steps:")
    print("   1. If no data, run: python generate_test_data.py")
    print("   2. Configure Grafana datasource")
    print("   3. Import dashboard from grafana/dashboard-orders-delivered.json")
    print("   4. View your metrics in Grafana!")

if __name__ == "__main__":
    asyncio.run(test_metrics_endpoints())
