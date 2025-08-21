#!/usr/bin/env python3
"""
Test script for Glassdoor browser stability and authentication.
This script tests the enhanced browser initialization and stability features.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.glassdoor_web_agent import GlassdoorWebAgent
from agents.base_agent import AgentState
from config import Config

async def test_browser_stability():
    """Test the enhanced browser stability features."""
    
    print("🧪 Testing Glassdoor Browser Stability...")
    print("=" * 50)
    
    # Create agent instance
    agent = GlassdoorWebAgent()
    
    try:
        print("1️⃣ Testing browser initialization...")
        await agent._init_browser()
        print("✅ Browser initialized successfully")
        
        print("2️⃣ Testing browser stability...")
        if await agent._test_browser_stability():
            print("✅ Browser stability test passed")
        else:
            print("❌ Browser stability test failed")
            return False
        
        print("3️⃣ Testing browser health monitoring...")
        if await agent._monitor_browser_health():
            print("✅ Browser health monitoring working")
        else:
            print("❌ Browser health monitoring failed")
            return False
        
        print("4️⃣ Testing browser crash recovery...")
        if await agent._handle_browser_crash():
            print("✅ Browser crash recovery working")
        else:
            print("❌ Browser crash recovery failed")
            return False
        
        print("\n🎉 All browser stability tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False
        
    finally:
        await agent.close()

async def test_authentication_workflow():
    """Test the authentication workflow with enhanced stability."""
    
    print("\n🔐 Testing Authentication Workflow...")
    print("=" * 50)
    
    # Create agent instance
    agent = GlassdoorWebAgent()
    
    try:
        # Create a test state with required fields for Pydantic validation
        state = AgentState(
            session_id="auth_test",
            start_time=datetime.now().isoformat(),
            current_step="authentication",
            steps_completed=[],
            status="running",
            error=None,
            role="Test Role",
            resume_path="./resume.docx",
            location="Remote",
            max_jobs=0,
            auto_apply=False,
            resume_analysis=None,
            job_search_results=None,
            processed_jobs=[],
            final_report=None,
            end_time=None,
            workflow_duration=None,
        )
        state.glassdoor_email = Config.GLASSDOOR_EMAIL
        state.glassdoor_password = Config.GLASSDOOR_PASSWORD
        
        print("1️⃣ Testing authentication with retry mechanism...")
        print("   Note: This will attempt to log in to Glassdoor")
        print("   Make sure your credentials are correct in config.py")
        
        # Test the authentication retry mechanism
        if await agent._authenticate_with_retry(state):
            print("✅ Authentication successful")
            return True
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed with error: {str(e)}")
        return False
        
    finally:
        await agent.close()

async def main():
    """Main test function."""
    
    print("🚀 Glassdoor Browser Stability Test Suite")
    print("=" * 60)
    
    # Test 1: Browser stability
    stability_result = await test_browser_stability()
    
    if stability_result:
        print("\n" + "=" * 60)
        print("✅ Browser stability tests completed successfully!")
        
        # Test 2: Authentication workflow (optional)
        print("\n🔐 Would you like to test the authentication workflow?")
        print("   This requires valid Glassdoor credentials in config.py")
        print("   Type 'yes' to continue, or press Enter to skip...")
        
        user_input = input("> ").strip().lower()
        if user_input == 'yes':
            auth_result = await test_authentication_workflow()
            if auth_result:
                print("\n🎉 All tests passed! Your Glassdoor automation is ready.")
            else:
                print("\n⚠️  Authentication test failed. Check your credentials.")
        else:
            print("\n⏭️  Skipping authentication test.")
    else:
        print("\n❌ Browser stability tests failed. Check the error messages above.")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
