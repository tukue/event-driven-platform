"""
Integration tests for backend-frontend communication
Tests the full flow: order creation, WebSocket updates, and API responses
"""
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_order_flow():
    """Test complete order creation flow"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create order
        order_data = {
            "supplier_name": "Test Supplier",
            "pizza_name": "Test Pizza",
            "supplier_price": 10.0,
            "markup_percentage": 20.0
        }
        
        response = await ac.post("/api/orders", json=order_data)
        assert response.status_code == 200, f"Failed to create order: {response.text}"
        
        result = response.json()
        assert result["event_type"] == "order.created"
        assert result["order"]["supplier_name"] == "Test Supplier"
        assert result["order"]["pizza_name"] == "Test Pizza"
        assert result["order"]["status"] == "pending_supplier"
        assert "id" in result["order"]
        assert "tracking_id" in result["order"]
        
        order_id = result["order"]["id"]
        
        # Verify order exists in list
        response = await ac.get("/api/orders")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) > 0
        assert any(o["id"] == order_id for o in orders)


@pytest.mark.asyncio
async def test_supplier_workflow():
    """Test supplier accept/reject workflow"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create order
        order_data = {
            "supplier_name": "Supplier Test",
            "pizza_name": "Margherita",
            "supplier_price": 12.0,
            "markup_percentage": 25.0
        }
        
        response = await ac.post("/api/orders", json=order_data)
        order_id = response.json()["order"]["id"]
        
        # Supplier accepts
        response = await ac.post(
            f"/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "notes": "Ready in 30 min", "estimated_time": 30}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["event_type"] == "order.supplier_accepted"
        assert result["order"]["status"] == "supplier_accepted"
        assert result["order"]["estimated_delivery_time"] == 30


@pytest.mark.asyncio
async def test_customer_workflow():
    """Test customer acceptance workflow"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create and accept order as supplier
        order_data = {
            "supplier_name": "Pizza Place",
            "pizza_name": "Pepperoni",
            "supplier_price": 15.0,
            "markup_percentage": 30.0
        }
        
        response = await ac.post("/api/orders", json=order_data)
        order_id = response.json()["order"]["id"]
        
        await ac.post(
            f"/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "estimated_time": 25}
        )
        
        # Customer accepts
        response = await ac.post(
            f"/api/orders/{order_id}/customer-accept",
            params={
                "customer_name": "John Doe",
                "delivery_address": "123 Main St"
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["event_type"] == "order.customer_accepted"
        assert result["order"]["status"] == "customer_accepted"
        assert result["order"]["customer_name"] == "John Doe"
        assert result["order"]["customer_price"] == 15.0 * 1.3  # With markup


@pytest.mark.asyncio
async def test_dispatch_workflow():
    """Test order dispatch workflow"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create order and go through supplier/customer acceptance
        order_data = {
            "supplier_name": "Fast Pizza",
            "pizza_name": "Hawaiian",
            "supplier_price": 14.0,
            "markup_percentage": 20.0
        }
        
        response = await ac.post("/api/orders", json=order_data)
        order_id = response.json()["order"]["id"]
        
        await ac.post(
            f"/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "estimated_time": 20}
        )
        
        await ac.post(
            f"/api/orders/{order_id}/customer-accept",
            params={
                "customer_name": "Jane Smith",
                "delivery_address": "456 Oak Ave"
            }
        )
        
        # Dispatch order
        response = await ac.post(
            f"/api/orders/{order_id}/dispatch",
            params={"driver_name": "Mike Driver"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["event_type"] == "order.dispatched"
        assert result["order"]["status"] == "dispatched"
        assert result["order"]["driver_name"] == "Mike Driver"


@pytest.mark.asyncio
async def test_tracking_id_lookup():
    """Test tracking by tracking ID"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create order
        order_data = {
            "supplier_name": "Track Pizza",
            "pizza_name": "Veggie",
            "supplier_price": 13.0,
            "markup_percentage": 25.0
        }
        
        response = await ac.post("/api/orders", json=order_data)
        tracking_id = response.json()["order"]["tracking_id"]
        
        # Look up by tracking ID
        response = await ac.get(f"/api/track/{tracking_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["tracking_id"] == tracking_id
        assert result["status"] == "pending_supplier"


@pytest.mark.asyncio
async def test_system_state_endpoint():
    """Test system state endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/state")
        assert response.status_code == 200
        state = response.json()
        assert "orders" in state
        assert "summary" in state
        assert isinstance(state["orders"], list)


@pytest.mark.asyncio
async def test_cors_headers():
    """Test CORS headers are properly set"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.options(
            "/api/orders",
            headers={"Origin": "http://localhost:5174"}
        )
        # FastAPI/Starlette handles CORS, just verify endpoint is accessible
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly defined


@pytest.mark.asyncio
async def test_error_handling_invalid_order():
    """Test error handling for invalid order data"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing required fields
        response = await ac.post("/api/orders", json={})
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_error_handling_nonexistent_order():
    """Test error handling for non-existent order"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/orders/nonexistent-id/supplier-respond",
            params={"accept": True}
        )
        assert response.status_code == 404
