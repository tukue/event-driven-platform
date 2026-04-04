import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
import os

# Set test environment variables before importing main
os.environ['REDIS_HOST'] = 'test-host'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_USERNAME'] = 'test'
os.environ['REDIS_PASSWORD'] = 'test'
os.environ['REDIS_DB'] = '0'

from main import app
from services.order_service import OrderService

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = MagicMock()
    mock.client = AsyncMock()
    
    # Mock storage for orders
    mock._storage = {}
    mock._streams = {}  # Storage for stream data
    
    # Mock set operation
    async def mock_set(key, value):
        mock._storage[key] = value
        return True
    
    # Mock get operation
    async def mock_get(key):
        return mock._storage.get(key)
    
    # Mock keys operation
    async def mock_keys(pattern):
        return [k for k in mock._storage.keys() if pattern.replace("*", "") in k]
    
    # Mock publish operation (must be AsyncMock)
    mock.publish = AsyncMock(return_value=1)
    
    # Mock stream operations
    async def mock_add_to_stream(stream_name, event_data, stream_id="*"):
        """Mock adding to stream"""
        if stream_name not in mock._streams:
            mock._streams[stream_name] = []
        # Generate a simple stream ID if not provided
        if stream_id == "*":
            stream_id = f"{len(mock._streams[stream_name])+1}-0"
        mock._streams[stream_name].append((stream_id, event_data))
        return stream_id
    
    async def mock_read_stream(stream_name, start_id="0", stop_id="+", count=None):
        """Mock reading from stream"""
        if stream_name not in mock._streams:
            return []
        entries = mock._streams[stream_name]
        if count:
            return entries[-count:]
        return entries
    
    async def mock_read_stream_group(stream_name, group_name, consumer_name, count=1, block=None):
        """Mock reading from consumer group"""
        if stream_name not in mock._streams:
            return []
        entries = mock._streams[stream_name]
        if count and len(entries) > 0:
            return [(stream_name, entries[-count:])]
        return []
    
    async def mock_create_consumer_group(stream_name, group_name, start_id="0", mkstream=True):
        """Mock creating consumer group"""
        return True
    
    async def mock_acknowledge_message(stream_name, group_name, message_ids):
        """Mock acknowledging messages"""
        return len(message_ids)
    
    async def mock_get_stream_info(stream_name):
        """Mock getting stream info"""
        if stream_name in mock._streams:
            return {
                "length": len(mock._streams[stream_name]),
                "first-entry": mock._streams[stream_name][0] if mock._streams[stream_name] else None,
                "last-entry": mock._streams[stream_name][-1] if mock._streams[stream_name] else None,
            }
        return None
    
    async def mock_get_pending_messages(stream_name, group_name, consumer_name=None):
        """Mock getting pending messages"""
        return []
    
    async def mock_trim_stream(stream_name, max_len, approximate=True):
        """Mock trimming stream"""
        if stream_name in mock._streams:
            mock._streams[stream_name] = mock._streams[stream_name][-max_len:]
        return len(mock._streams.get(stream_name, []))
    
    # Assign mock methods to the mock object
    mock.client.set = mock_set
    mock.client.get = mock_get
    mock.client.keys = mock_keys
    mock.add_to_stream = mock_add_to_stream
    mock.read_stream = mock_read_stream
    mock.read_stream_group = mock_read_stream_group
    mock.create_consumer_group = mock_create_consumer_group
    mock.acknowledge_message = mock_acknowledge_message
    mock.get_stream_info = mock_get_stream_info
    mock.get_pending_messages = mock_get_pending_messages
    mock.trim_stream = mock_trim_stream
    
    return mock

@pytest.fixture
def order_service(mock_redis):
    """Create order service instance with mocked Redis"""
    return OrderService(mock_redis)

@pytest.fixture
async def client(mocker):
    """Create test client with mocked Redis"""
    from httpx import ASGITransport
    from services.order_service import OrderService
    from services.delivery_service import DeliveryService
    from services.state_service import StateService, CachedStateService
    import main
    
    # Mock the redis_client used by the app
    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis._storage = {}
    mock_redis._streams = {}  # Storage for stream data
    
    async def mock_set(key, value):
        mock_redis._storage[key] = value
        return True
    
    async def mock_get(key):
        return mock_redis._storage.get(key)
    
    async def mock_keys(pattern):
        return [k for k in mock_redis._storage.keys() if pattern.replace("*", "") in k]
    
    # Mock publish operation (must be AsyncMock)
    mock_redis.publish = AsyncMock(return_value=1)
    
    # Mock stream operations
    async def mock_add_to_stream(stream_name, event_data, stream_id="*"):
        """Mock adding to stream"""
        if stream_name not in mock_redis._streams:
            mock_redis._streams[stream_name] = []
        # Generate a simple stream ID if not provided
        if stream_id == "*":
            stream_id = f"{len(mock_redis._streams[stream_name])+1}-0"
        mock_redis._streams[stream_name].append((stream_id, event_data))
        return stream_id
    
    async def mock_read_stream(stream_name, start_id="0", stop_id="+", count=None):
        """Mock reading from stream"""
        if stream_name not in mock_redis._streams:
            return []
        entries = mock_redis._streams[stream_name]
        if count:
            return entries[-count:]
        return entries
    
    async def mock_read_stream_group(stream_name, group_name, consumer_name, count=1, block=None):
        """Mock reading from consumer group"""
        if stream_name not in mock_redis._streams:
            return []
        entries = mock_redis._streams[stream_name]
        if count and len(entries) > 0:
            return [(stream_name, entries[-count:])]
        return []
    
    async def mock_create_consumer_group(stream_name, group_name, start_id="0", mkstream=True):
        """Mock creating consumer group"""
        return True
    
    async def mock_acknowledge_message(stream_name, group_name, message_ids):
        """Mock acknowledging messages"""
        return len(message_ids)
    
    async def mock_get_stream_info(stream_name):
        """Mock getting stream info"""
        if stream_name in mock_redis._streams:
            return {
                "length": len(mock_redis._streams[stream_name]),
                "first-entry": mock_redis._streams[stream_name][0] if mock_redis._streams[stream_name] else None,
                "last-entry": mock_redis._streams[stream_name][-1] if mock_redis._streams[stream_name] else None,
            }
        return None
    
    async def mock_get_pending_messages(stream_name, group_name, consumer_name=None):
        """Mock getting pending messages"""
        return []
    
    async def mock_trim_stream(stream_name, max_len, approximate=True):
        """Mock trimming stream"""
        if stream_name in mock_redis._streams:
            mock_redis._streams[stream_name] = mock_redis._streams[stream_name][-max_len:]
        return len(mock_redis._streams.get(stream_name, []))
    
    # Assign mock methods to the mock object
    mock_redis.client.set = mock_set
    mock_redis.client.get = mock_get
    mock_redis.client.keys = mock_keys
    mock_redis.add_to_stream = mock_add_to_stream
    mock_redis.read_stream = mock_read_stream
    mock_redis.read_stream_group = mock_read_stream_group
    mock_redis.create_consumer_group = mock_create_consumer_group
    mock_redis.acknowledge_message = mock_acknowledge_message
    mock_redis.get_stream_info = mock_get_stream_info
    mock_redis.get_pending_messages = mock_get_pending_messages
    mock_redis.trim_stream = mock_trim_stream
    
    # Patch the redis_client in main module
    mocker.patch('main.redis_client', mock_redis)
    
    # Create services with mocked redis and set them directly on main module
    main.order_service = OrderService(mock_redis)
    main.delivery_service = DeliveryService(mock_redis)
    base_state_service = StateService(mock_redis)
    main.state_service = CachedStateService(base_state_service, mock_redis)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
