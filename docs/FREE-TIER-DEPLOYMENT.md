# Free Tier Deployment — Event Driven Platform

Deploy the event-driven pizza delivery platform using only free tier services.

---

## Free Deployment Stack

```
Frontend (Vercel Free)
    |
    v
Backend (Render Free)
    |
    v
Redis Cloud (Free 30MB)
    |
    v
Kafka (Redpanda Dev Container — Local Only)
```

---

## Free Tier Services

| Service | Provider | Limits |
|---------|----------|--------|
| Frontend | Vercel Free | 100GB bandwidth/month, HTTPS, CDN |
| Backend | Render Free | 750 hours/month, 512MB RAM, spins down after 15min inactivity |
| Database | Redis Cloud Free | 30MB storage, Pub/Sub support |
| Event Streaming | Redpanda Dev Container | Local Docker only, Kafka-compatible |
| Domain | Vercel/Render subdomains | `your-app.vercel.app` or `your-app.onrender.com` |
| Monitoring | UptimeRobot Free | 50 monitors |
| Error Tracking | Sentry Free | 5K errors/month |

---

## Deployment Steps

### Phase 1: Prepare Code

#### 1.1 Create `render.yaml` (Backend)

```yaml
services:
  - type: web
    name: pizza-delivery-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: REDIS_HOST
        value: your-redis-host.cloud.redislabs.com
      - key: REDIS_PORT
        value: your-port
      - key: REDIS_USERNAME
        value: default
      - key: REDIS_PASSWORD
        sync: false
      - key: REDIS_DB
        value: 0
```

#### 1.2 Create `.env.production` (Frontend)

```env
VITE_API_URL=https://pizza-delivery-backend.onrender.com
```

#### 1.3 Add Health Check Endpoint

```python
# backend/main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

#### 1.4 Add Connection Pooling

```python
# backend/redis_client.py
connection_params["max_connections"] = 10
```

### Phase 2: Deploy Backend to Render

1. Go to https://render.com, sign up with GitHub
2. Click "New +" -> "Web Service"
3. Connect GitHub repository, select `backend` folder
4. Configure:
   - Name: `pizza-delivery-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: **Free**
5. Add environment variables:
   ```
   REDIS_HOST=your-redis-host.cloud.redislabs.com
   REDIS_PORT=your-port
   REDIS_USERNAME=default
   REDIS_PASSWORD=your-redis-password
   REDIS_DB=0
   CORS_ORIGINS=https://your-app.vercel.app
   ```
6. Click "Create Web Service", wait 5-10 minutes

### Phase 3: Deploy Frontend to Vercel

1. Go to https://vercel.com, sign up with GitHub
2. Click "Add New..." -> "Project"
3. Import GitHub repository
4. Configure:
   - Framework Preset: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Add environment variable:
   ```
   VITE_API_URL=https://pizza-delivery-backend.onrender.com
   ```
6. Click "Deploy", wait 2-3 minutes

### Phase 4: Update CORS

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push — Render will auto-deploy.

---

## Local Kafka Demo

Kafka runs locally via Docker Compose for development and demos.

### Start Kafka

```bash
docker compose up -d redpanda
docker compose logs redpanda
docker compose exec redpanda rpk topic create pizza.orders --partitions 3
```

### Connect Backend to Kafka

Add to `backend/.env`:
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=pizza.orders
```

### Watch Events

```bash
# Terminal 1: Watch Kafka events
docker compose exec redpanda rpk topic consume pizza.orders

# Terminal 2: Create an order
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"supplier_name":"Pizza Palace","pizza_name":"Margherita","supplier_price":10.0,"markup_percentage":30.0}'

# Terminal 3: Watch WebSocket (browser console)
# const ws = new WebSocket('ws://localhost:8000/ws');
# ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### Verify Dual-Write

Every event goes to both Redis Streams AND Kafka:
1. Redis Pub/Sub broadcasts instantly to WebSocket clients
2. Redis Streams persists the event for replay
3. Kafka provides durable, scalable event backbone

---

## Free Tier Limitations

### Backend Sleeps After 15 Minutes

First request takes ~30 seconds (cold start).

**Workaround — loading message:**
```javascript
"Server is waking up... This takes ~30 seconds on free tier"
```

**Workaround — keep-alive ping:**
```javascript
setInterval(() => {
  fetch('https://your-backend.onrender.com/health')
}, 14 * 60 * 1000)
```

### 512MB RAM Limit

May crash under heavy load. Optimize memory usage and limit concurrent connections.

### Redis 30MB Storage

Enough for ~1000 orders. Add data cleanup for old delivered orders.

---

## Quick Deploy Checklist

- [ ] Code pushed to GitHub
- [ ] Backend deployed to Render
- [ ] Frontend deployed to Vercel
- [ ] Environment variables configured
- [ ] CORS updated
- [ ] Health check working
- [ ] WebSocket connecting
- [ ] Orders creating successfully
- [ ] Real-time updates working
- [ ] Kafka demo working locally
- [ ] Demo data added

---

## Maintenance

| Frequency | Task |
|-----------|------|
| Daily | Check if app is running, monitor error logs |
| Weekly | Clear old orders from Redis, check storage usage |
| Monthly | Update dependencies, review costs |
