# Pizza Delivery Marketplace - Technical Documentation

## Overview

An event-driven pizza delivery platform built with React, FastAPI, and Redis Cloud. The system connects suppliers, customers, and dispatch services through real-time WebSocket communication and Redis Pub/Sub messaging.

## Architecture

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- Redis Cloud (data storage + pub/sub messaging)
- WebSocket (real-time communication)
- Pydantic (data validation)

**Frontend:**
- React 18
- Vite (build tool)
- Native WebSocket API
- Component-based architecture

### System Architecture

```
┌─────────────┐         WebSocket          ┌──────────────┐
│   React     │◄──────────────────────────►│   FastAPI    │
│  Frontend   │                             │   Backend    │
└─────────────┘                             └──────┬───────┘
                                                   │
                                                   │ Redis Client
                                                   │
                                            ┌──────▼───────┐
                                            │ Redis Cloud  │
                                            │  - Storage   │
                                            │  - Pub/Sub   │
                                            └──────────────┘
```

## Business Flow

### Order Lifecycle

1. **Order Creation** (`pending_supplier`)
   - Supplier creates pizza order with base price and markup percentage
   - Order stored in Redis with unique ID
   - Event published: `order.created`

2. **Supplier Response** (`supplier_accepted` / `supplier_rejected`)
   - Supplier reviews pending order
   - Can accept with notes and estimated delivery time
   - Can reject with reason
   - Events: `order.supplier_accepted` or `order.supplier_rejected`

3. **Customer Acceptance** (`customer_accepted`)
   - Customer views supplier-accepted orders
   - Sees pricing breakdown (base + markup)
   - Provides delivery details
   - System calculates final customer price
   - Event: `order.customer_accepted`

4. **Preparation** (`preparing` → `ready`)
   - Supplier starts preparing pizza
   - Marks as ready when complete
   - Events: `order.preparing`, `order.ready`

5. **Dispatch** (`dispatched` → `in_transit`)
   - Dispatch assigns driver to ready order
   - Driver picks up order
   - Event: `order.dispatched`, `order.in_transit`

6. **Delivery** (`delivered`)
   - Driver delivers to customer
   - Order marked as complete
   - Event: `order.delivered`

## Data Models

### PizzaOrder

```python
{
    "id": "uuid",
    "supplier_name": "string",
    "pizza_name": "string",
    "supplier_price": float,
    "customer_price": float | null,
    "markup_percentage": float (default: 30.0),
    "status": OrderStatus,
    "customer_name": "string" | null,
    "delivery_address": "string" | null,
    "driver_name": "string" | null,
    "estimated_delivery_time": int | null,  # minutes
    "supplier_notes": "string" | null,
    "created_at": datetime,
    "updated_at": datetime
}
```

### Order Statuses

| Status | Description |
|--------|-------------|
| `pending_supplier` | Awaiting supplier response |
| `supplier_accepted` | Supplier confirmed availability |
| `supplier_rejected` | Supplier declined order |
| `customer_accepted` | Customer placed order with markup |
| `preparing` | Pizza being prepared |
| `ready` | Ready for pickup |
| `dispatched` | Driver assigned |
| `in_transit` | Out for delivery |
| `delivered` | Successfully delivered |
| `cancelled` | Order cancelled |

## API Endpoints

### Orders

**Create Order**
```http
POST /api/orders
Content-Type: application/json

{
    "supplier_name": "Pizza Palace",
    "pizza_name": "Margherita",
    "supplier_price": 10.00,
    "markup_percentage": 30
}
```

**Supplier Response**
```http
POST /api/orders/{order_id}/supplier-respond?accept=true&notes=Fresh%20ingredients&estimated_time=30
```

**Customer Accept**
```http
POST /api/orders/{order_id}/customer-accept?customer_name=John%20Doe&delivery_address=123%20Main%20St
```

**Dispatch Order**
```http
POST /api/orders/{order_id}/dispatch?driver_name=Mike%20Driver
```

**Update Status**
```http
POST /api/orders/{order_id}/status?status=preparing
```

**Get All Orders**
```http
GET /api/orders
```

### WebSocket

**Connect**
```javascript
ws://localhost:8000/ws
```

**Event Format**
```json
{
    "event_type": "order.supplier_accepted",
    "order": { /* PizzaOrder object */ },
    "timestamp": "2026-02-17T10:30:00Z"
}
```

## Redis Integration

### Data Storage

Orders stored as key-value pairs:
```
Key: order:{uuid}
Value: JSON serialized PizzaOrder
```

### Pub/Sub Channel

**Channel:** `pizza_orders`

**Published Events:**
- `order.created`
- `order.supplier_accepted`
- `order.supplier_rejected`
- `order.customer_accepted`
- `order.preparing`
- `order.ready`
- `order.dispatched`
- `order.in_transit`
- `order.delivered`

### Connection Configuration

```python
# backend/.env
REDIS_HOST=your-redis-host.cloud.redislabs.com
REDIS_PORT=your-port
REDIS_USERNAME=default
REDIS_PASSWORD=your-password
REDIS_DB=0
```

## Frontend Components

### Component Structure

```
App.jsx
├── SupplierPanel.jsx      # Create orders, accept/reject
├── CustomerPanel.jsx      # View and accept orders
├── DispatchPanel.jsx      # Assign drivers
└── OrdersPanel.jsx        # View all orders with status updates
```

### Real-Time Updates

**WebSocket Hook** (`useWebSocket.js`)
- Establishes WebSocket connection
- Auto-reconnects on disconnect
- Parses incoming events
- Updates React state

**State Management**
- Orders stored in App component state
- Updates propagated to child components
- Real-time synchronization across all panels

## Event-Driven Architecture

### Event Flow

```
Action (UI) → API Call → Service Layer → Redis Storage
                              ↓
                        Publish Event
                              ↓
                        Redis Pub/Sub
                              ↓
                        WebSocket Server
                              ↓
                    All Connected Clients
                              ↓
                        UI Updates
```

### Benefits

1. **Real-time Updates**: All clients see changes instantly
2. **Decoupled Components**: Services communicate via events
3. **Scalability**: Multiple backend instances can share Redis
4. **Persistence**: Orders survive server restarts
5. **Audit Trail**: All state changes tracked as events

## Setup & Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- Redis Cloud account

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure Redis
copy .env.example .env
# Edit .env with your Redis credentials

# Test connection
python test_redis.py

# Start server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Access Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing

### Test Redis Connection

```bash
cd backend
python test_redis.py
```

### Diagnose Connection Issues

```bash
python diagnose_redis.py
```

### Inspect Stored Data

```bash
python inspect_redis.py
```

### Manual Testing Flow

1. Open app in 3 browser windows (Supplier, Customer, Dispatch)
2. **Supplier Window**: Create order
3. **Supplier Window**: Accept order with notes
4. **Customer Window**: Accept order with delivery details
5. **Supplier Window**: Mark as preparing → ready
6. **Dispatch Window**: Assign driver → dispatch
7. **Dispatch Window**: Mark in transit → delivered
8. Verify real-time updates across all windows

## File Structure

```
event-driven-platform/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings & environment
│   ├── models.py               # Pydantic models
│   ├── redis_client.py         # Redis connection wrapper
│   ├── services/
│   │   └── order_service.py    # Business logic
│   ├── test_redis.py           # Connection test
│   ├── diagnose_redis.py       # Connection diagnostics
│   ├── inspect_redis.py        # Data inspection
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables
│   └── .env.example            # Environment template
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main application
│   │   ├── main.jsx            # Entry point
│   │   ├── components/
│   │   │   ├── SupplierPanel.jsx
│   │   │   ├── CustomerPanel.jsx
│   │   │   ├── DispatchPanel.jsx
│   │   │   └── OrdersPanel.jsx
│   │   └── hooks/
│   │       └── useWebSocket.js # WebSocket hook
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── README.md
├── DOCUMENTATION.md
└── .gitignore
```

## Key Features Implemented

### ✅ Event-Driven Architecture
- Redis Pub/Sub for event broadcasting
- Real-time WebSocket communication
- Decoupled service architecture

### ✅ Multi-Role System
- Supplier: Create and manage orders
- Customer: Browse and purchase with markup
- Dispatch: Assign drivers and track delivery

### ✅ Order Management
- Complete order lifecycle tracking
- Status transitions with validation
- Supplier acceptance/rejection workflow
- Customer pricing with configurable markup

### ✅ Real-Time Updates
- WebSocket connection with auto-reconnect
- Live order status updates
- Multi-window synchronization

### ✅ Data Persistence
- Redis Cloud integration
- Order storage and retrieval
- Event history tracking

### ✅ Developer Tools
- Connection testing utilities
- Data inspection scripts
- Diagnostic tools

## Configuration

### Environment Variables

**Backend** (`backend/.env`)
```env
REDIS_HOST=your-redis-host
REDIS_PORT=13869
REDIS_USERNAME=default
REDIS_PASSWORD=your-password
REDIS_DB=0
```

### CORS Configuration

Backend allows connections from:
- http://localhost:5173 (Vite dev server)
- http://localhost:3000 (Alternative port)

## Security Considerations

### Current Implementation
- Redis authentication with username/password
- CORS restrictions on backend
- Environment variables for sensitive data

### Production Recommendations
1. Use HTTPS/WSS for all connections
2. Implement JWT authentication
3. Add rate limiting
4. Validate all user inputs
5. Use Redis ACLs for fine-grained permissions
6. Enable Redis TLS/SSL
7. Implement proper error handling
8. Add logging and monitoring

## Performance Considerations

### Current Setup
- Single Redis instance
- In-memory data storage
- WebSocket for real-time updates

### Scaling Recommendations
1. Redis Cluster for high availability
2. Load balancer for multiple backend instances
3. CDN for frontend assets
4. Database indexing for large datasets
5. Caching layer for frequently accessed data
6. Message queue for async processing

## Troubleshooting

### Redis Connection Issues

**Problem:** "invalid username-password pair"
- Verify credentials in `.env`
- Check username (usually "default" for Redis Cloud)
- Ensure password is copied correctly

**Problem:** Connection timeout
- Whitelist your IP in Redis Cloud Security settings
- Check firewall rules
- Verify Redis instance is running

### WebSocket Issues

**Problem:** "🔴 Disconnected" status
- Ensure backend is running
- Check backend logs for errors
- Verify WebSocket endpoint is accessible

### Frontend Issues

**Problem:** Orders not updating
- Check browser console for errors
- Verify WebSocket connection status
- Ensure backend is publishing events

## Future Enhancements

### Potential Features
- [ ] User authentication and authorization
- [ ] Order history and analytics
- [ ] Payment integration
- [ ] SMS/Email notifications
- [ ] Driver location tracking
- [ ] Rating and review system
- [ ] Multi-restaurant support
- [ ] Order scheduling
- [ ] Promotional codes and discounts
- [ ] Admin dashboard

### Technical Improvements
- [ ] Unit and integration tests
- [ ] API documentation with OpenAPI
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Monitoring and alerting
- [ ] Database migrations
- [ ] API versioning
- [ ] GraphQL API option

## License

This project is for educational purposes.

## Support

For issues or questions:
1. Check this documentation
2. Review backend logs
3. Test Redis connection with provided tools
4. Inspect stored data with `inspect_redis.py`

---

**Last Updated:** February 17, 2026
**Version:** 1.0.0
