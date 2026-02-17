import redis.asyncio as redis
from config import settings

class RedisClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        connection_params = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True
        }
        
        # Add username if provided
        if settings.redis_username:
            connection_params["username"] = settings.redis_username
        
        # Add password if provided
        if settings.redis_password:
            connection_params["password"] = settings.redis_password
        
        self.client = redis.Redis(**connection_params)
        await self.client.ping()
    
    async def disconnect(self):
        if self.client:
            await self.client.aclose()
    
    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)
    
    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

redis_client = RedisClient()
