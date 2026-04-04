# Troubleshooting Order Creation Issue

## Problem
Order creation not working from the frontend.

## Backend Status
✅ Backend is running on http://127.0.0.1:8000
✅ Server started successfully

## Diagnostic Steps

### 1. Check Backend Logs
When you try to create an order, check the terminal running `uvicorn main:app --reload` for any error messages.

### 2. Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Try to create an order
4. Look for any error messages (red text)
5. Check Network tab for the POST request to `/api/orders`

### 3. Test Backend Directly

Run this in a new terminal:

```bash
cd backend
python test_create_order.py
```

Or use curl (PowerShell):
```powershell
$body = @{
    supplier_name = "Test Supplier"
    pizza_name = "Margherita"
    supplier_price = 10.00
    markup_percentage = 30
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/orders" -Method Post -Body $body -ContentType "application/json"
```

### 4. Check Redis Connection

```bash
cd backend
python test_redis.py
```

Expected output: ✓ Redis connection test passed!

### 5. Check API Documentation

Open http://localhost:8000/docs and try creating an order through the Swagger UI:
1. Click on `POST /api/orders`
2. Click "Try it out"
3. Fill in the example:
```json
{
  "supplier_name": "Pizza Palace",
  "pizza_name": "Margherita",
  "supplier_price": 10.00,
  "markup_percentage": 30
}
```
4. Click "Execute"
5. Check the response

## Common Issues

### Issue 1: CORS Error
**Symptom:** Browser console shows CORS error
**Solution:** Check that backend CORS settings include frontend URL

### Issue 2: Redis Connection Failed
**Symptom:** Backend logs show Redis connection error
**Solution:** 
- Check `.env` file has correct Redis credentials
- Run `python test_redis.py` to verify connection

### Issue 3: Network Error
**Symptom:** Browser shows "Failed to fetch" or network error
**Solution:**
- Verify backend is running on port 8000
- Check firewall isn't blocking the connection
- Try accessing http://localhost:8000/docs directly

### Issue 4: Validation Error
**Symptom:** 422 Unprocessable Entity error
**Solution:**
- Check all required fields are filled
- Verify price is a valid number
- Check markup_percentage is a number

## Quick Test

1. **Backend Health Check:**
   ```
   Open: http://localhost:8000/docs
   Should see: Swagger UI with API documentation
   ```

2. **Create Order via Swagger:**
   - Use the Swagger UI to test order creation
   - If it works there but not in frontend, it's a frontend issue
   - If it fails in Swagger too, it's a backend issue

3. **Check Frontend Console:**
   - Open browser DevTools (F12)
   - Look for JavaScript errors
   - Check Network tab for failed requests

## Next Steps

Please provide:
1. Any error messages from backend terminal
2. Any error messages from browser console
3. Result of testing via Swagger UI
4. Result of `python test_redis.py`

This will help identify the exact issue.
