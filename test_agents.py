#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام الوكلاء الذكية
Test AI Agents System
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.agent_manager import agent_manager


def test_intent_detection():
    """اختبار تحليل النوايا"""
    
    print("=" * 80)
    print("🧪 اختبار تحليل النوايا")
    print("=" * 80)
    
    test_messages = [
        "مرحباً",
        "أضف حساب تويتر",
        "انشر تغريدة 'مرحباً بالجميع!'",
        "ساعدني",
        "أرني إحصائيات حسابي",
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. الرسالة: '{message}'")
        print("-" * 80)
        
        try:
            result = agent_manager.process_user_message(message)
            
            print(f"✅ النجاح: {result['success']}")
            print(f"📝 الرد: {result['message']}")
            
            if result.get('intent_result'):
                intent_result = result['intent_result']
                print(f"🎯 النية: {intent_result.get('intent')}")
                print(f"📊 الثقة: {intent_result.get('confidence', 0):.2%}")
                if intent_result.get('platform'):
                    print(f"🌐 المنصة: {intent_result.get('platform')}")
            
            if result.get('agent'):
                print(f"🤖 الوكيل: {result['agent']}")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")


def test_x_agent_commands():
    """اختبار أوامر وكيل X"""
    
    print("\n\n" + "=" * 80)
    print("🐦 اختبار أوامر وكيل X")
    print("=" * 80)
    
    x_commands = [
        "سجل دخول حساب تويتر باسم test_user",
        "انشر تغريدة 'هذا اختبار للنظام الجديد!'",
        "حدث الملف الشخصي بالاسم 'اسم جديد'",
    ]
    
    for i, command in enumerate(x_commands, 1):
        print(f"\n{i}. الأمر: '{command}'")
        print("-" * 80)
        
        try:
            result = agent_manager.process_user_message(command)
            
            print(f"✅ النجاح: {result['success']}")
            print(f"📝 الرد: {result['message'][:200]}...")
            
            if result.get('agent'):
                print(f"🤖 الوكيل: {result['agent']}")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")


def test_help_and_greetings():
    """اختبار المساعدة والتحيات"""
    
    print("\n\n" + "=" * 80)
    print("💬 اختبار المساعدة والتحيات")
    print("=" * 80)
    
    messages = [
        "مرحباً",
        "السلام عليكم",
        "ساعدني",
        "كيف أستخدم النظام؟",
    ]
    
    for message in messages:
        print(f"\n📝 الرسالة: '{message}'")
        print("-" * 80)
        
        try:
            result = agent_manager.process_user_message(message)
            print(f"✅ الرد:\n{result['message']}\n")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")


def test_api_integration():
    """اختبار التكامل مع API"""
    
    print("\n\n" + "=" * 80)
    print("🔌 اختبار التكامل مع API")
    print("=" * 80)
    
    import requests
    
    base_url = "http://localhost:5789"
    
    print("\n1. فحص صحة نظام الوكلاء...")
    try:
        response = requests.get(f"{base_url}/api/agent/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ النظام يعمل: {response.json()}")
        else:
            print(f"❌ خطأ: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")
        print("⚠️  تأكد من تشغيل الخادم: python app/main.py")
    
    print("\n2. إرسال رسالة للوكيل...")
    try:
        payload = {
            "message": "مرحباً، أريد إضافة حساب تويتر",
            "user_id": 1
        }
        
        response = requests.post(
            f"{base_url}/api/agent/message",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ النجاح!")
            print(f"📝 الرد: {result['message']}")
            print(f"🤖 الوكيل: {result.get('agent')}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 بدء اختبار نظام الوكلاء الذكية\n")
    
    print("⚠️  ملاحظة: تأكد من تعيين OPENAI_API_KEY في ملف .env.agents")
    print("   أو استخدم نموذج محلي (Ollama, LM Studio)\n")
    
    try:
        agent_manager.initialize()
        print("✅ تم تهيئة نظام الوكلاء بنجاح!\n")
    except Exception as e:
        print(f"❌ خطأ في التهيئة: {str(e)}")
        print("   تحقق من إعدادات LLM في .env.agents\n")
        sys.exit(1)
    
    test_intent_detection()
    test_help_and_greetings()
    
    print("\n\n" + "=" * 80)
    print("🎉 اكتملت الاختبارات الأساسية!")
    print("=" * 80)
    
    print("\n\n📌 للاختبار الكامل مع API:")
    print("   1. شغل الخادم: python app/main.py")
    print("   2. شغل اختبار API في نافذة أخرى")
    print("=" * 80)
