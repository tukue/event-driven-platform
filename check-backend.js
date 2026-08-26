/**
 * Quick backend health check
 * Run: node check-backend.js
 */

const API_BASE = 'http://localhost:8000';

async function checkBackend() {
  console.log('🔍 Checking backend status...\n');
  
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    
    console.log('✅ Backend is running');
    console.log('   Status:', data.status);
    console.log('   Message:', data.message);
    console.log('\n✅ Backend is ready for integration tests');
    process.exit(0);
  } catch (error) {
    console.log('❌ Backend is NOT running');
    console.log('   Error:', error.message);
    console.log('\n📝 To start backend:');
    console.log('   cd backend');
    console.log('   uvicorn main:app --reload');
    process.exit(1);
  }
}

checkBackend();
