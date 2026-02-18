# Grafana Dashboard for Pizza Delivery Analytics

This directory contains the Grafana dashboard configuration for visualizing pizza delivery metrics.

## Files

- `dashboard-orders-delivered.json` - Pre-configured dashboard with 7 panels

## Dashboard Panels

### 1. Total Delivered Orders (Stat)
- Shows total number of delivered orders
- Color-coded thresholds (green/yellow/red)

### 2. Delivery Rate (Gauge)
- Percentage of orders successfully delivered
- Visual gauge with threshold markers

### 3. Orders In Transit (Stat)
- Current count of orders in transit
- Real-time updates

### 4. Orders Dispatched (Stat)
- Current count of dispatched orders
- Real-time updates

### 5. Deliveries Over Time (Time Series)
- Line graph showing delivery trends
- Three series: Today, Last 7 Days, Last 30 Days
- Smooth interpolation with fill

### 6. Deliveries by Supplier (Pie Chart)
- Distribution of deliveries across suppliers
- Shows percentages and counts

### 7. Deliveries by Driver (Bar Chart)
- Horizontal bar chart of driver performance
- Sorted by delivery count

## Quick Import

1. Open Grafana
2. Go to Dashboards → Import
3. Upload `dashboard-orders-delivered.json`
4. Select your Prometheus datasource
5. Click Import

## Customization

### Changing Refresh Rate

Default: 5 seconds

To change:
1. Open dashboard
2. Click time picker (top right)
3. Select different refresh interval

### Adding New Panels

1. Click "Add panel" button
2. Select visualization type
3. Configure query using available metrics
4. Save panel

### Available Metrics

See `../GRAFANA_SETUP.md` for complete list of available metrics.

## Dashboard Settings

- **Timezone**: Browser (uses your local timezone)
- **Refresh**: 5 seconds
- **Time Range**: Last 24 hours (adjustable)

## Troubleshooting

### Dashboard Shows "No Data"

1. Verify backend is running
2. Check metrics endpoint: http://localhost:8000/metrics
3. Generate test data: `python backend/generate_test_data.py`
4. Verify datasource connection in Grafana

### Panels Not Updating

1. Check refresh interval is enabled
2. Verify WebSocket connection (if using)
3. Check browser console for errors

## Export/Backup

To export your customized dashboard:

1. Dashboard Settings → JSON Model
2. Copy JSON
3. Save to file

## Version

Dashboard Version: 1.0
Compatible with: Grafana 8.0+
