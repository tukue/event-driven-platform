"""
Test data fixtures for Kafka producer/consumer tests.

Provides realistic order event payloads that mirror the shapes produced by
OrderService._publish_event, covering every stage of the order lifecycle.
"""

from datetime import datetime, timedelta
import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _tracking_id() -> str:
    return f"ORD-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"


def _source_tracking_id(prefix: str = "QM") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _iso(dt: datetime | None = None) -> str:
    return (dt or datetime.utcnow()).isoformat()


# ---------------------------------------------------------------------------
# Single order event factories
# ---------------------------------------------------------------------------

def make_order_created_event(
    order_id: str | None = None,
    item_name: str = "Electronics Bundle",
    source_name: str = "Quick Mart",
    source_price: float = 49.99,
    markup_percentage: float = 30.0,
    timestamp: datetime | None = None,
) -> dict:
    oid = order_id or _uuid()
    ts = timestamp or datetime.utcnow()
    return {
        "event_type": "order.created",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": source_name,
            "item_name": item_name,
            "source_price": source_price,
            "buyer_price": None,
            "markup_percentage": markup_percentage,
            "status": "pending_source",
            "buyer_name": None,
            "delivery_address": None,
            "driver_name": None,
            "estimated_delivery_time": None,
            "source_notes": None,
            "created_at": _iso(ts),
            "updated_at": _iso(ts),
        },
        "timestamp": _iso(ts),
        "correlation_id": None,
    }


def make_source_accepted_event(
    order_id: str | None = None,
    source_price: float = 49.99,
    estimated_time: int = 30,
) -> dict:
    oid = order_id or _uuid()
    return {
        "event_type": "order.source_accepted",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": "Quick Mart",
            "item_name": "Electronics Bundle",
            "source_price": source_price,
            "buyer_price": None,
            "markup_percentage": 30.0,
            "status": "source_accepted",
            "buyer_name": None,
            "delivery_address": None,
            "driver_name": None,
            "estimated_delivery_time": estimated_time,
            "source_notes": "In stock, ready to ship",
            "created_at": _iso(),
            "updated_at": _iso(),
        },
        "timestamp": _iso(),
        "correlation_id": None,
    }


def make_source_rejected_event(order_id: str | None = None) -> dict:
    oid = order_id or _uuid()
    return {
        "event_type": "order.source_rejected",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": "Quick Mart",
            "item_name": "Electronics Bundle",
            "source_price": 49.99,
            "buyer_price": None,
            "markup_percentage": 30.0,
            "status": "source_rejected",
            "buyer_name": None,
            "delivery_address": None,
            "driver_name": None,
            "estimated_delivery_time": None,
            "source_notes": "Out of stock",
            "created_at": _iso(),
            "updated_at": _iso(),
        },
        "timestamp": _iso(),
        "correlation_id": None,
    }


def make_buyer_accepted_event(
    order_id: str | None = None,
    buyer_name: str = "Alice Johnson",
    delivery_address: str = "123 Main St, Apt 4B",
) -> dict:
    oid = order_id or _uuid()
    return {
        "event_type": "order.buyer_accepted",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": "Quick Mart",
            "item_name": "Electronics Bundle",
            "source_price": 49.99,
            "buyer_price": 64.99,
            "markup_percentage": 30.0,
            "status": "buyer_accepted",
            "buyer_name": buyer_name,
            "delivery_address": delivery_address,
            "driver_name": None,
            "estimated_delivery_time": 30,
            "source_notes": "In stock, ready to ship",
            "created_at": _iso(),
            "updated_at": _iso(),
        },
        "timestamp": _iso(),
        "correlation_id": None,
    }


def make_dispatched_event(
    order_id: str | None = None,
    driver_name: str = "John Smith",
) -> dict:
    oid = order_id or _uuid()
    return {
        "event_type": "order.dispatched",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": "Quick Mart",
            "item_name": "Electronics Bundle",
            "source_price": 49.99,
            "buyer_price": 64.99,
            "markup_percentage": 30.0,
            "status": "dispatched",
            "buyer_name": "Alice Johnson",
            "delivery_address": "123 Main St, Apt 4B",
            "driver_name": driver_name,
            "estimated_delivery_time": 30,
            "source_notes": "In stock, ready to ship",
            "created_at": _iso(),
            "updated_at": _iso(),
        },
        "timestamp": _iso(),
        "correlation_id": None,
    }


def make_delivered_event(order_id: str | None = None) -> dict:
    oid = order_id or _uuid()
    return {
        "event_type": "order.delivered",
        "order": {
            "id": oid,
            "tracking_id": _tracking_id(),
            "source_tracking_id": _source_tracking_id(),
            "source_name": "Quick Mart",
            "item_name": "Electronics Bundle",
            "source_price": 49.99,
            "buyer_price": 64.99,
            "markup_percentage": 30.0,
            "status": "delivered",
            "buyer_name": "Alice Johnson",
            "delivery_address": "123 Main St, Apt 4B",
            "driver_name": "John Smith",
            "estimated_delivery_time": 30,
            "source_notes": "In stock, ready to ship",
            "created_at": _iso(),
            "updated_at": _iso(),
        },
        "timestamp": _iso(),
        "correlation_id": None,
    }


def make_batch_rollback_event(correlation_id: str = "batch-test-123") -> dict:
    return {
        "event_type": "batch.rollback",
        "correlation_id": correlation_id,
        "errors": ["Failed to publish event: Kafka broker unreachable"],
        "timestamp": _iso(),
    }


# ---------------------------------------------------------------------------
# Composite sequences — a full lifecycle for one order
# ---------------------------------------------------------------------------

def make_full_lifecycle_events(order_id: str | None = None) -> list[dict]:
    oid = order_id or _uuid()
    return [
        make_order_created_event(order_id=oid),
        make_source_accepted_event(order_id=oid),
        make_buyer_accepted_event(order_id=oid),
        make_dispatched_event(order_id=oid),
        make_delivered_event(order_id=oid),
    ]


# ---------------------------------------------------------------------------
# Bulk test data
# ---------------------------------------------------------------------------

BULK_SOURCES = ["Quick Mart", "Fresh Foods", "Speed Supplies", "Urban Goods", "Prime Picks"]
BULK_ITEMS = ["Electronics Bundle", "Kitchen Set", "Book Collection", "Fitness Kit", "Garden Tools"]
BULK_DRIVERS = ["John Smith", "Maria Garcia", "Ahmed Khan", "Lisa Chen", "Carlos Rodriguez"]
BULK_BUYERS = ["Alice Johnson", "Bob Williams", "Carol Davis", "David Martinez", "Emma Wilson"]
BULK_ADDRESSES = [
    "123 Main St, Apt 4B",
    "456 Oak Avenue",
    "789 Pine Road, Suite 200",
    "321 Elm Street",
    "654 Maple Drive",
]


def make_bulk_events(count: int = 20) -> list[dict]:
    """Generate a batch of order.created events with varied data"""
    events = []
    for i in range(count):
        events.append(
            make_order_created_event(
                order_id=_uuid(),
                item_name=BULK_ITEMS[i % len(BULK_ITEMS)],
                source_name=BULK_SOURCES[i % len(BULK_SOURCES)],
                source_price=round(10.0 + (i * 3.7), 2),
            )
        )
    return events
