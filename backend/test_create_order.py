import requests
import json

# Test order creation
url = "http://localhost:8000/api/orders"
data = {
    "supplier_name": "Test Supplier",
    "pizza_name": "Margherita",
    "supplier_price": 10.00,
    "markup_percentage": 30
}

print("Testing order creation...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.ok:
        print("\n✅ Order created successfully!")
        result = response.json()
        print(f"Order ID: {result.get('id', 'N/A')}")
    else:
        print("\n❌ Failed to create order")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
