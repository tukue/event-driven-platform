# Integration Tests

Automated tests to validate backend-frontend communication and identify issues quickly.

## Quick Start

### Prerequisites
- Backend running on `http://localhost:8000`
- Redis connected and services initialized

### Run All Tests

**Windows:**
```powershell
.\run-integration-tests.ps1
```

**Linux/Mac:**
```bash
chmod +x run-integration-tests.sh
./run-integration-tests.sh
```

## Test Suites

### Backend Integration Tests
Location: `backend/tests/test_backend_frontend_integration.py`

Tests:
- ✅ Health endpoint
- ✅ Service initialization
- ✅ Order creation flow
- ✅ Supplier workflow (accept/reject)
- ✅ Customer workflow (acceptance)
- ✅ Dispatch workflow
- ✅ Tracking ID lookup
- ✅ System state endpoint
- ✅ CORS configuration
- ✅ Error handling

Run individually:
```bash
cd backend
python -m pytest tests/test_backend_frontend_integration.py -v
```

### Frontend Integration Tests
Location: `test-integration.js`

Tests:
- ✅ Backend health check
- ✅ Fetch orders
- ✅ Create order
- ✅ CORS headers

Run individually:
```bash
node test-integration.js
```

## Common Issues

### Backend Not Running
```
❌ Backend is not running on port 8000
```
**Solution:** Start backend with `cd backend && uvicorn main:app --reload`

### Services Not Initialized
```
❌ order_service should be initialized
```
**Solution:** Check Redis connection. Services fail if Redis doesn't connect.

### CORS Errors
```
❌ CORS test failed
```
**Solution:** Verify `allow_origins` in `backend/main.py` includes your frontend port (5173 or 5174)

### WebSocket Connection Failed
```
❌ WebSocket connection timeout
```
**Solution:** Ensure Redis client is connected. WebSocket requires Redis pubsub.

## Debugging

### Check Backend Startup
Look for these messages when starting backend:
```
🔵 Starting up...
🔵 Connecting to Redis...
✅ Redis connected
🔵 Initializing services...
✅ Services initialized
✅ order_service is: <services.order_service.OrderService object at 0x...>
✅ Startup complete!
```

If you see errors or missing messages, check:
1. Redis credentials in `backend/.env`
2. Redis server is accessible
3. No firewall blocking Redis port

### Test Individual Endpoints

**Health check:**
```bash
curl http://localhost:8000/health
```

**Create order:**
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"supplier_name":"Test","pizza_name":"Margherita","supplier_price":10,"markup_percentage":20}'
```

**Get orders:**
```bash
curl http://localhost:8000/api/orders
```

## CI/CD Integration

Add to your CI pipeline:
```yaml
- name: Run Integration Tests
  run: |
    # Start backend
    cd backend && uvicorn main:app &
    sleep 5
    
    # Run tests
    ./run-integration-tests.sh
```

## Adding New Tests

### Backend Test
Add to `backend/tests/test_backend_frontend_integration.py`:
```python
@pytest.mark.asyncio
async def test_my_feature():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/my-endpoint")
        assert response.status_code == 200
```

### Frontend Test
Add to `test-integration.js`:
```javascript
async function testMyFeature() {
  console.log('🔍 Testing my feature...');
  try {
    const response = await fetch(`${API_BASE}/api/my-endpoint`);
    const data = await response.json();
    console.log('✅ Feature test passed');
    return true;
  } catch (error) {
    console.error('❌ Feature test failed:', error.message);
    return false;
  }
}
```
