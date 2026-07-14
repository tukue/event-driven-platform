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
        
        total_orders = len(orders)
        delivered_orders = [o for o in orders if o.get('status') == 'delivered']
        in_transit_orders = [o for o in orders if o.get('status') == 'in_transit']
        dispatched_orders = [o for o in orders if o.get('status') == 'dispatched']
        
        today_delivered = self._count_orders_by_date(delivered_orders, days=1)
        week_delivered = self._count_orders_by_date(delivered_orders, days=7)
        month_delivered = self._count_orders_by_date(delivered_orders, days=30)
        
        source_stats = self._get_source_statistics(delivered_orders)
        driver_stats = self._get_driver_statistics(delivered_orders)
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
            "by_source": source_stats,
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
            "# HELP orders_total Total number of orders",
            "# TYPE orders_total counter",
            f"orders_total {metrics['summary']['total_orders']}",
            "",
            "# HELP orders_delivered Total number of delivered orders",
            "# TYPE orders_delivered counter",
            f"orders_delivered {metrics['summary']['total_delivered']}",
            "",
            "# HELP orders_in_transit Number of orders currently in transit",
            "# TYPE orders_in_transit gauge",
            f"orders_in_transit {metrics['summary']['in_transit']}",
            "",
            "# HELP orders_dispatched Number of orders dispatched",
            "# TYPE orders_dispatched gauge",
            f"orders_dispatched {metrics['summary']['dispatched']}",
            "",
            "# HELP delivery_rate_percent Percentage of orders delivered",
            "# TYPE delivery_rate_percent gauge",
            f"delivery_rate_percent {metrics['summary']['delivery_rate']}",
            "",
            "# HELP delivered_today Orders delivered today",
            "# TYPE delivered_today counter",
            f"delivered_today {metrics['time_series']['today']}",
            "",
            "# HELP delivered_week Orders delivered in last 7 days",
            "# TYPE delivered_week counter",
            f"delivered_week {metrics['time_series']['last_7_days']}",
            "",
            "# HELP delivered_month Orders delivered in last 30 days",
            "# TYPE delivered_month counter",
            f"delivered_month {metrics['time_series']['last_30_days']}",
            ""
        ]
        
        for source, count in metrics['by_source'].items():
            lines.append(f'delivered_by_source{{source="{source}"}} {count}')
        lines.append("")
        
        for driver, count in metrics['by_driver'].items():
            lines.append(f'delivered_by_driver{{driver="{driver}"}} {count}')
        lines.append("")
        
        return "\n".join(lines)
    
    async def _get_all_orders(self) -> List[Dict]:
        """Fetch all orders from Redis"""
        keys = []
        cursor = 0
        while True:
            cursor, partial_keys = await self.redis.client.scan(cursor, match="order:*", count=100)
            keys.extend(partial_keys)
            if cursor == 0:
                break
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
    
    def _get_source_statistics(self, orders: List[Dict]) -> Dict[str, int]:
        """Get delivery count by source"""
        stats = {}
        for order in orders:
            source = order.get('source_name', 'Unknown')
            stats[source] = stats.get(source, 0) + 1
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
