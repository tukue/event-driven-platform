from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid

class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING_SOURCE = "pending_source"
    SOURCE_ACCEPTED = "source_accepted"
    SOURCE_REJECTED = "source_rejected"
    BUYER_ACCEPTED = "buyer_accepted"
    PREPARING = "preparing"
    READY = "ready"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(BaseModel):
    id: Optional[str] = None
    tracking_id: Optional[str] = None  # Human-readable tracking ID (e.g., "ORD-2026-A3F7B2C1")
    source_tracking_id: Optional[str] = None  # Source-specific tracking ID
    source_name: str
    item_name: str
    source_price: float
    buyer_price: Optional[float] = None
    markup_percentage: float = 30.0
    status: OrderStatus = OrderStatus.CREATED
    buyer_name: Optional[str] = None
    delivery_address: Optional[str] = None
    driver_name: Optional[str] = None
    estimated_delivery_time: Optional[int] = None  # minutes
    source_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class OrderEvent(BaseModel):
    """Versioned event envelope emitted by the order service."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = 1
    event_type: str
    order: Order
    order_id: Optional[str] = None
    timestamp: datetime
    correlation_id: Optional[str] = None

    @model_validator(mode="after")
    def populate_order_id(self):
        if self.order_id is None:
            self.order_id = self.order.id
        elif self.order.id and self.order_id != self.order.id:
            raise ValueError("order_id must match order.id")
        return self

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
    buyer_name: Optional[str] = None
    progress_percentage: int
    estimated_arrival_minutes: Optional[int] = None
    timeline: list[DeliveryTimeline]
    current_stage: str

class SystemStatistics(BaseModel):
    """System-wide statistics"""
    total_orders: int
    active_deliveries: int
    completed_today: int
    pending_source: int
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
