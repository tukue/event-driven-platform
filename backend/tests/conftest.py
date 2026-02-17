import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
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
    
    mock.client.set = mock_set
    mock.client.get = mock_get
    mock.client.keys = mock_keys
    
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
    
    # Mock the redis_client used by the app
    mock_redis = MagicMock()
    mock_redis.client = AsyncMock()
    mock_redis._storage = {}
    
    async def mock_set(key, value):
        mock_redis._storage[key] = value
        return True
    
    async def mock_get(key):
        return mock_redis._storage.get(key)
    
    async def mock_keys(pattern):
        return [k for k in mock_redis._storage.keys() if pattern.replace("*", "") in k]
    
    # Mock publish operation (must be AsyncMock)
    mock_redis.publish = AsyncMock(return_value=1)
    
    mock_redis.client.set = mock_set
    mock_redis.client.get = mock_get
    mock_redis.client.keys = mock_keys
    
    # Patch the redis_client in main module
    mocker.patch('main.redis_client', mock_redis)
    
    # Create order service with mocked redis and patch it in main
    mock_order_service = OrderService(mock_redis)
    mocker.patch('main.order_service', mock_order_service)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
