import pytest
import asyncio

@pytest.mark.asyncio
async def test_complete_order_flow_integration(client):
    """
    Integration test: Complete order flow from creation to delivery
    Tests the entire system end-to-end
    """
    # Step 1: Supplier creates order
    print("\n1. Creating order...")
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Integration Test Pizza",
            "pizza_name": "Supreme",
            "supplier_price": 15.0,
            "markup_percentage": 35.0
        }
    )
    assert create_response.status_code == 200
    order_data = create_response.json()
    order_id = order_data["order"]["id"]
    assert order_data["order"]["status"] == "pending_supplier"
    print(f"   ✓ Order created: {order_id}")
    
    # Step 2: Supplier accepts order
    print("2. Supplier accepting order...")
    supplier_response = await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={
            "accept": True,
            "notes": "Premium ingredients",
            "estimated_time": 35
        }
    )
    assert supplier_response.status_code == 200
    supplier_data = supplier_response.json()
    assert supplier_data["order"]["status"] == "supplier_accepted"
    assert supplier_data["order"]["supplier_notes"] == "Premium ingredients"
    assert supplier_data["order"]["estimated_delivery_time"] == 35
    print("   ✓ Supplier accepted")
    
    # Step 3: Customer accepts order
    print("3. Customer accepting order...")
    customer_response = await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={
            "customer_name": "Integration Test Customer",
            "delivery_address": "789 Integration Ave"
        }
    )
    assert customer_response.status_code == 200
    customer_data = customer_response.json()
    assert customer_data["order"]["status"] == "customer_accepted"
    assert customer_data["order"]["customer_name"] == "Integration Test Customer"
    assert customer_data["order"]["customer_price"] == 20.25  # 15 + 35%
    print(f"   ✓ Customer accepted (Price: ${customer_data['order']['customer_price']})")
    
    # Step 4: Start preparing
    print("4. Starting preparation...")
    preparing_response = await client.post(
        f"/api/orders/{order_id}/status",
        params={"status": "preparing"}
    )
    assert preparing_response.status_code == 200
    assert preparing_response.json()["order"]["status"] == "preparing"
    print("   ✓ Preparing")
    
    # Step 5: Mark as ready
    print("5. Marking as ready...")
    ready_response = await client.post(
        f"/api/orders/{order_id}/status",
        params={"status": "ready"}
    )
    assert ready_response.status_code == 200
    assert ready_response.json()["order"]["status"] == "ready"
    print("   ✓ Ready for pickup")
    
    # Step 6: Dispatch order
    print("6. Dispatching order...")
    dispatch_response = await client.post(
        f"/api/orders/{order_id}/dispatch",
        params={"driver_name": "Integration Test Driver"}
    )
    assert dispatch_response.status_code == 200
    dispatch_data = dispatch_response.json()
    assert dispatch_data["order"]["status"] == "dispatched"
    assert dispatch_data["order"]["driver_name"] == "Integration Test Driver"
    print("   ✓ Dispatched to driver")
    
    # Step 7: Mark in transit
    print("7. Marking in transit...")
    transit_response = await client.post(
        f"/api/orders/{order_id}/status",
        params={"status": "in_transit"}
    )
    assert transit_response.status_code == 200
    assert transit_response.json()["order"]["status"] == "in_transit"
    print("   ✓ In transit")
    
    # Step 8: Mark as delivered
    print("8. Marking as delivered...")
    delivered_response = await client.post(
        f"/api/orders/{order_id}/status",
        params={"status": "delivered"}
    )
    assert delivered_response.status_code == 200
    final_data = delivered_response.json()
    assert final_data["order"]["status"] == "delivered"
    print("   ✓ Delivered!")
    
    # Step 9: Verify final order state
    print("9. Verifying final state...")
    orders_response = await client.get("/api/orders")
    assert orders_response.status_code == 200
    orders = orders_response.json()
    
    completed_order = next((o for o in orders if o["id"] == order_id), None)
    assert completed_order is not None
    assert completed_order["status"] == "delivered"
    assert completed_order["supplier_name"] == "Integration Test Pizza"
    assert completed_order["customer_name"] == "Integration Test Customer"
    assert completed_order["driver_name"] == "Integration Test Driver"
    assert completed_order["customer_price"] == 20.25
    print("   ✓ Final state verified")
    
    print("\n✅ Complete integration test passed!")

@pytest.mark.asyncio
async def test_multiple_orders_concurrent(client):
    """Test handling multiple orders concurrently"""
    # Create 5 orders concurrently
    tasks = []
    for i in range(5):
        task = client.post(
            "/api/orders",
            json={
                "supplier_name": f"Concurrent Pizza {i}",
                "pizza_name": f"Pizza Type {i}",
                "supplier_price": 10.0 + i,
                "markup_percentage": 30.0
            }
        )
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    
    # Verify all created successfully
    assert all(r.status_code == 200 for r in responses)
    order_ids = [r.json()["order"]["id"] for r in responses]
    assert len(set(order_ids)) == 5  # All unique IDs
    
    # Verify all orders exist
    orders_response = await client.get("/api/orders")
    orders = orders_response.json()
    assert len(orders) >= 5

@pytest.mark.asyncio
async def test_supplier_rejection_flow(client):
    """Test order flow when supplier rejects"""
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
    
    # Supplier rejects
    reject_response = await client.post(
        f"/api/orders/{order_id}/supplier-respond",
        params={
            "accept": False,
            "notes": "Out of stock"
        }
    )
    
    assert reject_response.status_code == 200
    reject_data = reject_response.json()
    assert reject_data["order"]["status"] == "supplier_rejected"
    assert reject_data["order"]["supplier_notes"] == "Out of stock"
    
    # Customer should not be able to accept rejected order
    customer_response = await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={
            "customer_name": "John Doe",
            "delivery_address": "123 Main St"
        }
    )
    
    assert customer_response.status_code == 400

@pytest.mark.asyncio
async def test_pricing_calculation(client):
    """Test automatic pricing calculation with different markups"""
    test_cases = [
        (10.0, 30.0, 13.0),   # $10 + 30% = $13
        (15.0, 20.0, 18.0),   # $15 + 20% = $18
        (20.0, 50.0, 30.0),   # $20 + 50% = $30
        (12.50, 25.0, 15.62), # $12.50 + 25% = $15.625 → $15.62 (rounded)
    ]
    
    for base_price, markup, expected_price in test_cases:
        # Create and process order
        create_response = await client.post(
            "/api/orders",
            json={
                "supplier_name": "Test Pizza",
                "pizza_name": "Test",
                "supplier_price": base_price,
                "markup_percentage": markup
            }
        )
        order_id = create_response.json()["order"]["id"]
        
        await client.post(f"/api/orders/{order_id}/supplier-respond", params={"accept": True})
        
        customer_response = await client.post(
            f"/api/orders/{order_id}/customer-accept",
            params={"customer_name": "Test", "delivery_address": "Test St"}
        )
        
        actual_price = customer_response.json()["order"]["customer_price"]
        assert actual_price == expected_price, f"Expected ${expected_price}, got ${actual_price}"

@pytest.mark.asyncio
async def test_order_state_validation(client):
    """Test that orders can only transition through valid states"""
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
    
    # Try to skip states (should work but not recommended)
    # Customer cannot accept before supplier
    customer_response = await client.post(
        f"/api/orders/{order_id}/customer-accept",
        params={"customer_name": "John", "delivery_address": "123 St"}
    )
    assert customer_response.status_code == 400  # Should fail
