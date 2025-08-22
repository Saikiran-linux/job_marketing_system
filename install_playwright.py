#!/usr/bin/env python3
"""
Playwright Browser Installation Script
This script helps install Playwright browsers for the job application system.
"""

import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers."""
    
    print("🚀 Playwright Browser Installation Script")
    print("=" * 50)
    
    try:
        # Check if playwright is installed
        try:
            import playwright
            print("✅ Playwright Python package is already installed")
        except ImportError:
            print("❌ Playwright Python package not found")
            print("Installing Playwright...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            print("✅ Playwright Python package installed successfully")
        
        # Install Playwright browsers
        print("\n📦 Installing Playwright browsers...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        
        print("\n✅ Playwright browsers installed successfully!")
        print("\n🎉 Setup complete! You can now run the job application system.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing Playwright browsers: {e}")
        print("\n💡 Try running these commands manually:")
        print("   pip install playwright")
        print("   playwright install")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def main():
    """Main function."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python install_playwright.py")
        print("\nThis script will:")
        print("1. Install Playwright Python package (if not already installed)")
        print("2. Install Playwright browsers (Chromium, Firefox, WebKit)")
        print("\nAfter installation, you can run the job application system.")
        return
    
    success = install_playwright_browsers()
    
    if success:
        print("\n📋 Next steps:")
        print("1. Set up your .env file with credentials")
        print("2. Configure job_config.py with your preferences")
        print("3. Run: python main.py")
    else:
        print("\n❌ Installation failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
