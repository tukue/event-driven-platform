# Grafana Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Pizza Delivery System                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Events & State Changes
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Redis Cloud                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Order Storage│  │   Pub/Sub    │  │  State Cache │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Read Orders
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Metrics Service                           │
│  ┌──────────────────────────────────────────────────┐      │
│  │  • Aggregate order data                          │      │
│  │  • Calculate delivery statistics                 │      │
│  │  • Generate time-series metrics                  │      │
│  │  • Format for Prometheus/JSON                    │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  /metrics (Prometheus)   │  │  /api/metrics (JSON)     │
│  ┌────────────────────┐  │  │  ┌────────────────────┐  │
│  │ pizza_orders_total │  │  │  │ { "summary": {...} │  │
│  │ pizza_delivered    │  │  │  │   "time_series": { │  │
│  │ delivery_rate      │  │  │  │   "by_supplier": { │  │
│  │ ...                │  │  │  │   ... }            │  │
│  └────────────────────┘  │  │  └────────────────────┘  │
└──────────────────────────┘  └──────────────────────────┘
                │                           │
                │                           │
                └─────────────┬─────────────┘
                              │
                              │ HTTP Scrape/Poll
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Grafana                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Prometheus Datasource                │      │
│  │  • Scrapes /metrics endpoint                      │      │
│  │  • Parses Prometheus format                       │      │
│  │  • Stores time-series data                        │      │
│  └──────────────────────────────────────────────────┘      │
│                              │                               │
│                              ▼                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │                  Dashboard                        │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │      │
│  │  │ Stat     │  │  Gauge   │  │ Time     │      │      │
│  │  │ Panels   │  │  Panels  │  │ Series   │      │      │
│  │  └──────────┘  └──────────┘  └──────────┘      │      │
│  │  ┌──────────┐  ┌──────────┐                    │      │
│  │  │ Pie      │  │  Bar     │                    │      │
│  │  │ Chart    │  │  Chart   │                    │      │
│  │  └──────────┘  └──────────┘                    │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Visual Display
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      End User Browser                        │
│  • Real-time metrics visualization                           │
│  • Auto-refresh every 5 seconds                              │
│  • Interactive dashboards                                    │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Order Creation & Updates
```
User Action → API → OrderService → Redis Storage → Pub/Sub Event
```

### 2. Metrics Collection
```
MetricsService → Read from Redis → Aggregate Data → Format Output
```

### 3. Metrics Exposure
```
FastAPI Endpoint → MetricsService → Prometheus/JSON Format → HTTP Response
```

### 4. Grafana Visualization
```
Grafana → HTTP Request → Backend Endpoint → Parse Metrics → Render Dashboard
```

## Components

### Backend Services

#### MetricsService
- **Location**: `backend/services/metrics_service.py`
- **Purpose**: Aggregate and format metrics
- **Methods**:
  - `get_delivery_metrics()` - JSON format
  - `get_prometheus_metrics()` - Prometheus format

#### API Endpoints
- **Location**: `backend/main.py`
- **Endpoints**:
  - `GET /metrics` - Prometheus format
  - `GET /api/metrics` - JSON format

### Grafana Components

#### Datasource
- **Type**: Prometheus
- **URL**: `http://localhost:8000/metrics`
- **Scrape Interval**: 5 seconds

#### Dashboard
- **Location**: `grafana/dashboard-orders-delivered.json`
- **Panels**: 7 visualization panels
- **Refresh**: Auto-refresh every 5s

## Metrics Categories

### Summary Metrics
- Total orders
- Delivered count
- In-transit count
- Dispatched count
- Delivery rate percentage

### Time-Series Metrics
- Deliveries today
- Deliveries last 7 days
- Deliveries last 30 days

### Dimensional Metrics
- Deliveries by supplier (labeled)
- Deliveries by driver (labeled)
- Hourly distribution

## Scalability Considerations

### Current Architecture (Direct Scraping)
```
Grafana → Backend API → Redis
```
- ✅ Simple setup
- ✅ No additional infrastructure
- ⚠️  Backend handles scraping load
- ⚠️  Limited historical data

### Production Architecture (Prometheus Server)
```
Grafana → Prometheus Server → Backend API → Redis
```
- ✅ Dedicated metrics storage
- ✅ Historical data retention
- ✅ Advanced querying (PromQL)
- ✅ High availability
- ✅ Reduced backend load

## Performance

### Metrics Endpoint
- **Response Time**: < 100ms
- **Data Size**: ~2KB (Prometheus), ~5KB (JSON)
- **Caching**: None (real-time data)

### Dashboard
- **Load Time**: < 2 seconds
- **Refresh Rate**: 5 seconds
- **Concurrent Users**: 10+ supported

### Optimization Tips
1. Use Prometheus server for production
2. Implement caching for metrics aggregation
3. Add database indexes for faster queries
4. Use Redis pipelining for bulk reads

## Security

### Current Setup (Development)
- No authentication on metrics endpoints
- HTTP (not HTTPS)
- Open CORS policy

### Production Recommendations
1. **Authentication**: Add API key or OAuth
2. **Encryption**: Use HTTPS/TLS
3. **Network**: Keep metrics internal (VPN)
4. **Rate Limiting**: Prevent abuse
5. **CORS**: Restrict to Grafana domain

## Monitoring the Monitor

### Health Checks
- Backend uptime
- Redis connectivity
- Metrics endpoint availability
- Grafana datasource status

### Alerts
- Metrics endpoint down
- High response time (> 500ms)
- Redis connection failures
- Data staleness (no updates)

## Future Enhancements

### Planned Features
1. **Additional Metrics**
   - Average delivery time
   - Customer satisfaction scores
   - Revenue metrics
   - Peak hour analysis

2. **Advanced Visualizations**
   - Heatmaps for delivery zones
   - Geolocation tracking
   - Predictive analytics
   - Anomaly detection

3. **Integration**
   - Alerting (PagerDuty, Slack)
   - Log aggregation (ELK stack)
   - Tracing (Jaeger)
   - APM (Application Performance Monitoring)

## References

- [Prometheus Exposition Format](https://prometheus.io/docs/instrumenting/exposition_formats/)
- [Grafana Datasources](https://grafana.com/docs/grafana/latest/datasources/)
- [FastAPI Metrics](https://fastapi.tiangolo.com/advanced/custom-response/)
- [Redis Performance](https://redis.io/docs/management/optimization/)
