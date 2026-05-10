#!/usr/bin/env python3
"""
Debug script لتشخيص مشكلة تسجيل الدخول في X
"""
import asyncio
import sys
import os
import json
import time
import random
import requests
from pathlib import Path

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x_auth.login import x_login

async def debug_session():
    """جلسة debug مفصلة"""
    print("=" * 60)
    print("🔍 DEBUG SESSION - X LOGIN DIAGNOSTIC")
    print("=" * 60)
    
    # 1. فحص IP الحالي
    print("\n[1] فحص IP الحالي:")
    try:
        ip_response = requests.get('https://api.ipify.org?format=json', timeout=10)
        ip_data = ip_response.json()
        current_ip = ip_data.get('ip', 'Unknown')
        print(f"   IP: {current_ip}")
        
        # فحص تفاصيل IP
        geo_response = requests.get(f'http://ip-api.com/json/{current_ip}', timeout=10)
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            print(f"   Country: {geo_data.get('country', 'Unknown')}")
            print(f"   Region: {geo_data.get('regionName', 'Unknown')}")
            print(f"   ISP: {geo_data.get('isp', 'Unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. فحص الاتصال بـ X
    print("\n[2] فحص الاتصال بـ X:")
    try:
        x_response = requests.get('https://x.com', timeout=10, allow_redirects=True)
        print(f"   Status: {x_response.status_code}")
        print(f"   Final URL: {x_response.url}")
        
        if 'captcha' in x_response.text.lower():
            print("   ⚠️  CAPTCHA detected!")
        if 'suspended' in x_response.text.lower():
            print("   ⚠️  Suspension detected!")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. فحص API endpoints
    print("\n[3] فحص API Endpoints:")
    endpoints = [
        'https://api.x.com/1.1/onboarding/task.json',
        'https://api.x.com/1.1/onboarding/sso_init.json'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   {endpoint}: Error - {e}")
    
    # 4. محاولة تسجيل الدخول
    print("\n[4] محاولة تسجيل الدخول:")
    username = input("   Enter username: ").strip()
    password = input("   Enter password: ").strip()
    
    if not username or not password:
        print("   ⚠️  Username or password missing!")
        return
    
    try:
        print("   Attempting login...")
        cookies = await x_login(username, password)
        print("   ✅ Login successful!")
        print(f"   Auth token: {cookies.get('auth_token', 'N/A')[:20]}...")
        print(f"   CSRF token: {cookies.get('ct0', 'N/A')[:20]}...")
        
        # حفظ النتائج
        result_file = Path(f"debug_result_{username}_{int(time.time())}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'ip': current_ip,
                'username': username,
                'success': True,
                'cookies': cookies
            }, f, indent=2, ensure_ascii=False)
        print(f"   Results saved to: {result_file}")
        
    except Exception as e:
        print(f"   ❌ Login failed: {e}")
        
        # حفظ الخطأ
        error_file = Path(f"debug_error_{username}_{int(time.time())}.json")
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'ip': current_ip,
                'username': username,
                'success': False,
                'error': str(e)
            }, f, indent=2, ensure_ascii=False)
        print(f"   Error saved to: {error_file}")

def check_account_status():
    """فحص حالة الحساب"""
    print("\n[5] فحص حالة الحساب:")
    username = input("   Enter username to check: ").strip()
    
    if not username:
        return
    
    try:
        # فحص إذا كان الحساب موجود
        response = requests.get(f'https://x.com/{username}', timeout=10)
        print(f"   Profile status: {response.status_code}")
        
        if response.status_code == 200:
            if 'suspended' in response.text.lower():
                print("   ⚠️  Account appears to be SUSPENDED")
            elif 'account withheld' in response.text.lower():
                print("   ⚠️  Account appears to be WITHHELD")
            else:
                print("   ✅ Account appears to be active")
        elif response.status_code == 404:
            print("   ❌ Account not found")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   Error checking account: {e}")

def suggest_solutions():
    """اقتراح حلول"""
    print("\n" + "=" * 60)
    print("💡 SUGGESTED SOLUTIONS")
    print("=" * 60)
    
    print("\n1. 🌍 Change IP/Network:")
    print("   - Use VPN or proxy")
    print("   - Try different network (mobile data)")
    print("   - Wait 24-48 hours for IP reset")
    
    print("\n2. 📱 Account Issues:")
    print("   - Check if account is suspended")
    print("   - Try logging in via browser first")
    print("   - Use different account for testing")
    
    print("\n3. 🔧 Technical Solutions:")
    print("   - Use existing cookies: python -m x_auth.login_from_browser")
    print("   - Try different timing/delays")
    print("   - Update curl_cffi to latest version")
    
    print("\n4. 🛡️ Detection Avoidance:")
    print("   - Rotate user agents more frequently")
    print("   - Add longer delays between attempts")
    print("   - Use residential proxy")

def main():
    """الوظيفة الرئيسية"""
    print("🔍 X LOGIN DEBUG TOOL")
    print("Choose an option:")
    print("1. Full debug session")
    print("2. Check account status")
    print("3. Show solutions")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        asyncio.run(debug_session())
    elif choice == '2':
        check_account_status()
    elif choice == '3':
        suggest_solutions()
    elif choice == '4':
        print("Goodbye!")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
