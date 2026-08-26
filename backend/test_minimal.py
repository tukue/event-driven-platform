"""
Minimal FastAPI test to isolate the hanging issue
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    print("✅ Root endpoint hit")
    return {"message": "Hello World"}

@app.get("/test")
async def test():
    print("✅ Test endpoint hit")
    return {"status": "working"}

@app.post("/test-post")
async def test_post(data: dict):
    print(f"✅ Post endpoint hit with data: {data}")
    return {"received": data}

if __name__ == "__main__":
    print("🚀 Starting minimal test server on port 8001...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
