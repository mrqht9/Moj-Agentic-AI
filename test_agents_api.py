#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار Agent API عبر HTTP
Test Agent API via HTTP Requests
"""

import requests
import json

BASE_URL = "http://localhost:5789"


def test_health_check():
    """اختبار صحة نظام الوكلاء"""
    
    print("=" * 80)
    print("🏥 فحص صحة نظام الوكلاء")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/health"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ الحالة: {result['status']}")
            print(f"🤖 الوكيل الرئيسي: {result['main_agent']}")
            print(f"⏰ الوقت: {result['timestamp']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")
        print("⚠️  تأكد من تشغيل الخادم: python app/main.py")


def test_agent_messages():
    """اختبار إرسال رسائل للوكيل"""
    
    print("\n\n" + "=" * 80)
    print("💬 اختبار إرسال رسائل للوكيل")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/message"
    
    test_messages = [
        {
            "message": "مرحباً",
            "description": "تحية بسيطة"
        },
        {
            "message": "أضف حساب تويتر",
            "description": "طلب إضافة حساب"
        },
        {
            "message": "انشر تغريدة 'مرحباً بالجميع!'",
            "description": "طلب نشر تغريدة"
        },
        {
            "message": "ساعدني",
            "description": "طلب المساعدة"
        },
        {
            "message": "أرني إحصائيات حسابي",
            "description": "طلب الإحصائيات"
        },
    ]
    
    for i, test_case in enumerate(test_messages, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   الرسالة: '{test_case['message']}'")
        print("-" * 80)
        
        payload = {
            "message": test_case['message'],
            "user_id": 1
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"✅ النجاح: {result['success']}")
                print(f"📝 الرد: {result['message'][:200]}...")
                
                if result.get('intent_result'):
                    intent_result = result['intent_result']
                    print(f"🎯 النية: {intent_result.get('intent')}")
                    print(f"📊 الثقة: {intent_result.get('confidence', 0):.2%}")
                    if intent_result.get('platform'):
                        print(f"🌐 المنصة: {intent_result.get('platform')}")
                
                if result.get('agent'):
                    print(f"🤖 الوكيل: {result['agent']}")
            
            else:
                print(f"❌ خطأ: {response.status_code}")
                print(f"   {response.text}")
        
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {str(e)}")


def test_x_agent_operations():
    """اختبار عمليات وكيل X"""
    
    print("\n\n" + "=" * 80)
    print("🐦 اختبار عمليات وكيل X")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/message"
    
    x_operations = [
        {
            "message": "سجل دخول حساب تويتر باسم test_user وكلمة المرور test123 واحفظه باسم my_test_account",
            "description": "تسجيل دخول"
        },
        {
            "message": "انشر تغريدة 'هذا اختبار للنظام الجديد!' على حساب my_test_account",
            "description": "نشر تغريدة"
        },
        {
            "message": "حدث الملف الشخصي للحساب my_test_account بالاسم 'اسم اختبار' والسيرة 'مطور برمجيات'",
            "description": "تحديث الملف الشخصي"
        },
    ]
    
    for i, operation in enumerate(x_operations, 1):
        print(f"\n{i}. {operation['description']}")
        print(f"   الأمر: '{operation['message'][:80]}...'")
        print("-" * 80)
        
        payload = {
            "message": operation['message'],
            "user_id": 1
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"✅ النجاح: {result['success']}")
                print(f"📝 الرد: {result['message'][:150]}...")
                
                if result.get('agent'):
                    print(f"🤖 الوكيل: {result['agent']}")
            
            else:
                print(f"❌ خطأ: {response.status_code}")
                print(f"   {response.text}")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")


def test_intent_detection_integration():
    """اختبار التكامل مع Intent System"""
    
    print("\n\n" + "=" * 80)
    print("🎯 اختبار التكامل مع Intent System")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/message"
    
    test_cases = [
        "أضف حساب انستقرام",
        "جدول منشور على فيسبوك غداً",
        "احذف آخر تغريدة",
        "أرني متابعيني على تويتر",
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{i}. الرسالة: '{message}'")
        print("-" * 80)
        
        payload = {"message": message, "user_id": 1}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('intent_result'):
                    intent_result = result['intent_result']
                    print(f"🎯 النية: {intent_result.get('intent')}")
                    print(f"📊 الثقة: {intent_result.get('confidence', 0):.2%}")
                    print(f"🌐 المنصة: {intent_result.get('platform', 'غير محددة')}")
                    
                    if intent_result.get('entities'):
                        print(f"📦 الكيانات: {json.dumps(intent_result['entities'], ensure_ascii=False)}")
                
                print(f"🤖 الوكيل: {result.get('agent', 'غير محدد')}")
                print(f"✅ الحالة: {'نجح' if result['success'] else 'فشل'}")
            
            else:
                print(f"❌ خطأ: {response.status_code}")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")


def test_reset_agents():
    """اختبار إعادة تعيين النظام"""
    
    print("\n\n" + "=" * 80)
    print("🔄 اختبار إعادة تعيين نظام الوكلاء")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/reset"
    
    try:
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"⏰ الوقت: {result['timestamp']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 بدء اختبار Agent API\n")
    
    test_health_check()
    test_agent_messages()
    test_intent_detection_integration()
    
    print("\n\n" + "=" * 80)
    print("🎉 اكتملت الاختبارات!")
    print("=" * 80)
    
    print("\n\n📌 معلومات API:")
    print("-" * 80)
    print(f"Base URL: {BASE_URL}")
    print("\nEndpoints:")
    print(f"  1. POST {BASE_URL}/api/agent/message")
    print(f"     Body: {{'message': 'رسالتك هنا', 'user_id': 1}}")
    print(f"\n  2. GET {BASE_URL}/api/agent/health")
    print(f"\n  3. POST {BASE_URL}/api/agent/reset")
    print("=" * 80)
    
    print("\n\n💡 للاستخدام في n8n:")
    print("-" * 80)
    print("1. أضف HTTP Request node")
    print("2. Method: POST")
    print(f"3. URL: {BASE_URL}/api/agent/message")
    print("4. Body: {\"message\": \"={{$json.user_message}}\"}")
    print("5. استخدم {{$json.message}} للحصول على الرد")
    print("=" * 80)
