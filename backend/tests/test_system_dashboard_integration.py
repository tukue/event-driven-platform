"""
Integration tests for System Dashboard (Phase 5).
Tests the /api/state endpoint and related functionality.
"""
import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_system_state_endpoint_structure(client):
    """Test that /api/state returns correct structure."""
    
    response = await client.get("/api/state")
    assert response.status_code == 200
    
    state = response.json()
    
    # Verify top-level structure
    assert "statistics" in state
    assert "orders_by_status" in state
    assert "active_drivers" in state
    assert "last_updated" in state


@pytest.mark.asyncio
async def test_system_statistics_fields(client):
    """Test that statistics contain all required fields."""
    
    response = await client.get("/api/state")
    assert response.status_code == 200
    
    stats = response.json()["statistics"]
    
    # Verify all statistic fields exist
    required_fields = [
        "total_orders",
        "active_deliveries",
        "completed_today",
        "pending_supplier",
        "preparing",
        "ready",
        "dispatched",
        "in_transit",
        "delivered"
    ]
    
    for field in required_fields:
        assert field in stats, f"Missing field: {field}"
        assert isinstance(stats[field], int), f"{field} should be an integer"
        assert stats[field] >= 0, f"{field} should be non-negative"


@pytest.mark.asyncio
async def test_orders_by_status_structure(client):
    """Test that orders_by_status is properly structured."""
    
    # Create a test order
    order_data = {
        "pizza_name": "Test Pizza",
        "supplier_name": "Test Supplier",
        "supplier_price": 12.99
    }
    create_response = await client.post("/api/orders", json=order_data)
    assert create_response.status_code == 200
    order_id = create_response.json()["order"]["id"]
    
    # Get system state
    response = await client.get("/api/state")
    assert response.status_code == 200
    
    orders_by_status = response.json()["orders_by_status"]
    
    # Should be a dictionary
    assert isinstance(orders_by_status, dict)
    
    # Find our order
    found = False
    for status, orders in orders_by_status.items():
        assert isinstance(orders, list)
        for order in orders:
            if order["id"] == order_id:
                found = True
                # Verify order structure
                assert "id" in order
                assert "pizza_name" in order
                assert "supplier_name" in order
                assert "status" in order
                break
        if found:
            break
    
    assert found, "Created order not found in orders_by_status"


@pytest.mark.asyncio
async def test_active_drivers_tracking(client):
    """Test that active drivers are tracked correctly."""
    
    # Create and dispatch an order
    order_data = {
        "pizza_name": "Driver Test Pizza",
        "supplier_name": "Test Supplier",
        "supplier_price": 13.99
    }
    response = await client.post("/api/orders", json=order_data)
    order_id = response.json()["order"]["id"]
    
    # Accept as supplier
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True, "notes": "Test", "estimated_time": 30}
    )
    
    # Accept as customer
    await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "Test Customer", "delivery_address": "Test Address"}
    )
    
    # Prepare
    await client.post(f"/api/orders/{order_id}/status?status=preparing")
    await client.post(f"/api/orders/{order_id}/status?status=ready")
    
    # Dispatch with driver
    await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Integration Test Driver"}
    )
    
    # Get system state
    response = await client.get("/api/state")
    assert response.status_code == 200
    
    active_drivers = response.json()["active_drivers"]
    
    # Find our driver
    driver = next((d for d in active_drivers if d["driver_name"] == "Integration Test Driver"), None)
    assert driver is not None, "Driver not found in active drivers"
    
    # Verify driver structure
    assert "driver_name" in driver
    assert "order_id" in driver
    assert "status" in driver
    assert driver["order_id"] == order_id
    assert driver["status"] == "dispatched"


@pytest.mark.asyncio
async def test_active_drivers_removed_after_delivery(client):
    """Test that drivers are removed from active list after delivery."""
    
    # Create and complete an order
    order_data = {
        "pizza_name": "Completion Test Pizza",
        "supplier_name": "Test Supplier",
        "supplier_price": 14.99
    }
    response = await client.post("/api/orders", json=order_data)
    order_id = response.json()["order"]["id"]
    
    # Progress through workflow
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True, "estimated_time": 30}
    )
    await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "Test", "delivery_address": "Test"}
    )
    await client.post(f"/api/orders/{order_id}/status?status=preparing")
    await client.post(f"/api/orders/{order_id}/status?status=ready")
    await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Completion Driver"}
    )
    
    # Verify driver is active
    response = await client.get("/api/state")
    active_drivers = response.json()["active_drivers"]
    assert any(d["driver_name"] == "Completion Driver" for d in active_drivers)
    
    # Mark as delivered
    await client.post(f"/api/orders/{order_id}/status?status=delivered")
    
    # Verify driver is no longer active
    response = await client.get("/api/state")
    active_drivers = response.json()["active_drivers"]
    assert not any(d["driver_name"] == "Completion Driver" for d in active_drivers)


@pytest.mark.asyncio
async def test_include_completed_parameter(client):
    """Test that include_completed parameter filters correctly."""
    
    # Create and complete an order
    order_data = {
        "pizza_name": "Completed Pizza",
        "supplier_name": "Test Supplier",
        "supplier_price": 15.99
    }
    response = await client.post("/api/orders", json=order_data)
    order_id = response.json()["order"]["id"]
    
    # Complete the order
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True, "estimated_time": 30}
    )
    await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "Test", "delivery_address": "Test"}
    )
    await client.post(f"/api/orders/{order_id}/status?status=preparing")
    await client.post(f"/api/orders/{order_id}/status?status=ready")
    await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Test Driver"}
    )
    await client.post(f"/api/orders/{order_id}/status?status=in_transit")
    await client.post(f"/api/orders/{order_id}/status?status=delivered")
    
    # Test with include_completed=true (default)
    response = await client.get("/api/state?include_completed=true")
    assert response.status_code == 200
    orders_with_completed = response.json()["orders_by_status"]
    
    # Should have delivered orders
    assert "delivered" in orders_with_completed
    assert any(o["id"] == order_id for o in orders_with_completed.get("delivered", []))
    
    # Test with include_completed=false
    response = await client.get("/api/state?include_completed=false")
    assert response.status_code == 200
    orders_without_completed = response.json()["orders_by_status"]
    
    # Should not have delivered orders
    delivered_orders = orders_without_completed.get("delivered", [])
    assert len(delivered_orders) == 0 or not any(o["id"] == order_id for o in delivered_orders)


@pytest.mark.asyncio
async def test_limit_parameter(client):
    """Test that limit parameter restricts order count per status."""
    
    # Create multiple orders in same status
    for i in range(5):
        order_data = {
            "pizza_name": f"Limit Test Pizza {i}",
            "supplier_name": "Test Supplier",
            "supplier_price": 10.99 + i
        }
        await client.post("/api/orders", json=order_data)
    
    # Test with limit=2
    response = await client.get("/api/state?limit=2")
    assert response.status_code == 200
    
    orders_by_status = response.json()["orders_by_status"]
    
    # Each status should have at most 2 orders
    for status, orders in orders_by_status.items():
        assert len(orders) <= 2, f"Status {status} has {len(orders)} orders, expected <= 2"


@pytest.mark.asyncio
async def test_statistics_update_on_order_creation(client):
    """Test that statistics update when orders are created."""
    
    # Get initial state
    response = await client.get("/api/state")
    initial_stats = response.json()["statistics"]
    initial_total = initial_stats["total_orders"]
    
    # Create a new order
    order_data = {
        "pizza_name": "Stats Test Pizza",
        "supplier_name": "Test Supplier",
        "supplier_price": 11.99
    }
    await client.post("/api/orders", json=order_data)
    
    # Get updated state
    response = await client.get("/api/state")
    updated_stats = response.json()["statistics"]
    updated_total = updated_stats["total_orders"]
    
    # Total should increase by 1
    assert updated_total == initial_total + 1


@pytest.mark.asyncio
async def test_active_deliveries_count(client):
    """Test that active_deliveries count is accurate."""
    
    # Get initial count
    response = await client.get("/api/state")
    initial_active = response.json()["statistics"]["active_deliveries"]
    
    # Create and dispatch an order
    order_data = {
        "pizza_name": "Active Delivery Test",
        "supplier_name": "Test Supplier",
        "supplier_price": 12.99
    }
    response = await client.post("/api/orders", json=order_data)
    order_id = response.json()["order"]["id"]
    
    # Progress to dispatched
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True, "estimated_time": 30}
    )
    await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "Test", "delivery_address": "Test"}
    )
    await client.post(f"/api/orders/{order_id}/status?status=preparing")
    await client.post(f"/api/orders/{order_id}/status?status=ready")
    await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Test Driver"}
    )
    
    # Check active deliveries increased
    response = await client.get("/api/state")
    current_active = response.json()["statistics"]["active_deliveries"]
    assert current_active == initial_active + 1
    
    # Mark as delivered
    await client.post(f"/api/orders/{order_id}/status?status=delivered")
    
    # Check active deliveries decreased
    response = await client.get("/api/state")
    final_active = response.json()["statistics"]["active_deliveries"]
    assert final_active == initial_active


@pytest.mark.asyncio
async def test_last_updated_timestamp(client):
    """Test that last_updated timestamp is valid."""
    
    response = await client.get("/api/state")
    assert response.status_code == 200
    
    state = response.json()
    last_updated = state["last_updated"]
    
    # Should be a valid ISO timestamp
    try:
        dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        assert dt is not None
    except ValueError:
        pytest.fail(f"Invalid timestamp format: {last_updated}")
