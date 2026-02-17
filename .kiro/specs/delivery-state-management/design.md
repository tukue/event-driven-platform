# Delivery State Management - Design Document

## Architecture Overview

### System Components

```
┌─────────────────┐
│  React Frontend │
│  - Delivery UI  │
│  - State Dash   │
└────────┬────────┘
         │ WebSocket + HTTP
         │
┌────────▼────────┐
│   FastAPI       │
│  - Delivery EP  │
│  - State EP     │
│  - Event Batch  │
└────────┬────────┘
         │
┌────────▼────────┐
│  Redis Cloud    │
│  - Orders       │
│  - State Cache  │
│  - Pub/Sub      │
└─────────────────┘
```

## API Design

### 1. Delivery Tracking Endpoint

**Endpoint:** `GET /api/orders/{order_id}/delivery`

**Response:**
```json
{
  "order_id": "uuid",
  "status": "in_transit",
  "driver": {
    "name": "Mike Driver",
    "phone": "+1234567890"
  },
  "delivery": {
    "estimated_arrival": "2026-02-17T11:30:00Z",
    "current_location": "En route",
    "progress_percentage": 75
  },
  "timeline": [
    {"status": "dispatched", "timestamp": "2026-02-17T11:00:00Z"},
    {"status": "in_transit", "timestamp": "2026-02-17T11:15:00Z"}
  ]
}
```

**Error Responses:**
- 404: Order not found
- 400: Order not dispatched yet

### 2. State Management Endpoint

**Endpoint:** `GET /api/state`

**Query Parameters:**
- `include_completed` (bool): Include delivered orders
- `limit` (int): Max orders per status

**Response:**
```json
{
  "timestamp": "2026-02-17T11:00:00Z",
  "statistics": {
    "total_orders": 150,
    "active_deliveries": 12,
    "completed_today": 45,
    "pending_supplier": 3
  },
  "orders_by_status": {
    "pending_supplier": [...],
    "in_transit": [...],
    "ready": [...]
  },
  "active_drivers": [
    {"name": "Mike", "order_id": "uuid", "status": "in_transit"}
  ]
}
```


### 3. Multi-Event Dispatch

**Service Method:** `dispatch_events(events: List[OrderEvent])`

**Implementation:**
```python
async def dispatch_events(self, events: List[OrderEvent], correlation_id: str = None):
    """Dispatch multiple events atomically"""
    correlation_id = correlation_id or str(uuid.uuid4())
    
    try:
        # Publish all events with correlation ID
        for event in events:
            event_data = event.model_dump(mode='json')
            event_data['correlation_id'] = correlation_id
            await self.redis.publish("pizza_orders", json.dumps(event_data))
        
        return {"success": True, "correlation_id": correlation_id}
    except Exception as e:
        # Publish rollback event
        rollback_event = {
            "event_type": "batch.failed",
            "correlation_id": correlation_id,
            "error": str(e)
        }
        await self.redis.publish("pizza_orders", json.dumps(rollback_event))
        raise
```

## Data Models

### DeliveryInfo
```python
class DeliveryInfo(BaseModel):
    estimated_arrival: datetime
    current_location: str
    progress_percentage: int
    driver_phone: Optional[str] = None
```

### SystemState
```python
class SystemState(BaseModel):
    timestamp: datetime
    statistics: Dict[str, int]
    orders_by_status: Dict[str, List[PizzaOrder]]
    active_drivers: List[Dict[str, Any]]
```

### EventBatch
```python
class EventBatch(BaseModel):
    correlation_id: str
    events: List[OrderEvent]
    timestamp: datetime
```

## Service Layer Design

### DeliveryService

```python
class DeliveryService:
    async def get_delivery_info(self, order_id: str) -> DeliveryInfo:
        """Get delivery tracking information"""
        
    async def calculate_progress(self, order: PizzaOrder) -> int:
        """Calculate delivery progress percentage"""
        
    async def estimate_arrival(self, order: PizzaOrder) -> datetime:
        """Estimate delivery arrival time"""
```

### StateService

```python
class StateService:
    async def get_system_state(self, include_completed: bool = False) -> SystemState:
        """Get aggregated system state"""
        
    async def get_statistics(self) -> Dict[str, int]:
        """Calculate system statistics"""
        
    async def get_orders_by_status(self) -> Dict[str, List[PizzaOrder]]:
        """Group orders by status"""
        
    async def get_active_drivers(self) -> List[Dict]:
        """Get list of active drivers"""
```


## Frontend Design

### Component Structure

```
App.jsx
├── DeliveryTracker.jsx       # NEW: Track individual delivery
├── SystemDashboard.jsx       # NEW: System state overview
├── SupplierPanel.jsx
├── CustomerPanel.jsx
├── DispatchPanel.jsx
└── OrdersPanel.jsx
```

### DeliveryTracker Component

**Purpose:** Display real-time delivery tracking for a specific order

**Props:**
- `orderId`: string
- `onClose`: function

**Features:**
- Progress stepper (Dispatched → In Transit → Delivered)
- Driver information card
- Estimated arrival countdown
- Order details summary
- Real-time status updates

**UI Layout:**
```
┌─────────────────────────────────┐
│  Delivery Tracking              │
│  Order #1234                    │
├─────────────────────────────────┤
│  ●━━━━●━━━━○                   │
│  Dispatched  In Transit  Delivered│
├─────────────────────────────────┤
│  Driver: Mike Driver            │
│  Phone: +1234567890             │
│  ETA: 15 minutes                │
├─────────────────────────────────┤
│  Pizza: Margherita              │
│  Address: 123 Main St           │
└─────────────────────────────────┘
```

### SystemDashboard Component

**Purpose:** Display aggregated system state and statistics

**Features:**
- Statistics cards (total orders, active deliveries, etc.)
- Orders grouped by status
- Active drivers list
- Recent activity feed
- Auto-refresh every 5 seconds

**UI Layout:**
```
┌──────────────────────────────────────┐
│  System Dashboard                    │
├──────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │150 │ │ 12 │ │ 45 │ │ 3  │       │
│  │Tot │ │Act │ │Cmp │ │Pnd │       │
│  └────┘ └────┘ └────┘ └────┘       │
├──────────────────────────────────────┤
│  Orders by Status                    │
│  ▸ In Transit (12)                   │
│  ▸ Ready (5)                         │
│  ▸ Preparing (8)                     │
├──────────────────────────────────────┤
│  Active Drivers                      │
│  • Mike - Order #1234 (In Transit)  │
│  • Sarah - Order #5678 (In Transit) │
└──────────────────────────────────────┘
```

## Caching Strategy

### State Endpoint Cache

**Implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedStateService:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 5  # seconds
    
    async def get_cached_state(self):
        now = datetime.utcnow()
        
        if 'state' in self.cache:
            cached_time, cached_data = self.cache['state']
            if (now - cached_time).seconds < self.cache_ttl:
                return cached_data
        
        # Fetch fresh data
        state = await self.fetch_state()
        self.cache['state'] = (now, state)
        return state
```

## Event Correlation

### Correlation ID Pattern

**Purpose:** Track related events across the system

**Implementation:**
```python
# Generate correlation ID
correlation_id = f"batch_{uuid.uuid4()}"

# Add to all events in batch
for event in events:
    event.correlation_id = correlation_id
    
# Use for debugging and tracing
logger.info(f"Processing batch {correlation_id}")
```

