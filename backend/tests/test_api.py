import pytest

@pytest.mark.asyncio
async def test_create_order_endpoint(client):
    """Test POST /api/orders endpoint"""
    response = await client.post(
        "/api/orders",
        json={
            "source_name": "API Test Source",
            "item_name": "Kitchen Set",
            "source_price": 12.0,
            "markup_percentage": 25.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.created"
    assert data["order"]["item_name"] == "Kitchen Set"
    assert data["order"]["id"] is not None

@pytest.mark.asyncio
async def test_get_orders_endpoint(client):
    """Test GET /api/orders endpoint"""
    # Create an order first
    await client.post(
        "/api/orders",
        json={
            "source_name": "Test Source",
            "item_name": "Test Item",
            "source_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    
    # Get all orders
    response = await client.get("/api/orders")
    
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 1
    assert orders[0]["item_name"] == "Test Item"

@pytest.mark.asyncio
async def test_source_respond_endpoint(client):
    """Test POST /api/orders/{id}/source-respond endpoint"""
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "source_name": "Test Source",
            "item_name": "Test Item",
            "source_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Source accepts
    response = await client.post(
        f"/api/orders/{order_id}/source-respond",
        params={
            "accept": True,
            "notes": "Fresh ingredients",
            "estimated_time": 30
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.source_accepted"
    assert data["order"]["source_notes"] == "Fresh ingredients"

@pytest.mark.asyncio
async def test_buyer_accept_endpoint(client):
    """Test POST /api/orders/{id}/buyer-accept endpoint"""
    # Create and source accepts order
    create_response = await client.post(
        "/api/orders",
        json={
            "source_name": "Test Source",
            "item_name": "Test Item",
            "source_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(
        f"/api/orders/{order_id}/source-respond",
        params={"accept": True}
    )
    
    # Buyer accepts
    response = await client.post(
        f"/api/orders/{order_id}/buyer-accept",
        params={
            "buyer_name": "John Doe",
            "delivery_address": "123 Main St"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.buyer_accepted"
    assert data["order"]["buyer_name"] == "John Doe"
    assert data["order"]["buyer_price"] == 13.0

@pytest.mark.asyncio
async def test_dispatch_endpoint(client):
    """Test POST /api/orders/{id}/dispatch endpoint"""
    # Create full order flow
    create_response = await client.post(
        "/api/orders",
        json={
            "source_name": "Test Source",
            "item_name": "Test Item",
            "source_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/source-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/buyer-accept", params={"buyer_name": "John", "delivery_address": "123 St"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "preparing"})
    await client.post(f"/api/orders/{order_id}/status", params={"status": "ready"})
    
    # Dispatch
    response = await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Mike Driver"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.dispatched"
    assert data["order"]["driver_name"] == "Mike Driver"

@pytest.mark.asyncio
async def test_update_status_endpoint(client):
    """Test POST /api/orders/{id}/status endpoint"""
    # Create order with full flow
    create_response = await client.post(
        "/api/orders",
        json={
            "source_name": "Test Source",
            "item_name": "Test Item",
            "source_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/source-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/buyer-accept", params={"buyer_name": "John", "delivery_address": "123 St"})
    
    # Update to preparing
    response = await client.post(
        f"/api/orders/{order_id}/status",
        params={"status": "preparing"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["order"]["status"] == "preparing"

@pytest.mark.asyncio
async def test_invalid_order_id(client):
    """Test endpoints with invalid order ID"""
    response = await client.post(
        "/api/orders/invalid-id/source-respond",
        params={"accept": True}
    )
    
    assert response.status_code == 404
