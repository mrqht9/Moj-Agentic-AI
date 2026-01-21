#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار Intent API للاستخدام في n8n
"""

import requests
import json

# عنوان API
BASE_URL = "http://localhost:5789"

def test_detect_intent():
    """اختبار endpoint التعرف على النية"""
    
    url = f"{BASE_URL}/api/intent/detect"
    
    # أمثلة للاختبار
    test_cases = [
        "أضف حساب تويتر الخاص بي",
        "انشر تغريدة 'مرحباً بالجميع!' على تويتر",
        "جدول منشور على انستقرام غداً الساعة 10 صباحاً",
        "أرني إحصائيات حسابي",
        "اعرض حساباتي",
    ]
    
    print("=" * 80)
    print("🧪 اختبار Intent Detection API")
    print("=" * 80)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. النص: '{text}'")
        print("-" * 80)
        
        payload = {
            "text": text,
            "context": {},
            "user_id": 1
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ النجاح!")
                print(f"   النية: {result['intent']}")
                print(f"   الثقة: {result['confidence']:.2%}")
                if result.get('platform'):
                    print(f"   المنصة: {result['platform']}")
                if result.get('entities'):
                    print(f"   الكيانات: {json.dumps(result['entities'], ensure_ascii=False, indent=6)}")
                if result.get('suggestions'):
                    print(f"   الاقتراحات:")
                    for suggestion in result['suggestions'][:3]:
                        print(f"      - {suggestion}")
            else:
                print(f"❌ خطأ: {response.status_code}")
                print(f"   {response.text}")
        
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {str(e)}")


def test_list_intents():
    """اختبار endpoint قائمة النوايا"""
    
    url = f"{BASE_URL}/api/intent/list"
    
    print("\n\n" + "=" * 80)
    print("📋 قائمة النوايا المدعومة")
    print("=" * 80)
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ عدد النوايا المدعومة: {len(result['intents'])}")
            print(f"✅ المنصات المدعومة: {', '.join(result['platforms'])}")
            
            print("\n📝 النوايا حسب الفئة:")
            
            categories = {}
            for intent in result['intents']:
                category = intent['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(intent)
            
            for category, intents in categories.items():
                print(f"\n   {category.upper()}:")
                for intent in intents:
                    print(f"      - {intent['intent']}: {intent['description']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
    
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")


def test_suggestions():
    """اختبار endpoint الاقتراحات"""
    
    url = f"{BASE_URL}/api/intent/suggestions"
    
    print("\n\n" + "=" * 80)
    print("💡 اختبار الاقتراحات")
    print("=" * 80)
    
    partial_texts = ["أضف", "انشر", "إحصائيات"]
    
    for text in partial_texts:
        print(f"\n📝 نص جزئي: '{text}'")
        
        payload = {"partial_text": text}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   الاقتراحات:")
                for suggestion in result['suggestions'][:3]:
                    print(f"      - {suggestion['intent']}: {suggestion['example']}")
            else:
                print(f"❌ خطأ: {response.status_code}")
        
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {str(e)}")


def test_batch_detection():
    """اختبار endpoint الدفعات"""
    
    url = f"{BASE_URL}/api/intent/batch"
    
    print("\n\n" + "=" * 80)
    print("📦 اختبار Batch Detection")
    print("=" * 80)
    
    batch_requests = [
        {"text": "أضف حساب تويتر", "user_id": 1},
        {"text": "انشر منشور على انستقرام", "user_id": 1},
        {"text": "أرني الإحصائيات", "user_id": 1}
    ]
    
    try:
        response = requests.post(url, json=batch_requests, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            print(f"\n✅ تم معالجة {len(results)} طلب بنجاح!")
            
            for i, result in enumerate(results, 1):
                print(f"\n   {i}. النية: {result['intent']} (ثقة: {result['confidence']:.2%})")
        else:
            print(f"❌ خطأ: {response.status_code}")
    
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 بدء اختبار Intent API\n")
    
    test_detect_intent()
    test_list_intents()
    test_suggestions()
    test_batch_detection()
    
    print("\n\n" + "=" * 80)
    print("🎉 اكتملت جميع الاختبارات!")
    print("=" * 80)
    
    print("\n\n📌 معلومات للاستخدام في n8n:")
    print("-" * 80)
    print(f"Base URL: {BASE_URL}")
    print("\nEndpoints المتاحة:")
    print(f"  1. POST {BASE_URL}/api/intent/detect")
    print(f"     Body: {{'text': 'النص هنا', 'user_id': 1}}")
    print(f"\n  2. GET {BASE_URL}/api/intent/list")
    print(f"\n  3. POST {BASE_URL}/api/intent/suggestions")
    print(f"     Body: {{'partial_text': 'نص جزئي'}}")
    print(f"\n  4. POST {BASE_URL}/api/intent/batch")
    print(f"     Body: [{{'text': 'نص 1'}}, {{'text': 'نص 2'}}]")
    print("=" * 80)
