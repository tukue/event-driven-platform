from datetime import datetime, timedelta
from typing import Dict, List
import json

class MetricsService:
    """Service for generating metrics for monitoring and visualization"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_delivery_metrics(self) -> Dict:
        """
        Get comprehensive delivery metrics for Grafana visualization
        
        Returns:
            Dictionary with delivery statistics and time-series data
        """
        orders = await self._get_all_orders()
        
        # Calculate metrics
        total_orders = len(orders)
        delivered_orders = [o for o in orders if o.get('status') == 'delivered']
        in_transit_orders = [o for o in orders if o.get('status') == 'in_transit']
        dispatched_orders = [o for o in orders if o.get('status') == 'dispatched']
        
        # Time-based metrics
        today_delivered = self._count_orders_by_date(delivered_orders, days=1)
        week_delivered = self._count_orders_by_date(delivered_orders, days=7)
        month_delivered = self._count_orders_by_date(delivered_orders, days=30)
        
        # Supplier metrics
        supplier_stats = self._get_supplier_statistics(delivered_orders)
        
        # Driver metrics
        driver_stats = self._get_driver_statistics(delivered_orders)
        
        # Hourly delivery distribution
        hourly_distribution = self._get_hourly_distribution(delivered_orders)
        
        return {
            "summary": {
                "total_orders": total_orders,
                "total_delivered": len(delivered_orders),
                "in_transit": len(in_transit_orders),
                "dispatched": len(dispatched_orders),
                "delivery_rate": round(len(delivered_orders) / total_orders * 100, 2) if total_orders > 0 else 0
            },
            "time_series": {
                "today": today_delivered,
                "last_7_days": week_delivered,
                "last_30_days": month_delivered
            },
            "by_supplier": supplier_stats,
            "by_driver": driver_stats,
            "hourly_distribution": hourly_distribution,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format for Grafana
        
        Returns:
            String in Prometheus exposition format
        """
        metrics = await self.get_delivery_metrics()
        
        lines = [
            "# HELP pizza_orders_total Total number of pizza orders",
            "# TYPE pizza_orders_total counter",
            f"pizza_orders_total {metrics['summary']['total_orders']}",
            "",
            "# HELP pizza_orders_delivered Total number of delivered orders",
            "# TYPE pizza_orders_delivered counter",
            f"pizza_orders_delivered {metrics['summary']['total_delivered']}",
            "",
            "# HELP pizza_orders_in_transit Number of orders currently in transit",
            "# TYPE pizza_orders_in_transit gauge",
            f"pizza_orders_in_transit {metrics['summary']['in_transit']}",
            "",
            "# HELP pizza_orders_dispatched Number of orders dispatched",
            "# TYPE pizza_orders_dispatched gauge",
            f"pizza_orders_dispatched {metrics['summary']['dispatched']}",
            "",
            "# HELP pizza_delivery_rate_percent Percentage of orders delivered",
            "# TYPE pizza_delivery_rate_percent gauge",
            f"pizza_delivery_rate_percent {metrics['summary']['delivery_rate']}",
            "",
            "# HELP pizza_delivered_today Orders delivered today",
            "# TYPE pizza_delivered_today counter",
            f"pizza_delivered_today {metrics['time_series']['today']}",
            "",
            "# HELP pizza_delivered_week Orders delivered in last 7 days",
            "# TYPE pizza_delivered_week counter",
            f"pizza_delivered_week {metrics['time_series']['last_7_days']}",
            "",
            "# HELP pizza_delivered_month Orders delivered in last 30 days",
            "# TYPE pizza_delivered_month counter",
            f"pizza_delivered_month {metrics['time_series']['last_30_days']}",
            ""
        ]
        
        # Add supplier metrics
        for supplier, count in metrics['by_supplier'].items():
            lines.append(f'pizza_delivered_by_supplier{{supplier="{supplier}"}} {count}')
        lines.append("")
        
        # Add driver metrics
        for driver, count in metrics['by_driver'].items():
            lines.append(f'pizza_delivered_by_driver{{driver="{driver}"}} {count}')
        lines.append("")
        
        return "\n".join(lines)
    
    async def _get_all_orders(self) -> List[Dict]:
        """Fetch all orders from Redis"""
        keys = await self.redis.client.keys("order:*")
        orders = []
        for key in keys:
            order_data = await self.redis.client.get(key)
            if order_data:
                orders.append(json.loads(order_data))
        return orders
    
    def _count_orders_by_date(self, orders: List[Dict], days: int) -> int:
        """Count orders within the last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = 0
        
        for order in orders:
            updated_at = order.get('updated_at')
            if updated_at:
                try:
                    order_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    if order_date >= cutoff:
                        count += 1
                except (ValueError, AttributeError):
                    continue
        
        return count
    
    def _get_supplier_statistics(self, orders: List[Dict]) -> Dict[str, int]:
        """Get delivery count by supplier"""
        stats = {}
        for order in orders:
            supplier = order.get('supplier_name', 'Unknown')
            stats[supplier] = stats.get(supplier, 0) + 1
        return stats
    
    def _get_driver_statistics(self, orders: List[Dict]) -> Dict[str, int]:
        """Get delivery count by driver"""
        stats = {}
        for order in orders:
            driver = order.get('driver_name')
            if driver:
                stats[driver] = stats.get(driver, 0) + 1
        return stats
    
    def _get_hourly_distribution(self, orders: List[Dict]) -> Dict[int, int]:
        """Get delivery distribution by hour of day"""
        distribution = {hour: 0 for hour in range(24)}
        
        for order in orders:
            updated_at = order.get('updated_at')
            if updated_at:
                try:
                    order_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    hour = order_date.hour
                    distribution[hour] += 1
                except (ValueError, AttributeError):
                    continue
        
        return distribution
