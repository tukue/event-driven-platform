"""
Integration tests for Event Batching (Phase 3)
Following TDD principles - tests for multi-event dispatching
"""
import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_batch_dispatch_success(client):
    """
    Test successful batch event dispatching
    Requirement 3.1: Service can publish multiple events in a single transaction
    Requirement 3.3: Events are published in order
    """
    # Create a batch of events
    batch_data = {
        "correlation_id": "test-batch-001",
        "events": [
            {
                "event_type": "test.event1",
                "data": {"message": "First event"},
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "event_type": "test.event2",
                "data": {"message": "Second event"},
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "event_type": "test.event3",
                "data": {"message": "Third event"},
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Verify batch result
    assert result["correlation_id"] == "test-batch-001"
    assert result["success"] is True
    assert result["processed_count"] == 3
    assert result["failed_count"] == 0
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_batch_dispatch_with_correlation_id(client):
    """
    Test batch dispatching includes correlation ID in all events
    Requirement 3.4: Event batch includes correlation ID for tracking
    """
    batch_data = {
        "correlation_id": "test-correlation-123",
        "events": [
            {
                "event_type": "test.correlated_event",
                "data": {"test": "data"},
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["correlation_id"] == "test-correlation-123"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_batch_dispatch_empty_events(client):
    """
    Test batch dispatching with empty events list
    Edge case: Empty batch should succeed with 0 processed
    """
    batch_data = {
        "correlation_id": "test-empty-batch",
        "events": [],
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["processed_count"] == 0
    assert result["failed_count"] == 0


@pytest.mark.asyncio
async def test_batch_dispatch_large_batch(client):
    """
    Test batch dispatching with many events
    Performance test: Ensure system handles large batches
    """
    # Create a batch with 50 events
    events = [
        {
            "event_type": f"test.event_{i}",
            "data": {"index": i, "message": f"Event {i}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        for i in range(50)
    ]
    
    batch_data = {
        "correlation_id": "test-large-batch",
        "events": events,
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["processed_count"] == 50
    assert result["failed_count"] == 0


@pytest.mark.asyncio
async def test_batch_dispatch_order_workflow(client):
    """
    Test batch dispatching for complete order workflow
    Integration test: Multiple order state transitions in one batch
    """
    # Create an order first
    create_response = await client.post(
        "/api/orders",
        json={
            "supplier_name": "Batch Test Pizza",
            "pizza_name": "Workflow Pizza",
            "supplier_price": 15.0,
            "markup_percentage": 30.0
        }
    )
    
    assert create_response.status_code == 200
    order_id = create_response.json()["order"]["id"]
    
    # Create a batch of workflow events
    batch_data = {
        "correlation_id": f"workflow-{order_id}",
        "events": [
            {
                "event_type": "order.workflow_started",
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "event_type": "order.validation_passed",
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "event_type": "order.notification_sent",
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["processed_count"] == 3
    assert result["correlation_id"] == f"workflow-{order_id}"


@pytest.mark.asyncio
async def test_batch_dispatch_concurrent_batches(client):
    """
    Test multiple concurrent batch dispatches
    Concurrency test: Ensure batches don't interfere with each other
    """
    import asyncio
    
    # Create multiple batches concurrently
    batch_tasks = []
    for i in range(5):
        batch_data = {
            "correlation_id": f"concurrent-batch-{i}",
            "events": [
                {
                    "event_type": f"test.concurrent_{i}",
                    "data": {"batch_number": i},
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "created_at": datetime.utcnow().isoformat()
        }
        batch_tasks.append(client.post("/api/events/batch", json=batch_data))
    
    # Execute all batches concurrently
    responses = await asyncio.gather(*batch_tasks)
    
    # Verify all batches succeeded
    assert all(r.status_code == 200 for r in responses)
    
    # Verify each batch has unique correlation ID
    correlation_ids = [r.json()["correlation_id"] for r in responses]
    assert len(set(correlation_ids)) == 5  # All unique


@pytest.mark.asyncio
async def test_batch_dispatch_with_metadata(client):
    """
    Test batch dispatching with rich event metadata
    Requirement: Events can include arbitrary metadata
    """
    batch_data = {
        "correlation_id": "test-metadata-batch",
        "events": [
            {
                "event_type": "order.metadata_test",
                "data": {
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "custom_field": "custom_value"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await client.post("/api/events/batch", json=batch_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["processed_count"] == 1


@pytest.mark.asyncio
async def test_batch_dispatch_idempotency(client):
    """
    Test batch dispatching with same correlation ID
    Idempotency test: Same correlation ID can be used multiple times
    """
    batch_data = {
        "correlation_id": "idempotent-batch",
        "events": [
            {
                "event_type": "test.idempotent",
                "data": {"attempt": 1},
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Send same batch twice
    response1 = await client.post("/api/events/batch", json=batch_data)
    response2 = await client.post("/api/events/batch", json=batch_data)
    
    # Both should succeed
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Both should have same correlation ID
    assert response1.json()["correlation_id"] == "idempotent-batch"
    assert response2.json()["correlation_id"] == "idempotent-batch"


@pytest.mark.asyncio
async def test_batch_dispatch_performance(client):
    """
    Performance test: Ensure batch dispatching is fast
    Requirement: Batch endpoint responds within reasonable time
    """
    import time
    
    batch_data = {
        "correlation_id": "performance-test-batch",
        "events": [
            {
                "event_type": f"test.perf_{i}",
                "data": {"index": i},
                "timestamp": datetime.utcnow().isoformat()
            }
            for i in range(10)
        ],
        "created_at": datetime.utcnow().isoformat()
    }
    
    start_time = time.time()
    response = await client.post("/api/events/batch", json=batch_data)
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    # Batch of 10 events should complete quickly
    print(f"\nBatch dispatch time: {response_time_ms:.2f}ms")
    assert response_time_ms < 1000  # Should be under 1 second
