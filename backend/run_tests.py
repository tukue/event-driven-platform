#!/usr/bin/env python
"""
Test runner script for pizza delivery app
Run all tests or specific test suites
"""
import sys
import subprocess

def run_tests(test_type="all"):
    """Run tests based on type"""
    
    print("=" * 60)
    print("🧪 Pizza Delivery App - Test Suite")
    print("=" * 60)
    
    if test_type == "unit":
        print("\n📦 Running Unit Tests...")
        cmd = ["pytest", "tests/test_models.py", "tests/test_order_service.py", "-v"]
    elif test_type == "api":
        print("\n🌐 Running API Tests...")
        cmd = ["pytest", "tests/test_api.py", "-v"]
    elif test_type == "integration":
        print("\n🔗 Running Integration Tests...")
        cmd = ["pytest", "tests/test_integration.py", "-v"]
    else:
        print("\n🚀 Running All Tests...")
        cmd = ["pytest", "tests/", "-v"]
    
    result = subprocess.run(cmd)
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 60)
    
    return result.returncode

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    valid_types = ["all", "unit", "api", "integration"]
    if test_type not in valid_types:
        print(f"Invalid test type. Choose from: {', '.join(valid_types)}")
        sys.exit(1)
    
    sys.exit(run_tests(test_type))
