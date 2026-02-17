import pytest

@pytest.mark.asyncio
async def test_create_order_endpoint(client):
    """Test POST /api/orders endpoint"""
    response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "API Test Pizza",
            "pizza_name": "Pepperoni",
            "supplier_price": 12.0,
            "markup_percentage": 25.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.created"
    assert data["order"]["pizza_name"] == "Pepperoni"
    assert data["order"]["id"] is not None

@pytest.mark.asyncio
async def test_get_orders_endpoint(client):
    """Test GET /api/orders endpoint"""
    # Create an order first
    await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    
    # Get all orders
    response = await client.get("/api/orders")
    
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 1
    assert orders[0]["pizza_name"] == "Margherita"

@pytest.mark.asyncio
async def test_supplier_respond_endpoint(client):
    """Test POST /api/orders/{id}/supplier-respond endpoint"""
    # Create order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    # Supplier accepts
    response = await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={
            "accept": True,
            "notes": "Fresh ingredients",
            "estimated_time": 30
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.supplier_accepted"
    assert data["order"]["supplier_notes"] == "Fresh ingredients"

@pytest.mark.asyncio
async def test_customer_accept_endpoint(client):
    """Test POST /api/orders/{id}/customer-accept endpoint"""
    # Create and supplier accepts order
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={"accept": True}
    )
    
    # Customer accepts
    response = await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={
            "customer_name": "John Doe",
            "delivery_address": "123 Main St"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "order.customer_accepted"
    assert data["order"]["customer_name"] == "John Doe"
    assert data["order"]["customer_price"] == 13.0

@pytest.mark.asyncio
async def test_dispatch_endpoint(client):
    """Test POST /api/orders/{id}/dispatch endpoint"""
    # Create full order flow
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "John", "delivery_address": "123 St"})
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
            "supplier_name": "Test Pizza",
            "pizza_name": "Margherita",
            "supplier_price": 10.0,
            "markup_percentage": 30.0
        }
    )
    order_id = create_response.json()["order"]["id"]
    
    await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
    await client.post(f"/api/orders/{order_id}/customer-accept", params={"customer_name": "John", "delivery_address": "123 St"})
    
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
        "/api/orders/invalid-id/supplier-respond",
        params={"accept": True}
    )
    
    assert response.status_code == 404
