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
    
    # Legacy pub/sub methods (keeping for backward compatibility)
    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)
    
    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    # Redis Streams methods
    async def add_to_stream(self, stream_name: str, event_data: dict, stream_id: str = "*") -> str:
        """
        Add an event to a Redis Stream
        
        Args:
            stream_name: Name of the stream
            event_data: Event data as dictionary
            stream_id: Stream ID (use "*" for auto-generated)
            
        Returns:
            The stream ID of the added entry
        """
        return await self.client.xadd(stream_name, event_data, id=stream_id)
    
    async def read_stream(self, stream_name: str, start_id: str = "0", count: int = None) -> list:
        """
        Read events from a stream
        
        Args:
            stream_name: Name of the stream
            start_id: Starting ID ("0" for all, "$" for new messages)
            count: Maximum number of entries to return
            
        Returns:
            List of stream entries
        """
        entries = await self.client.xrange(stream_name, start_id, "+", count=count)
        return entries
    
    async def read_stream_group(self, stream_name: str, group_name: str, consumer_name: str, 
                               count: int = 1, block: int = None) -> list:
        """
        Read events from a stream using consumer groups
        
        Args:
            stream_name: Name of the stream
            group_name: Consumer group name
            consumer_name: Consumer name
            count: Number of messages to read
            block: Block timeout in milliseconds
            
        Returns:
            List of pending messages for the consumer
        """
        try:
            messages = await self.client.xreadgroup(
                group_name, consumer_name, {stream_name: ">"}, count=count, block=block
            )
            return messages
        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                # Create consumer group if it doesn't exist
                await self.create_consumer_group(stream_name, group_name)
                # Retry reading
                messages = await self.client.xreadgroup(
                    group_name, consumer_name, {stream_name: ">"}, count=count, block=block
                )
                return messages
            raise
    
    async def create_consumer_group(self, stream_name: str, group_name: str, start_id: str = "0"):
        """
        Create a consumer group for a stream
        
        Args:
            stream_name: Name of the stream
            group_name: Consumer group name
            start_id: Starting ID for the group
        """
        try:
            await self.client.xgroup_create(stream_name, group_name, start_id, mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    
    async def acknowledge_message(self, stream_name: str, group_name: str, message_ids: list):
        """
        Acknowledge processing of messages in a consumer group
        
        Args:
            stream_name: Name of the stream
            group_name: Consumer group name
            message_ids: List of message IDs to acknowledge
        """
        await self.client.xack(stream_name, group_name, *message_ids)
    
    async def get_stream_info(self, stream_name: str) -> dict:
        """
        Get information about a stream
        
        Args:
            stream_name: Name of the stream
            
        Returns:
            Stream information dictionary
        """
        try:
            info = await self.client.xinfo_stream(stream_name)
            return info
        except redis.ResponseError:
            return None
    
    async def get_pending_messages(self, stream_name: str, group_name: str, consumer_name: str = None) -> list:
        """
        Get pending messages for a consumer group
        
        Args:
            stream_name: Name of the stream
            group_name: Consumer group name
            consumer_name: Specific consumer name (optional)
            
        Returns:
            List of pending messages
        """
        pending = await self.client.xpending(stream_name, group_name)
        return pending
    
    async def trim_stream(self, stream_name: str, max_len: int, approximate: bool = True):
        """
        Trim a stream to a maximum length
        
        Args:
            stream_name: Name of the stream
            max_len: Maximum number of entries to keep
            approximate: Whether to use approximate trimming
        """
        await self.client.xtrim(stream_name, maxlen=max_len, approximate=approximate)

redis_client = RedisClient()
