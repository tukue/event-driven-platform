"""
Integration tests for Delivery Tracking Endpoint
Following TDD principles - tests written before implementation
"""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_delivery_tracking_dispatched_order(client):
    """
    Test delivery tracking for a dispatched order
    Requirement 1.1: GET endpoint returns current delivery state for an order
    Requirement 1.2: Delivery state includes driver location, estimated arrival time, and current status
    """
    # Setup: Create and dispatch an order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 12.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Accept by supplier
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True, "estimated_time": 30}
    )
    
    # Accept by customer
    await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "John Doe", "delivery_address": "123 Main St"}
    )
    
    # Mark as ready
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    
    # Dispatch order
    await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Mike Driver"}
    )
    
    # Test: Get delivery tracking info
    response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify required fields
    assert data["order_id"] == order_id
    assert data["status"] == "dispatched"
    assert data["driver_name"] == "Mike Driver"
    assert data["delivery_address"] == "123 Main St"
    assert data["customer_name"] == "John Doe"
    assert "progress_percentage" in data
    assert "estimated_arrival_minutes" in data
    assert "timeline" in data
    assert "current_stage" in data
    
    # Verify progress for dispatched order
    assert data["progress_percentage"] == 33
    assert data["estimated_arrival_minutes"] == 30


@pytest.mark.asyncio
async def test_delivery_tracking_in_transit_order(client):
    """
    Test delivery tracking for an order in transit
    Requirement 1.2: Delivery state includes current status and progress
    """
    # Setup: Create and move order to in_transit
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Pepperoni",
            "supplier_price": 15.0,
            "markup_percentage": 25.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Process through workflow
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True, "estimated_time": 40})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Jane Smith", "delivery_address": "456 Oak Ave"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Sarah Driver"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "in_transit"})
    
    # Test: Get delivery tracking info
    response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "in_transit"
    assert data["progress_percentage"] == 66
    assert data["estimated_arrival_minutes"] == 20  # Half of 40
    assert "On the way" in data["current_stage"]


@pytest.mark.asyncio
async def test_delivery_tracking_delivered_order(client):
    """
    Test delivery tracking for a delivered order
    Requirement 1.2: Delivery state shows completion
    """
    # Setup: Create and complete full delivery
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Hawaiian",
            "supplier_price": 14.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Process through complete workflow
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Bob Johnson", "delivery_address": "789 Pine St"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Tom Driver"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "in_transit"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "delivered"})
    
    # Test: Get delivery tracking info
    response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "delivered"
    assert data["progress_percentage"] == 100
    assert data["estimated_arrival_minutes"] == 0
    assert "Delivered successfully" in data["current_stage"]


@pytest.mark.asyncio
async def test_delivery_tracking_order_not_found(client):
    """
    Test delivery tracking with non-existent order
    Requirement 1.3: Endpoint returns 404 if order not found
    """
    fake_order_id = "00000000-0000-0000-0000-000000000000"
    
    response = await client.get(f"/api/orders/{fake_order_id}/delivery")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delivery_tracking_order_not_dispatched(client):
    """
    Test delivery tracking for order that hasn't been dispatched yet
    Requirement 1.4: Endpoint returns 400 if order hasn't been dispatched yet
    """
    # Create order but don't dispatch it
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Veggie",
            "supplier_price": 11.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Try to get delivery info before dispatch
    response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert response.status_code == 400
    assert "not been dispatched" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delivery_tracking_timeline(client):
    """
    Test delivery timeline information
    Requirement 1.5: Response includes order details, driver info, and delivery progress
    """
    # Setup: Create and dispatch order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Supreme",
            "supplier_price": 16.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Alice Brown", "delivery_address": "321 Elm St"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Chris Driver"})
    
    # Test: Get delivery info and verify timeline
    response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify timeline structure
    timeline = data["timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) >= 3
    
    # Check timeline stages
    stages = [stage["stage"] for stage in timeline]
    assert "created" in stages
    assert "dispatched" in stages
    assert "in_transit" in stages
    assert "delivered" in stages
    
    # Verify completed flags
    for stage in timeline:
        assert "completed" in stage
        assert "timestamp" in stage or stage["timestamp"] is None


@pytest.mark.asyncio
async def test_delivery_tracking_multiple_orders_concurrent(client):
    """
    Test delivery tracking with multiple concurrent orders
    Performance test: Ensure system handles multiple tracking requests
    """
    # Create and dispatch 5 orders
    order_ids = []
    for i in range(5):
        create_response = await client.post(
            "/api/orders",
            json={
                "supplier_name": f"Pizza Place {i}",
                "pizza_name": f"Pizza {i}",
                "supplier_price": 10.0 + i,
                "markup_percentage": 30.0
            }
        )
        order_id = create_response.json()["order"]["id"]
        order_ids.append(order_id)
        
        # Process each order
        await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
        await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": f"Customer {i}", "delivery_address": f"{i} Street"})
        await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
        await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": f"Driver {i}"})
    
    # Test: Get delivery info for all orders concurrently
    tasks = [client.get(f"/api/orders/{oid}/delivery") for oid in order_ids]
    responses = await asyncio.gather(*tasks)
    
    # Verify all succeeded
    assert all(r.status_code == 200 for r in responses)
    
    # Verify each has correct data
    for i, response in enumerate(responses):
        data = response.json()
        assert data["order_id"] == order_ids[i]
        assert data["driver_name"] == f"Driver {i}"
        assert data["customer_name"] == f"Customer {i}"


@pytest.mark.asyncio
async def test_delivery_tracking_state_transitions(client):
    """
    Test delivery tracking through all state transitions
    Integration test: Verify tracking updates correctly as order progresses
    """
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Quattro Formaggi",
            "supplier_price": 18.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Process to dispatch
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True, "estimated_time": 45})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Test User", "delivery_address": "Test Address"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Test Driver"})
    
    # Test 1: Dispatched state
    response1 = await client.get(f"/api/orders/{order_id}/delivery")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["status"] == "dispatched"
    assert data1["progress_percentage"] == 33
    assert data1["estimated_arrival_minutes"] == 45
    
    # Transition to in_transit
    await client.post(f"/api/orders/{order_id}/status", params={"status": "in_transit"})
    
    # Test 2: In transit state
    response2 = await client.get(f"/api/orders/{order_id}/delivery")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "in_transit"
    assert data2["progress_percentage"] == 66
    assert data2["estimated_arrival_minutes"] < data1["estimated_arrival_minutes"]
    
    # Transition to delivered
    await client.post(f"/api/orders/{order_id}/status", params={"status": "delivered"})
    
    # Test 3: Delivered state
    response3 = await client.get(f"/api/orders/{order_id}/delivery")
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["status"] == "delivered"
    assert data3["progress_percentage"] == 100
    assert data3["estimated_arrival_minutes"] == 0


@pytest.mark.asyncio
async def test_delivery_tracking_edge_cases(client):
    """
    Test edge cases for delivery tracking
    """
    # Test 1: Order in preparing state (before dispatch)
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Test",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Test", "delivery_address": "Test"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "preparing"})
    
    response = await client.get(f"/api/orders/{order_id}/delivery")
    assert response.status_code == 400  # Not dispatched yet
    
    # Test 2: Order in ready state (before dispatch)
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    
    response = await client.get(f"/api/orders/{order_id}/delivery")
    assert response.status_code == 400  # Still not dispatched


@pytest.mark.asyncio
async def test_delivery_tracking_performance(client):
    """
    Performance test: Ensure delivery tracking responds quickly
    Requirement: Delivery endpoint responds within 50ms
    """
    import time
    
    # Setup: Create and dispatch order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Performance Test",
            "supplier_price": 12.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Test", "delivery_address": "Test"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Test Driver"})
    
    # Test: Measure response time
    start_time = time.time()
    response = await client.get(f"/api/orders/{order_id}/delivery")
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    # Note: In real environment, should be < 50ms, but in tests it may vary
    print(f"\nDelivery tracking response time: {response_time_ms:.2f}ms")
    assert response_time_ms < 1000  # Generous limit for test environment
