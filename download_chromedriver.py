#!/usr/bin/env python3
"""
ChromeDriver Download Script
This script helps download the correct ChromeDriver version for your system.
"""

import os
import sys
import subprocess
import platform
import requests
import zipfile
import tarfile
from pathlib import Path

def get_chrome_version():
    """Get the installed Chrome version."""
    system = platform.system()
    
    if system == "Windows":
        try:
            # Try to get Chrome version from registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version
        except:
            # Fallback: try common Chrome paths
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run([path, "--version"], capture_output=True, text=True)
                        if result.returncode == 0:
                            # Extract version from output like "Google Chrome 120.0.6099.109"
                            version = result.stdout.strip().split()[-1]
                            return version
                    except:
                        continue
    
    elif system == "Darwin":  # macOS
        try:
            result = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return version
        except:
            pass
    
    elif system == "Linux":
        try:
            result = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return version
        except:
            pass
    
    return None

def get_chromedriver_url(version):
    """Get the ChromeDriver download URL for the given Chrome version."""
    # Extract major version (e.g., "120" from "120.0.6099.109")
    major_version = version.split('.')[0]
    
    system = platform.system()
    machine = platform.machine()
    
    # For Chrome 115+, use the new download structure
    if int(major_version) >= 115:
        if system == "Windows":
            return f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/win64/chromedriver-win64.zip"
        elif system == "Darwin":  # macOS
            if machine == "arm64":
                return f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/mac-arm64/chromedriver-mac-arm64.zip"
            else:
                return f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/mac-x64/chromedriver-mac-x64.zip"
        elif system == "Linux":
            return f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/linux64/chromedriver-linux64.zip"
    else:
        # For older Chrome versions, use the legacy method
        if system == "Windows":
            return f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        elif system == "Darwin":  # macOS
            return f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        elif system == "Linux":
            return f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
    
    return None

def download_chromedriver():
    """Download ChromeDriver for the current system."""
    print("🔍 Detecting Chrome version...")
    chrome_version = get_chrome_version()
    
    if not chrome_version:
        print("❌ Could not detect Chrome version. Please ensure Chrome is installed.")
        return False
    
    print(f"✅ Chrome version detected: {chrome_version}")
    
    # Get the ChromeDriver download URL
    print("🔍 Getting ChromeDriver download URL...")
    try:
        download_url = get_chromedriver_url(chrome_version)
        if not download_url:
            print("❌ Unsupported system architecture")
            return False
        
        system = platform.system()
        machine = platform.machine()
        
        # Determine filename based on system
        if system == "Windows":
            filename = "chromedriver-win64.zip"
        elif system == "Darwin":  # macOS
            if machine == "arm64":
                filename = "chromedriver-mac-arm64.zip"
            else:
                filename = "chromedriver-mac-x64.zip"
        elif system == "Linux":
            filename = "chromedriver-linux64.zip"
        else:
            print("❌ Unsupported operating system")
            return False
        
        print(f"📥 Downloading ChromeDriver from: {download_url}")
        
        # Download the file
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            print("❌ Failed to download ChromeDriver")
            return False
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {filename}")
        
        # Extract the file
        print("📦 Extracting ChromeDriver...")
        if filename.endswith('.zip'):
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall('.')
        
        # Clean up downloaded file
        os.remove(filename)
        
        print("✅ ChromeDriver extracted successfully!")
        
        # Verify the file and move to correct location
        extracted_dir = filename.replace('.zip', '')
        driver_path = os.path.join(extracted_dir, "chromedriver.exe" if system == "Windows" else "chromedriver")
        
        if os.path.exists(driver_path):
            # Move to current directory
            final_path = "chromedriver.exe" if system == "Windows" else "chromedriver"
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(driver_path, final_path)
            
            # Remove empty directory
            try:
                os.rmdir(extracted_dir)
            except:
                pass
            
            print(f"✅ ChromeDriver is ready at: {os.path.abspath(final_path)}")
            return True
        else:
            print("❌ ChromeDriver extraction failed")
            return False
        
    except Exception as e:
        print(f"❌ Error downloading ChromeDriver: {str(e)}")
        return False

def main():
    """Main function."""
    print("🚀 ChromeDriver Download Script")
    print("=" * 40)
    
    if download_chromedriver():
        print("\n🎉 ChromeDriver download completed successfully!")
        print("\n📋 Next steps:")
        print("1. Ensure ChromeDriver is in your PATH or current directory")
        print("2. Run your job application system")
        print("3. If you still have issues, try running the system from the same directory as ChromeDriver")
    else:
        print("\n❌ ChromeDriver download failed!")
        print("\n🔧 Alternative solutions:")
        print("1. Download ChromeDriver manually from: https://chromedriver.chromium.org/")
        print("2. Use webdriver-manager: pip install webdriver-manager")
        print("3. Check if Chrome browser is properly installed and up to date")

if __name__ == "__main__":
    main()
