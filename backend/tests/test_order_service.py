import pytest
from models import Order, OrderStatus

@pytest.mark.asyncio
async def test_create_order(order_service):
    """Test creating an order"""
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0,
        markup_percentage=30.0
    )
    
    event = await order_service.create_order(order)
    
    assert event.event_type == "order.created"
    assert event.order.id is not None
    assert event.order.status == OrderStatus.PENDING_SOURCE
    assert event.order.created_at is not None

@pytest.mark.asyncio
async def test_source_accept_order(order_service):
    """Test source accepting an order"""
    # Create order
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Source accepts
    accept_event = await order_service.source_respond(
        order_id=order_id,
        accept=True,
        notes="Fresh ingredients",
        estimated_time=30
    )
    
    assert accept_event.event_type == "order.source_accepted"
    assert accept_event.order.status == OrderStatus.SOURCE_ACCEPTED
    assert accept_event.order.source_notes == "Fresh ingredients"
    assert accept_event.order.estimated_delivery_time == 30

@pytest.mark.asyncio
async def test_source_reject_order(order_service):
    """Test source rejecting an order"""
    # Create order
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Source rejects
    reject_event = await order_service.source_respond(
        order_id=order_id,
        accept=False,
        notes="Out of ingredients"
    )
    
    assert reject_event.event_type == "order.source_rejected"
    assert reject_event.order.status == OrderStatus.SOURCE_REJECTED
    assert reject_event.order.source_notes == "Out of ingredients"

@pytest.mark.asyncio
async def test_buyer_accept_order(order_service):
    """Test buyer accepting an order"""
    # Create and source accepts order
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0,
        markup_percentage=30.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    await order_service.source_respond(order_id, accept=True)
    
    # Buyer accepts
    buyer_event = await order_service.buyer_accept(
        order_id=order_id,
        buyer_name="John Doe",
        delivery_address="123 Main St"
    )
    
    assert buyer_event.event_type == "order.buyer_accepted"
    assert buyer_event.order.status == OrderStatus.BUYER_ACCEPTED
    assert buyer_event.order.buyer_name == "John Doe"
    assert buyer_event.order.delivery_address == "123 Main St"
    assert buyer_event.order.buyer_price == 13.0  # 10 + 30%

@pytest.mark.asyncio
async def test_buyer_accept_without_source_fails(order_service):
    """Test buyer cannot accept before source"""
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Should fail
    with pytest.raises(ValueError, match="must be accepted by source first"):
        await order_service.buyer_accept(
            order_id=order_id,
            buyer_name="John Doe",
            delivery_address="123 Main St"
        )

@pytest.mark.asyncio
async def test_dispatch_order(order_service):
    """Test dispatching an order"""
    # Create full order flow
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    await order_service.source_respond(order_id, accept=True)
    await order_service.buyer_accept(order_id, "John Doe", "123 Main St")
    await order_service.update_status(order_id, OrderStatus.PREPARING)
    await order_service.update_status(order_id, OrderStatus.READY)
    
    # Dispatch
    dispatch_event = await order_service.dispatch_order(
        order_id=order_id,
        driver_name="Mike Driver"
    )
    
    assert dispatch_event.event_type == "order.dispatched"
    assert dispatch_event.order.status == OrderStatus.DISPATCHED
    assert dispatch_event.order.driver_name == "Mike Driver"

@pytest.mark.asyncio
async def test_complete_order_lifecycle(order_service):
    """Test complete order lifecycle from creation to delivery"""
    # 1. Create order
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0,
        markup_percentage=30.0
    )
    event = await order_service.create_order(order)
    order_id = event.order.id
    assert event.order.status == OrderStatus.PENDING_SOURCE
    
    # 2. Source accepts
    event = await order_service.source_respond(order_id, accept=True, notes="Ready", estimated_time=25)
    assert event.order.status == OrderStatus.SOURCE_ACCEPTED
    
    # 3. Buyer accepts
    event = await order_service.buyer_accept(order_id, "Jane Doe", "456 Oak St")
    assert event.order.status == OrderStatus.BUYER_ACCEPTED
    assert event.order.buyer_price == 13.0
    
    # 4. Preparing
    event = await order_service.update_status(order_id, OrderStatus.PREPARING)
    assert event.order.status == OrderStatus.PREPARING
    
    # 5. Ready
    event = await order_service.update_status(order_id, OrderStatus.READY)
    assert event.order.status == OrderStatus.READY
    
    # 6. Dispatched
    event = await order_service.dispatch_order(order_id, "Sarah Driver")
    assert event.order.status == OrderStatus.DISPATCHED
    assert event.order.driver_name == "Sarah Driver"
    
    # 7. In Transit
    event = await order_service.update_status(order_id, OrderStatus.IN_TRANSIT)
    assert event.order.status == OrderStatus.IN_TRANSIT
    
    # 8. Delivered
    event = await order_service.update_status(order_id, OrderStatus.DELIVERED)
    assert event.order.status == OrderStatus.DELIVERED
    
    # Verify final state
    final_order = event.order
    assert final_order.source_name == "Test Source"
    assert final_order.buyer_name == "Jane Doe"
    assert final_order.driver_name == "Sarah Driver"
    assert final_order.buyer_price == 13.0

@pytest.mark.asyncio
async def test_get_all_orders(order_service):
    """Test retrieving all orders"""
    # Create multiple orders
    for i in range(3):
        order = Order(
            source_name=f"Source {i}",
            item_name=f"Item Type {i}",
            source_price=10.0 + i
        )
        await order_service.create_order(order)
    
    # Get all orders
    orders = await order_service.get_all_orders()
    
    assert len(orders) == 3
    assert all('item_name' in order for order in orders)
