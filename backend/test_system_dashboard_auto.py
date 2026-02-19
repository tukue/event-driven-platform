"""
Automated integration test for System Dashboard (Phase 5).
Run this with: python test_system_dashboard_auto.py
"""
import requests
import sys
import time

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


def test_system_state_endpoint():
    """Test the /api/state endpoint structure and data."""
    
    print("\n=== SYSTEM DASHBOARD INTEGRATION TEST ===\n")
    
    try:
        # Step 1: Test basic endpoint access
        print_step(1, "Testing /api/state endpoint")
        response = requests.get(f"{BASE_URL}/api/state")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print_success("Endpoint accessible")
        
        state = response.json()
        
        # Step 2: Verify statistics structure
        print_step(2, "Verifying statistics structure")
        assert "statistics" in state, "Missing 'statistics' field"
        stats = state["statistics"]
        
        required_stats = [
            "total_orders", "active_deliveries", "completed_today",
            "pending_supplier", "preparing", "ready",
            "dispatched", "in_transit", "delivered"
        ]
        
        for stat in required_stats:
            assert stat in stats, f"Missing statistic: {stat}"
            assert isinstance(stats[stat], int), f"{stat} should be an integer"
        
        print_success(f"All statistics present: {len(required_stats)} fields")
        print_success(f"Total orders: {stats['total_orders']}")
        print_success(f"Active deliveries: {stats['active_deliveries']}")
        print_success(f"Completed today: {stats['completed_today']}")
        
        # Step 3: Verify orders_by_status structure
        print_step(3, "Verifying orders_by_status structure")
        assert "orders_by_status" in state, "Missing 'orders_by_status' field"
        orders_by_status = state["orders_by_status"]
        assert isinstance(orders_by_status, dict), "orders_by_status should be a dict"
        
        total_orders_in_lists = sum(len(orders) for orders in orders_by_status.values())
        print_success(f"Orders grouped by status: {len(orders_by_status)} statuses")
        print_success(f"Total orders in lists: {total_orders_in_lists}")
        
        # Verify order structure
        for status, orders in orders_by_status.items():
            if orders:
                order = orders[0]
                required_fields = ["id", "pizza_name", "supplier_name", "status"]
                for field in required_fields:
                    assert field in order, f"Order missing field: {field}"
                print_success(f"Status '{status}': {len(orders)} orders")
                break
        
        # Step 4: Verify active_drivers structure
        print_step(4, "Verifying active_drivers structure")
        assert "active_drivers" in state, "Missing 'active_drivers' field"
        active_drivers = state["active_drivers"]
        assert isinstance(active_drivers, list), "active_drivers should be a list"
        
        print_success(f"Active drivers: {len(active_drivers)}")
        
        if active_drivers:
            driver = active_drivers[0]
            required_fields = ["driver_name", "status"]
            for field in required_fields:
                assert field in driver, f"Driver missing field: {field}"
            print_success(f"Driver structure valid: {driver['driver_name']}")
        
        # Step 5: Verify last_updated
        print_step(5, "Verifying last_updated timestamp")
        assert "last_updated" in state, "Missing 'last_updated' field"
        print_success(f"Last updated: {state['last_updated']}")
        
        # Step 6: Test with query parameters
        print_step(6, "Testing query parameters")
        
        # Test include_completed=false
        response = requests.get(f"{BASE_URL}/api/state?include_completed=false")
        assert response.status_code == 200
        state_no_completed = response.json()
        
        # Should not have delivered or cancelled orders
        orders_by_status = state_no_completed["orders_by_status"]
        assert "delivered" not in orders_by_status or len(orders_by_status["delivered"]) == 0
        assert "cancelled" not in orders_by_status or len(orders_by_status["cancelled"]) == 0
        print_success("include_completed=false works correctly")
        
        # Test limit parameter
        response = requests.get(f"{BASE_URL}/api/state?limit=2")
        assert response.status_code == 200
        state_limited = response.json()
        
        # Each status should have max 2 orders
        for status, orders in state_limited["orders_by_status"].items():
            assert len(orders) <= 2, f"Status {status} has more than 2 orders"
        print_success("limit parameter works correctly")
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        
        return True
        
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend at http://localhost:8000")
        print("  Make sure the backend is running: python backend/main.py")
        return False
    except AssertionError as e:
        print_error(f"Test failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_real_time_updates():
    """Test that creating orders updates the dashboard."""
    
    print("\n=== REAL-TIME UPDATES TEST ===\n")
    
    try:
        # Get initial state
        print_step(1, "Getting initial state")
        response = requests.get(f"{BASE_URL}/api/state")
        initial_state = response.json()
        initial_total = initial_state["statistics"]["total_orders"]
        print_success(f"Initial total orders: {initial_total}")
        
        # Create a new order
        print_step(2, "Creating new order")
        order_data = {
            "pizza_name": "Dashboard Test Pizza",
            "supplier_name": "Test Supplier",
            "supplier_price": 12.99
        }
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data)
        assert response.status_code == 200
        order_id = response.json()["order"]["id"]
        print_success(f"Order created: {order_id[:8]}")
        
        # Wait a moment for cache to expire (5 seconds)
        print_step(3, "Waiting for cache to expire...")
        time.sleep(6)
        
        # Get updated state
        print_step(4, "Getting updated state")
        response = requests.get(f"{BASE_URL}/api/state")
        updated_state = response.json()
        updated_total = updated_state["statistics"]["total_orders"]
        
        assert updated_total == initial_total + 1, \
            f"Expected {initial_total + 1} orders, got {updated_total}"
        print_success(f"Updated total orders: {updated_total}")
        print_success("Dashboard reflects new order!")
        
        # Verify order appears in orders_by_status
        print_step(5, "Verifying order in orders_by_status")
        orders_by_status = updated_state["orders_by_status"]
        
        found = False
        for status, orders in orders_by_status.items():
            if any(o["id"] == order_id for o in orders):
                found = True
                print_success(f"Order found in status: {status}")
                break
        
        assert found, "Order not found in orders_by_status"
        
        print("\n" + "="*60)
        print("✓ REAL-TIME UPDATE TEST PASSED!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_active_drivers_tracking():
    """Test active drivers tracking."""
    
    print("\n=== ACTIVE DRIVERS TRACKING TEST ===\n")
    
    try:
        # Create and dispatch an order
        print_step(1, "Creating and dispatching order")
        
        # Create order
        order_data = {
            "pizza_name": "Driver Test Pizza",
            "supplier_name": "Test Supplier",
            "supplier_price": 13.99
        }
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data)
        order_id = response.json()["order"]["id"]
        print_success(f"Order created: {order_id[:8]}")
        
        # Accept as supplier
        requests.post(
            f"{BASE_URL}/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "notes": "Test", "estimated_time": 30}
        )
        
        # Accept as customer
        requests.post(
            f"{BASE_URL}/api/orders/{order_id}/customer-accept",
            params={"customer_name": "Test Customer", "delivery_address": "Test Address"}
        )
        
        # Prepare
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=preparing")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=ready")
        
        # Dispatch
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/dispatch",
            params={"driver_name": "Test Driver"}
        )
        assert response.status_code == 200
        print_success("Order dispatched with Test Driver")
        
        # Wait for cache
        time.sleep(6)
        
        # Check active drivers
        print_step(2, "Checking active drivers")
        response = requests.get(f"{BASE_URL}/api/state")
        state = response.json()
        active_drivers = state["active_drivers"]
        
        # Find our driver
        driver_found = any(d["driver_name"] == "Test Driver" for d in active_drivers)
        assert driver_found, "Test Driver not found in active drivers"
        print_success("Test Driver appears in active drivers list")
        
        # Verify driver has correct order
        test_driver = next(d for d in active_drivers if d["driver_name"] == "Test Driver")
        assert test_driver["order_id"] == order_id
        assert test_driver["status"] == "dispatched"
        print_success(f"Driver assigned to correct order: {order_id[:8]}")
        print_success(f"Driver status: {test_driver['status']}")
        
        # Update to in_transit
        print_step(3, "Updating to in_transit")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=in_transit")
        time.sleep(6)
        
        response = requests.get(f"{BASE_URL}/api/state")
        state = response.json()
        active_drivers = state["active_drivers"]
        
        test_driver = next(d for d in active_drivers if d["driver_name"] == "Test Driver")
        assert test_driver["status"] == "in_transit"
        print_success("Driver status updated to in_transit")
        
        # Mark as delivered
        print_step(4, "Marking as delivered")
        requests.post(f"{BASE_URL}/api/orders/{order_id}/status?status=delivered")
        time.sleep(6)
        
        response = requests.get(f"{BASE_URL}/api/state")
        state = response.json()
        active_drivers = state["active_drivers"]
        
        # Driver should no longer be in active list
        driver_still_active = any(d["driver_name"] == "Test Driver" for d in active_drivers)
        assert not driver_still_active, "Driver should not be active after delivery"
        print_success("Driver removed from active list after delivery")
        
        print("\n" + "="*60)
        print("✓ ACTIVE DRIVERS TEST PASSED!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" "*15 + "SYSTEM DASHBOARD TEST SUITE")
    print("="*70)
    print("\nMake sure the backend is running: python backend/main.py")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        sys.exit(0)
    
    results = []
    
    # Run all tests
    results.append(("System State Endpoint", test_system_state_endpoint()))
    results.append(("Real-Time Updates", test_real_time_updates()))
    results.append(("Active Drivers Tracking", test_active_drivers_tracking()))
    
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
        print("\n🎉 All tests passed! The System Dashboard is working correctly.")
        print("\nNext steps:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Navigate to the Dashboard tab")
        print("3. Watch real-time updates as you create/update orders")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    sys.exit(0 if passed == total else 1)
