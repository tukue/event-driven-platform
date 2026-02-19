"""
Automated integration test for Delivery Tracker with WebSocket updates.
Run this with: python test_delivery_tracker_auto.py
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_complete_delivery_flow():
    """Test complete delivery flow from creation to delivery."""
    
    print("\n=== DELIVERY TRACKER INTEGRATION TEST ===\n")
    
    try:
        # Step 1: Create order
        print("1. Creating order...")
        response = requests.post(f"{BASE_URL}/api/orders", json={
            "pizza_name": "Margherita Test",
            "supplier_name": "Test Pizza Palace",
            "supplier_price": 12.99
        })
        assert response.status_code == 200
        order_id = response.json()["order"]["id"]
        print(f"   ✓ Order created: {order_id[:8]}")
        
        # Step 2: Test before dispatch (should fail)
        print("\n2. Testing delivery tracker before dispatch...")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 400
        print("   ✓ Correctly returned error for non-dispatched order")
        
        # Step 3: Supplier accept
        print("\n3. Supplier accepting order...")
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "notes": "Test notes", "estimated_time": 30}
        )
        assert response.status_code == 200
        print("   ✓ Supplier accepted")
        
        # Step 4: Customer accept
        print("\n4. Customer accepting order...")
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/customer-accept",
            params={"customer_name": "Test Customer", "delivery_address": "123 Test St"}
        )
        assert response.status_code == 200
        print("   ✓ Customer accepted")
        
        # Step 5-6: Prepare
        print("\n5. Preparing order...")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=preparing")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=ready")
        print("   ✓ Order ready")
        
        # Step 7: Dispatch
        print("\n6. Dispatching order...")
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/dispatch",
            params={"driver_name": "Test Driver"}
        )
        assert response.status_code == 200
        print("   ✓ Order dispatched")
        
        # Step 8: Get delivery info - Dispatched
        print("\n7. Getting delivery info (dispatched)...")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 200
        info = response.json()
        assert info["status"] == "dispatched"
        assert info["progress_percentage"] == 33
        print(f"   ✓ Progress: {info['progress_percentage']}%")
        print(f"   ✓ Driver: {info['driver_name']}")
        
        # Step 9: In transit
        print("\n8. Updating to in_transit...")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=in_transit")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        info = response.json()
        assert info["status"] == "in_transit"
        assert info["progress_percentage"] == 66
        print(f"   ✓ Progress: {info['progress_percentage']}%")
        
        # Step 10: Delivered
        print("\n9. Marking as delivered...")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=delivered")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        info = response.json()
        assert info["status"] == "delivered"
        assert info["progress_percentage"] == 100
        print(f"   ✓ Progress: {info['progress_percentage']}%")
        
        # Verify timeline
        print("\n10. Verifying timeline...")
        timeline = info["timeline"]
        assert len(timeline) > 0
        assert any(t["stage"] == "dispatched" and t["completed"] for t in timeline)
        assert any(t["stage"] == "in_transit" and t["completed"] for t in timeline)
        assert any(t["stage"] == "delivered" and t["completed"] for t in timeline)
        print("   ✓ All timeline events recorded")
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        print(f"\nTest Order ID: {order_id}")
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to backend at http://localhost:8000")
        print("  Make sure the backend is running: python backend/main.py")
        return False
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_complete_delivery_flow()
    sys.exit(0 if success else 1)
