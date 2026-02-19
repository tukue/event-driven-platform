from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pizza Delivery Marketplace - Simple")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    print("✅ Health check hit")
    return {"status": "ok"}

@app.get("/api/orders")
async def get_orders():
    print("✅ Get orders hit")
    return []

@app.post("/api/orders")
async def create_order(data: dict):
    print(f"✅ Create order hit: {data}")
    return {"status": "created", "data": data}
