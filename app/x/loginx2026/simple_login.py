#!/usr/bin/env python3
"""
Simple login alternative - استخدام cookies من المتصفح
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x_auth.login import x_login_from_browser

async def main():
    """الدخول باستخدام كوكيز المتصفح"""
    print("🍪 SIMPLE LOGIN - Browser Cookies Method")
    print("=" * 50)
    
    print("\nThis method extracts cookies from your browser.")
    print("Make sure you're logged into X/Twitter in your browser first!")
    
    print("\nSupported browsers:")
    print("1. Chrome")
    print("2. Edge") 
    print("3. Firefox")
    print("4. Brave")
    
    browser_choice = input("\nSelect browser (1-4): ").strip()
    
    browser_map = {
        '1': 'chrome',
        '2': 'edge', 
        '3': 'firefox',
        '4': 'brave'
    }
    
    browser = browser_map.get(browser_choice, 'chrome')
    
    try:
        print(f"\n🔄 Extracting cookies from {browser}...")
        print("⚠️  Close your browser first if it's open!")
        
        input("Press Enter to continue...")
        
        cookies = await x_login_from_browser(browser=browser)
        
        print("✅ Success! Cookies extracted and saved.")
        print(f"Auth token: {cookies.get('auth_token', 'N/A')[:20]}...")
        print(f"CSRF token: {cookies.get('ct0', 'N/A')[:20]}...")
        
        # اختبار الكوكيز
        print("\n🧪 Testing cookies...")
        from x_auth.login import x_login_with_cookies
        
        cookies_dir = "cookies"
        cookie_files = list(Path(cookies_dir).glob(f"browser_{browser}.json"))
        
        if cookie_files:
            await x_login_with_cookies(str(cookie_files[0]))
            print("✅ Cookies are valid!")
        else:
            print("❌ Cookie file not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Solutions:")
        print("1. Make sure browser is completely closed")
        print("2. Check if you're logged into X/Twitter")
        print("3. Try different browser")
        print("4. Run as administrator if needed")

if __name__ == "__main__":
    asyncio.run(main())
