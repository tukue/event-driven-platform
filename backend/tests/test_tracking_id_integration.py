"""
Integration tests for Tracking ID feature
Tests both customer tracking ID and supplier tracking ID
"""
import pytest


@pytest.mark.asyncio
async def test_order_creation_generates_tracking_ids(client):
    """
    Test that creating an order generates both tracking IDs
    """
    # Create order
    response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Pizza Palace",
            "pizza_name": "Margherita",
            "supplier_price": 12.0,
            "markup_percentage": 30.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    order = data["order"]
    
    # Verify tracking IDs are generated
    assert "tracking_id" in order
    assert "supplier_tracking_id" in order
    assert order["tracking_id"] is not None
    assert order["supplier_tracking_id"] is not None
    
    # Verify tracking ID format (PIZZA-YYYY-NNNNNN)
    tracking_id = order["tracking_id"]
    assert tracking_id.startswith("PIZZA-")
    parts = tracking_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 4  # Year
    assert len(parts[2]) == 6  # 6-digit number
    
    # Verify supplier tracking ID format (PREFIX-NNNN)
    supplier_tracking_id = order["supplier_tracking_id"]
    assert "-" in supplier_tracking_id
    prefix, number = supplier_tracking_id.split("-")
    assert len(prefix) <= 3  # Max 3 letters
    assert len(number) == 4  # 4-digit number
    assert prefix == "PP"  # Pizza Palace -> PP


@pytest.mark.asyncio
async def test_track_order_by_tracking_id_not_dispatched(client):
    """
    Test tracking order by tracking ID before dispatch
    """
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Pepperoni",
            "supplier_price": 15.0,
            "markup_percentage": 25.0
        }
    )
    
    order_data = create_response.json()["order"]
    tracking_id = order_data["tracking_id"]
    
    # Track by tracking ID
    track_response = await client.get(f"/api/track/{tracking_id}")
    
    assert track_response.status_code == 200
    track_data = track_response.json()
    
    # Verify response for non-dispatched order
    assert track_data["tracking_id"] == tracking_id
    assert track_data["status"] == "pending_supplier"
    assert "message" in track_data
    assert "not yet dispatched" in track_data["message"].lower()


@pytest.mark.asyncio
async def test_track_order_by_tracking_id_dispatched(client):
    """
    Test tracking order by tracking ID after dispatch
    """
    # Create and dispatch order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Gourmet Pizza",
            "pizza_name": "Hawaiian",
            "supplier_price": 14.0,
            "markup_percentage": 30.0
        }
    )
    
    order_data = create_response.json()["order"]
    order_id = order_data["id"]
    tracking_id = order_data["tracking_id"]
    
    # Process order to dispatch
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True, "estimated_time": 30})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "John Doe", "delivery_address": "123 Main St"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Mike Driver"})
    
    # Track by tracking ID
    track_response = await client.get(f"/api/track/{tracking_id}")
    
    assert track_response.status_code == 200
    track_data = track_response.json()
    
    # Verify full delivery info is returned
    assert track_data["tracking_id"] == tracking_id
    assert track_data["status"] == "dispatched"
    assert track_data["driver_name"] == "Mike Driver"
    assert "progress_percentage" in track_data
    assert "estimated_arrival_minutes" in track_data
    assert "timeline" in track_data


@pytest.mark.asyncio
async def test_track_order_by_supplier_tracking_id(client):
    """
    Test tracking order using supplier tracking ID
    """
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Quick Pizza",
            "pizza_name": "Veggie Supreme",
            "supplier_price": 13.0,
            "markup_percentage": 30.0
        }
    )
    
    order_data = create_response.json()["order"]
    supplier_tracking_id = order_data["supplier_tracking_id"]
    
    # Track by supplier tracking ID
    track_response = await client.get(f"/api/track/{supplier_tracking_id}")
    
    assert track_response.status_code == 200
    track_data = track_response.json()
    
    # Verify it finds the order
    assert track_data["supplier_tracking_id"] == supplier_tracking_id
    assert track_data["supplier_name"] == "Quick Pizza"


@pytest.mark.asyncio
async def test_track_invalid_tracking_id(client):
    """
    Test tracking with invalid tracking ID
    """
    fake_tracking_id = "PIZZA-2024-999999"
    
    response = await client.get(f"/api/track/{fake_tracking_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tracking_ids_are_unique(client):
    """
    Test that tracking IDs are unique across multiple orders
    """
    tracking_ids = set()
    supplier_tracking_ids = set()
    
    # Create 10 orders
    for i in range(10):
        response = await client.post(
            "/api/orders",
            json={
                "supplier_name": f"Pizza Place {i}",
                "pizza_name": f"Pizza {i}",
                "supplier_price": 10.0 + i,
                "markup_percentage": 30.0
            }
        )
        
        order = response.json()["order"]
        tracking_ids.add(order["tracking_id"])
        supplier_tracking_ids.add(order["supplier_tracking_id"])
    
    # Verify all tracking IDs are unique
    assert len(tracking_ids) == 10
    assert len(supplier_tracking_ids) == 10


@pytest.mark.asyncio
async def test_delivery_info_includes_tracking_ids(client):
    """
    Test that delivery info endpoint includes tracking IDs
    """
    # Create and dispatch order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Premium Pizza",
            "pizza_name": "Deluxe",
            "supplier_price": 18.0,
            "markup_percentage": 30.0
        }
    )
    
    order_data = create_response.json()["order"]
    order_id = order_data["id"]
    tracking_id = order_data["tracking_id"]
    supplier_tracking_id = order_data["supplier_tracking_id"]
    
    # Process to dispatch
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Jane Smith", "delivery_address": "456 Oak Ave"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Sarah Driver"})
    
    # Get delivery info
    delivery_response = await client.get(f"/api/orders/{order_id}/delivery")
    
    assert delivery_response.status_code == 200
    delivery_data = delivery_response.json()
    
    # Verify tracking IDs are included
    assert delivery_data["tracking_id"] == tracking_id
    assert delivery_data["supplier_tracking_id"] == supplier_tracking_id


@pytest.mark.asyncio
async def test_supplier_tracking_id_prefix_generation(client):
    """
    Test that supplier tracking ID prefix is generated correctly from supplier name
    """
    test_cases = [
        ("Pizza Palace", "PP"),
        ("Quick Bites", "QB"),
        ("The Best Pizza", "TBP"),
        ("A", "A"),
        ("AB CD EF GH", "ACE"),  # Max 3 letters
    ]
    
    for supplier_name, expected_prefix in test_cases:
        response = await client.post(
            "/api/orders",
            json={
                "supplier_name": supplier_name,
                "pizza_name": "Test Pizza",
                "supplier_price": 10.0,
                "markup_percentage": 30.0
            }
        )
        
        order = response.json()["order"]
        supplier_tracking_id = order["supplier_tracking_id"]
        actual_prefix = supplier_tracking_id.split("-")[0]
        
        assert actual_prefix == expected_prefix, f"Expected {expected_prefix}, got {actual_prefix} for {supplier_name}"


@pytest.mark.asyncio
async def test_tracking_id_persists_through_order_lifecycle(client):
    """
    Test that tracking IDs remain consistent throughout order lifecycle
    """
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Lifecycle Test",
            "supplier_price": 12.0,
            "markup_percentage": 30.0
        }
    )
    
    original_order = create_response.json()["order"]
    order_id = original_order["id"]
    original_tracking_id = original_order["tracking_id"]
    original_supplier_tracking_id = original_order["supplier_tracking_id"]
    
    # Process through entire lifecycle
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "Test", "delivery_address": "Test"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "preparing"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    await client.post(f"/api/orders/{order_id}/dispatch", params={"driver_name": "Test Driver"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "in_transit"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "delivered"})
    
    # Get final order state
    orders_response = await client.get("/api/orders")
    orders = orders_response.json()
    final_order = next(o for o in orders if o["id"] == order_id)
    
    # Verify tracking IDs haven't changed
    assert final_order["tracking_id"] == original_tracking_id
    assert final_order["supplier_tracking_id"] == original_supplier_tracking_id
