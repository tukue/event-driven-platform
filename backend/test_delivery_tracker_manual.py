"""
Simple manual integration test for Delivery Tracker with WebSocket updates.
Run this with: python test_delivery_tracker_manual.py
"""
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_step(step_num, description):
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print('='*60)

def print_success(message):
    """Print a success message."""
    print(f"✓ {message}")

def print_error(message):
    """Print an error message."""
    print(f"✗ {message}")

def test_complete_delivery_flow():
    """Test complete delivery flow from creation to delivery."""
    
    print("\n" + "="*60)
    print("DELIVERY TRACKER INTEGRATION TEST")
    print("="*60)
    
    try:
        # Step 1: Create an order
        print_step(1, "Create Order")
        response = requests.post(f"{BASE_URL}/api/orders", json={
            "pizza_name": "Margherita Test",
            "supplier_name": "Test Pizza Palace",
            "supplier_price": 12.99
        })
        assert response.status_code == 200, f"Failed to create order: {response.status_code}"
        event = response.json()
        order_id = event["order"]["id"]
        print_success(f"Order created: {order_id[:8]}")
        
        # Step 2: Try to get delivery info (should fail - not dispatched yet)
        print_step(2, "Test Delivery Tracker Before Dispatch (Should Fail)")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 400, "Should return 400 for non-dispatched order"
        print_success("Correctly returned error for non-dispatched order")
        
        # Step 3: Accept order as customer
        print_step(3, "Customer Accepts Order")
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/customer-accept",
            params={
                "customer_name": "Test Customer",
                "delivery_address": "123 Test Street"
            }
        )
        assert response.status_code == 200, f"Failed to accept order: {response.status_code} - {response.text}"
        print_success("Order accepted by customer")
        
        # Step 4: Update to preparing
        print_step(4, "Start Preparing")
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=preparing")
        assert response.status_code == 200, "Failed to update to preparing"
        print_success("Order status: preparing")
        
        # Step 5: Update to ready
        print_step(5, "Mark Ready")
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=ready")
        assert response.status_code == 200, "Failed to update to ready"
        print_success("Order status: ready")
        
        # Step 6: Dispatch order
        print_step(6, "Dispatch Order")
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/dispatch",
            params={"driver_name": "Test Driver"}
        )
        assert response.status_code == 200, f"Failed to dispatch order: {response.status_code} - {response.text}"
        print_success("Order dispatched with driver: Test Driver")
        
        # Step 7: Get delivery info (should work now)
        print_step(7, "Get Delivery Info - Dispatched State")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 200, "Failed to get delivery info"
        delivery_info = response.json()
        
        # Verify delivery info structure
        assert delivery_info["order_id"] == order_id
        assert delivery_info["current_status"] == "dispatched"
        assert delivery_info["driver_name"] == "Test Driver"
        assert delivery_info["progress_percentage"] == 33
        assert "estimated_arrival" in delivery_info
        assert delivery_info["timeline"]["dispatched_at"] is not None
        
        print_success(f"Progress: {delivery_info['progress_percentage']}%")
        print_success(f"Driver: {delivery_info['driver_name']}")
        print_success(f"ETA: {delivery_info['estimated_arrival']}")
        
        # Step 8: Update to in_transit
        print_step(8, "Update to In Transit")
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=in_transit")
        assert response.status_code == 200, "Failed to update to in_transit"
        print_success("Order status: in_transit")
        
        # Step 9: Get updated delivery info
        print_step(9, "Get Delivery Info - In Transit State")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 200, "Failed to get delivery info"
        delivery_info = response.json()
        
        assert delivery_info["current_status"] == "in_transit"
        assert delivery_info["progress_percentage"] == 66
        assert delivery_info["timeline"]["in_transit_at"] is not None
        
        print_success(f"Progress: {delivery_info['progress_percentage']}%")
        print_success(f"In transit since: {delivery_info['timeline']['in_transit_at']}")
        
        # Step 10: Update to delivered
        print_step(10, "Mark as Delivered")
        response = requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=delivered")
        assert response.status_code == 200, "Failed to update to delivered"
        print_success("Order status: delivered")
        
        # Step 11: Get final delivery info
        print_step(11, "Get Delivery Info - Delivered State")
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 200, "Failed to get delivery info"
        delivery_info = response.json()
        
        assert delivery_info["current_status"] == "delivered"
        assert delivery_info["progress_percentage"] == 100
        assert delivery_info["timeline"]["delivered_at"] is not None
        
        print_success(f"Progress: {delivery_info['progress_percentage']}%")
        print_success(f"Delivered at: {delivery_info['timeline']['delivered_at']}")
        
        # Step 12: Verify timeline completeness
        print_step(12, "Verify Complete Timeline")
        timeline = delivery_info["timeline"]
        assert timeline["dispatched_at"] is not None
        assert timeline["in_transit_at"] is not None
        assert timeline["delivered_at"] is not None
        print_success("All timeline events recorded")
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print(f"\nTest Order ID: {order_id}")
        print("You can now test the frontend by clicking 'Track Delivery' button")
        
        return True
        
    except AssertionError as e:
        print_error(f"Test failed: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Make sure it's running on http://localhost:8000")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_invalid_order():
    """Test delivery tracker with invalid order ID."""
    print("\n" + "="*60)
    print("TEST: Invalid Order ID")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/orders/invalid-id-12345/delivery")
        assert response.status_code == 404, "Should return 404 for invalid order"
        print_success("Correctly returned 404 for invalid order")
        return True
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_multiple_orders():
    """Test tracking multiple orders simultaneously."""
    print("\n" + "="*60)
    print("TEST: Multiple Orders Tracking")
    print("="*60)
    
    try:
        order_ids = []
        
        # Create 3 orders
        for i in range(3):
            response = requests.post(f"{BASE_URL}/api/orders", json={
                "pizza_name": f"Test Pizza {i+1}",
                "supplier_name": f"Test Supplier {i+1}",
                "supplier_price": 10.99 + i
            })
            assert response.status_code == 200
            order_id = response.json()["order"]["id"]
            order_ids.append(order_id)
            
            # Accept and dispatch
            requests.post(
                f"{BASE_URL}/api/orders/{order_id}/customer-accept",
                params={
                    "customer_name": f"Customer {i+1}",
                    "delivery_address": f"{i+1} Street"
                }
            )
            requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=preparing")
            requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=ready")
            requests.post(
                f"{BASE_URL}/api/orders/{order_id}/dispatch",
                params={"driver_name": f"Driver {i+1}"}
            )
            
            print_success(f"Order {i+1} created and dispatched: {order_id[:8]}")
        
        # Verify all can be tracked
        for i, order_id in enumerate(order_ids):
            response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
            assert response.status_code == 200
            delivery_info = response.json()
            assert delivery_info["driver_name"] == f"Driver {i+1}"
            print_success(f"Order {i+1} tracking verified")
        
        print_success("All orders can be tracked simultaneously")
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_state_endpoint_integration():
    """Test that delivery tracker works with state endpoint."""
    print("\n" + "="*60)
    print("TEST: State Endpoint Integration")
    print("="*60)
    
    try:
        # Create and dispatch an order
        response = requests.post(f"{BASE_URL}/api/orders", json={
            "pizza_name": "State Test Pizza",
            "supplier_name": "State Test Supplier",
            "supplier_price": 13.99
        })
        order_id = response.json()["order"]["id"]
        
        requests.post(
            f"{BASE_URL}/api/orders/{order_id}/customer-accept",
            params={
                "customer_name": "State Test Customer",
                "delivery_address": "State Test Address"
            }
        )
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=preparing")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=ready")
        requests.post(
            f"{BASE_URL}/api/orders/{order_id}/dispatch",
            params={"driver_name": "State Test Driver"}
        )
        
        print_success(f"Test order created: {order_id[:8]}")
        
        # Get system state
        response = requests.get(f"{BASE_URL}/api/state")
        assert response.status_code == 200
        state = response.json()
        
        # Verify order appears in state (check all orders in orders_by_status)
        all_orders = []
        for status_orders in state["orders_by_status"].values():
            all_orders.extend(status_orders)
        
        assert any(o["id"] == order_id for o in all_orders), "Order not found in system state"
        print_success("Order appears in system state")
        
        # Verify delivery info is accessible
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/delivery")
        assert response.status_code == 200
        print_success("Delivery info accessible via delivery endpoint")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" "*15 + "DELIVERY TRACKER TEST SUITE")
    print("="*70)
    print("\nMake sure the backend is running: python backend/main.py")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        exit(0)
    
    results = []
    
    # Run all tests
    results.append(("Complete Delivery Flow", test_complete_delivery_flow()))
    results.append(("Invalid Order ID", test_invalid_order()))
    results.append(("Multiple Orders", test_multiple_orders()))
    results.append(("State Endpoint Integration", test_state_endpoint_integration()))
    
    # Print summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {test_name}")
    
    print("="*70)
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The delivery tracker is working correctly.")
        print("\nNext steps:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Create an order and dispatch it")
        print("3. Click the '🚚 Track Delivery' button")
        print("4. Watch real-time updates as you change order status")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    exit(0 if passed == total else 1)
