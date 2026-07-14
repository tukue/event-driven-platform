"""
Interactive setup script for Grafana integration
Guides user through the complete setup process
"""
import asyncio
import sys

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_step(number, text):
    """Print a step number and description"""
    print(f"\n{number}️⃣  {text}")

def print_success(text):
    """Print success message"""
    print(f"   ✅ {text}")

def print_info(text):
    """Print info message"""
    print(f"   💡 {text}")

def print_command(text):
    """Print command to run"""
    print(f"   $ {text}")

async def main():
    """Interactive setup wizard"""
    print_header("🚀 Grafana Setup Wizard")
    print("\nThis wizard will guide you through setting up Grafana")
    print("visualization for your order delivery system.")
    
    # Step 1: Check prerequisites
    print_step(1, "Prerequisites Check")
    print_info("Checking if required files exist...")
    
    import os
    required_files = [
        "services/metrics_service.py",
        "main.py",
        "redis_client.py",
        ".env"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"   ❌ Missing files: {', '.join(missing_files)}")
        print_info("Please ensure you're in the backend directory")
        return
    else:
        print_success("All required files found")
    
    # Step 2: Verify setup
    print_step(2, "System Verification")
    print_info("Running verification checks...")
    print_command("python verify_grafana_setup.py")
    
    input("\n   Press Enter to run verification...")
    
    from verify_grafana_setup import main as verify_main
    await verify_main()
    
    # Step 3: Generate test data
    print_step(3, "Test Data Generation")
    print_info("Generate sample orders for visualization")
    
    response = input("\n   Generate test data? (y/n): ").lower()
    
    if response == 'y':
        print_info("Generating 76 sample orders...")
        print_command("python generate_test_data.py")
        
        from generate_test_data import generate_test_data
        await generate_test_data()
    else:
        print_info("Skipped. You can run 'python generate_test_data.py' later")
    
    # Step 4: Test endpoints
    print_step(4, "Metrics Endpoints")
    print_info("Testing Prometheus and JSON endpoints...")
    
    response = input("\n   Test endpoints now? (y/n): ").lower()
    
    if response == 'y':
        from test_grafana_metrics import test_metrics_endpoints
        await test_metrics_endpoints()
    else:
        print_info("Skipped. You can run 'python test_grafana_metrics.py' later")
    
    # Step 5: Grafana setup instructions
    print_step(5, "Grafana Configuration")
    print_info("Next, you need to configure Grafana")
    
    print("\n   📋 Grafana Setup Steps:")
    print("   1. Install Grafana:")
    print("      • Docker: docker run -d -p 3000:3000 grafana/grafana")
    print("      • Or download from: https://grafana.com/grafana/download")
    print("\n   2. Open Grafana: http://localhost:3000")
    print("      • Default login: admin/admin")
    print("\n   3. Add Datasource:")
    print("      • Configuration → Data Sources → Add")
    print("      • Select 'Prometheus'")
    print("      • URL: http://localhost:8000/metrics")
    print("      • Click 'Save & Test'")
    print("\n   4. Import Dashboard:")
    print("      • Dashboards → Import")
    print("      • Upload: grafana/dashboard-orders-delivered.json")
    print("      • Select your datasource")
    print("      • Click 'Import'")
    
    # Step 6: Documentation
    print_step(6, "Documentation")
    print_info("Available documentation:")
    print("\n   📚 Guides:")
    print("   • GRAFANA_SETUP.md - Complete setup guide")
    print("   • GRAFANA_TESTING_GUIDE.md - Testing procedures")
    print("   • GRAFANA_QUICK_REFERENCE.md - Quick commands")
    print("   • GRAFANA_ARCHITECTURE.md - System architecture")
    print("   • GRAFANA_IMPLEMENTATION_SUMMARY.md - Overview")
    
    # Final summary
    print_header("✅ Setup Complete!")
    print("\n📋 What's Next:")
    print("   1. Ensure backend is running: uvicorn main:app --reload")
    print("   2. Install and configure Grafana (see step 5 above)")
    print("   3. Import the dashboard")
    print("   4. View your metrics!")
    
    print("\n🔗 Quick Links:")
    print("   • Prometheus metrics: http://localhost:8000/metrics")
    print("   • JSON metrics: http://localhost:8000/api/metrics")
    print("   • API docs: http://localhost:8000/docs")
    print("   • Grafana: http://localhost:3000")
    
    print("\n💡 Need help? Check GRAFANA_SETUP.md for detailed instructions")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        print("💡 Check the documentation for troubleshooting")
        sys.exit(1)
