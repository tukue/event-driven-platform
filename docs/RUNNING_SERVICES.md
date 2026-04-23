# Running Backend Services - Quick Start Guide

## Prerequisites

Before running the backend, ensure you have:

- ✅ Python 3.11 or higher
- ✅ Redis Cloud account (or local Redis)
- ✅ Git installed
- ✅ Terminal/Command Prompt access

## Quick Start (5 Minutes)

### Step 1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2: Create Virtual Environment

**Windows (PowerShell/CMD):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Windows (Git Bash):**
```bash
python -m venv venv
source venv/Scripts/activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Redis (database client)
- Pydantic (data validation)
- Python-dotenv (environment variables)

### Step 4: Configure Environment Variables

**Create `.env` file:**

```bash
# Copy the example file
cp .env.example .env

# Or on Windows
copy .env.example .env
```

**Edit `.env` file with your credentials:**

```env
REDIS_HOST=your-redis-host.cloud.redislabs.com
REDIS_PORT=your-port
REDIS_USERNAME=default
REDIS_PASSWORD=your-actual-password
REDIS_DB=0
```

**⚠️ IMPORTANT:** 
- Replace with your actual Redis credentials
- Never commit this file to Git (it's in .gitignore)
- Get credentials from Redis Cloud dashboard

### Step 5: Test Redis Connection

```bash
python test_redis.py
```

**Expected output:**
```
Testing Redis connection...
✓ Connected to Redis successfully!
✓ Set test key
✓ Retrieved test value: test_value
✓ Deleted test key
✓ Redis connection test passed!
```

**If connection fails:**
```bash
# Run diagnostics
python diagnose_redis.py
```

### Step 6: Start the Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Server is now running at:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

### Step 7: Verify Server is Running

**Open a new terminal and test:**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Or open in browser
# http://localhost:8000/docs
```

**Expected response:**
```json
{"status": "healthy"}
```

## Running Frontend (Optional)

If you want to test the full application:

**Open a new terminal:**

```bash
cd frontend
npm install
npm run dev
```

**Frontend will be available at:**
- http://localhost:5173

## Common Commands

### Start Backend (Development)

```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
uvicorn main:app --reload
```

### Start Backend (Production Mode)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=term

# Specific test file
pytest tests/test_api.py -v

# Run integration tests
pytest tests/test_integration.py -v
```

### Check Code Quality

```bash
# Linting
flake8 .

# Format check
black --check .

# Format code
black .

# Import sorting
isort .
```

### Inspect Redis Data

```bash
# View all orders in Redis
python inspect_redis.py

# Diagnose connection issues
python diagnose_redis.py
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

### Create Order
```bash
POST http://localhost:8000/api/orders
Content-Type: application/json

{
  "supplier_name": "Pizza Palace",
  "pizza_name": "Margherita",
  "supplier_price": 10.00,
  "markup_percentage": 30
}
```

### Get All Orders
```bash
GET http://localhost:8000/api/orders
```

### Supplier Accept Order
```bash
POST http://localhost:8000/api/orders/{order_id}/supplier-respond?accept=true&notes=Fresh%20ingredients&estimated_time=30
```

### Customer Accept Order
```bash
POST http://localhost:8000/api/orders/{order_id}/customer-accept?customer_name=John%20Doe&delivery_address=123%20Main%20St
```

### Update Order Status
```bash
POST http://localhost:8000/api/orders/{order_id}/status?status=preparing
```

### Dispatch Order
```bash
POST http://localhost:8000/api/orders/{order_id}/dispatch?driver_name=Mike%20Driver
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
# Make sure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Redis connection failed"

**Solution:**
```bash
# 1. Check .env file exists and has correct credentials
cat .env  # Linux/Mac
type .env  # Windows

# 2. Run diagnostics
python diagnose_redis.py

# 3. Verify Redis Cloud instance is running
# Log into https://app.redislabs.com/

# 4. Check IP whitelist in Redis Cloud
# Add your IP: 0.0.0.0/0 (for testing only!)
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Or use a different port
uvicorn main:app --reload --port 8001
```

### Issue: "uvicorn: command not found"

**Solution:**
```bash
# Make sure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall uvicorn
pip install uvicorn
```

### Issue: WebSocket connection fails

**Solution:**
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check CORS settings in main.py
# Should include your frontend URL

# 3. Use correct WebSocket URL
# ws://localhost:8000/ws (not http://)
```

### Issue: Tests fail with Redis errors

**Solution:**
```bash
# Tests use mocked Redis by default
# If you want to test with real Redis:

# 1. Ensure .env is configured
# 2. Run specific test
pytest tests/test_integration.py -v

# Or run with mocked Redis
pytest tests/test_api.py -v
```

## Development Workflow

### 1. Start Development Session

```bash
# Terminal 1: Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload

# Terminal 2: Frontend (optional)
cd frontend
npm run dev

# Terminal 3: Testing/Commands
cd backend
venv\Scripts\activate
# Run tests, inspect data, etc.
```

### 2. Make Changes

- Edit Python files in `backend/`
- Server auto-reloads on file changes (--reload flag)
- Check http://localhost:8000/docs for API changes

### 3. Test Changes

```bash
# Run tests
pytest tests/ -v

# Manual testing via API docs
# Open http://localhost:8000/docs
# Try endpoints interactively
```

### 4. Check Code Quality

```bash
# Before committing
black .
isort .
flake8 .
pytest tests/ -v
```

## Production Deployment

### Using Docker (Recommended)

```bash
# Build image
docker build -t pizza-backend .

# Run container
docker run -p 8000:8000 --env-file .env pizza-backend
```

### Using Systemd (Linux)

Create `/etc/systemd/system/pizza-backend.service`:

```ini
[Unit]
Description=Pizza Delivery Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pizza-backend
sudo systemctl start pizza-backend
sudo systemctl status pizza-backend
```

### Using PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Start backend
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name pizza-backend

# View logs
pm2 logs pizza-backend

# Restart
pm2 restart pizza-backend
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server hostname | `redis-xxxxx.cloud.redislabs.com` |
| `REDIS_PORT` | Redis server port | `13869` |
| `REDIS_USERNAME` | Redis username | `default` |
| `REDIS_PASSWORD` | Redis password | `your-secure-password` |
| `REDIS_DB` | Redis database number | `0` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

## Performance Tips

### 1. Use Connection Pooling

Already configured in `redis_client.py`:
```python
connection_params["max_connections"] = 10
```

### 2. Enable Compression

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --limit-concurrency 100
```

### 3. Use Production ASGI Server

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. Monitor Performance

```bash
# Install monitoring tools
pip install prometheus-fastapi-instrumentator

# Add to main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

## Monitoring & Logs

### View Logs

```bash
# Development (console output)
uvicorn main:app --reload --log-level debug

# Production (file output)
uvicorn main:app --log-config logging.yaml
```

### Health Monitoring

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check Redis connection
python test_redis.py

# View all orders
python inspect_redis.py
```

## Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] Redis password is strong and rotated
- [ ] CORS origins are restricted
- [ ] Rate limiting is enabled (production)
- [ ] HTTPS is used (production)
- [ ] Environment variables are secured
- [ ] Dependencies are up to date

## Quick Reference Card

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Start server
uvicorn main:app --reload

# Run tests
pytest tests/ -v

# Check Redis
python test_redis.py

# View data
python inspect_redis.py

# API docs
http://localhost:8000/docs

# Stop server
Ctrl+C
```

## Support

- **Documentation:** See `DOCUMENTATION.md`
- **Testing Guide:** See `TEST_GUIDE.md`
- **Deployment:** See `DEPLOYMENT.md`
- **Security:** See `URGENT_SECURITY_ACTIONS.md`

---

**Setup Time:** 5 minutes  
**Prerequisites:** Python 3.11+, Redis Cloud account  
**Default Port:** 8000  
**Status:** Ready to run!
