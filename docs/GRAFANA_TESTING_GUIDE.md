# Grafana Testing Guide

Complete guide to test the Grafana visualization setup for event-driven platform analytics.

## Prerequisites

- Python 3.11+
- Redis Cloud connection configured
- Backend dependencies installed

## Step-by-Step Testing

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Redis

Ensure your `.env` file has Redis credentials:

```env
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=your-password
REDIS_DB=0
```

### Step 3: Start Backend Server

Open a terminal and run:

```bash
cd backend
uvicorn main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Keep this terminal running!

### Step 4: Generate Test Data

Open a NEW terminal and run:

```bash
cd backend
python generate_test_data.py
```

Expected output:
```
🚀 Starting test data generation...
============================================================
📦 Generating delivered orders (past 30 days)...
   ✅ Created 10 delivered orders
   ✅ Created 20 delivered orders
   ✅ Created 30 delivered orders
   ✅ Created 40 delivered orders
   ✅ Created 50 delivered orders

✅ Total delivered orders: 50

🔄 Generating active orders...
   🚚 Created 5 in-transit orders
   📤 Created 3 dispatched orders
   ✅ Created 4 ready orders
   👨‍🍳 Created 6 preparing orders
   ⏳ Created 8 pending orders

============================================================
📊 DATA GENERATION SUMMARY
============================================================
Total Orders Created: 76
  - Delivered: 50
  - In Transit: 5
  - Dispatched: 3
  - Ready: 4
  - Preparing: 6
  - Pending: 8
============================================================

✅ Test data generation complete!
```

### Step 5: Test Metrics Endpoints

```bash
cd backend
python test_grafana_metrics.py
```

Expected output:
```
🧪 Testing Grafana Metrics Endpoints
============================================================

1️⃣  Testing Prometheus endpoint (/metrics)...
   ✅ Prometheus endpoint is working
   📊 Response contains 50+ lines

   Sample metrics:
orders_total 76
orders_delivered 50
orders_in_transit 5
orders_dispatched 3
delivery_rate_percent 65.79

2️⃣  Testing JSON API endpoint (/api/metrics)...
   ✅ JSON API endpoint is working

   📊 Metrics Summary:
      Total Orders: 76
      Delivered: 50
      In Transit: 5
      Delivery Rate: 65.79%

   📈 Time Series:
      Today: 2
      Last 7 Days: 12
      Last 30 Days: 50

   🏪 Top Sources:
      Quick Mart: 12 deliveries
      Fresh Foods: 10 deliveries
      Speed Supplies: 9 deliveries

   🚗 Top Drivers:
      Maria Garcia: 11 deliveries
      John Smith: 8 deliveries
      Ahmed Khan: 7 deliveries

============================================================
✅ Metrics endpoints test complete!
```

### Step 6: Manual Verification

#### Test Prometheus Endpoint

Open in browser: http://localhost:8000/metrics

You should see:
```
# HELP orders_total Total number of orders
# TYPE orders_total counter
orders_total 76

# HELP orders_delivered Total number of delivered orders
# TYPE orders_delivered counter
orders_delivered 50
...
```

#### Test JSON Endpoint

Open in browser: http://localhost:8000/api/metrics

You should see JSON response with:
```json
{
  "summary": {
    "total_orders": 76,
    "total_delivered": 50,
    "in_transit": 5,
    "dispatched": 3,
    "delivery_rate": 65.79
  },
  "time_series": { ... },
  "by_source": { ... },
  "by_driver": { ... }
}
```

### Step 7: Setup Grafana

#### Option A: Local Grafana (Docker)

```bash
docker run -d -p 3000:3000 --name=grafana grafana/grafana
```

Access: http://localhost:3000 (admin/admin)

#### Option B: Grafana Cloud

1. Sign up at https://grafana.com/
2. Create free stack
3. Note your Grafana URL

### Step 8: Configure Datasource

1. Open Grafana
2. Go to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Select **Prometheus**
5. Configure:
    - **Name**: `Order Delivery Metrics`
   - **URL**: `http://host.docker.internal:8000/metrics` (Docker) or `http://localhost:8000/metrics` (local)
   - **Access**: Browser
6. Click **Save & Test**

Expected: ✅ "Data source is working"

### Step 9: Import Dashboard

1. Go to **Dashboards** → **Import**
2. Click **Upload JSON file**
3. Select `grafana/dashboard-orders-delivered.json`
4. Select datasource: `Order Delivery Metrics`
5. Click **Import**

### Step 10: Verify Dashboard

You should see 7 panels with data:

1. ✅ **Total Delivered Orders**: Shows 50
2. ✅ **Delivery Rate**: Shows ~66%
3. ✅ **Orders In Transit**: Shows 5
4. ✅ **Orders Dispatched**: Shows 3
5. ✅ **Deliveries Over Time**: Line graph with data
6. ✅ **Deliveries by Source**: Pie chart with 5 sources
7. ✅ **Deliveries by Driver**: Bar chart with 5 drivers

### Step 11: Test Real-Time Updates

1. Set dashboard refresh to **5s** (top right)
2. In a new terminal, create a new order:

```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "Quick Mart",
    "item_name": "Electronics Bundle",
    "source_price": 12.50
  }'
```

3. Progress the order through states (use API docs: http://localhost:8000/docs)
4. Watch dashboard update in real-time

## Troubleshooting

### Issue: "Data source is working" but no data in dashboard

**Solution:**
1. Check time range (top right) - set to "Last 24 hours"
2. Verify test data was generated
3. Check metrics endpoint manually
4. Review panel queries in edit mode

### Issue: Connection refused to localhost:8000

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/metrics`
2. If using Docker Grafana, use `host.docker.internal:8000` instead of `localhost:8000`
3. Check firewall settings

### Issue: Metrics show 0 for everything

**Solution:**
1. Run `python generate_test_data.py` again
2. Verify Redis connection: `python test_redis.py`
3. Check backend logs for errors

### Issue: Dashboard panels show "No data"

**Solution:**
1. Edit panel → Check query expression
2. Verify datasource is selected
3. Check time range matches your data
4. Test query in Explore view

### Issue: Some metrics missing

**Solution:**
1. Refresh metrics endpoint
2. Check backend logs for errors in metrics_service.py
3. Verify all orders have required fields (driver_name, source_name, etc.)

## Testing Checklist

- [ ] Backend server running
- [ ] Redis connection working
- [ ] Test data generated (76 orders)
- [ ] Prometheus endpoint accessible
- [ ] JSON endpoint accessible
- [ ] Grafana installed/accessible
- [ ] Datasource configured and tested
- [ ] Dashboard imported successfully
- [ ] All 7 panels showing data
- [ ] Real-time updates working

## Performance Testing

### Load Test with More Data

Generate 500 orders:

```python
# Modify generate_test_data.py
# Change: for i in range(50):
# To: for i in range(500):
```

Run and verify:
- Metrics endpoint response time < 200ms
- Dashboard loads within 2 seconds
- Refresh works smoothly

### Concurrent Access Test

Open dashboard in multiple browser tabs and verify:
- All tabs update simultaneously
- No performance degradation
- Metrics remain consistent

## Next Steps

1. ✅ Customize dashboard colors and thresholds
2. ✅ Add alerts for critical metrics
3. ✅ Create additional dashboards for specific views
4. ✅ Set up Grafana notifications
5. ✅ Deploy to production environment

## Production Considerations

### Use Prometheus Server

Instead of direct scraping:

1. Install Prometheus
2. Configure scrape target
3. Point Grafana to Prometheus
4. Benefits: Historical data, better performance, HA

### Security

1. Add authentication to metrics endpoint
2. Use HTTPS/TLS
3. Implement rate limiting
4. Keep metrics internal (VPN/private network)

### Monitoring

1. Set up alerts for:
   - Delivery rate < 80%
   - Orders stuck in transit > 1 hour
   - No deliveries in last hour
2. Configure notification channels (email, Slack, PagerDuty)

## Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Dashboard Design Guide](https://grafana.com/docs/grafana/latest/best-practices/)

---

**Questions?** Check the main [GRAFANA_SETUP.md](GRAFANA_SETUP.md) for detailed configuration options.
