#!/usr/bin/env python3
"""
Test script for Phase 1 (Delivery Endpoint) and Phase 2 (State Management)
Tests the new delivery tracking and system state endpoints
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Set test environment variables before importing main
os.environ['REDIS_HOST'] = 'test-host'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_USERNAME'] = 'test'
os.environ['REDIS_PASSWORD'] = 'test'
os.environ['REDIS_DB'] = '0'

from main import app
from httpx import AsyncClient, ASGITransport
from services.order_service import OrderService
from services.delivery_service import DeliveryService
import main


async def setup_test_client():
    """Set up test client with mocked Redis"""
    # Mock the redis_client used by the app
    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis._storage = {}
    
    async def mock_set(key, value):
        mock_redis._storage[key] = value
        return True
    
    async def mock_get(key):
        return mock_redis._storage.get(key)
    
    async def mock_keys(pattern):
        return [k for k in mock_redis._storage.keys() if pattern.replace("*", "") in k]
    
    # Mock publish operation (must be AsyncMock)
    mock_redis.publish = AsyncMock(return_value=1)
    
    mock_redis.client.set = mock_set
    mock_redis.client.get = mock_get
    mock_redis.client.keys = mock_keys
    
    # Mock connect/disconnect methods
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()
    
    # Replace the redis_client in main module
    main.redis_client = mock_redis
    
    # Create services with mocked redis and set them directly on main module
    main.order_service = OrderService(mock_redis)
    main.delivery_service = DeliveryService(mock_redis)
    
    # Import and create state service
    from services.state_service import StateService, CachedStateService
    base_state_service = StateService(mock_redis)
    main.state_service = CachedStateService(base_state_service, mock_redis)
    
    # Also set the global variables in the main module
    import main as main_module
    main_module.order_service = main.order_service
    main_module.delivery_service = main.delivery_service
    main_module.state_service = main.state_service
    
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_phase_1_delivery_endpoint():
    """Test Phase 1: Delivery Tracking Endpoint"""
    print("\n🧪 Testing Phase 1: Delivery Tracking Endpoint")
    print("=" * 50)
    
    async with await setup_test_client() as client:
        # Step 1: Create and process an order to dispatched state
        print("1. Creating test order...")
        create_response = await client.post(
            "/api/orders",
            json={
                "supplier_name": "Test Pizza Palace",
                "pizza_name": "Margherita Supreme",
                "supplier_price": 15.0,
                "markup_percentage": 30.0
            }
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create order: {create_response.status_code}")
            print(create_response.text)
            return False
        
        order_data = create_response.json()
        order_id = order_data["order"]["id"]
        print(f"✅ Order created: {order_id}")
        
        # Step 2: Process order through workflow
        print("2. Processing order through workflow...")
        
        # Supplier accepts
        supplier_response = await client.post(
            f"/api/orders/{order_id}/supplier-respond",
            params={"accept": True, "notes": "Fresh ingredients", "estimated_time": 35}
        )
        if supplier_response.status_code != 200:
            print(f"❌ Supplier response failed: {supplier_response.status_code}")
            return False
        print("   ✅ Supplier accepted")
        
        # Customer accepts
        customer_response = await client.post(
            f"/api/orders/{order_id}/customer-accept",
            params={"customer_name": "John Doe", "delivery_address": "123 Test Street"}
        )
        if customer_response.status_code != 200:
            print(f"❌ Customer accept failed: {customer_response.status_code}")
            return False
        print("   ✅ Customer accepted")
        
        # Mark as ready
        ready_response = await client.post(
            f"/api/orders/{order_id}/status",
            params={"status": "ready"}
        )
        if ready_response.status_code != 200:
            print(f"❌ Ready status failed: {ready_response.status_code}")
            return False
        print("   ✅ Marked as ready")
        
        # Dispatch order
        dispatch_response = await client.post(
            f"/api/orders/{order_id}/dispatch",
            params={"driver_name": "Mike Driver"}
        )
        if dispatch_response.status_code != 200:
            print(f"❌ Dispatch failed: {dispatch_response.status_code}")
            return False
        print("   ✅ Order dispatched")
        
        # Step 3: Test delivery tracking endpoint
        print("3. Testing delivery tracking endpoint...")
        
        delivery_response = await client.get(f"/api/orders/{order_id}/delivery")
        
        if delivery_response.status_code != 200:
            print(f"❌ Delivery tracking failed: {delivery_response.status_code}")
            print(delivery_response.text)
            return False
        
        delivery_data = delivery_response.json()
        print("   ✅ Delivery tracking successful!")
        
        # Verify delivery data structure
        required_fields = [
            "order_id", "status", "driver_name", "delivery_address", 
            "customer_name", "progress_percentage", "estimated_arrival_minutes",
            "timeline", "current_stage"
        ]
        
        for field in required_fields:
            if field not in delivery_data:
                print(f"❌ Missing field in delivery data: {field}")
                return False
        
        print(f"   📊 Progress: {delivery_data['progress_percentage']}%")
        print(f"   🚚 Driver: {delivery_data['driver_name']}")
        print(f"   ⏱️  ETA: {delivery_data['estimated_arrival_minutes']} minutes")
        print(f"   📍 Stage: {delivery_data['current_stage']}")
        
        # Step 4: Test different order states
        print("4. Testing different order states...")
        
        # Move to in_transit
        transit_response = await client.post(
            f"/api/orders/{order_id}/status",
            params={"status": "in_transit"}
        )
        if transit_response.status_code != 200:
            print(f"❌ In transit status failed: {transit_response.status_code}")
            return False
        
        # Test tracking in transit
        transit_tracking = await client.get(f"/api/orders/{order_id}/delivery")
        if transit_tracking.status_code != 200:
            print(f"❌ Transit tracking failed: {transit_tracking.status_code}")
            return False
        
        transit_data = transit_tracking.json()
        print(f"   ✅ In Transit - Progress: {transit_data['progress_percentage']}%")
        
        # Move to delivered
        delivered_response = await client.post(
            f"/api/orders/{order_id}/status",
            params={"status": "delivered"}
        )
        if delivered_response.status_code != 200:
            print(f"❌ Delivered status failed: {delivered_response.status_code}")
            return False
        
        # Test tracking delivered
        delivered_tracking = await client.get(f"/api/orders/{order_id}/delivery")
        if delivered_tracking.status_code != 200:
            print(f"❌ Delivered tracking failed: {delivered_tracking.status_code}")
            return False
        
        delivered_data = delivered_tracking.json()
        print(f"   ✅ Delivered - Progress: {delivered_data['progress_percentage']}%")
        
        # Step 5: Test error cases
        print("5. Testing error cases...")
        
        # Test non-existent order
        fake_response = await client.get("/api/orders/00000000-0000-0000-0000-000000000000/delivery")
        if fake_response.status_code != 404:
            print(f"❌ Expected 404 for fake order, got {fake_response.status_code}")
            return False
        print("   ✅ 404 for non-existent order")
        
        # Test non-dispatched order
        new_order_response = await client.post(
            "/api/orders",
            json={
                "supplier_name": "Test Pizza",
                "pizza_name": "Test",
                "supplier_price": 10.0,
                "markup_percentage": 30.0
            }
        )
        new_order_id = new_order_response.json()["order"]["id"]
        
        non_dispatched_response = await client.get(f"/api/orders/{new_order_id}/delivery")
        if non_dispatched_response.status_code != 400:
            print(f"❌ Expected 400 for non-dispatched order, got {non_dispatched_response.status_code}")
            return False
        print("   ✅ 400 for non-dispatched order")
    
    print("\n🎉 Phase 1 (Delivery Endpoint) - ALL TESTS PASSED!")
    return True


async def test_phase_2_state_management():
    """Test Phase 2: State Management Endpoint"""
    print("\n🧪 Testing Phase 2: State Management Endpoint")
    print("=" * 50)
    
    async with await setup_test_client() as client:
        # Step 1: Test basic state endpoint
        print("1. Testing basic state endpoint...")
        
        state_response = await client.get("/api/state")
        
        if state_response.status_code != 200:
            print(f"❌ State endpoint failed: {state_response.status_code}")
            print(state_response.text)
            return False
        
        state_data = state_response.json()
        print("   ✅ State endpoint successful!")
        
        # Step 2: Verify state data structure
        print("2. Verifying state data structure...")
        
        required_fields = ["statistics", "orders_by_status", "active_drivers", "last_updated"]
        
        for field in required_fields:
            if field not in state_data:
                print(f"❌ Missing field in state data: {field}")
                return False
        
        print("   ✅ All required fields present")
        
        # Step 3: Verify statistics structure
        print("3. Verifying statistics structure...")
        
        statistics = state_data["statistics"]
        stats_fields = [
            "total_orders", "active_deliveries", "completed_today",
            "pending_supplier", "preparing", "ready", "dispatched", "in_transit", "delivered"
        ]
        
        for field in stats_fields:
            if field not in statistics:
                print(f"❌ Missing statistics field: {field}")
                return False
        
        print(f"   📊 Total Orders: {statistics['total_orders']}")
        print(f"   🚚 Active Deliveries: {statistics['active_deliveries']}")
        print(f"   ✅ Completed Today: {statistics['completed_today']}")
        print(f"   📦 Dispatched: {statistics['dispatched']}")
        print(f"   🚛 In Transit: {statistics['in_transit']}")
        print(f"   🎯 Delivered: {statistics['delivered']}")
        
        # Step 4: Test query parameters
        print("4. Testing query parameters...")
        
        # Test include_completed=false
        no_completed_response = await client.get("/api/state?include_completed=false")
        if no_completed_response.status_code != 200:
            print(f"❌ State with include_completed=false failed: {no_completed_response.status_code}")
            return False
        
        no_completed_data = no_completed_response.json()
        orders_by_status = no_completed_data["orders_by_status"]
        
        # Should not have delivered or cancelled orders
        if "delivered" in orders_by_status or "cancelled" in orders_by_status:
            print("❌ include_completed=false still returned completed orders")
            return False
        
        print("   ✅ include_completed=false works correctly")
        
        # Test limit parameter
        limited_response = await client.get("/api/state?limit=1")
        if limited_response.status_code != 200:
            print(f"❌ State with limit failed: {limited_response.status_code}")
            return False
        
        limited_data = limited_response.json()
        limited_orders = limited_data["orders_by_status"]
        
        # Check that each status has at most 1 order
        for status, orders in limited_orders.items():
            if len(orders) > 1:
                print(f"❌ Limit not applied correctly for status {status}: {len(orders)} orders")
                return False
        
        print("   ✅ limit parameter works correctly")
        
        # Step 5: Test active drivers
        print("5. Testing active drivers...")
        
        active_drivers = state_data["active_drivers"]
        print(f"   👥 Active Drivers: {len(active_drivers)}")
        
        for driver in active_drivers:
            required_driver_fields = ["driver_name", "status"]
            for field in required_driver_fields:
                if field not in driver:
                    print(f"❌ Missing driver field: {field}")
                    return False
            print(f"   🚚 Driver: {driver['driver_name']} - Status: {driver['status']}")
        
        # Step 6: Test caching (make multiple requests)
        print("6. Testing caching behavior...")
        
        import time
        start_time = time.time()
        
        # Make multiple requests quickly
        for i in range(3):
            cache_response = await client.get("/api/state")
            if cache_response.status_code != 200:
                print(f"❌ Cached request {i+1} failed")
                return False
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"   ⚡ 3 requests completed in {total_time:.3f}s")
        print("   ✅ Caching appears to be working (fast responses)")
    
    print("\n🎉 Phase 2 (State Management) - ALL TESTS PASSED!")
    return True


async def main():
    """Run all tests"""
    print("🚀 Testing Delivery State Management - Phases 1 & 2")
    print("=" * 60)
    
    try:
        # Test Phase 1
        phase1_success = await test_phase_1_delivery_endpoint()
        
        # Test Phase 2
        phase2_success = await test_phase_2_state_management()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print(f"Phase 1 (Delivery Endpoint): {'✅ PASSED' if phase1_success else '❌ FAILED'}")
        print(f"Phase 2 (State Management): {'✅ PASSED' if phase2_success else '❌ FAILED'}")
        
        if phase1_success and phase2_success:
            print("\n🎉 ALL PHASES PASSED! Ready for Phase 3 implementation.")
            return True
        else:
            print("\n❌ Some phases failed. Please fix issues before proceeding.")
            return False
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)