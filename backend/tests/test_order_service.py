import pytest
from models import PizzaOrder, OrderStatus

@pytest.mark.asyncio
async def test_create_order(order_service):
    """Test creating an order"""
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0,
        markup_percentage=30.0
    )
    
    event = await order_service.create_order(order)
    
    assert event.event_type == "order.created"
    assert event.order.id is not None
    assert event.order.status == OrderStatus.PENDING_SUPPLIER
    assert event.order.created_at is not None

@pytest.mark.asyncio
async def test_supplier_accept_order(order_service):
    """Test supplier accepting an order"""
    # Create order
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Supplier accepts
    accept_event = await order_service.supplier_respond(
        order_id=order_id,
        accept=True,
        notes="Fresh ingredients",
        estimated_time=30
    )
    
    assert accept_event.event_type == "order.supplier_accepted"
    assert accept_event.order.status == OrderStatus.SUPPLIER_ACCEPTED
    assert accept_event.order.supplier_notes == "Fresh ingredients"
    assert accept_event.order.estimated_delivery_time == 30

@pytest.mark.asyncio
async def test_supplier_reject_order(order_service):
    """Test supplier rejecting an order"""
    # Create order
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Supplier rejects
    reject_event = await order_service.supplier_respond(
        order_id=order_id,
        accept=False,
        notes="Out of ingredients"
    )
    
    assert reject_event.event_type == "order.supplier_rejected"
    assert reject_event.order.status == OrderStatus.SUPPLIER_REJECTED
    assert reject_event.order.supplier_notes == "Out of ingredients"

@pytest.mark.asyncio
async def test_customer_accept_order(order_service):
    """Test customer accepting an order"""
    # Create and supplier accepts order
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0,
        markup_percentage=30.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    await order_service.supplier_respond(order_id, accept=True)
    
    # Customer accepts
    customer_event = await order_service.customer_accept(
        order_id=order_id,
        customer_name="John Doe",
        delivery_address="123 Main St"
    )
    
    assert customer_event.event_type == "order.customer_accepted"
    assert customer_event.order.status == OrderStatus.CUSTOMER_ACCEPTED
    assert customer_event.order.customer_name == "John Doe"
    assert customer_event.order.delivery_address == "123 Main St"
    assert customer_event.order.customer_price == 13.0  # 10 + 30%

@pytest.mark.asyncio
async def test_customer_accept_without_supplier_fails(order_service):
    """Test customer cannot accept before supplier"""
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    # Should fail
    with pytest.raises(ValueError, match="must be accepted by supplier first"):
        await order_service.customer_accept(
            order_id=order_id,
            customer_name="John Doe",
            delivery_address="123 Main St"
        )

@pytest.mark.asyncio
async def test_dispatch_order(order_service):
    """Test dispatching an order"""
    # Create full order flow
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0
    )
    create_event = await order_service.create_order(order)
    order_id = create_event.order.id
    
    await order_service.supplier_respond(order_id, accept=True)
    await order_service.customer_accept(order_id, "John Doe", "123 Main St")
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
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0,
        markup_percentage=30.0
    )
    event = await order_service.create_order(order)
    order_id = event.order.id
    assert event.order.status == OrderStatus.PENDING_SUPPLIER
    
    # 2. Supplier accepts
    event = await order_service.supplier_respond(order_id, accept=True, notes="Ready", estimated_time=25)
    assert event.order.status == OrderStatus.SUPPLIER_ACCEPTED
    
    # 3. Customer accepts
    event = await order_service.customer_accept(order_id, "Jane Doe", "456 Oak St")
    assert event.order.status == OrderStatus.CUSTOMER_ACCEPTED
    assert event.order.customer_price == 13.0
    
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
    assert final_order.supplier_name == "Test Pizza"
    assert final_order.customer_name == "Jane Doe"
    assert final_order.driver_name == "Sarah Driver"
    assert final_order.customer_price == 13.0

@pytest.mark.asyncio
async def test_get_all_orders(order_service):
    """Test retrieving all orders"""
    # Create multiple orders
    for i in range(3):
        order = PizzaOrder(
            supplier_name=f"Pizza {i}",
            pizza_name=f"Pizza Type {i}",
            supplier_price=10.0 + i
        )
        await order_service.create_order(order)
    
    # Get all orders
    orders = await order_service.get_all_orders()
    
    assert len(orders) == 3
    assert all('pizza_name' in order for order in orders)
