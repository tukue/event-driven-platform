import requests
import time

print("Waiting for backend to start...")
time.sleep(3)

print("\n1. Testing /docs endpoint...")
try:
    r = requests.get("http://localhost:8000/docs", timeout=2)
    print(f"   Status: {r.status_code}")
except Exception as e:
    print(f"   Error: {e}")

print("\n2. Testing /api/orders GET...")
try:
    r = requests.get("http://localhost:8000/api/orders", timeout=5)
    print(f"   Status: {r.status_code}")
    print(f"   Orders: {len(r.json())}")
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Testing /api/orders POST...")
try:
    data = {
        "supplier_name": "Quick Test",
        "pizza_name": "Test Pizza",
        "supplier_price": 5.0,
        "markup_percentage": 30
    }
    r = requests.post("http://localhost:8000/api/orders", json=data, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.ok:
        print(f"   ✅ Success!")
    else:
        print(f"   Response: {r.text}")
except Exception as e:
    print(f"   Error: {e}")
