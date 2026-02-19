#!/bin/bash

echo "🧪 Running Backend-Frontend Integration Tests"
echo "=============================================="
echo ""

# Check if backend is running
echo "📡 Checking backend connection..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend is not running on port 8000"
    echo "   Start it with: cd backend && uvicorn main:app --reload"
    exit 1
fi
echo "✅ Backend is running"
echo ""

# Run backend integration tests
echo "🔧 Running backend integration tests..."
cd backend
python -m pytest tests/test_backend_frontend_integration.py -v
BACKEND_RESULT=$?
cd ..
echo ""

# Run frontend integration tests
echo "🌐 Running frontend integration tests..."
node test-integration.js
FRONTEND_RESULT=$?
echo ""

# Summary
echo "=============================================="
if [ $BACKEND_RESULT -eq 0 ] && [ $FRONTEND_RESULT -eq 0 ]; then
    echo "✅ All integration tests passed!"
    exit 0
else
    echo "❌ Some tests failed"
    [ $BACKEND_RESULT -ne 0 ] && echo "   - Backend tests failed"
    [ $FRONTEND_RESULT -ne 0 ] && echo "   - Frontend tests failed"
    exit 1
fi
