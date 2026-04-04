# Backend-Frontend Connection Fix

## Issue
Frontend on port 5174 cannot connect to backend on port 8000.

## Root Causes
1. CORS configuration missing port 5174
2. Backend might not be fully started
3. Possible network/firewall issues

## Quick Fix Steps

### 1. Verify Backend is Running
```bash
# Check if backend is listening on port 8000
curl http://localhost:8000/docs
```

Expected: Should return HTML (Swagger UI)

### 2. Verify CORS Configuration
Backend `main.py` should have:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Test Backend Directly
```bash
cd backend
python simple_test.py
```

Expected output:
```
1. Testing /docs endpoint...
   Status: 200
2. Testing /api/orders GET...
   Status: 200
   Orders: 0
3. Testing /api/orders POST...
   Status: 200
   ✅ Success!
```

### 4. Check Browser Console
1. Open http://localhost:5174
2. Press F12 to open DevTools
3. Go to Console tab
4. Try creating an order
5. Look for errors (especially CORS errors)

### 5. Check Network Tab
1. In DevTools, go to Network tab
2. Try creating an order
3. Look for the POST request to `/api/orders`
4. Check:
   - Status code (should be 200)
   - Response (should have order data)
   - Any error messages

## Common Issues & Solutions

### Issue 1: CORS Error
**Symptom:** Console shows "CORS policy" error

**Solution:**
1. Stop backend (CTRL+C)
2. Verify `main.py` has port 5174 in CORS origins
3. Restart backend: `uvicorn main:app --reload`

### Issue 2: Connection Refused
**Symptom:** "Failed to fetch" or "Connection refused"

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/docs`
2. Check no firewall is blocking port 8000
3. Try accessing backend directly in browser

### Issue 3: Request Timeout
**Symptom:** Request hangs forever

**Solution:**
1. Check backend terminal for errors
2. Verify Redis is connected (should see "✅ Redis connected")
3. Restart backend

### Issue 4: 500 Internal Server Error
**Symptom:** Backend returns 500 error

**Solution:**
1. Check backend terminal for error stack trace
2. Verify Redis connection
3. Check all required fields are filled in form

## Manual Test

### Test 1: Backend Health
```bash
curl http://localhost:8000/docs
```
Should return HTML

### Test 2: Get Orders
```bash
curl http://localhost:8000/api/orders
```
Should return JSON array (might be empty)

### Test 3: Create Order
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_name": "Test",
    "pizza_name": "Test Pizza",
    "supplier_price": 10.0,
    "markup_percentage": 30
  }'
```
Should return order data with ID

### Test 4: WebSocket
Open browser console and run:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('✅ WebSocket connected');
ws.onerror = (e) => console.error('❌ WebSocket error:', e);
ws.onmessage = (e) => console.log('📨 Message:', e.data);
```

## Restart Everything

If nothing works, restart everything:

```bash
# 1. Stop backend (CTRL+C in backend terminal)

# 2. Stop frontend (CTRL+C in frontend terminal)

# 3. Start backend
cd backend
uvicorn main:app --reload

# Wait for "Application startup complete"

# 4. Start frontend (in new terminal)
cd frontend
npm run dev

# 5. Open browser to the URL shown (probably http://localhost:5174)
```

## Verification Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 5174 (or 5173)
- [ ] Backend shows "✅ Redis connected"
- [ ] Backend shows "✅ Services initialized"
- [ ] Can access http://localhost:8000/docs
- [ ] Can access http://localhost:5174
- [ ] No CORS errors in browser console
- [ ] WebSocket shows "🟢 Connected" in UI

## Still Not Working?

1. Check backend terminal for error messages
2. Check browser console for error messages
3. Try the manual curl tests above
4. Verify Redis is running: `python backend/test_redis.py`
5. Check if another process is using port 8000 or 5174

## Success Indicators

When working correctly, you should see:

**Backend Terminal:**
```
INFO:     Application startup complete.
🔵 Received order creation request: Test Pizza
📝 Creating order: Test Pizza from Test
✅ Order created and published: [uuid]
🟢 Order created successfully: [uuid]
```

**Browser:**
- Alert: "✅ Order created successfully!"
- Order appears in the orders list
- WebSocket indicator shows "🟢 Connected"

**Browser Console:**
```
Submitting order: {supplier_name: "Test", ...}
Response status: 200
Order created: {event_type: "order.created", ...}
```
