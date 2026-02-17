from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis_client import redis_client
from services.order_service import OrderService
from models import PizzaOrder, OrderStatus
import asyncio

app = FastAPI(title="Pizza Delivery Marketplace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

order_service = None

@app.on_event("startup")
async def startup():
    await redis_client.connect()
    global order_service
    order_service = OrderService(redis_client)

@app.on_event("shutdown")
async def shutdown():
    await redis_client.disconnect()

@app.post("/api/orders")
async def create_order(order: PizzaOrder):
    event = await order_service.create_order(order)
    return event.model_dump(mode='json')

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
