import pytest
from models import Order, OrderStatus, OrderEvent
from datetime import datetime

# These tests don't need Redis - they're pure unit tests
pytestmark = pytest.mark.unit

def test_order_creation():
    """Test creating an order"""
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0,
        markup_percentage=30.0
    )
    
    assert order.source_name == "Test Source"
    assert order.item_name == "Test Item"
    assert order.source_price == 10.0
    assert order.markup_percentage == 30.0

def test_order_with_buyer():
    """Test order with buyer details"""
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0,
        markup_percentage=30.0,
        buyer_name="John Doe",
        delivery_address="123 Main St",
        buyer_price=13.0
    )
    
    assert order.buyer_name == "John Doe"
    assert order.delivery_address == "123 Main St"
    assert order.buyer_price == 13.0

def test_order_event_creation():
    """Test creating an order event"""
    order = Order(
        source_name="Test Source",
        item_name="Test Item",
        source_price=10.0
    )
    
    event = OrderEvent(
        event_type="order.created",
        order=order,
        timestamp=datetime.utcnow()
    )
    
    assert event.event_type == "order.created"
    assert event.order.item_name == "Test Item"
    assert isinstance(event.timestamp, datetime)

def test_order_status_enum():
    """Test order status enum values"""
    assert OrderStatus.PENDING_SOURCE == "pending_source"
    assert OrderStatus.SOURCE_ACCEPTED == "source_accepted"
    assert OrderStatus.BUYER_ACCEPTED == "buyer_accepted"
    assert OrderStatus.PREPARING == "preparing"
    assert OrderStatus.READY == "ready"
    assert OrderStatus.DISPATCHED == "dispatched"
    assert OrderStatus.IN_TRANSIT == "in_transit"
    assert OrderStatus.DELIVERED == "delivered"
