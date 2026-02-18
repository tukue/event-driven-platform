from models import PizzaOrder, OrderStatus
from datetime import datetime, timedelta
from typing import Optional

class DeliveryService:
    """Service for managing delivery tracking and information"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_delivery_info(self, order_id: str) -> dict:
        """
        Get delivery information for an order
        
        Args:
            order_id: The order ID to get delivery info for
            
        Returns:
            Dictionary with delivery information
            
        Raises:
            ValueError: If order not found or not dispatched
        """
        from services.order_service import OrderService
        order_service = OrderService(self.redis)
        
        try:
            order = await order_service._get_order(order_id)
        except ValueError:
            raise ValueError(f"Order {order_id} not found")
        
        # Check if order has been dispatched
        if order.status not in [OrderStatus.DISPATCHED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
            raise ValueError(f"Order {order_id} has not been dispatched yet")
        
        # Calculate delivery progress
        progress = self.calculate_progress(order)
        
        # Estimate arrival time
        estimated_arrival = self.estimate_arrival(order)
        
        return {
            "order_id": order.id,
            "tracking_id": order.tracking_id,
            "supplier_tracking_id": order.supplier_tracking_id,
            "status": order.status.value,
            "driver_name": order.driver_name,
            "delivery_address": order.delivery_address,
            "customer_name": order.customer_name,
            "supplier_name": order.supplier_name,
            "pizza_name": order.pizza_name,
            "progress_percentage": progress,
            "estimated_arrival_minutes": estimated_arrival,
            "timeline": self._get_timeline(order),
            "current_stage": self._get_current_stage(order.status)
        }
    
    def calculate_progress(self, order: PizzaOrder) -> int:
        """
        Calculate delivery progress as a percentage
        
        Args:
            order: The pizza order
            
        Returns:
            Progress percentage (0-100)
        """
        status_progress = {
            OrderStatus.DISPATCHED: 33,
            OrderStatus.IN_TRANSIT: 66,
            OrderStatus.DELIVERED: 100
        }
        return status_progress.get(order.status, 0)
    
    def estimate_arrival(self, order: PizzaOrder) -> Optional[int]:
        """
        Estimate arrival time in minutes
        
        Args:
            order: The pizza order
            
        Returns:
            Estimated minutes until arrival, or None if delivered
        """
        if order.status == OrderStatus.DELIVERED:
            return 0
        
        # Use estimated delivery time from order, or default
        base_time = order.estimated_delivery_time or 30
        
        # Adjust based on current status
        if order.status == OrderStatus.DISPATCHED:
            return base_time
        elif order.status == OrderStatus.IN_TRANSIT:
            # Assume halfway through delivery
            return base_time // 2
        
        return None
    
    def _get_timeline(self, order: PizzaOrder) -> list:
        """Get delivery timeline with timestamps"""
        timeline = []
        
        if order.created_at:
            timeline.append({
                "stage": "created",
                "timestamp": order.created_at.isoformat(),
                "completed": True
            })
        
        timeline.append({
            "stage": "dispatched",
            "timestamp": order.updated_at.isoformat() if order.status != OrderStatus.DISPATCHED else None,
            "completed": order.status in [OrderStatus.DISPATCHED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]
        })
        
        timeline.append({
            "stage": "in_transit",
            "timestamp": order.updated_at.isoformat() if order.status == OrderStatus.IN_TRANSIT else None,
            "completed": order.status in [OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]
        })
        
        timeline.append({
            "stage": "delivered",
            "timestamp": order.updated_at.isoformat() if order.status == OrderStatus.DELIVERED else None,
            "completed": order.status == OrderStatus.DELIVERED
        })
        
        return timeline
    
    def _get_current_stage(self, status: OrderStatus) -> str:
        """Get human-readable current stage"""
        stage_map = {
            OrderStatus.DISPATCHED: "Driver assigned - preparing for pickup",
            OrderStatus.IN_TRANSIT: "On the way to your location",
            OrderStatus.DELIVERED: "Delivered successfully"
        }
        return stage_map.get(status, "Unknown")
