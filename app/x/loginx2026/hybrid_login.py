#!/usr/bin/env python3
"""
Hybrid Login - يجمع بين x_auth الأصلي والتحسينات الجديدة
"""
import asyncio
import json
import time
import random
import uuid
import sys
import os
from pathlib import Path

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x_auth.login import x_login, HTTPClient
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

class HybridLogin:
    def __init__(self):
        self.http = None
        self.castle = None
        
    async def login(self, username, password, email=None, cookies_dir="cookies"):
        """تسجيل الدخول باستخدام x_auth الأصلي مع تحسينات"""
        print("🔄 HYBRID LOGIN - Using x_auth with enhancements")
        print("=" * 60)
        
        try:
            # استخدام x_login الأصلي مع تحسينات
            cookies = await x_login(username, password, email, cookies_dir)
            
            print("\n🎉 HYBRID LOGIN SUCCESSFUL!")
            print(f"Auth token: {cookies.get('auth_token', 'N/A')[:20]}...")
            print(f"CSRF token: {cookies.get('ct0', 'N/A')[:20]}...")
            
            return cookies
            
        except Exception as e:
            print(f"\n❌ Hybrid login failed: {e}")
            
            # تحليل الخطأ وتقديم حلول
            error_str = str(e).lower()
            
            if "could not log you in now" in error_str:
                print("\n💡 This is the IP/account restriction error.")
                print("Solutions:")
                print("1. Try manual_cookies.py (most reliable)")
                print("2. Change IP/VPN")
                print("3. Wait 24-48 hours")
                print("4. Try different account")
                
            elif "missing data" in error_str:
                print("\n💡 This is a data/format error.")
                print("Solutions:")
                print("1. Try manual_cookies.py")
                print("2. Check if x_auth needs updates")
                print("3. Try different browser fingerprint")
                
            elif "impersonating" in error_str:
                print("\n💡 This is a browser version error.")
                print("Solutions:")
                print("1. Update curl_cffi")
                print("2. Try manual_cookies.py")
                
            else:
                print("\n💡 Unknown error. Try manual_cookies.py as fallback.")
            
            raise

async def main():
    """الوظيفة الرئيسية"""
    print("🔄 HYBRID LOGIN SYSTEM")
    print("Combines original x_auth with modern enhancements")
    print("=" * 60)
    
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    email = input("Enter email (optional): ").strip() or None
    
    if not username or not password:
        print("❌ Username and password required!")
        return
    
    hybrid = HybridLogin()
    
    try:
        cookies = await hybrid.login(username, password, email)
        
        # حفظ النتائج
        results = {
            'timestamp': time.time(),
            'username': username,
            'success': True,
            'cookies': cookies,
            'method': 'hybrid_x_auth'
        }
        
        results_file = Path(f"hybrid_success_{username}_{int(time.time())}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {results_file}")
        
    except Exception as e:
        print(f"\n❌ Hybrid login failed: {e}")
        
        # حفظ الخطأ
        error_results = {
            'timestamp': time.time(),
            'username': username,
            'success': False,
            'error': str(e),
            'method': 'hybrid_x_auth'
        }
        
        error_file = Path(f"hybrid_error_{username}_{int(time.time())}.json")
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Error saved to: {error_file}")
        
        print("\n🔄 Trying fallback solutions...")
        print("1. manual_cookies.py - Most reliable")
        print("2. alternative_login.py - Tries all methods")
        print("3. simple_login.py - Browser extraction")

if __name__ == "__main__":
    asyncio.run(main())
