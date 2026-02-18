from models import SystemState, SystemStatistics, ActiveDriver, OrderStatus
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

class StateService:
    """Service for managing system state and statistics"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_system_state(self, include_completed: bool = True, limit: Optional[int] = None) -> SystemState:
        """
        Get complete system state
        
        Args:
            include_completed: Whether to include completed orders
            limit: Maximum number of orders per status to return
            
        Returns:
            SystemState object with all system information
        """
        # Get statistics
        statistics = await self.get_statistics()
        
        # Get orders grouped by status
        orders_by_status = await self.get_orders_by_status(include_completed, limit)
        
        # Get active drivers
        active_drivers = await self.get_active_drivers()
        
        return SystemState(
            statistics=statistics,
            orders_by_status=orders_by_status,
            active_drivers=active_drivers,
            last_updated=datetime.utcnow()
        )
    
    async def get_statistics(self) -> SystemStatistics:
        """
        Get system-wide statistics
        
        Returns:
            SystemStatistics object with counts and metrics
        """
        # Get all orders
        keys = await self.redis.client.keys("order:*")
        orders = []
        
        for key in keys:
            order_data = await self.redis.client.get(key)
            if order_data:
                orders.append(json.loads(order_data))
        
        # Count orders by status
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = 0
        
        today = datetime.utcnow().date()
        completed_today = 0
        active_deliveries = 0
        
        for order in orders:
            status = order.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            
            # Count completed today
            if status == 'delivered':
                order_date = datetime.fromisoformat(order.get('updated_at', '1970-01-01')).date()
                if order_date == today:
                    completed_today += 1
            
            # Count active deliveries
            if status in ['dispatched', 'in_transit']:
                active_deliveries += 1
        
        return SystemStatistics(
            total_orders=len(orders),
            active_deliveries=active_deliveries,
            completed_today=completed_today,
            pending_supplier=status_counts.get('pending_supplier', 0),
            preparing=status_counts.get('preparing', 0),
            ready=status_counts.get('ready', 0),
            dispatched=status_counts.get('dispatched', 0),
            in_transit=status_counts.get('in_transit', 0),
            delivered=status_counts.get('delivered', 0)
        )
    
    async def get_orders_by_status(self, include_completed: bool = True, limit: Optional[int] = None) -> Dict[str, List[dict]]:
        """
        Get orders grouped by status
        
        Args:
            include_completed: Whether to include delivered/cancelled orders
            limit: Maximum orders per status
            
        Returns:
            Dictionary with status as key and list of orders as value
        """
        # Get all orders
        keys = await self.redis.client.keys("order:*")
        orders = []
        
        for key in keys:
            order_data = await self.redis.client.get(key)
            if order_data:
                orders.append(json.loads(order_data))
        
        # Group by status
        orders_by_status = {}
        
        for order in orders:
            status = order.get('status', 'unknown')
            
            # Skip completed orders if not requested
            if not include_completed and status in ['delivered', 'cancelled']:
                continue
            
            if status not in orders_by_status:
                orders_by_status[status] = []
            
            orders_by_status[status].append(order)
        
        # Apply limit if specified
        if limit:
            for status in orders_by_status:
                orders_by_status[status] = orders_by_status[status][:limit]
        
        # Sort orders within each status by created_at (newest first)
        for status in orders_by_status:
            orders_by_status[status].sort(
                key=lambda x: x.get('created_at', '1970-01-01'),
                reverse=True
            )
        
        return orders_by_status
    
    async def get_active_drivers(self) -> List[ActiveDriver]:
        """
        Get list of active drivers and their assignments
        
        Returns:
            List of ActiveDriver objects
        """
        # Get all orders with drivers assigned
        keys = await self.redis.client.keys("order:*")
        active_drivers = {}
        
        for key in keys:
            order_data = await self.redis.client.get(key)
            if order_data:
                order = json.loads(order_data)
                driver_name = order.get('driver_name')
                status = order.get('status')
                
                if driver_name and status in ['dispatched', 'in_transit']:
                    if driver_name not in active_drivers:
                        active_drivers[driver_name] = ActiveDriver(
                            driver_name=driver_name,
                            order_id=order.get('id'),
                            status=status,
                            assigned_at=datetime.fromisoformat(order.get('updated_at', '1970-01-01'))
                        )
                    else:
                        # If driver has multiple orders, keep the most recent
                        current_assigned = active_drivers[driver_name].assigned_at
                        order_assigned = datetime.fromisoformat(order.get('updated_at', '1970-01-01'))
                        if order_assigned > current_assigned:
                            active_drivers[driver_name] = ActiveDriver(
                                driver_name=driver_name,
                                order_id=order.get('id'),
                                status=status,
                                assigned_at=order_assigned
                            )
        
        return list(active_drivers.values())


class CachedStateService:
    """Cached wrapper for StateService with 5-second TTL"""
    
    def __init__(self, state_service: StateService, redis_client):
        self.state_service = state_service
        self.redis = redis_client
        self.cache_ttl = 5  # 5 seconds
        self.cache_key_prefix = "state_cache:"
    
    async def get_system_state(self, include_completed: bool = True, limit: Optional[int] = None) -> SystemState:
        """
        Get system state with caching
        
        Args:
            include_completed: Whether to include completed orders
            limit: Maximum orders per status
            
        Returns:
            Cached or fresh SystemState
        """
        # Create cache key based on parameters
        cache_key = f"{self.cache_key_prefix}system_state:{include_completed}:{limit}"
        
        # Try to get from cache
        cached_data = await self.redis.client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return SystemState(**data)
            except (json.JSONDecodeError, ValueError):
                # Cache corrupted, continue to fetch fresh data
                pass
        
        # Get fresh data
        state = await self.state_service.get_system_state(include_completed, limit)
        
        # Cache the result
        await self.redis.client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(state.model_dump(mode='json'), default=str)
        )
        
        return state
    
    async def get_statistics(self) -> SystemStatistics:
        """Get statistics with caching"""
        cache_key = f"{self.cache_key_prefix}statistics"
        
        # Try cache first
        cached_data = await self.redis.client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return SystemStatistics(**data)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Get fresh data
        stats = await self.state_service.get_statistics()
        
        # Cache it
        await self.redis.client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(stats.model_dump(mode='json'), default=str)
        )
        
        return stats
    
    async def invalidate_cache(self):
        """Invalidate all state cache entries"""
        keys = await self.redis.client.keys(f"{self.cache_key_prefix}*")
        if keys:
            await self.redis.client.delete(*keys)
    
    async def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics"""
        # This would require implementing cache metrics tracking
        # For now, return basic info
        keys = await self.redis.client.keys(f"{self.cache_key_prefix}*")
        return {
            "cached_entries": len(keys),
            "cache_ttl_seconds": self.cache_ttl
        }   