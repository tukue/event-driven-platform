# Grafana Quick Reference

## 🚀 Quick Start (5 Minutes)

### 1. Generate Test Data
```bash
cd backend
python generate_test_data.py
```

### 2. Start Backend
```bash
uvicorn main:app --reload
```

### 3. Verify Setup
```bash
python verify_grafana_setup.py
```

### 4. Test Endpoints
- Prometheus: http://localhost:8000/metrics
- JSON: http://localhost:8000/api/metrics

## 📊 Available Metrics

### Counters
- `pizza_orders_total` - Total orders
- `pizza_orders_delivered` - Total delivered
- `pizza_delivered_today` - Delivered today
- `pizza_delivered_week` - Last 7 days
- `pizza_delivered_month` - Last 30 days

### Gauges
- `pizza_orders_in_transit` - Currently in transit
- `pizza_orders_dispatched` - Currently dispatched
- `pizza_delivery_rate_percent` - Success rate

### Labels
- `pizza_delivered_by_supplier{supplier="..."}` - By supplier
- `pizza_delivered_by_driver{driver="..."}` - By driver

## 🔧 Grafana Setup

### Add Datasource
1. Configuration → Data Sources → Add
2. Select "Prometheus"
3. URL: `http://localhost:8000/metrics`
4. Save & Test

### Import Dashboard
1. Dashboards → Import
2. Upload: `grafana/dashboard-orders-delivered.json`
3. Select datasource
4. Import

## 🧪 Testing Commands

```bash
# Verify all components
python verify_grafana_setup.py

# Test metrics endpoints
python test_grafana_metrics.py

# Generate more data
python generate_test_data.py

# Check Redis
python test_redis.py
```

## 📁 Key Files

- `GRAFANA_SETUP.md` - Full setup guide
- `GRAFANA_TESTING_GUIDE.md` - Testing procedures
- `grafana/dashboard-orders-delivered.json` - Dashboard config
- `backend/services/metrics_service.py` - Metrics logic

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No data | Run `generate_test_data.py` |
| Connection refused | Start backend server |
| Redis error | Check `.env` credentials |
| Dashboard empty | Verify datasource URL |

## 📚 Documentation

- Full Guide: [GRAFANA_SETUP.md](GRAFANA_SETUP.md)
- Testing: [GRAFANA_TESTING_GUIDE.md](GRAFANA_TESTING_GUIDE.md)
- Dashboard: [grafana/README.md](grafana/README.md)
