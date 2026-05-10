#!/usr/bin/env python3
"""
Alternative login methods - حلول بديلة لتسجيل الدخول
"""
import asyncio
import sys
import os
import json
import subprocess
from pathlib import Path

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_as_admin():
    """تشغيل كـ administrator"""
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("🔐 Requesting administrator privileges...")
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, 
                    " ".join(sys.argv), None, 1
                )
                return False
        except:
            pass
    return True

async def try_edge_firefox():
    """تجربة Edge و Firefox"""
    print("🔄 Trying alternative browsers...")
    
    browsers = ['edge', 'firefox']
    
    for browser in browsers:
        try:
            print(f"\n📱 Trying {browser}...")
            from x_auth.login import x_login_from_browser
            cookies = await x_login_from_browser(browser=browser)
            print(f"✅ Success with {browser}!")
            return cookies
        except Exception as e:
            print(f"❌ {browser} failed: {e}")
            continue
    
    return None

async def try_manual_input():
    """تجربة الإدخال اليدوي"""
    print("\n🖊️  Trying manual input...")
    
    try:
        # استدعاء manual_cookies.py
        manual_script = Path(__file__).parent / "manual_cookies.py"
        if manual_script.exists():
            result = subprocess.run([sys.executable, str(manual_script)], 
                                  capture_output=True, text=True, encoding='utf-8')
            
            if "✅ Cookies are valid" in result.stdout:
                print("✅ Manual input successful!")
                return True
            else:
                print(f"❌ Manual input failed: {result.stdout}")
        else:
            print("❌ manual_cookies.py not found")
    except Exception as e:
        print(f"❌ Error running manual input: {e}")
    
    return False

async def try_existing_cookies():
    """تجربة الكوكيز الموجودة"""
    print("\n🍪 Checking for existing cookies...")
    
    cookies_dir = Path("cookies")
    if not cookies_dir.exists():
        print("❌ No cookies directory found")
        return False
    
    cookie_files = list(cookies_dir.glob("*.json"))
    if not cookie_files:
        print("❌ No cookie files found")
        return False
    
    for cookie_file in cookie_files:
        try:
            print(f"🧪 Testing {cookie_file.name}...")
            from x_auth.login import x_login_with_cookies
            await x_login_with_cookies(str(cookie_file))
            print(f"✅ {cookie_file.name} is valid!")
            return True
        except Exception as e:
            print(f"❌ {cookie_file.name} failed: {e}")
            continue
    
    return False

def show_solutions():
    """عرض الحلول المتاحة"""
    print("\n" + "=" * 60)
    print("💡 AVAILABLE SOLUTIONS")
    print("=" * 60)
    
    print("\n🔧 Technical Solutions:")
    print("1. 📱 Use Edge or Firefox instead of Chrome")
    print("2. 🖊️  Manual cookie input")
    print("3. 🍪 Use existing cookies")
    print("4. 🔐 Run as administrator")
    print("5. 🌍 Change IP/VPN")
    
    print("\n🌐 Browser Solutions:")
    print("- Chrome: Close completely, run as admin")
    print("- Edge: Usually works better than Chrome")
    print("- Firefox: Different encryption, might work")
    print("- Brave: Similar to Chrome but different profile")
    
    print("\n🔑 Manual Steps:")
    print("1. Open X/Twitter in browser")
    print("2. Press F12 > Application > Cookies")
    print("3. Copy auth_token and ct0")
    print("4. Use manual_cookies.py to input them")
    
    print("\n⚠️  If nothing works:")
    print("- Account might be suspended")
    print("- IP might be blocked")
    print("- Try different network/VPN")
    print("- Wait 24-48 hours")

async def main():
    """الوظيفة الرئيسية"""
    print("🔄 ALTERNATIVE LOGIN METHODS")
    print("=" * 50)
    
    print("\nThis tool tries multiple methods to get working cookies.")
    
    # 1. تجربة الكوكيز الموجودة
    if await try_existing_cookies():
        print("\n🎉 Success! Using existing cookies.")
        return
    
    # 2. تجربة متصفحات أخرى
    alt_cookies = await try_edge_firefox()
    if alt_cookies:
        print("\n🎉 Success! Using alternative browser cookies.")
        return
    
    # 3. تجربة الإدخال اليدوي
    if await try_manual_input():
        print("\n🎉 Success! Using manual input.")
        return
    
    # 4. عرض الحلول
    show_solutions()
    
    print("\n❌ All automatic methods failed.")
    print("Try the manual methods shown above.")

if __name__ == "__main__":
    # التحقق من صلاحيات administrator
    if not run_as_admin():
        sys.exit(0)
    
    asyncio.run(main())
