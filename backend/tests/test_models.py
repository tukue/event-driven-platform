import pytest
from models import PizzaOrder, OrderStatus, OrderEvent
from datetime import datetime

# These tests don't need Redis - they're pure unit tests
pytestmark = pytest.mark.unit

def test_pizza_order_creation():
    """Test creating a pizza order"""
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0,
        markup_percentage=30.0
    )
    
    assert order.supplier_name == "Test Pizza"
    assert order.pizza_name == "Margherita"
    assert order.supplier_price == 10.0
    assert order.markup_percentage == 30.0

def test_pizza_order_with_customer():
    """Test order with customer details"""
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0,
        markup_percentage=30.0,
        customer_name="John Doe",
        delivery_address="123 Main St",
        customer_price=13.0
    )
    
    assert order.customer_name == "John Doe"
    assert order.delivery_address == "123 Main St"
    assert order.customer_price == 13.0

def test_order_event_creation():
    """Test creating an order event"""
    order = PizzaOrder(
        supplier_name="Test Pizza",
        pizza_name="Margherita",
        supplier_price=10.0
    )
    
    event = OrderEvent(
        event_type="order.created",
        order=order,
        timestamp=datetime.utcnow()
    )
    
    assert event.event_type == "order.created"
    assert event.order.pizza_name == "Margherita"
    assert isinstance(event.timestamp, datetime)

def test_order_status_enum():
    """Test order status enum values"""
    assert OrderStatus.PENDING_SUPPLIER == "pending_supplier"
    assert OrderStatus.SUPPLIER_ACCEPTED == "supplier_accepted"
    assert OrderStatus.CUSTOMER_ACCEPTED == "customer_accepted"
    assert OrderStatus.PREPARING == "preparing"
    assert OrderStatus.READY == "ready"
    assert OrderStatus.DISPATCHED == "dispatched"
    assert OrderStatus.IN_TRANSIT == "in_transit"
    assert OrderStatus.DELIVERED == "delivered"
