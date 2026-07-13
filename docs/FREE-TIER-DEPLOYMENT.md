# Free Tier Deployment - Event Driven Platform
## Portfolio Project - Deployment Strategy

## Overview
Deploy your event-driven platform for portfolio/consulting demonstrations.

---

## Free Deployment Stack

### Architecture
```
Frontend (Vercel Free)
    ↓
Backend (Render Free)
    ↓
Redis Cloud (Free 30MB)
    ↓
Kafka (Redpanda Dev Container - Local Only)
```

---

## Free Tier Services

### 1. Frontend Hosting: **Vercel Free Tier**
- Unlimited bandwidth
- Automatic HTTPS
- Global CDN
- Automatic deployments from Git
- Custom domain support
- Limit: 100GB bandwidth/month (more than enough)

### 2. Backend Hosting: **Render Free Tier**
- 750 hours/month free
- Automatic HTTPS
- Git-based deployments
- Environment variables
- Spins down after 15 min inactivity (cold start ~30s)
- 512MB RAM limit

### 3. Database: **Redis Cloud Free Tier** (Already Using)
- 30MB storage (enough for 1000+ orders)
- Pub/Sub support
- High availability
- Already provisioned

### 4. Domain: **Free Options**
- Vercel subdomain: `your-app.vercel.app` (Free)
- Render subdomain: `your-app.onrender.com` (Free)
- Or use Freenom for custom domain (Free)

### 5. Monitoring: **Free Tier Tools**
- Sentry (Free: 5K errors/month)
- UptimeRobot (Free: 50 monitors)
- Vercel Analytics (Free)

### 6. Event Streaming: **Redpanda Dev Container (Local Only)**
- Kafka-compatible, zero-cost
- Runs locally in Docker for development/demo
- No cloud Kafka needed for portfolio demos

---

## Step-by-Step Free Deployment

### Phase 1: Prepare Code (15 minutes)

#### 1.1 Create Production Config Files

**Backend: Create `render.yaml`**
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
        sync: false  # Add via dashboard
      - key: REDIS_DB
        value: 0
```

**Frontend: Update `.env.production`**
```env
VITE_API_URL=https://pizza-delivery-backend.onrender.com
```

#### 1.2 Add Health Check Endpoint

Add to `backend/main.py`:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

#### 1.3 Optimize for Free Tier

**Backend: Add connection pooling**
```python
# In redis_client.py
# Add max_connections to prevent exhaustion
connection_params["max_connections"] = 10
```

**Frontend: Add loading states for cold starts**
```javascript
// Show "Waking up server..." message on first load
```

### Phase 2: Deploy Backend to Render (10 minutes)

**Step 1: Sign Up**
1. Go to https://render.com
2. Sign up with GitHub (free)

**Step 2: Create Web Service**
1. Click "New +" -> "Web Service"
2. Connect your GitHub repository
3. Select `backend` folder as root directory
4. Configure:
   - Name: `pizza-delivery-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: **Free**

**Step 3: Add Environment Variables**
```
REDIS_HOST=your-redis-host.cloud.redislabs.com
REDIS_PORT=your-port
REDIS_USERNAME=default
REDIS_PASSWORD=your-redis-password
REDIS_DB=0
CORS_ORIGINS=https://your-app.vercel.app
```

**Step 4: Deploy**
- Click "Create Web Service"
- Wait 5-10 minutes for first deployment
- Note your URL: `https://pizza-delivery-backend.onrender.com`

### Phase 3: Deploy Frontend to Vercel (5 minutes)

**Step 1: Sign Up**
1. Go to https://vercel.com
2. Sign up with GitHub (free)

**Step 2: Import Project**
1. Click "Add New..." -> "Project"
2. Import your GitHub repository
3. Configure:
   - Framework Preset: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

**Step 3: Add Environment Variable**
```
VITE_API_URL=https://pizza-delivery-backend.onrender.com
```

**Step 4: Deploy**
- Click "Deploy"
- Wait 2-3 minutes
- Your app is live at: `https://your-app.vercel.app`

### Phase 4: Update CORS (2 minutes)

Update `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "http://localhost:5173",  # Keep for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push - Render will auto-deploy.

---

## Local Kafka Demo (Redpanda Dev Container)

For portfolio demos, Kafka runs locally via Docker Compose. No cloud Kafka needed.

### Start Kafka Locally
```bash
# From project root
docker compose up -d redpanda

# Verify Redpanda is running
docker compose logs redpanda

# Create the topic
docker compose exec redpanda rpk topic create pizza.orders --partitions 3
```

### Connect Backend to Local Kafka

Add to `backend/.env`:
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=pizza.orders
```

Start the backend with Kafka enabled:
```bash
cd backend
python main.py
```

### Watch Events Flow in Real-Time

```bash
# Terminal 1: Watch Kafka events
docker compose exec redpanda rpk topic consume pizza.orders

# Terminal 2: Create an order via API
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"supplier_name":"Pizza Palace","pizza_name":"Margherita","supplier_price":10.0,"markup_percentage":30.0}'

# Terminal 3: Watch WebSocket events (optional)
# Open browser console and connect to ws://localhost:8000/ws
```

### Verify Dual-Write

When Kafka is configured, every event goes to both Redis Streams AND Kafka:
1. Redis Pub/Sub broadcasts instantly to WebSocket clients
2. Redis Streams persists the event for replay
3. Kafka provides durable, scalable event backbone

This demonstrates the **dual-write migration pattern** - a key enterprise architecture pattern.

---

## Portfolio Optimization

### Add Professional Touches

#### 1. Custom Domain (Optional - Free)
**Option A: Use Vercel subdomain**
- `pizza-delivery.vercel.app`

**Option B: Free domain from Freenom**
- Get `.tk`, `.ml`, `.ga` domain free
- Point to Vercel

#### 2. Add Demo Credentials
Create a demo mode for portfolio viewers:

```javascript
// frontend/src/App.jsx
const DEMO_MODE = true;

if (DEMO_MODE) {
  // Auto-populate forms
  // Show sample data
  // Add "Demo Mode" banner
}
```

#### 3. Add Project Description
Update `README.md` with:
- Live demo link
- Screenshots
- Technology stack
- Architecture diagram
- Key features

#### 4. Create Landing Page
Add a simple landing page explaining the project:

```javascript
// frontend/src/components/LandingPage.jsx
function LandingPage() {
  return (
    <div>
      <h1>Event-Driven Pizza Delivery System</h1>
      <p>Real-time order management with React, FastAPI, and Redis</p>
      <button>View Demo</button>
      <button>View Code</button>
    </div>
  )
}
```

---

## Free Tier Limitations & Solutions

### Limitation 1: Backend Sleeps After 15 Minutes
**Impact:** First request takes 30 seconds (cold start)

**Solutions:**
1. **Add loading message:**
```javascript
"Server is waking up... This takes ~30 seconds on free tier"
```

2. **Keep-alive ping (optional):**
```javascript
// Ping every 14 minutes to keep awake
setInterval(() => {
  fetch('https://your-backend.onrender.com/health')
}, 14 * 60 * 1000)
```

### Limitation 2: 512MB RAM
**Impact:** May crash under heavy load

**Solutions:**
- Optimize memory usage
- Limit concurrent connections
- Add request queuing

### Limitation 3: Redis 30MB Storage
**Impact:** ~1000 orders max

**Solutions:**
- Add data cleanup (delete old delivered orders)
- Archive to JSON file

---

## Portfolio Presentation Tips

### 1. Create a Demo Video
- Record 2-3 minute walkthrough
- Show real-time updates
- Explain architecture
- Upload to YouTube

### 2. Add to Portfolio Site
```markdown
## Event Driven Platform
Event-driven real-time order management system

**Tech Stack:** React, FastAPI, Redis, WebSocket, Kafka
**Live Demo:** https://pizza-delivery.vercel.app
**Source Code:** https://github.com/yourusername/pizza-delivery
**Video Demo:** https://youtube.com/...

**Key Features:**
- Real-time order updates via WebSocket
- Event-driven architecture with Redis Pub/Sub
- Kafka dual-write for scalable event streaming
- Multi-role system (Supplier, Customer, Dispatch)
- State machine for order lifecycle
- Responsive UI with live status updates
```

### 3. Prepare Talking Points
- "Built event-driven architecture using Redis Pub/Sub and Kafka"
- "Implemented dual-write migration pattern for zero-downtime migration"
- "Real-time WebSocket communication with auto-reconnect"
- "Deployed on free tier cloud infrastructure"
- "Handles concurrent users with async Python"
- "State management with React hooks"

---

## Monitoring Your Free Deployment

### 1. Uptime Monitoring (Free)
**UptimeRobot:**
1. Sign up at uptimerobot.com
2. Add monitor for your backend
3. Get alerts if it goes down

### 2. Error Tracking (Free)
**Sentry:**
1. Sign up at sentry.io
2. Add to backend:
```python
import sentry_sdk
sentry_sdk.init(dsn="your-dsn")
```

### 3. Analytics (Free)
**Vercel Analytics:**
- Automatically enabled
- View in Vercel dashboard

---

## Maintenance on Free Tier

### Daily
- Check if app is running
- Monitor error logs

### Weekly
- Clear old orders from Redis
- Check storage usage
- Review performance

### Monthly
- Update dependencies
- Backup important data

---

## Cost Breakdown

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Vercel | Free | Unlimited bandwidth, 100GB transfer |
| Render | Free | 750 hours/month, 512MB RAM |
| Redis Cloud | Free | 30MB storage, Pub/Sub |
| Kafka (Redpanda) | Free | Local Docker only |
| Domain | Free | Vercel/Render subdomains |

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
- [ ] README updated with live link
- [ ] Screenshots added
- [ ] Portfolio page updated

---

## Sample Portfolio Description

```markdown
# Event-Driven Platform

A real-time order management system demonstrating event-driven architecture
and WebSocket communication with Kafka integration.

**Live Demo:** https://pizza-delivery.vercel.app
**Video Demo:** [2-minute walkthrough]
**Source Code:** https://github.com/yourusername/pizza-delivery

## Technical Highlights

- **Event-Driven Architecture:** Redis Pub/Sub + Kafka for real-time event broadcasting
- **Dual-Write Pattern:** Events published to both Redis and Kafka simultaneously
- **WebSocket Communication:** Live order updates across all connected clients
- **State Machine:** Complete order lifecycle management
- **Async Python:** FastAPI with async/await for high concurrency
- **React Hooks:** Modern state management with custom hooks
- **Cloud Deployment:** Serverless deployment on free tier infrastructure

## Architecture

[Include your architecture diagram here]

## Features

- Multi-role system (Supplier, Customer, Dispatch)
- Real-time order status updates
- Automatic price markup calculation
- Driver assignment and tracking
- Complete order history

## Tech Stack

**Frontend:** React 18, Vite, WebSocket API
**Backend:** FastAPI, Python 3.11, Uvicorn
**Database:** Redis Cloud (Pub/Sub + Storage)
**Event Streaming:** Kafka/Redpanda (dual-write)
**Deployment:** Vercel (Frontend), Render (Backend)

## Local Development

[Include setup instructions]

---

**Deployed on free tier infrastructure**
```

---

## Learning Outcomes to Highlight

For consulting/interviews, emphasize:

1. **Event-Driven Architecture**
   - Pub/Sub pattern implementation
   - Dual-write migration strategy
   - Decoupled services
   - Scalable design

2. **Real-Time Communication**
   - WebSocket implementation
   - State synchronization
   - Connection management
   - Auto-reconnect patterns

3. **Cloud Deployment**
   - CI/CD with Git
   - Environment management
   - Free tier optimization
   - Container orchestration

4. **Full-Stack Development**
   - React frontend
   - Python backend
   - Database integration
   - Event streaming

5. **Production Readiness**
   - Error handling
   - Monitoring
   - Security (HTTPS, CORS)
   - Graceful degradation

---

## You're Ready!

Your pizza delivery app is now:
- Deployed on free tier
- Accessible worldwide
- Professional looking
- Portfolio ready
- Kafka-ready for demos

**Next Steps:**
1. Deploy following the steps above
2. Add to your portfolio
3. Share with potential clients/employers
4. Iterate based on feedback

**Deployment Time:** ~30 minutes total
**Portfolio Impact:** High
