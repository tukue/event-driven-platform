from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING_SUPPLIER = "pending_supplier"
    SUPPLIER_ACCEPTED = "supplier_accepted"
    SUPPLIER_REJECTED = "supplier_rejected"
    CUSTOMER_ACCEPTED = "customer_accepted"
    PREPARING = "preparing"
    READY = "ready"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PizzaOrder(BaseModel):
    id: Optional[str] = None
    supplier_name: str
    pizza_name: str
    supplier_price: float
    customer_price: Optional[float] = None
    markup_percentage: float = 30.0
    status: OrderStatus = OrderStatus.CREATED
    customer_name: Optional[str] = None
    delivery_address: Optional[str] = None
    driver_name: Optional[str] = None
    estimated_delivery_time: Optional[int] = None  # minutes
    supplier_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class OrderEvent(BaseModel):
    event_type: str
    order: PizzaOrder
    timestamp: datetime
