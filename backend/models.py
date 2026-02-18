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
    tracking_id: Optional[str] = None  # Human-readable tracking ID (e.g., "PIZZA-2024-001234")
    supplier_tracking_id: Optional[str] = None  # Supplier-specific tracking ID
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
    correlation_id: Optional[str] = None

class DeliveryTimeline(BaseModel):
    """Timeline entry for delivery tracking"""
    stage: str
    timestamp: Optional[str] = None
    completed: bool

class DeliveryInfo(BaseModel):
    """Delivery tracking information"""
    order_id: str
    status: str
    driver_name: Optional[str] = None
    delivery_address: Optional[str] = None
    customer_name: Optional[str] = None
    progress_percentage: int
    estimated_arrival_minutes: Optional[int] = None
    timeline: list[DeliveryTimeline]
    current_stage: str

class SystemStatistics(BaseModel):
    """System-wide statistics"""
    total_orders: int
    active_deliveries: int
    completed_today: int
    pending_supplier: int
    preparing: int
    ready: int
    dispatched: int
    in_transit: int
    delivered: int

class ActiveDriver(BaseModel):
    """Active driver information"""
    driver_name: str
    order_id: Optional[str] = None
    status: str
    assigned_at: Optional[datetime] = None

class SystemState(BaseModel):
    """Complete system state"""
    statistics: SystemStatistics
    orders_by_status: dict[str, list[dict]]
    active_drivers: list[ActiveDriver]
    last_updated: datetime

class EventBatch(BaseModel):
    """Batch of events to be processed atomically"""
    correlation_id: str
    events: list[dict]
    created_at: datetime

class BatchResult(BaseModel):
    """Result of batch event processing"""
    correlation_id: str
    success: bool
    processed_count: int
    failed_count: int
    errors: list[str] = []
    timestamp: datetime
