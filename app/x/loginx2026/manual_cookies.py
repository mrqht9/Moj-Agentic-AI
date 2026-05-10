#!/usr/bin/env python3
"""
Manual cookies input - إدخال الكوكيز يدوياً
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x_auth.login import x_login_with_cookies

async def main():
    """إدخال الكوكيز يدوياً"""
    print("🖊️  MANUAL COOKIES INPUT")
    print("=" * 50)
    
    print("\nThis method allows you to manually enter cookies.")
    print("Get cookies from browser developer tools:")
    print("1. Open X/Twitter in browser")
    print("2. Press F12 (Developer Tools)")
    print("3. Go to Application > Cookies > https://x.com")
    print("4. Copy auth_token and ct0 values")
    
    print("\n📋 Required cookies:")
    print("- auth_token (long string starting with '')")
    print("- ct0 (shorter string)")
    
    # إدخال الكوكيز
    auth_token = input("\nEnter auth_token: ").strip()
    ct0 = input("Enter ct0: ").strip()
    
    if not auth_token or not ct0:
        print("❌ Both auth_token and ct0 are required!")
        return
    
    # إنشاء ملف الكوكيز
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "manual_input.json"
    
    # حفظ الكوكيز بصيغة Playwright
    playwright_cookies = [
        {
            "name": "auth_token",
            "value": auth_token,
            "domain": ".x.com",
            "path": "/",
            "expires": 2147483647.0,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        },
        {
            "name": "ct0",
            "value": ct0,
            "domain": ".x.com",
            "path": "/",
            "expires": 2147483647.0,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        }
    ]
    
    cookie_data = {
        "cookies": playwright_cookies,
        "origins": []
    }
    
    with open(cookie_file, 'w', encoding='utf-8') as f:
        json.dump(cookie_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Cookies saved to: {cookie_file}")
    
    # اختبار الكوكيز
    try:
        print("\n🧪 Testing cookies...")
        await x_login_with_cookies(str(cookie_file))
        print("✅ Cookies are valid and working!")
        
        print("\n🎉 Success! You can now use these cookies for login.")
        print("The cookies are saved as 'manual_input.json' in the cookies folder.")
        
    except Exception as e:
        print(f"❌ Error testing cookies: {e}")
        print("\n💡 Possible solutions:")
        print("1. Check if cookies are copied correctly")
        print("2. Make sure cookies are not expired")
        print("3. Try getting fresh cookies from browser")
        print("4. Check if account is suspended")

def show_instructions():
    """عرض تعليمات مفصلة"""
    print("\n" + "=" * 60)
    print("📖 DETAILED INSTRUCTIONS")
    print("=" * 60)
    
    print("\n🔍 How to get cookies from Chrome:")
    print("1. Open Chrome and go to https://x.com")
    print("2. Make sure you're logged in")
    print("3. Press F12 or right-click > Inspect")
    print("4. Click on 'Application' tab")
    print("5. On the left, expand 'Storage' > 'Cookies'")
    print("6. Click on 'https://x.com'")
    print("7. Find 'auth_token' and 'ct0' in the list")
    print("8. Click on each and copy the 'Value' field")
    
    print("\n🔍 How to get cookies from Firefox:")
    print("1. Open Firefox and go to https://x.com")
    print("2. Make sure you're logged in")
    print("3. Press F12")
    print("4. Click on 'Storage' tab")
    print("5. Expand 'Cookies' > 'https://x.com'")
    print("6. Find 'auth_token' and 'ct0'")
    print("7. Copy the values")
    
    print("\n⚠️  Important notes:")
    print("- auth_token is usually very long (100+ characters)")
    print("- ct0 is shorter (around 40 characters)")
    print("- Don't share these cookies with anyone")
    print("- Cookies expire, you may need to update them")

if __name__ == "__main__":
    print("🖊️  MANUAL COOKIES INPUT TOOL")
    print("Choose an option:")
    print("1. Enter cookies manually")
    print("2. Show detailed instructions")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        asyncio.run(main())
    elif choice == '2':
        show_instructions()
    elif choice == '3':
        print("Goodbye!")
    else:
        print("Invalid choice!")
