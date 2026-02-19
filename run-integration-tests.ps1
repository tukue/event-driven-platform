# PowerShell script for Windows
Write-Host "🧪 Running Backend-Frontend Integration Tests" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "📡 Checking backend connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Backend is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend is not running on port 8000" -ForegroundColor Red
    Write-Host "   Start it with: cd backend; uvicorn main:app --reload" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Run backend integration tests
Write-Host "🔧 Running backend integration tests..." -ForegroundColor Yellow
Push-Location backend
python -m pytest tests/test_backend_frontend_integration.py -v
$backendResult = $LASTEXITCODE
Pop-Location
Write-Host ""

# Run frontend integration tests
Write-Host "🌐 Running frontend integration tests..." -ForegroundColor Yellow
node test-integration.js
$frontendResult = $LASTEXITCODE
Write-Host ""

# Summary
Write-Host "==============================================" -ForegroundColor Cyan
if ($backendResult -eq 0 -and $frontendResult -eq 0) {
    Write-Host "✅ All integration tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Some tests failed" -ForegroundColor Red
    if ($backendResult -ne 0) { Write-Host "   - Backend tests failed" -ForegroundColor Red }
    if ($frontendResult -ne 0) { Write-Host "   - Frontend tests failed" -ForegroundColor Red }
    exit 1
}
