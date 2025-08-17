#!/usr/bin/env python3
"""
Quick start script for the Multi-Agent Job Application System.
"""

import os
import sys
import subprocess
import asyncio

def check_dependencies():
    """Check if required dependencies are installed."""
    
    required_packages = [
        "openai", "beautifulsoup4", "requests", "python-docx", 
        "python-dotenv", "selenium", "webdriver-manager", "aiohttp", "nltk"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def setup_environment():
    """Set up the environment and directories."""
    
    print("🔧 Setting up environment...")
    
    # Create necessary directories
    directories = ["data", "output", "output/resumes", "logs", "logs/reports"]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ Created directory: {directory}")
    
    # Check for .env file
    if not os.path.exists(".env"):
        print("⚠️  No .env file found. Create one with your API keys:")
        print("   OPENAI_API_KEY=your_api_key_here")
        print("   (See README.md for full configuration)")
    else:
        print("✅ Found .env configuration file")

def run_basic_examples():
    """Run basic usage examples."""
    
    print("\n🚀 Running basic examples...")
    
    try:
        result = subprocess.run([
            sys.executable, "examples/basic_usage.py"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Basic examples completed successfully")
            print(result.stdout)
        else:
            print("❌ Basic examples failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Basic examples timed out (this is normal for demo mode)")
        return True
    except Exception as e:
        print(f"❌ Error running basic examples: {str(e)}")
        return False
    
    return True

def run_advanced_examples():
    """Run advanced usage examples."""
    
    print("\n🚀 Running advanced examples...")
    
    try:
        result = subprocess.run([
            sys.executable, "examples/advanced_usage.py"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Advanced examples completed successfully")
            print(result.stdout)
        else:
            print("❌ Advanced examples failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Advanced examples timed out (this is normal for demo mode)")
        return True
    except Exception as e:
        print(f"❌ Error running advanced examples: {str(e)}")
        return False
    
    return True

def show_next_steps():
    """Show next steps for the user."""
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("1. Set up your .env file with OpenAI API key")
    print("2. Add your resume file to the data/ directory")
    print("3. Run your first job search:")
    print("   python main.py --role \"Your Target Role\" --resume \"data/your_resume.docx\"")
    print("\n⚠️  Safety Tips:")
    print("• Start with --dry-run to test without applying")
    print("• Use --max-jobs 5 to limit initial searches")
    print("• Only use --auto-apply when you're confident")
    
    print("\n📚 Documentation:")
    print("• README.md - Complete documentation")
    print("• examples/basic_usage.py - Basic examples")
    print("• examples/advanced_usage.py - Advanced features")
    
    print("\n🔧 Configuration Check:")
    print("   python main.py --config-check")

def main():
    """Main setup and demo function."""
    
    print("🤖 Multi-Agent Job Application System - Setup & Demo")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install required dependencies first:")
        print("   pip install -r requirements.txt")
        return
    
    # Setup environment
    setup_environment()
    
    # Ask user what they want to do
    print("\n" + "=" * 60)
    print("What would you like to do?")
    print("1. Run basic examples (recommended for first time)")
    print("2. Run advanced examples")
    print("3. Just set up environment and show next steps")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            if run_basic_examples():
                show_next_steps()
        elif choice == "2":
            if run_advanced_examples():
                show_next_steps()
        elif choice == "3":
            show_next_steps()
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice. Please run again and select 1-4.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted by user. Run again anytime!")
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}")

if __name__ == "__main__":
    main()
