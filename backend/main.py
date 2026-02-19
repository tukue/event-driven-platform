from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from redis_client import redis_client
from services.order_service import OrderService
from services.delivery_service import DeliveryService
from services.state_service import StateService, CachedStateService
from services.metrics_service import MetricsService
from models import PizzaOrder, OrderStatus, EventBatch, BatchResult
import asyncio

app = FastAPI(title="Pizza Delivery Marketplace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

order_service = None
delivery_service = None
state_service = None
metrics_service = None

@app.on_event("startup")
async def startup():
    print("🔵 Starting up...")
    try:
        print("🔵 Connecting to Redis...")
        # Comment out Redis for testing
        # await asyncio.wait_for(redis_client.connect(), timeout=10.0)
        print("⚠️  Redis connection SKIPPED for testing")
        
        global order_service, delivery_service, state_service, metrics_service
        # Comment out services that need Redis
        # order_service = OrderService(redis_client)
        # delivery_service = DeliveryService(redis_client)
        # base_state_service = StateService(redis_client)
        # state_service = CachedStateService(base_state_service, redis_client)
        # metrics_service = MetricsService(redis_client)
        print("⚠️  Services initialization SKIPPED for testing")
        print("✅ Startup complete (test mode)")
    except asyncio.TimeoutError:
        print("❌ Redis connection timed out!")
        raise
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    await redis_client.disconnect()

@app.get("/health")
async def health():
    """Simple health check that doesn't use Redis"""
    return {"status": "ok", "message": "Backend is running"}

@app.post("/api/orders")
async def create_order(order: PizzaOrder):
    print(f"🔵 Received order creation request: {order.pizza_name}")
    try:
        event = await order_service.create_order(order)
        print(f"🟢 Order created successfully: {event.order.id}")
        return event.model_dump(mode='json')
    except Exception as e:
        print(f"🔴 Error creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders/{order_id}/supplier-respond")
async def supplier_respond(order_id: str, accept: bool, notes: str = None, estimated_time: int = None):
    try:
        event = await order_service.supplier_respond(order_id, accept, notes, estimated_time)
        return event.model_dump(mode='json')
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/orders/{order_id}/customer-accept")
async def customer_accept(order_id: str, customer_name: str, delivery_address: str):
    try:
        event = await order_service.customer_accept(order_id, customer_name, delivery_address)
        return event.model_dump(mode='json')
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/orders/{order_id}/dispatch")
async def dispatch_order(order_id: str, driver_name: str):
    try:
        event = await order_service.dispatch_order(order_id, driver_name)
        return event.model_dump(mode='json')
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/orders/{order_id}/status")
async def update_order_status(order_id: str, status: OrderStatus):
    try:
        event = await order_service.update_status(order_id, status)
        return event.model_dump(mode='json')
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/orders")
async def get_orders():
    return await order_service.get_all_orders()

@app.get("/api/orders/{order_id}/delivery")
async def get_delivery_info(order_id: str):
    """Get delivery tracking information for an order by UUID"""
    try:
        delivery_info = await delivery_service.get_delivery_info(order_id)
        return delivery_info
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not been dispatched" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.get("/api/track/{tracking_id}")
async def track_by_tracking_id(tracking_id: str):
    """Track order using human-readable tracking ID (e.g., PIZZA-2024-001234)"""
    try:
        # Find order by tracking_id
        order = await order_service.get_order_by_tracking_id(tracking_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order with tracking ID {tracking_id} not found")
        
        # If dispatched, return full delivery info
        if order["status"] in ["dispatched", "in_transit", "delivered"]:
            delivery_info = await delivery_service.get_delivery_info(order["id"])
            return delivery_info
        else:
            # Return basic order info if not yet dispatched
            return {
                "order_id": order["id"],
                "tracking_id": order["tracking_id"],
                "supplier_tracking_id": order["supplier_tracking_id"],
                "status": order["status"],
                "supplier_name": order["supplier_name"],
                "pizza_name": order["pizza_name"],
                "created_at": order["created_at"],
                "message": "Order not yet dispatched. Check back soon!"
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/state")
async def get_system_state(include_completed: bool = True, limit: int = None):
    """Get complete system state with caching"""
    try:
        state = await state_service.get_system_state(include_completed, limit)
        return state.model_dump(mode='json')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system state: {str(e)}")

@app.post("/api/events/batch")
async def dispatch_event_batch(batch: EventBatch):
    """
    Dispatch multiple events atomically with correlation ID tracking
    
    This endpoint allows publishing multiple related events in a single transaction.
    All events succeed or all fail (atomic operation).
    """
    try:
        result = await order_service.dispatch_events(
            events=batch.events,
            correlation_id=batch.correlation_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Batch processing failed",
                    "correlation_id": result.correlation_id,
                    "processed_count": result.processed_count,
                    "failed_count": result.failed_count,
                    "errors": result.errors
                }
            )
        
        return result.model_dump(mode='json')
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process event batch: {str(e)}")

@app.get("/api/metrics")
async def get_metrics():
    """Get delivery metrics in JSON format for Grafana JSON datasource"""
    if metrics_service is None:
        raise HTTPException(status_code=503, detail="Metrics service not initialized")
    try:
        metrics = await metrics_service.get_delivery_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get metrics in Prometheus format for Grafana Prometheus datasource"""
    if metrics_service is None:
        raise HTTPException(status_code=503, detail="Metrics service not initialized")
    try:
        metrics = await metrics_service.get_prometheus_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Prometheus metrics: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pubsub = await redis_client.subscribe("pizza_orders")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        await pubsub.unsubscribe("pizza_orders")
        await pubsub.close()