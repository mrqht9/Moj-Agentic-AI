#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام الذاكرة والمحادثات
Test Memory System
"""

import requests
import json

BASE_URL = "http://localhost:5789"


def test_conversation_with_memory():
    """اختبار المحادثة مع حفظ في الذاكرة"""
    
    print("=" * 80)
    print("💾 اختبار نظام الذاكرة")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/agent/message"
    
    # محادثة متسلسلة
    messages = [
        "مرحباً",
        "أضف حساب تويتر",
        "انشر تغريدة 'اختبار النظام الجديد!'",
        "ما هي المنصات التي أستخدمها؟",
    ]
    
    user_id = 1
    session_id = "test_session_123"
    
    for i, message in enumerate(messages, 1):
        print(f"\n{i}. المستخدم: '{message}'")
        print("-" * 80)
        
        payload = {
            "message": message,
            "user_id": user_id,
            "context": {"session_id": session_id}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"🤖 المساعد: {result['message'][:150]}...")
                
                if result.get('conversation_id'):
                    print(f"💬 معرف المحادثة: {result['conversation_id']}")
                
                if result.get('intent_result'):
                    intent = result['intent_result'].get('intent')
                    confidence = result['intent_result'].get('confidence', 0)
                    print(f"🎯 النية: {intent} (ثقة: {confidence:.2%})")
                
                if result.get('agent'):
                    print(f"🔧 الوكيل: {result['agent']}")
            else:
                print(f"❌ خطأ: {response.status_code}")
        
        except Exception as e:
            print(f"❌ خطأ: {str(e)}")
        
        print()


def test_get_conversations():
    """اختبار الحصول على المحادثات"""
    
    print("\n" + "=" * 80)
    print("📋 اختبار عرض المحادثات")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/conversations/"
    
    try:
        response = requests.get(url, params={"user_id": 1, "limit": 10}, timeout=10)
        
        if response.status_code == 200:
            conversations = response.json()
            
            print(f"\n✅ عدد المحادثات: {len(conversations)}")
            
            for i, conv in enumerate(conversations[:5], 1):
                print(f"\n{i}. {conv['title']}")
                print(f"   📅 تاريخ الإنشاء: {conv['created_at']}")
                print(f"   💬 عدد الرسائل: {conv['message_count']}")
                print(f"   🆔 المعرف: {conv['id']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


def test_get_conversation_detail():
    """اختبار الحصول على تفاصيل محادثة"""
    
    print("\n" + "=" * 80)
    print("🔍 اختبار تفاصيل المحادثة")
    print("=" * 80)
    
    # أولاً، احصل على قائمة المحادثات
    conversations_url = f"{BASE_URL}/api/conversations/"
    
    try:
        response = requests.get(conversations_url, params={"user_id": 1, "limit": 1}, timeout=10)
        
        if response.status_code == 200:
            conversations = response.json()
            
            if conversations:
                conversation_id = conversations[0]['id']
                
                # احصل على تفاصيل المحادثة
                detail_url = f"{BASE_URL}/api/conversations/{conversation_id}"
                detail_response = requests.get(detail_url, timeout=10)
                
                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    
                    print(f"\n📝 المحادثة: {detail['conversation']['title']}")
                    print(f"💬 عدد الرسائل: {len(detail['messages'])}")
                    print("\nالرسائل:")
                    
                    for i, msg in enumerate(detail['messages'], 1):
                        role_ar = "👤 المستخدم" if msg['role'] == "user" else "🤖 المساعد"
                        print(f"\n{i}. {role_ar}:")
                        print(f"   {msg['content'][:100]}...")
                        if msg.get('intent'):
                            print(f"   🎯 النية: {msg['intent']}")
                        if msg.get('agent'):
                            print(f"   🔧 الوكيل: {msg['agent']}")
                else:
                    print(f"❌ خطأ: {detail_response.status_code}")
            else:
                print("⚠️  لا توجد محادثات")
        else:
            print(f"❌ خطأ: {response.status_code}")
    
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


def test_user_preferences():
    """اختبار الحصول على تفضيلات المستخدم"""
    
    print("\n" + "=" * 80)
    print("⚙️  اختبار تفضيلات المستخدم")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/conversations/user/1/preferences"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            preferences = response.json()
            
            print(f"\n✅ إجمالي المحادثات: {preferences['total_conversations']}")
            
            if preferences.get('common_intents'):
                print(f"\n🎯 النوايا الشائعة:")
                for intent in preferences['common_intents']:
                    print(f"   - {intent}")
            
            if preferences.get('preferred_platforms'):
                print(f"\n🌐 المنصات المفضلة:")
                for platform in preferences['preferred_platforms']:
                    print(f"   - {platform}")
            
            if preferences.get('last_interaction'):
                print(f"\n⏰ آخر تفاعل: {preferences['last_interaction']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


def test_conversation_stats():
    """اختبار إحصائيات المحادثات"""
    
    print("\n" + "=" * 80)
    print("📊 اختبار إحصائيات المحادثات")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/conversations/stats/summary"
    
    try:
        response = requests.get(url, params={"user_id": 1}, timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            
            print(f"\n✅ إجمالي المحادثات: {stats['total_conversations']}")
            print(f"✅ إجمالي الرسائل: {stats['total_messages']}")
            
            if stats.get('top_intents'):
                print(f"\n🔝 أكثر النوايا استخداماً:")
                for item in stats['top_intents']:
                    print(f"   - {item['intent']}: {item['count']} مرة")
            
            if stats.get('last_conversation'):
                print(f"\n⏰ آخر محادثة: {stats['last_conversation']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 بدء اختبار نظام الذاكرة\n")
    
    print("⚠️  تأكد من:")
    print("   1. تشغيل الخادم: python app/main.py")
    print("   2. قاعدة البيانات PostgreSQL تعمل")
    print("   3. تم تشغيل migrations\n")
    
    test_conversation_with_memory()
    test_get_conversations()
    test_get_conversation_detail()
    test_user_preferences()
    test_conversation_stats()
    
    print("\n\n" + "=" * 80)
    print("🎉 اكتملت جميع الاختبارات!")
    print("=" * 80)
    
    print("\n\n📌 API Endpoints المتاحة:")
    print("-" * 80)
    print(f"1. GET  {BASE_URL}/api/conversations/")
    print(f"   الحصول على محادثات المستخدم")
    print(f"\n2. GET  {BASE_URL}/api/conversations/{{id}}")
    print(f"   الحصول على تفاصيل محادثة")
    print(f"\n3. GET  {BASE_URL}/api/conversations/user/{{user_id}}/preferences")
    print(f"   الحصول على تفضيلات المستخدم")
    print(f"\n4. GET  {BASE_URL}/api/conversations/stats/summary")
    print(f"   الحصول على إحصائيات المحادثات")
    print(f"\n5. DELETE {BASE_URL}/api/conversations/{{id}}")
    print(f"   حذف محادثة")
    print("=" * 80)
