# Phase 5: System Dashboard - Testing Guide

## 🧪 Test Suite Overview

Phase 5 includes comprehensive integration tests for the System Dashboard functionality.

## 📋 Test Files

### 1. Automated Integration Test
**File**: `backend/test_system_dashboard_auto.py`

Simple standalone test script that validates:
- `/api/state` endpoint structure
- Statistics accuracy
- Orders by status grouping
- Active drivers tracking
- Real-time updates
- Query parameters (include_completed, limit)

**Run**:
```bash
cd backend
python test_system_dashboard_auto.py
```

### 2. Pytest Integration Tests
**File**: `backend/tests/test_system_dashboard_integration.py`

Comprehensive pytest test suite with 11 test cases:
1. `test_system_state_endpoint_structure` - Validates response structure
2. `test_system_statistics_fields` - Checks all statistic fields
3. `test_orders_by_status_structure` - Verifies order grouping
4. `test_active_drivers_tracking` - Tests driver tracking
5. `test_active_drivers_removed_after_delivery` - Validates driver removal
6. `test_include_completed_parameter` - Tests filtering
7. `test_limit_parameter` - Tests pagination
8. `test_statistics_update_on_order_creation` - Tests real-time stats
9. `test_active_deliveries_count` - Validates delivery counting
10. `test_last_updated_timestamp` - Checks timestamp format

**Run**:
```bash
cd backend
pytest tests/test_system_dashboard_integration.py -v
```

## 🚀 Running Tests

### Prerequisites

1. **Backend Running**:
```bash
cd backend
python main.py
```

2. **Redis Running**:
```bash
# Make sure Redis is accessible
redis-cli ping
# Should return: PONG
```

### Quick Test (Automated)

```bash
cd backend
python test_system_dashboard_auto.py
```

**Expected Output**:
```
=== SYSTEM DASHBOARD INTEGRATION TEST ===

============================================================
Step 1: Testing /api/state endpoint
============================================================
✓ Endpoint accessible

============================================================
Step 2: Verifying statistics structure
============================================================
✓ All statistics present: 9 fields
✓ Total orders: 5
✓ Active deliveries: 2
✓ Completed today: 1

... (more steps)

============================================================
✓ ALL TESTS PASSED!
============================================================
```

### Full Test Suite (Pytest)

```bash
cd backend
pytest tests/test_system_dashboard_integration.py -v
```

**Expected Output**:
```
tests/test_system_dashboard_integration.py::test_system_state_endpoint_structure PASSED
tests/test_system_dashboard_integration.py::test_system_statistics_fields PASSED
tests/test_system_dashboard_integration.py::test_orders_by_status_structure PASSED
... (11 tests total)

============ 11 passed in 2.34s ============
```

## 📊 Test Coverage

### API Endpoints Tested
- ✅ `GET /api/state`
- ✅ `GET /api/state?include_completed=false`
- ✅ `GET /api/state?limit=2`
- ✅ `POST /api/orders` (for test data)
- ✅ `POST /api/orders/{id}/dispatch` (for driver tests)

### Features Tested

#### Statistics
- ✅ Total orders count
- ✅ Active deliveries count
- ✅ Completed today count
- ✅ Status-specific counts (pending, preparing, ready, etc.)
- ✅ Real-time updates on order changes

#### Orders by Status
- ✅ Proper grouping by status
- ✅ Order structure validation
- ✅ Filtering (include_completed parameter)
- ✅ Pagination (limit parameter)
- ✅ Sorting (newest first)

#### Active Drivers
- ✅ Driver tracking when dispatched
- ✅ Driver status updates (dispatched → in_transit)
- ✅ Driver removal after delivery
- ✅ Multiple drivers handling
- ✅ Order assignment tracking

#### Data Integrity
- ✅ Response structure validation
- ✅ Field type checking
- ✅ Timestamp format validation
- ✅ Non-negative value validation

## 🎯 Manual Testing Checklist

### Dashboard UI Testing

1. **Initial Load**
   - [ ] Dashboard loads without errors
   - [ ] Statistics cards display correctly
   - [ ] Connection status shows "🟢 Live"
   - [ ] Last updated timestamp is current

2. **Statistics Cards**
   - [ ] Total Orders card shows correct count
   - [ ] Active Deliveries card shows correct count
   - [ ] Completed Today card shows correct count
   - [ ] Pending Source card shows correct count
   - [ ] Cards have hover effects

3. **Status Breakdown**
   - [ ] All status items display
   - [ ] Counts match statistics
   - [ ] Hover effects work

4. **Orders by Status**
   - [ ] Sections are collapsible
   - [ ] Click to expand shows orders
   - [ ] Order details are complete
   - [ ] Empty states show correctly
   - [ ] Color coding is correct

5. **Active Drivers**
   - [ ] Drivers display when orders dispatched
   - [ ] Driver names show correctly
   - [ ] Order IDs are displayed
   - [ ] Status indicators work (dispatched/in_transit)
   - [ ] Pulsing animation on in_transit
   - [ ] Drivers removed after delivery

6. **Real-Time Updates**
   - [ ] Create order → statistics update
   - [ ] Dispatch order → driver appears
   - [ ] Status change → UI updates
   - [ ] Notification toasts appear
   - [ ] Auto-refresh works (5 seconds)

7. **Navigation**
   - [ ] Switch between Marketplace and Dashboard
   - [ ] Active tab is highlighted
   - [ ] Connection status persists
   - [ ] No data loss on view switch

### Error Handling

1. **Backend Down**
   - [ ] Error message displays
   - [ ] Retry button works
   - [ ] Connection status shows "🔴 Disconnected"

2. **No Data**
   - [ ] Empty states display correctly
   - [ ] "No orders yet" message shows
   - [ ] "No active drivers" message shows

3. **Network Issues**
   - [ ] Loading states show during fetch
   - [ ] Errors are caught gracefully
   - [ ] User can retry

## 🔍 Test Scenarios

### Scenario 1: New Order Flow
```
1. Open Dashboard
2. Note initial statistics
3. Switch to Marketplace
4. Create new order
5. Switch back to Dashboard
6. Verify:
   - Total orders increased by 1
   - Order appears in "Pending Source" section
   - Notification toast appeared
   - Last updated timestamp changed
```

### Scenario 2: Complete Delivery Flow
```
1. Create order in Marketplace
2. Accept as source
3. Accept as buyer
4. Mark as preparing
5. Mark as ready
6. Dispatch with driver
7. Switch to Dashboard
8. Verify:
   - Active deliveries count increased
   - Driver appears in Active Drivers
   - Order in "Dispatched" section
9. Mark as in_transit
10. Verify:
    - Driver status updated
    - Pulsing indicator on driver
    - Order moved to "In Transit" section
11. Mark as delivered
12. Verify:
    - Active deliveries count decreased
    - Driver removed from Active Drivers
    - Order in "Delivered" section
    - Completed today count increased
```

### Scenario 3: Multiple Drivers
```
1. Create 3 orders
2. Dispatch all with different drivers
3. Open Dashboard
4. Verify:
   - All 3 drivers in Active Drivers
   - Each driver has correct order ID
   - Active deliveries count is 3
5. Complete 1 delivery
6. Verify:
   - 2 drivers remain
   - Active deliveries count is 2
```

## 📈 Performance Testing

### Load Test
```bash
# Create 50 orders quickly
for i in {1..50}; do
  curl -X POST http://localhost:8000/api/orders \
    -H "Content-Type: application/json" \
    -d "{\"item_name\":\"Test $i\",\"source_name\":\"Source\",\"source_price\":12.99}"
done

# Check dashboard performance
# Should load in < 2 seconds
```

### Cache Test
```bash
# First request (cache miss)
time curl http://localhost:8000/api/state

# Second request (cache hit, should be faster)
time curl http://localhost:8000/api/state

# Wait 6 seconds for cache expiry
sleep 6

# Third request (cache miss again)
time curl http://localhost:8000/api/state
```

## 🐛 Common Issues

### Issue: Tests Fail with Connection Error
**Solution**: Make sure backend is running on port 8000
```bash
cd backend
python main.py
```

### Issue: Statistics Don't Update
**Solution**: Wait for cache to expire (5 seconds) or restart backend

### Issue: Drivers Not Appearing
**Solution**: Ensure order is dispatched (not just ready)

### Issue: WebSocket Not Connecting
**Solution**: Check browser console for errors, verify backend WebSocket endpoint

## ✅ Test Completion Checklist

- [ ] Automated test passes (`test_system_dashboard_auto.py`)
- [ ] All pytest tests pass (11/11)
- [ ] Manual UI testing complete
- [ ] Real-time updates verified
- [ ] Error handling tested
- [ ] Performance acceptable
- [ ] Mobile responsive verified
- [ ] Cross-browser tested (Chrome, Firefox, Safari)

## 📝 Test Results Template

```
Date: ___________
Tester: ___________

Automated Tests:
- test_system_dashboard_auto.py: [ ] PASS [ ] FAIL
- pytest integration tests: ___/11 passed

Manual Tests:
- Dashboard Load: [ ] PASS [ ] FAIL
- Statistics Display: [ ] PASS [ ] FAIL
- Orders by Status: [ ] PASS [ ] FAIL
- Active Drivers: [ ] PASS [ ] FAIL
- Real-Time Updates: [ ] PASS [ ] FAIL
- Navigation: [ ] PASS [ ] FAIL
- Error Handling: [ ] PASS [ ] FAIL

Issues Found:
1. ___________
2. ___________

Notes:
___________
```

## 🎉 Success Criteria

Phase 5 testing is complete when:
- ✅ All automated tests pass
- ✅ All manual test scenarios work
- ✅ Real-time updates function correctly
- ✅ Error handling is robust
- ✅ Performance is acceptable
- ✅ UI is responsive and polished

Happy Testing! 🚀
