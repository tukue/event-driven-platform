# Testing Guide - Event Driven Platform

## Overview
Comprehensive test suite covering unit tests, API tests, and end-to-end integration tests.

## Setup

### Install Test Dependencies
```bash
cd backend
pip install -r requirements.txt
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suites

**Unit Tests (Models & Services):**
```bash
pytest tests/test_models.py tests/test_order_service.py -v
```

**API Tests:**
```bash
pytest tests/test_api.py -v
```

**Integration Tests:**
```bash
pytest tests/test_integration.py -v
```

### Using Test Runner Script
```bash
# All tests
python run_tests.py

# Unit tests only
python run_tests.py unit

# API tests only
python run_tests.py api

# Integration tests only
python run_tests.py integration
```

## Test Coverage

### Unit Tests (`test_models.py`)
- ✅ Pizza order creation
- ✅ Order with customer details
- ✅ Order event creation
- ✅ Order status enum validation

### Service Tests (`test_order_service.py`)
- ✅ Create order
- ✅ Supplier accept/reject order
- ✅ Customer accept order
- ✅ Customer cannot accept before supplier
- ✅ Dispatch order
- ✅ Complete order lifecycle (8 states)
- ✅ Get all orders

### API Tests (`test_api.py`)
- ✅ POST /api/orders
- ✅ GET /api/orders
- ✅ POST /api/orders/{id}/supplier-respond
- ✅ POST /api/orders/{id}/customer-accept
- ✅ POST /api/orders/{id}/dispatch
- ✅ POST /api/orders/{id}/status
- ✅ Invalid order ID handling

### Integration Tests (`test_integration.py`)
- ✅ Complete order flow (creation → delivery)
- ✅ Multiple concurrent orders
- ✅ Supplier rejection flow
- ✅ Pricing calculation with various markups
- ✅ Order state validation

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_models.py           # Model unit tests
├── test_order_service.py    # Service layer tests
├── test_api.py              # API endpoint tests
└── test_integration.py      # End-to-end tests
```

## Key Test Scenarios

### 1. Complete Order Lifecycle
Tests the full flow from creation to delivery:
```
pending_supplier → supplier_accepted → customer_accepted → 
preparing → ready → dispatched → in_transit → delivered
```

### 2. Pricing Validation
Tests automatic markup calculation:
- $10 + 30% = $13.00
- $15 + 20% = $18.00
- $20 + 50% = $30.00
- $12.50 + 25% = $15.63

### 3. State Validation
Tests that orders follow proper state transitions:
- Customer cannot accept before supplier
- Orders progress through valid states only

### 4. Concurrent Operations
Tests handling multiple orders simultaneously

## Fixtures

### `redis_connection`
Provides Redis connection for tests

### `order_service`
Creates OrderService instance with Redis

### `client`
Provides AsyncClient for API testing

### `cleanup_redis`
Automatically cleans up test data after each test

## Running Tests with Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html  # Windows
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Test Output Example

```
tests/test_integration.py::test_complete_order_flow_integration 
1. Creating order...
   ✓ Order created: abc-123-def
2. Supplier accepting order...
   ✓ Supplier accepted
3. Customer accepting order...
   ✓ Customer accepted (Price: $20.25)
4. Starting preparation...
   ✓ Preparing
5. Marking as ready...
   ✓ Ready for pickup
6. Dispatching order...
   ✓ Dispatched to driver
7. Marking in transit...
   ✓ In transit
8. Marking as delivered...
   ✓ Delivered!
9. Verifying final state...
   ✓ Final state verified

✅ Complete integration test passed!
PASSED
```

## Troubleshooting

### Redis Connection Issues
Ensure Redis is configured in `.env`:
```env
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-password
```

### Test Cleanup
Tests automatically clean up data. If needed, manually clear:
```bash
python inspect_redis.py
# Then delete test orders
```

### Async Test Issues
Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Isolation**: Each test is independent
2. **Cleanup**: Automatic cleanup after each test
3. **Descriptive Names**: Test names explain what they test
4. **Assertions**: Clear assertion messages
5. **Coverage**: Aim for >80% code coverage

## Adding New Tests

### Template for New Test
```python
@pytest.mark.asyncio
async def test_new_feature(order_service):
    """Test description"""
    # Arrange
    order = PizzaOrder(...)
    
    # Act
    result = await order_service.some_method(order)
    
    # Assert
    assert result.status == expected_status
```

## Performance Testing

For load testing, use:
```bash
pip install locust

# Create locustfile.py
# Run: locust -f locustfile.py
```

---

**Test Coverage Goal:** 80%+
**Current Status:** ✅ All critical paths covered
